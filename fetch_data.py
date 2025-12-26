import os
import sys
import datetime
import argparse
import json
import pandas as pd
import shutil
from dateutil.relativedelta import relativedelta
import requests # For Ollama
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import config
from database import (
    init_db, get_session, engine,
    Channel, ChannelDaily, Video, VideoDaily, Comment,
    DemographicsAge, DemographicsGender, Geography, TrafficSource,
    CompetitorChannel, CompetitorVideo
)
import prediction # Import prediction engine

# --- Constants ---
DATE_FORMAT = "%Y-%m-%d"
# Use host.docker.internal for Mac/Windows Docker, or localhost if running natively
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://host.docker.internal:11434/api/generate")
OLLAMA_MODEL = "llama3.1"

# TODO: Add your competitor channel IDs here
# Example: UC..., UC...
COMPETITOR_CHANNEL_IDS = [
    "UCSJ4gkVC6NrvII8umztf0Ow", # Lofi Girl
    "UC_aEa8K-EOJ3D6gOs7HcyNg", # NoCopyrightSounds
    "UC0FiLCwZZPqaVHUPz72Cr-A", # Chillhop Music
    "UCWzZ5TIGoZ6o-vpMwTuMWog", # College Music
    "UC5nc_ZtjKW1htCVZVRxlQAQ", # MrSuicideSheep
    "UC3ifMxTEKLV40GhD9i07M8g", # Proximity
]

