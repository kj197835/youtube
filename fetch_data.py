import os
import datetime
import pandas as pd
import json
import numpy as np
from datetime import timedelta, timezone
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from sklearn.linear_model import LinearRegression

import config
from database import init_db, get_session, Channel, DailyStat, Video, VideoStat

# --- Auth & API Functions ---

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
                print(f"Error refreshing token: {e}")
                creds = None
        
        if not creds:
            print("No valid credentials found. Starting OAuth flow...")
            flow = InstalledAppFlow.from_client_secrets_file(
                config.CLIENT_SECRET_FILE, config.SCOPES)
            flow.redirect_uri = 'http://localhost:8080/'
            auth_url, _ = flow.authorization_url(prompt='consent')
            print(f"Please visit: {auth_url}")
            code = input("Enter the authorization code: ")
            flow.fetch_token(code=code)
            creds = flow.credentials
        
        with open(config.TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            
    return creds

def fetch_channel_stats(youtube):
    print("Fetching channel statistics...")
    request = youtube.channels().list(part="statistics,snippet", mine=True)
    response = request.execute()
    
    if "items" in response and len(response["items"]) > 0:
        item = response["items"][0]
        stats = item["statistics"]
        snippet = item["snippet"]
        return {
            "channel_id": item["id"],
            "channel_name": snippet["title"],
            "profile_image": snippet["thumbnails"]["default"]["url"],
            "subscribers": int(stats["subscriberCount"]),
            "total_views": int(stats["viewCount"]),
            "video_count": int(stats["videoCount"])
        }
    return None

def fetch_analytics(analytics):
    print("Fetching analytics data (since 2024-01-01)...")
    end_date = (datetime.date.today() - datetime.timedelta(days=3)).strftime("%Y-%m-%d")
    start_date = "2024-01-01"
    
    metrics_list = "views,estimatedMinutesWatched,estimatedRevenue,subscribersGained,likes,dislikes,comments,shares,averageViewDuration"
    
    try:
        request = analytics.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics=metrics_list,
            dimensions="day",
            sort="day"
        )
        response = request.execute()
    except Exception as e:
        print(f"First attempt failed (maybe revenue?), retrying: {e}")
        metrics_list = "views,estimatedMinutesWatched,subscribersGained,likes,dislikes,comments,shares,averageViewDuration"
        request = analytics.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics=metrics_list,
            dimensions="day",
            sort="day"
        )
        response = request.execute()
    
    headers = [header["name"] for header in response.get("columnHeaders", [])]
    rows = response.get("rows", [])
    df = pd.DataFrame(rows, columns=headers)
    if 'estimatedRevenue' not in df.columns:
        df['estimatedRevenue'] = 0.0
        
    return df

def fetch_top_videos(analytics, youtube):
    print("Fetching top videos...")
    end_date = (datetime.date.today() - datetime.timedelta(days=3)).strftime("%Y-%m-%d")
    start_date = "2024-01-01" # Capture year to date
    
    metrics_list = "views,estimatedMinutesWatched,estimatedRevenue,subscribersGained,likes,dislikes,comments,shares"
    try:
        request = analytics.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics=metrics_list,
            dimensions="video",
            sort="-views",
            maxResults=20
        )
        response = request.execute()
    except:
        metrics_list = "views,estimatedMinutesWatched,subscribersGained,likes,dislikes,comments,shares"
        request = analytics.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics=metrics_list,
            dimensions="video",
            sort="-views",
            maxResults=20
        )
        response = request.execute()

    headers = [header["name"] for header in response.get("columnHeaders", [])]
    rows = response.get("rows", [])
    df = pd.DataFrame(rows, columns=headers)
    
    # Check for empty result
    if df.empty:
        return df

    # Enrich with Title/Thumbnail
    video_ids = df['video'].tolist()
    video_ids = [v for v in video_ids if v and v != "0"]
    
    id_to_meta = {}
    if video_ids:
        try:
            vid_request = youtube.videos().list(part="snippet", id=",".join(video_ids))
            vid_response = vid_request.execute()
            
            for item in vid_response.get("items", []):
                vid = item["id"]
                snip = item["snippet"]
                id_to_meta[vid] = {
                    "title": snip["title"],
                    "thumbnail": snip["thumbnails"].get("medium", snip["thumbnails"]["default"])["url"]
                }
                
                # Download thumbnail logic (simplified for brevity, can reinstate full logic if needed)
                # For now we use the URL or implement download separately
                # Keeping it simple: Use remote URL or local if already exists
                thumb_filename = f"{vid}.jpg"
                local_thumb = os.path.join("dashboard", "public", "thumbnails", thumb_filename)
                
                if not os.path.exists(local_thumb):
                    os.makedirs(os.path.dirname(local_thumb), exist_ok=True)
                    try:
                        import urllib.request
                        urllib.request.urlretrieve(id_to_meta[vid]["thumbnail"], local_thumb)
                        id_to_meta[vid]["thumbnail"] = f"thumbnails/{thumb_filename}"
                    except:
                        pass # Keep remote URL
                else:
                    id_to_meta[vid]["thumbnail"] = f"thumbnails/{thumb_filename}"

        except Exception as e:
            print(f"Error fetching video details: {e}")
            
    df['title'] = df['video'].map(lambda x: id_to_meta.get(x, {}).get("title", f"Video {x}"))
    df['thumbnail'] = df['video'].map(lambda x: id_to_meta.get(x, {}).get("thumbnail", ""))
    
    if 'estimatedRevenue' not in df.columns:
        df['estimatedRevenue'] = 0.0
    return df

