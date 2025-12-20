import os
import datetime
import pandas as pd
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import config

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
            
            # Manual Console Strategy (Copy-Paste from URL)
            # We use localhost:8080 because OOB is deprecated/restricted.
            # User will see "Connection Refused", but the code will be in the URL.
            flow.redirect_uri = 'http://localhost:8080/'
            auth_url, _ = flow.authorization_url(prompt='consent')
            
            print("Please visit this URL to authorize this application:")
            print(auth_url)
            print("-" * 50)
            print("NOTE: After authorizing, you might see 'This site can't be reached'.")
            print("This is NORMAL. Look at the address bar of your browser.")
            print("Copy the text starting with 'code=' ... (everything after code=)")
            print("-" * 50)
            
            code = input("Enter the authorization code (from the URL): ")
            flow.fetch_token(code=code)
            creds = flow.credentials
        
        with open(config.TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            print(f"Credentials saved to {config.TOKEN_FILE}")
            
    return creds

def fetch_channel_stats(youtube):
    print("Fetching channel statistics...")
    request = youtube.channels().list(
        part="statistics,snippet",
        mine=True
    )
    response = request.execute()
    
    if "items" in response and len(response["items"]) > 0:
        item = response["items"][0]
        stats = item["statistics"]
        snippet = item["snippet"]
        return {
            "channel_name": snippet["title"],
            "channel_id": item["id"], # Add ID to return
            "profile_image": snippet["thumbnails"]["default"]["url"], # Add profile image
            "subscribers": stats["subscriberCount"],
            "total_views": stats["viewCount"],
            "video_count": stats["videoCount"]
        }
    return None

def fetch_analytics(analytics):
    print("Fetching analytics data (since 2024-01-01)... with T-3 delay")
    # T-3 days because Analytics data is not real-time
    end_date = (datetime.date.today() - datetime.timedelta(days=3)).strftime("%Y-%m-%d")
    # Explicitly set to beginning of year to capture all history
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
        print(f"Error checking revenue (channel might not be monetized): {e}")
        print("Retrying without revenue metric...")
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
    
    # Ensure estimatedRevenue column exists even if we fell back
    if 'estimatedRevenue' not in df.columns:
        df['estimatedRevenue'] = 0.0
        
    df = pd.DataFrame(rows, columns=headers)
    
    # Ensure estimatedRevenue column exists even if we fell back
    if 'estimatedRevenue' not in df.columns:
        df['estimatedRevenue'] = 0.0
        
    return df

def fetch_top_videos(analytics, youtube):
    print("Fetching top videos (since 2024-01-01)... with T-3 delay")
    end_date = (datetime.date.today() - datetime.timedelta(days=3)).strftime("%Y-%m-%d")
    start_date = "2024-01-01"
    
    metrics_list = "views,estimatedMinutesWatched,estimatedRevenue,subscribersGained,likes,dislikes,comments,shares"
    
    try:
        request = analytics.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics=metrics_list,
            dimensions="video",
            sort="-views",
            maxResults=10
        )
        response = request.execute()
    except Exception as e:
        print(f"Error checking revenue for top videos: {e}")
        print("Retrying without revenue metric...")
        metrics_list = "views,estimatedMinutesWatched,subscribersGained,likes,dislikes,comments,shares"
        request = analytics.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics=metrics_list,
            dimensions="video",
            sort="-views",
            maxResults=100
        )
        response = request.execute()
        
    headers = [header["name"] for header in response.get("columnHeaders", [])]
    rows = response.get("rows", [])
    
    df = pd.DataFrame(rows, columns=headers)
    
    # Enrich with Video Titles and Thumbnails
    if not df.empty and 'video' in df.columns:
        video_ids = df['video'].tolist()
        video_ids = [vid for vid in video_ids if vid and vid != '0']
        
        if video_ids:
            try:
                print(f"Fetching details for {len(video_ids)} videos...")
                vid_request = youtube.videos().list(
                    part="snippet",
                    id=",".join(video_ids)
                )
                vid_response = vid_request.execute()
                
                # Create ID -> Metadata map
                id_to_meta = {}
                for item in vid_response.get("items", []):
                    vid_id = item["id"]
                    snippet = item["snippet"]
                    title = snippet["title"]
                    thumbnail_url = snippet["thumbnails"].get("medium", snippet["thumbnails"]["default"])["url"]
                    
                    # Thumbnail Caching Logic
                    thumb_filename = f"{vid_id}.jpg"
                    local_thumb_path = os.path.join("dashboard", "public", "thumbnails", thumb_filename)
                    public_path = f"/thumbnails/{thumb_filename}"
                    
                    # Create directory if not exists
                    os.makedirs(os.path.dirname(local_thumb_path), exist_ok=True)
                    
                    if not os.path.exists(local_thumb_path):
                        print(f"Downloading thumbnail for {vid_id}...")
                        try:
                            import urllib.request
                            urllib.request.urlretrieve(thumbnail_url, local_thumb_path)
                        except Exception as e:
                            print(f"Failed to download thumbnail {vid_id}: {e}")
                            public_path = thumbnail_url # Fallback to remote
                    
                    id_to_meta[vid_id] = {
                        "title": title,
                        "thumbnail": public_path
                    }
                
                # Map to dataframe
                df['title'] = df['video'].map(lambda x: id_to_meta.get(x, {}).get("title", f"Unknown Video ({x})"))
                df['thumbnail'] = df['video'].map(lambda x: id_to_meta.get(x, {}).get("thumbnail", ""))
            except Exception as e:
                print(f"Error fetching video details: {e}")
                df['title'] = df['video']
    else:
        df['title'] = df['video'] if 'video' in df.columns else "Unknown"
        df['thumbnail'] = ""

    if 'estimatedRevenue' not in df.columns:
        df['estimatedRevenue'] = 0.0
        
    return df