# --- Auth ---
def get_credentials():
    creds = None
    if os.path.exists(config.TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(config.TOKEN_FILE, config.SCOPES)
        except Exception as e:
            print(f"Error loading credentials: {e}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Token expired, refreshing...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing: {e}")
                creds = None
        
        if not creds:
            print("No valid credentials. Starting OAuth...")
            flow = InstalledAppFlow.from_client_secrets_file(
                config.CLIENT_SECRET_FILE, config.SCOPES)
            flow.redirect_uri = 'http://localhost:8080/'
            auth_url, _ = flow.authorization_url(prompt='consent')
            print(f"Please visit: {auth_url}")
            code = input("Enter auth code: ")
            flow.fetch_token(code=code)
            creds = flow.credentials
        
        with open(config.TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return creds

# --- Data Fetching (YouTube Data API) ---

def fetch_channel_info(youtube):
    print("Fetching Channel Info...")
    req = youtube.channels().list(part="snippet,contentDetails,statistics", mine=True)
    res = req.execute()
    if not res['items']: return None
    return res['items'][0]

def fetch_all_videos(youtube, channel_id):
    print("Fetching ALL Videos (Data API)...")
    # 1. Get Uploads Playlist ID
    req = youtube.channels().list(part="contentDetails", id=channel_id)
    res = req.execute()
    if not res['items']: return []
    uploads_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    
    videos = []
    next_page = None
    
    while True:
        pl_req = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_id,
            maxResults=50,
            pageToken=next_page
        )
        pl_res = pl_req.execute()
        
        for item in pl_res['items']:
            snippet = item['snippet']
            videos.append({
                'id': snippet['resourceId']['videoId'],
                'title': snippet['title'],
                'published_at': snippet['publishedAt'],
                'thumbnail': snippet['thumbnails'].get('medium', snippet['thumbnails']['default'])['url']
            })
            
        next_page = pl_res.get('nextPageToken')
        if not next_page: break
        
    print(f"Found {len(videos)} videos.")
    
    # Enrich with Duration (to check Shorts) in batches
    # YouTube Data API allows 50 ids per call
    videos_enriched = []
    chunk_size = 50
    for i in range(0, len(videos), chunk_size):
        chunk = videos[i:i+chunk_size]
        ids = ",".join([v['id'] for v in chunk])
        
        v_req = youtube.videos().list(part="contentDetails", id=ids)
        v_res = v_req.execute()
        
        durations = {item['id']: item['contentDetails']['duration'] for item in v_res['items']}
        
        for v in chunk:
            dur = durations.get(v['id'], "")
            # Simple heuristic: Shorts are usually <= 60s. 
            # Duration format PT1M, PT59S. 
            # We will just store the duration string for now or parse it if strictly needed.
            # Let's simple check: if 'M' is missing or 1M0S, likely short.
            # But accurate parsing is safer. Let's just store the duration string in DB.
            is_short = False 
            if "M" not in dur and "H" not in dur: is_short = True # Less than a minute
            if "PT1M0S" == dur: is_short = True
            
            v['duration'] = dur
            v['is_shorts'] = is_short
            videos_enriched.append(v)
            
    return videos_enriched

# --- Analytics API Wrappers ---

def robust_analytics_query(analytics, **kwargs):
    """Wrapper to handle retries or missing metrics (e.g. revenue) gracefully."""
    try:
        return analytics.reports().query(**kwargs).execute()
    except Exception as e:
        metrics = kwargs.get('metrics', "")
        print(f"Query Error for metrics='{metrics}': {e}")
        
        # Check for permission/401 related to revenue
        if "revenue" in metrics.lower():
            print("Attempting retry without revenue metrics...")
            new_metrics = metrics.replace("estimatedRevenue", "").replace(",,", ",").strip(",")
            if new_metrics.startswith(","): new_metrics = new_metrics[1:]
            if new_metrics.endswith(","): new_metrics = new_metrics[:-1]
            
            kwargs['metrics'] = new_metrics
            try:
                return analytics.reports().query(**kwargs).execute()
            except Exception as e2:
                print(f"Retry failed: {e2}")
                return {'rows': [], 'columnHeaders': []}
        else:
            print(f"Analytics Query Failed (Non-Revenue): {e}")
            return {'rows': [], 'columnHeaders': []}

# --- Upsert Logic ---

def upsert_channel_stats(session, channel, daily_res):
    if not daily_res.get('rows'): return
    headers = [h['name'] for h in daily_res.get('columnHeaders')]
    
    for row in daily_res.get('rows'):
        data = dict(zip(headers, row))
        date_obj = datetime.datetime.strptime(data['day'], DATE_FORMAT).date()
        
        stat = session.query(ChannelDaily).filter_by(channel_id=channel.id, date=date_obj).first()
        if not stat:
            stat = ChannelDaily(channel_id=channel.id, date=date_obj)
            session.add(stat)
        
        stat.views = int(data.get('views', 0))
        stat.estimated_revenue = float(data.get('estimatedRevenue', 0.0))
        stat.watch_time_minutes = float(data.get('estimatedMinutesWatched', 0))
        stat.subscribers_gained = int(data.get('subscribersGained', 0))
        stat.likes = int(data.get('likes', 0))
        stat.dislikes = int(data.get('dislikes', 0))
        stat.comments = int(data.get('comments', 0))
        stat.shares = int(data.get('shares', 0))
        stat.avg_view_duration_seconds = float(data.get('averageViewDuration', 0.0))

def upsert_videos(session, channel_id, video_list):
    for v in video_list:
        db_vid = session.query(Video).filter_by(id=v['id']).first()
        if not db_vid:
            db_vid = Video(id=v['id'], channel_id=channel_id)
            session.add(db_vid)
        
        db_vid.title = v['title']
        db_vid.thumbnail_url = v['thumbnail']
        try:
            pub_dt = datetime.datetime.strptime(v['published_at'], "%Y-%m-%dT%H:%M:%SZ")
            db_vid.published_at = pub_dt
        except:
            pass
            
        db_vid.video_length = v.get('duration', '')
        db_vid.is_shorts = v.get('is_shorts', False)

def upsert_video_daily(session, video_id, daily_res):
    if not daily_res.get('rows'): return
    headers = [h['name'] for h in daily_res.get('columnHeaders')]
    
    for row in daily_res.get('rows'):
        data = dict(zip(headers, row))
        date_obj = datetime.datetime.strptime(data['day'], DATE_FORMAT).date()
        
        stat = session.query(VideoDaily).filter_by(video_id=video_id, date=date_obj).first()
        if not stat:
            stat = VideoDaily(video_id=video_id, date=date_obj)
            session.add(stat)
        
        stat.views = int(data.get('views', 0))
        stat.estimated_revenue = float(data.get('estimatedRevenue', 0.0))
        stat.watch_time_minutes = float(data.get('estimatedMinutesWatched', 0))
        stat.subscribers_gained = int(data.get('subscribersGained', 0))
        stat.likes = int(data.get('likes', 0))
        stat.dislikes = int(data.get('dislikes', 0))
        stat.comments = int(data.get('comments', 0))
        stat.shares = int(data.get('shares', 0))

def fetch_channel_daily(analytics, start, end):
    print(f"Fetching Channel Daily Stats ({start} to {end})...")
    metrics = "views,estimatedRevenue,estimatedMinutesWatched,subscribersGained,likes,dislikes,comments,shares,averageViewDuration"
    return robust_analytics_query(
        analytics,
        ids="channel==MINE",
        startDate=start,
        endDate=end,
        metrics=metrics,
        dimensions="day",
        sort="day"
    )

def fetch_video_daily(analytics, video_id, start, end):
    # print(f"Fetching Daily for Video {video_id}...")
    metrics = "views,estimatedRevenue,estimatedMinutesWatched,subscribersGained,likes,dislikes,comments,shares"
    return robust_analytics_query(
        analytics,
        ids="channel==MINE",
        startDate=start,
        endDate=end,
        filters=f"video=={video_id}",
        metrics=metrics,
        dimensions="day",
        sort="day"
    )

def fetch_demographics_daily(analytics, start, end, dimension):
    print(f"Fetching Demographics ({dimension}) Aggregate ({start} to {end})...")
    # API Limitation: 'ageGroup' and 'gender' only support 'viewerPercentage' for channel owner reports.
    # 'country' supports 'views'.
    metrics = "views,estimatedMinutesWatched"
    sort = "-views"
    
    if dimension in ["ageGroup", "gender"]:
        metrics = "viewerPercentage"
        sort = "-viewerPercentage"
        
    return robust_analytics_query(
        analytics,
        ids="channel==MINE",
        startDate=start,
        endDate=end,
        metrics=metrics,
        dimensions=f"{dimension}",
        sort=sort
    )

def fetch_traffic_daily(analytics, start, end):
    print("Fetching Traffic Sources Daily...")
    return robust_analytics_query(
        analytics,
        ids="channel==MINE",
        startDate=start,
        endDate=end,
        metrics="views,estimatedMinutesWatched",
        dimensions="day,insightTrafficSourceType",
        sort="day"
    )

# --- Upsert Logic ---

def upsert_demographics_age(session, res, date_obj):
    if not res.get('rows'): return
    headers = [h['name'] for h in res.get('columnHeaders')]
    
    for row in res.get('rows'):
        data = dict(zip(headers, row)) 
        group = data['ageGroup']
        
        rec = session.query(DemographicsAge).filter_by(date=date_obj, age_group=group).first()
        if not rec:
            rec = DemographicsAge(date=date_obj, age_group=group)
            session.add(rec)
            
        rec.viewer_percentage = float(data.get('viewerPercentage', 0.0))
        rec.views = int(data.get('views', 0))
        rec.watch_time_minutes = float(data.get('estimatedMinutesWatched', 0))

def upsert_demographics_gender(session, res, date_obj):
    if not res.get('rows'): return
    headers = [h['name'] for h in res.get('columnHeaders')]
    
    for row in res.get('rows'):
        data = dict(zip(headers, row))
        gender = data['gender']
        
        rec = session.query(DemographicsGender).filter_by(date=date_obj, gender=gender).first()
        if not rec:
            rec = DemographicsGender(date=date_obj, gender=gender)
            session.add(rec)
        
        rec.viewer_percentage = float(data.get('viewerPercentage', 0.0))
        rec.views = int(data.get('views', 0))
        rec.watch_time_minutes = float(data.get('estimatedMinutesWatched', 0))

def upsert_geography(session, res, date_obj):
    if not res.get('rows'): return
    headers = [h['name'] for h in res.get('columnHeaders')]
    
    for row in res.get('rows'):
        data = dict(zip(headers, row))
        code = data['country']
        
        rec = session.query(Geography).filter_by(date=date_obj, country_code=code).first()
        if not rec:
            rec = Geography(date=date_obj, country_code=code)
            session.add(rec)
        
        rec.views = int(data.get('views', 0))
        rec.watch_time_minutes = float(data.get('estimatedMinutesWatched', 0))

def upsert_traffic(session, res):
    if not res.get('rows'): return
    headers = [h['name'] for h in res.get('columnHeaders')]
    
    for row in res.get('rows'):
        data = dict(zip(headers, row))
        date_obj = datetime.datetime.strptime(data['day'], DATE_FORMAT).date()
        src = data['insightTrafficSourceType']
        
        rec = session.query(TrafficSource).filter_by(date=date_obj, source_type=src).first()
        if not rec:
            rec = TrafficSource(date=date_obj, source_type=src)
            session.add(rec)
        
        rec.views = int(data.get('views', 0))
        rec.watch_time_minutes = float(data.get('estimatedMinutesWatched', 0))


# --- Competitor & AI Logic ---

def fetch_competitors(youtube, session):
    if not COMPETITOR_CHANNEL_IDS:
        print("No competitor IDs configured. Skipping competitor fetch.")
        return

    print("Fetching Competitor Data...")
    ids_str = ",".join(COMPETITOR_CHANNEL_IDS)
    
    # 1. Channel Stats
    req = youtube.channels().list(
        part="snippet,statistics,contentDetails",
        id=ids_str
    )
    res = req.execute()
    
    for item in res.get('items', []):
        cid = item['id']
        snippet = item['snippet']
        stats = item['statistics']
        
        comp = session.query(CompetitorChannel).get(cid)
        if not comp:
            comp = CompetitorChannel(channel_id=cid, channel_name=snippet['title'])
            session.add(comp)
            
        comp.channel_name = snippet['title']
        comp.custom_url = snippet.get('customUrl')
        comp.thumbnail_url = snippet['thumbnails']['default']['url']
        comp.subscribers = int(stats.get('subscriberCount', 0))
        comp.total_views = int(stats.get('viewCount', 0))
        comp.video_count = int(stats.get('videoCount', 0))
        comp.last_fetched = datetime.datetime.utcnow()
        
        # 2. Recent Videos (Last 3)
        uploads_id = item['contentDetails']['relatedPlaylists']['uploads']
        
        pl_req = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_id,
            maxResults=3
        )
        try:
            pl_res = pl_req.execute()
            video_ids = []
            video_snippets = {}
            for v_item in pl_res.get('items', []):
                vid = v_item['snippet']['resourceId']['videoId']
                video_ids.append(vid)
                video_snippets[vid] = v_item['snippet']
            
            # Fetch Video Stats
            if video_ids:
                v_stats_req = youtube.videos().list(
                    part="statistics",
                    id=",".join(video_ids)
                )
                v_stats_res = v_stats_req.execute()
                
                for v_item in v_stats_res.get('items', []):
                    vid = v_item['id']
                    stats = v_item['statistics']
                    snippet = video_snippets.get(vid)
                    
                    cv = session.query(CompetitorVideo).get(vid)
                    if not cv:
                        cv = CompetitorVideo(video_id=vid, channel_id=cid)
                        session.add(cv)
                    
                    if snippet:
                        cv.title = snippet['title']
                        cv.published_at = datetime.datetime.strptime(snippet['publishedAt'], "%Y-%m-%dT%H:%M:%SZ")
                    
                    cv.view_count = int(stats.get('viewCount', 0))
                    cv.like_count = int(stats.get('likeCount', 0))
                    cv.comment_count = int(stats.get('commentCount', 0))
                    cv.last_fetched = datetime.datetime.utcnow()
                    
        except Exception as e:
            print(f"Error fetching videos for {comp.channel_name}: {e}")

    session.commit()