def fetch_demographics(analytics):
    print("Fetching demographics...")
    end = datetime.date.today().strftime("%Y-%m-%d")
    start = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    
    data = {}
    try:
        req = analytics.reports().query(ids="channel==MINE", startDate=start, endDate=end, metrics="viewerPercentage", dimensions="ageGroup,gender", sort="ageGroup,gender")
        res = req.execute()
        data['age_gender'] = {'headers': [h['name'] for h in res.get('columnHeaders',[])], 'rows': res.get('rows',[])}
        
        req2 = analytics.reports().query(ids="channel==MINE", startDate=start, endDate=end, metrics="views,estimatedMinutesWatched", dimensions="country", sort="-views", maxResults=15)
        res2 = req2.execute()
        data['geography'] = {'headers': [h['name'] for h in res2.get('columnHeaders',[])], 'rows': res2.get('rows',[])}
    except Exception as e:
        print(f"Demographics error: {e}")
    return data

def fetch_traffic_sources(analytics):
    print("Fetching traffic sources...")
    end = (datetime.date.today() - datetime.timedelta(days=3)).strftime("%Y-%m-%d")
    start = "2024-01-01"
    try:
        req = analytics.reports().query(ids="channel==MINE", startDate=start, endDate=end, metrics="views,estimatedMinutesWatched", dimensions="insightTrafficSourceType", sort="-views")
        res = req.execute()
        headers = [h['name'] for h in res.get('columnHeaders',[])]
        return pd.DataFrame(res.get('rows',[]), columns=headers)
    except:
        return pd.DataFrame()

# --- Database Functions ---

def save_to_db(channel_info, analytics_df, top_videos_df):
    print("Saving data to database...")
    session = get_session()
    
    # 1. Update Channel
    cid = channel_info['channel_id']
    channel = session.query(Channel).filter_by(id=cid).first()
    if not channel:
        channel = Channel(id=cid)
        session.add(channel)
    
    channel.name = channel_info['channel_name']
    channel.profile_image = channel_info['profile_image']
    channel.last_updated = datetime.datetime.utcnow()
    
    # 2. Update Daily Stats
    # analytics_df has ['day', 'views', ...]
    for _, row in analytics_df.iterrows():
        try:
            d = datetime.datetime.strptime(row['day'], "%Y-%m-%d").date()
            stat = session.query(DailyStat).filter_by(channel_id=cid, date=d).first()
            if not stat:
                stat = DailyStat(channel_id=cid, date=d)
                session.add(stat)
            
            stat.views = int(row.get('views', 0))
            stat.subscribers = int(row.get('subscribersGained', 0))
            stat.revenue = float(row.get('estimatedRevenue', 0.0))
            stat.watch_time_hours = float(row.get('estimatedMinutesWatched', 0)) / 60.0
            stat.avg_engagement_rate = 0.0 # Calculate if needed
        except Exception as e:
            print(f"Error saving daily stat: {e}")
            
    # 3. Update Video Stats
    today = datetime.datetime.utcnow().date()
    for _, row in top_videos_df.iterrows():
        vid = row['video']
        if not vid or vid == "0": continue
        
        video = session.query(Video).filter_by(id=vid).first()
        if not video:
            video = Video(id=vid, channel_id=cid)
            session.add(video)
        
        video.title = row.get('title', 'Unknown')
        video.thumbnail_url = row.get('thumbnail', '')
        
        # Save Snapshot
        vstat = session.query(VideoStat).filter_by(video_id=vid, date=today).first()
        if not vstat:
            vstat = VideoStat(video_id=vid, date=today)
            session.add(vstat)
            
        vstat.views = int(row.get('views', 0))
        vstat.likes = int(row.get('likes', 0))
        vstat.dislikes = int(row.get('dislikes', 0))
        vstat.comments = int(row.get('comments', 0))
        vstat.revenue = float(row.get('estimatedRevenue', 0.0))
        
    session.commit()
    return cid

# --- Analysis & Output Functions ---

def get_kst_now():
    return datetime.datetime.now(timezone.utc) + timedelta(hours=9)