def fetch_demographics(analytics):
    print("Fetching demographics (last 30 days)...")
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    start_date = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    
    demographics = {}

    # 1. Age & Gender
    try:
        request = analytics.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics="viewerPercentage",
            dimensions="ageGroup,gender",
            sort="ageGroup,gender"
        )
        response = request.execute()
        demographics['age_gender'] = {
            'headers': [h['name'] for h in response.get('columnHeaders', [])],
            'rows': response.get('rows', [])
        }
    except Exception as e:
        print(f"Error fetching age/gender: {e}")

    # 2. Geography (Country)
    try:
        request = analytics.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics="views,estimatedMinutesWatched",
            dimensions="country",
            sort="-views",
            maxResults=15
        )
        response = request.execute()
        demographics['geography'] = {
            'headers': [h['name'] for h in response.get('columnHeaders', [])],
            'rows': response.get('rows', [])
        }
    except Exception as e:
        print(f"Error fetching geography: {e}")
        
    return demographics

def fetch_traffic_sources(analytics):
    print("Fetching traffic sources (since 2024-01-01)... with T-3 delay")
    end_date = (datetime.date.today() - datetime.timedelta(days=3)).strftime("%Y-%m-%d")
    start_date = "2024-01-01"
    
    try:
        request = analytics.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics="views,estimatedMinutesWatched",
            dimensions="insightTrafficSourceType",
            sort="-views"
        )
        response = request.execute()
        
        headers = [header["name"] for header in response.get("columnHeaders", [])]
        rows = response.get("rows", [])
        return pd.DataFrame(rows, columns=headers)
        
    except Exception as e:
        print(f"Error fetching traffic sources: {e}")
        return pd.DataFrame()

def fetch_interaction_stats(analytics):
    print("Trying to fetch interaction stats (Card/EndScreen)...")
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    start_date = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    
    # Try fetching Card Clicks
    try:
        request = analytics.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics="cardClicks,cardImpressions,endScreenElementClicks,endScreenElementImpressions",
            dimensions="day",
            sort="day"
        )
        response = request.execute()
        print("Successfully fetched interaction stats!")
        headers = [header["name"] for header in response.get("columnHeaders", [])]
        rows = response.get("rows", [])
        return pd.DataFrame(rows, columns=headers)
    except Exception as e:
        print(f"Warning: Could not fetch interaction stats (API might not support it for this channel): {e}")
        return pd.DataFrame()

def main():
    try:
        creds = get_credentials()
        youtube = build("youtube", "v3", credentials=creds)
        analytics = build("youtubeAnalytics", "v2", credentials=creds)
        
        # Fetch Data
        channel_stats = fetch_channel_stats(youtube)
        
        # Update Analytics Fetch to include AvViewDuration, CardClicks, EndScreenClicks
        analytics_df = fetch_analytics(analytics)
        
        # Pass YouTube service to get video titles
        top_videos_df = fetch_top_videos(analytics, youtube)
        demographics_data = fetch_demographics(analytics)
        traffic_df = fetch_traffic_sources(analytics)
        interaction_df = fetch_interaction_stats(analytics)
        
        
        if channel_stats:
            print(f"Channel: {channel_stats['channel_name']} ({channel_stats.get('channel_id', 'Unknown ID')})")
            print(f"Subscribers: {channel_stats['subscribers']}")
            print(f"Total Views: {channel_stats['total_views']}")
            
            # Save channel stats to JSON for realtime display
            import json
            channel_stats_file = config.DATA_DIR / "channel_stats.json"
            with open(channel_stats_file, 'w') as f:
                json.dump(channel_stats, f, indent=4)

        
        # Merge interaction stats if available
        output_file = config.STATS_FILE
        
        if not interaction_df.empty:
            # Merge on 'day'
            if 'day' in analytics_df.columns and 'day' in interaction_df.columns:
                print("Merging interaction stats into main data...")
                analytics_df = pd.merge(analytics_df, interaction_df, on='day', how='left')
        
        print(f"Saving data to {output_file}...")
        analytics_df.to_csv(output_file, index=False)
        
        # Save Top Videos
        top_videos_file = config.TOP_VIDEOS_FILE
        print(f"Saving top videos to {top_videos_file}...")
        top_videos_df.to_csv(top_videos_file, index=False)
        
        # Save Demographics
        if demographics_data:
            import json
            print(f"Saving demographics to {config.DEMOGRAPHICS_FILE}...")
            with open(config.DEMOGRAPHICS_FILE, 'w') as f:
                json.dump(demographics_data, f, indent=4)
                
        # Save Traffic Sources
        if not traffic_df.empty:
            print(f"Saving traffic sources to {config.TRAFFIC_SOURCES_FILE}...")
            traffic_df.to_csv(config.TRAFFIC_SOURCES_FILE, index=False)
        
        print("Done.")
        
    except Exception as e:
        print(f"An error occurred: {e}")
        # Log error to file
        with open("error.log", "a") as f:
            f.write(f"{datetime.datetime.now()}: {e}\n")
        import sys
        sys.exit(1)

if __name__ == "__main__":
    main()