def analyze_with_ollama(session, my_channel_id):
    print("Running AI Analysis (Ollama)...")
    
    # Gather Data
    channel = session.query(Channel).get(my_channel_id)
    my_name = channel.name if channel else "My Channel"
    
    # --- Intergrate Prediction Engine ---
    print("Generating Fresh Predictions (XGBoost/MA/WMA)...")
    try:
        prediction.generate_predictions() # This updates dashboard/public/prediction_data.json
    except Exception as e:
        print(f"Prediction Generation Failed: {e}")
        
    # Read Prediction Data
    pred_summary = "No prediction data available."
    try:
        with open('dashboard/public/prediction_data.json', 'r') as f:
            p_data = json.load(f)
            # Extract XGBoost for Views
            xgb_views = p_data.get('predictions', {}).get('xgboost', {}).get('view_count', [])
            if xgb_views:
                first_val = xgb_views[0]
                last_val = xgb_views[-1]
                growth_pct = ((last_val - first_val) / first_val * 100) if first_val > 0 else 0
                pred_summary = f"XGBoost Forecast (30 Days): Views from {first_val} to {last_val} ({growth_pct:.1f}% Growth)."
    except Exception as e:
        print(f"Failed to read prediction data: {e}")
    # ------------------------------------
    
    # Last 30 days stats
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=30)
    
    my_stats = session.query(ChannelDaily).filter(
        ChannelDaily.channel_id == my_channel_id,
        ChannelDaily.date >= start_date
    ).all()
    
    if not my_stats: 
        print("Not enough data for AI analysis.")
        return None
    
    my_views_30d = sum(s.views for s in my_stats)
    my_subs_30d = sum(s.subscribers_gained for s in my_stats)
    my_avg_views = int(my_views_30d / len(my_stats)) if my_stats else 0
    
    competitors = session.query(CompetitorChannel).all()
    comp_context = []
    for c in competitors:
        comp_context.append(f"- {c.channel_name}: {c.subscribers} Subs, {c.total_views} Total Views")
        
    comp_text = "\\n".join(comp_context) if comp_context else "No competitor data available."
    
    # Improved Prompt
    prompt = f"""
    Role: Professional YouTube Growth Strategist & Data Analyst.
    Task: specific analysis based on "future growth predictions" and current data.
    
    Target Channel: "{my_name}"
    - Performance (Last 30 Days): {my_views_30d} Views, {my_subs_30d} New Subs.
    - Future Forecast (XGBoost): {pred_summary}
    
    Competitors/Market Context:
    {comp_text}
    
    Output Requirement:
    Return a single valid JSON object with exactly these keys:
    "current_analysis": {{ "strengths": {{ "title": "...", "content": "..." }}, "improvements": {{ "title": "...", "content": "..." }}, "action_plan": {{ "title": "...", "content": "..." }}, "detailed_report": "markdown..." }},
    "future_strategy": {{ "growth_trend": {{ "title": "...", "content": "..." }}, "risk_factor": {{ "title": "...", "content": "..." }}, "action_strategy": {{ "title": "...", "content": "..." }}, "detailed_report": "markdown..." }}
    
    SECTION 1: "current_analysis" (Based on PAST 30 days data only)
    - "strengths": What went well? (Views, Subs)
    - "improvements": What needs sizing up?
    - "action_plan": Immediate authorized actions.
    - "detailed_report": Markdown report focusing on PAST performance.
    
    SECTION 2: "future_strategy" (Based on XGBOOST PREDICTION only)
    - Prediction Context: {pred_summary}
    - "growth_trend": Analyze the prediction (growth rate, direction).
    - "risk_factor": Identify future risks based on prediction.
    - "action_strategy": Future-oriented strategy.
    - "detailed_report": Markdown report focusing on FUTURE predictions (3 Sections: Growth/Risk/Strategy).
    
    Language: Korean (한국어).
    
    JSON Example:
    {{
      "current_analysis": {{
        "strengths": {{ "title": "...", "content": "..." }},
        "improvements": {{ "title": "...", "content": "..." }},
        "action_plan": {{ "title": "...", "content": "..." }},
        "detailed_report": "..."
      }},
      "future_strategy": {{
        "growth_trend": {{ "title": "...", "content": "..." }},
        "risk_factor": {{ "title": "...", "content": "..." }},
        "action_strategy": {{ "title": "...", "content": "..." }},
        "detailed_report": "..."
      }}
    }}
    """
    
    try:
        response = requests.post(OLLAMA_API_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }, timeout=300) # 300s timeout for slower CPUs
        
        if response.status_code == 200:
            res_json = response.json()
            raw_text = res_json.get('response', '{}')
            # Parse the inner JSON string if necessary, Ollama 'json' format usually returns a JSON object in 'response' BUT sometimes it's text.
            # With "format": "json", it tries to enforce structure.
            try:
                return json.loads(raw_text)
            except:
                print("Failed to parse AI JSON response.")
                return None
        else:
            print(f"Ollama Error ({response.status_code}): {response.text}")
            return None
    except Exception as e:
        print(f"AI Analysis Connection Failed (Is Ollama running?): {e}")
        return None