def aggregate_data(df, freq):
    if df.empty: return df
    df = df.copy()
    df['day'] = pd.to_datetime(df['day'])
    agg = df.set_index('day').resample(freq).sum().reset_index()
    agg['day'] = agg['day'].dt.strftime('%Y-%m-%d')
    return agg

def predict_metric(df, metric='views', days=7):
    if len(df) < 2: return [], []
    df = df.copy()
    df['day_ordinal'] = pd.to_datetime(df['day']).map(datetime.date.toordinal)
    X = df['day_ordinal'].values.reshape(-1, 1)
    y = df[metric].values
    
    model = LinearRegression()
    model.fit(X, y)
    
    last_date = pd.to_datetime(df['day'].iloc[-1])
    future_dates = [last_date + timedelta(days=i) for i in range(1, days + 1)]
    future_X = np.array([d.toordinal() for d in future_dates]).reshape(-1, 1)
    predictions = model.predict(future_X)
    
    return [d.strftime('%Y-%m-%d') for d in future_dates], [round(max(0, p)) for p in predictions]

def generate_dashboard_json(channel_id, top_videos_df, demographics, traffic_df):
    print("Generating dashboard_data.json from DB...")
    session = get_session()
    
    # Fetch Data from DB
    channel = session.query(Channel).filter_by(id=channel_id).first()
    stats = session.query(DailyStat).filter_by(channel_id=channel_id).order_by(DailyStat.date).all()
    
    # Convert to DataFrame
    data = []
    for s in stats:
        data.append({
            'day': s.date.strftime('%Y-%m-%d'),
            'views': s.views,
            'subscribersGained': s.subscribers,
            'estimatedRevenue': s.revenue,
            'estimatedMinutesWatched': s.watch_time_hours * 60,
            # Placeholder for missing columns in DailyStat if we want to match exact schema
            'likes': 0, 'dislikes': 0, 'comments': 0, 'shares': 0, 'averageViewDuration': 0
        })
    df = pd.DataFrame(data)
    
    # Fill gaps
    if not df.empty:
        df['day'] = pd.to_datetime(df['day'])
        full_range = pd.date_range(start=df['day'].min(), end=datetime.datetime.now().date(), freq='D')
        df = df.set_index('day').reindex(full_range).fillna(0).reset_index().rename(columns={'index': 'day'})
        df['day'] = df['day'].dt.strftime('%Y-%m-%d')

    # Aggregations
    daily_df = df
    weekly_df = aggregate_data(df, 'W-MON')
    monthly_df = aggregate_data(df, 'ME')
    
    # Predictions
    pred_dates, pred_views = predict_metric(df, 'views')
    
    # Summary (30d)
    last_30 = df.tail(30)
    summary = {
        "channel_name": channel.name if channel else "Unknown",
        "profile_image": channel.profile_image if channel else "",
        "total_views_30d": int(last_30['views'].sum()),
        "estimated_revenue_30d": round(last_30['estimatedRevenue'].sum(), 2),
        "subs_gained_30d": int(last_30['subscribersGained'].sum()),
        "total_watch_time_hours_30d": int(last_30['estimatedMinutesWatched'].sum() / 60),
        "avg_engagement_rate_30d": 0.0, # Implement if we track likes daily
        "last_updated": get_kst_now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # Build JSON
    output = {
        "summary": summary,
        "trends": {
            "daily": daily_df.to_dict(orient='list'),
            "weekly": weekly_df.to_dict(orient='list'),
            "monthly": monthly_df.to_dict(orient='list')
        },
        "prediction": { "dates": pred_dates, "views": pred_views },
        "top_videos": top_videos_df.to_dict(orient='records'),
        "demographics": demographics,
        "traffic_sources": traffic_df.to_dict(orient='records')
    }
    
    with open(config.DASHBOARD_DATA_FILE, 'w') as f:
        json.dump(output, f, indent=4)
        
    # Valid JS export
    with open(str(config.DASHBOARD_DATA_FILE).replace('.json', '.js'), 'w') as f:
        f.write(f"window.dashboardData = {json.dumps(output, indent=4)};")
        
    print("Dashboard Data Saved.")

def main():
    try:
        init_db()
        creds = get_credentials()
        youtube = build("youtube", "v3", credentials=creds)
        analytics = build("youtubeAnalytics", "v2", credentials=creds)
        
        # 1. Fetch
        c_stats = fetch_channel_stats(youtube)
        if not c_stats:
            print("Failed to fetch channel stats.")
            return

        a_stats = fetch_analytics(analytics)
        top_v = fetch_top_videos(analytics, youtube)
        demo = fetch_demographics(analytics)
        traffic = fetch_traffic_sources(analytics)
        
        # 2. Save
        channel_id = save_to_db(c_stats, a_stats, top_v)
        
        # 3. Generate
        generate_dashboard_json(channel_id, top_v, demo, traffic)
        
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