# --- JSON Generator (Frontend Compat) ---

def generate_frontend_json(session, channel_id):
    print("Generating dashboard_data.json from Relational DB...")
    
    # 1. Summary (Last 30 days)
    # We can query ChannelDaily for the last 30 entries
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=30)
    
    channel = session.query(Channel).filter_by(id=channel_id).first()
    stats_30d = session.query(ChannelDaily).filter(
        ChannelDaily.channel_id == channel_id,
        ChannelDaily.date >= start_date
    ).all()
    
    total_views = sum(s.views for s in stats_30d)
    total_rev = sum(s.estimated_revenue for s in stats_30d)
    total_subs = sum(s.subscribers_gained for s in stats_30d)
    total_wt = sum(s.watch_time_minutes for s in stats_30d) / 60
    total_likes = sum(s.likes for s in stats_30d)
    
    summary = {
        "channel_name": channel.name if channel else "Unknown",
        "profile_image": channel.profile_image if channel else "",
        "total_views_30d": total_views,
        "estimated_revenue_30d": round(total_rev, 2),
        "subs_gained_30d": total_subs,
        "total_watch_time_hours_30d": int(total_wt),
        "likes_30d": total_likes,
        "avg_engagement_rate_30d": 0.0, # Placeholder
        "last_updated": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S")[0:19]
    }
    
    # 2. Trends (Daily/Weekly/Monthly)
    # Fetch ALL history for trends
    all_stats = session.query(ChannelDaily).filter_by(channel_id=channel_id).order_by(ChannelDaily.date).all()
    
    df = pd.DataFrame([{
        'dates': s.date.strftime(DATE_FORMAT),
        'views': s.views,
        'revenue': s.estimated_revenue,
        'subscribers': s.subscribers_gained,
        'likes': s.likes,
        'comments': s.comments,
        'averageViewDuration': s.avg_view_duration_seconds,
        'estimatedMinutesWatched': s.watch_time_minutes
    } for s in all_stats])
    
    if df.empty:
        trend_data = {"daily": {}, "weekly": {}, "monthly": {}}
    else:
        df['dt'] = pd.to_datetime(df['dates'])
        
        # Resample logic
        def resample_df(frame, freq):
            r = frame.set_index('dt').resample(freq).sum().reset_index()
            r['dates'] = r['dt'].dt.strftime(DATE_FORMAT)
            return r.drop(columns=['dt'])
            
        daily = df.drop(columns=['dt'])
        weekly = resample_df(df, 'W-MON')
        monthly = resample_df(df, 'ME')
        
        trend_data = {
            "daily": daily.to_dict(orient='list'),
            "weekly": weekly.to_dict(orient='list'),
            "monthly": monthly.to_dict(orient='list')
        }
        
    # 3. Top Videos (Aggregated from VideoDaily or from Video metadata + Snapshot?)
    # Since we store daily history, we should Query sum of last 30 days per video
    # Optimization: Query VideoDaily joined with Video
    from sqlalchemy import func
    
    top_v_query = session.query(
        VideoDaily.video_id,
        func.sum(VideoDaily.views).label('total_views'),
        func.sum(VideoDaily.likes).label('total_likes'),
        func.sum(VideoDaily.comments).label('total_comments'),
        func.sum(VideoDaily.shares).label('total_shares'),
        func.sum(VideoDaily.estimated_revenue).label('total_rev')
    ).filter(
        VideoDaily.date >= start_date
    ).group_by(VideoDaily.video_id).order_by(func.sum(VideoDaily.views).desc()).limit(10).all()
    
    top_videos_list = []
    for row in top_v_query:
        vid = session.query(Video).get(row.video_id)
        top_videos_list.append({
            "video": row.video_id,
            "title": vid.title if vid else row.video_id,
            "thumbnail": vid.thumbnail_url if vid else "",
            "views": row.total_views,
            "likes": row.total_likes,
            "comments": row.total_comments,
            "shares": row.total_shares,
            "estimatedRevenue": round(row.total_rev, 2)
        })

    # 4. Demographics
    # Aggregate Age
    age_query = session.query(
        DemographicsAge.age_group,
        func.sum(DemographicsAge.views).label('total_views')
    ).filter(DemographicsAge.date >= start_date).group_by(DemographicsAge.age_group).all()
    
    # Calculate %
    total_age_views = sum(x.total_views for x in age_query) or 1
    age_rows = [[x.age_group, "All", x.total_views/total_age_views*100] for x in age_query] # Approximation
    
    # Geography
    geo_query = session.query(
        Geography.country_code,
        func.sum(Geography.views).label('v'),
        func.sum(Geography.watch_time_minutes).label('wt')
    ).group_by(Geography.country_code).order_by(func.sum(Geography.views).desc()).limit(10).all()
    
    geo_rows = [[x.country_code, x.v, x.wt] for x in geo_query]
    
    demographics = {
        "age_gender": {"headers": ["ageGroup", "gender", "viewerPercentage"], "rows": age_rows},
        "geography": {"headers": ["country", "views", "estimatedMinutesWatched"], "rows": geo_rows}
    }
    
    # 5. Traffic
    traf_query = session.query(
        TrafficSource.source_type,
        func.sum(TrafficSource.views).label('v'),
        func.sum(TrafficSource.watch_time_minutes).label('wt')
    ).filter(TrafficSource.date >= start_date).group_by(TrafficSource.source_type).order_by(func.sum(TrafficSource.views).desc()).all()
    
    traffic_out = [{"insightTrafficSourceType": x.source_type, "views": x.v, "estimatedMinutesWatched": x.wt} for x in traf_query]

    # 6. AI Insights
    ai_insights = analyze_with_ollama(session, channel_id)
    if not ai_insights:
        # Fallback/Default
        ai_insights = {
            "current_analysis": {
                "strengths": {"title": "데이터 분석 중", "content": "현재 성과를 분석하고 있습니다."},
                "improvements": {"title": "개선점 파악", "content": "데이터 부족으로 분석이 지연되고 있습니다."},
                "action_plan": {"title": "행동 계획", "content": "잠시 후 다시 시도해주세요."},
                "detailed_report": "# 분석 중..."
            },
            "future_strategy": {
                "growth_trend": {"title": "예측 로딩 중", "content": "XGBoost 엔진이 가동 중입니다."},
                "risk_factor": {"title": "리스크 탐지", "content": "미래 데이터를 계산하고 있습니다."},
                "action_strategy": {"title": "전략 수립", "content": "잠시만 기다려주세요."},
                "detailed_report": "# 예측 중..."
            }
        }

    # Final Output
    final_json = {
        "summary": summary,
        "trends": trend_data,
        "prediction": {"dates": [], "views": []}, 
        "ai_insights": ai_insights,
        "top_videos": top_videos_list,
        "demographics": demographics,
        "traffic_sources": traffic_out
    }
    
    with open(config.DASHBOARD_DATA_FILE, 'w') as f:
        json.dump(final_json, f, indent=4)
        
    # Copy to public
    public_path = config.BASE_DIR / "dashboard" / "public" / "dashboard_data.json"
    public_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(config.DASHBOARD_DATA_FILE, public_path)
    print("Dashboard JSON Generated & Synced.")
    

# --- Main Logic ---

def main():
    parser = argparse.ArgumentParser(description="YouTube Data Fetcher & Sync")
    parser.add_argument("--init", action="store_true", help="Run 3-Year Historical Backfill")
    args = parser.parse_args()
    
    init_db()
    session = get_session()
    
    creds = get_credentials()
    if not creds: return
    
    youtube = build("youtube", "v3", credentials=creds)
    analytics = build("youtubeAnalytics", "v2", credentials=creds)
    
    # 1. Channel Info
    c_info = fetch_channel_info(youtube)
    if not c_info:
        print("Channel Not Found.")
        return
        
    cid = c_info['id']
    # Upsert Channel
    ch = session.query(Channel).filter_by(id=cid).first()
    if not ch:
        ch = Channel(id=cid, name="Loading...")
        session.add(ch)
    
    ch.name = c_info['snippet']['title']
    ch.profil_image = c_info['snippet']['thumbnails']['default']['url']
    ch.last_updated = datetime.datetime.utcnow()
    session.commit()

    # 1.5 Fetch Competitors
    fetch_competitors(youtube, session)
    
    # 2. Scope Determination
    today = datetime.date.today()
    if args.init:
        print("!!! INITIALIZATION MODE: Fetching 3 Years of History !!!")
        start_date = (today - relativedelta(years=3)).strftime(DATE_FORMAT)
    else:
        print("--- SYNC MODE: Fetching 30 Days ---")
        start_date = (today - datetime.timedelta(days=30)).strftime(DATE_FORMAT)
        
    end_date = (today - datetime.timedelta(days=3)).strftime(DATE_FORMAT) # T-3 safety
    
    # 3. Channel Daily Stats
    res = fetch_channel_daily(analytics, start_date, end_date)
    upsert_channel_stats(session, ch, res)
    session.commit()
    
    # 4. Videos List
    videos = fetch_all_videos(youtube, cid)
    upsert_videos(session, cid, videos)
    session.commit()
    
    # 5. Video Daily Stats (Iterate)
    print(f"Syncing daily stats for {len(videos)} videos...")
    for i, v in enumerate(videos):
        if i % 10 == 0: print(f"Processing {i}/{len(videos)}: {v['title'][:20]}...")
        v_res = fetch_video_daily(analytics, v['id'], start_date, end_date)
        upsert_video_daily(session, v['id'], v_res)
        if i % 20 == 0: session.commit()
    session.commit()
    
    # 6. Demographics & Traffic
    snapshot_date = datetime.datetime.strptime(end_date, DATE_FORMAT).date()
    
    # Age
    upsert_demographics_age(session, fetch_demographics_daily(analytics, start_date, end_date, "ageGroup"), snapshot_date)
    # Gender
    upsert_demographics_gender(session, fetch_demographics_daily(analytics, start_date, end_date, "gender"), snapshot_date)
    # Country
    upsert_geography(session, fetch_demographics_daily(analytics, start_date, end_date, "country"), snapshot_date)
    
    # Traffic
    upsert_traffic(session, fetch_traffic_daily(analytics, start_date, end_date))
    session.commit()
    
    print("Data Sync Complete.")
    
    # 7. Generate JSON
    generate_frontend_json(session, cid)

if __name__ == "__main__":
    main()
