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
            # Use fixed port 8080 to allow Docker port mapping
            creds = flow.run_local_server(port=8080, open_browser=False, bind_addr='0.0.0.0', prompt='consent')
            print(f"Please visit the URL above to authorize this application.")
        
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
            "subscribers": stats["subscriberCount"],
            "total_views": stats["viewCount"],
            "video_count": stats["videoCount"]
        }
    return None

def fetch_analytics(analytics):
    print("Fetching analytics data (last 30 days)...")
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    # Fetch 1 year of data for better trending
    start_date = (datetime.date.today() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
    
    metrics_list = "views,estimatedMinutesWatched,estimatedRevenue,subscribersGained"
    
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
        metrics_list = "views,estimatedMinutesWatched,subscribersGained"
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
        
    return df

def fetch_top_videos(analytics):
    print("Fetching top videos (last 90 days)...")
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    # For top videos, 90 days is a good window for "recent popular"
    start_date = (datetime.date.today() - datetime.timedelta(days=90)).strftime("%Y-%m-%d")
    
    metrics_list = "views,estimatedMinutesWatched,estimatedRevenue,subscribersGained"
    
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
        metrics_list = "views,estimatedMinutesWatched,subscribersGained"
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
        
    headers = [header["name"] for header in response.get("columnHeaders", [])]
    rows = response.get("rows", [])
    
    df = pd.DataFrame(rows, columns=headers)
    
    if 'estimatedRevenue' not in df.columns:
        df['estimatedRevenue'] = 0.0
        
    return df

def main():
    try:
        creds = get_credentials()
        youtube = build("youtube", "v3", credentials=creds)
        analytics = build("youtubeAnalytics", "v2", credentials=creds)
        
        # Fetch Data
        channel_stats = fetch_channel_stats(youtube)
        analytics_df = fetch_analytics(analytics)
        top_videos_df = fetch_top_videos(analytics)
        
        # Add Channel Stats to DataFrame (as constant columns or metadata, but for CSV structure simply saving analytics is better)
        # We will save channel stats separately or just rely on analytics for trends.
        # The user wants "channel stats and profit".
        # Let's print channel stats and save analytics.
        
        if channel_stats:
            print(f"Channel: {channel_stats['channel_name']}")
            print(f"Subscribers: {channel_stats['subscribers']}")
            print(f"Total Views: {channel_stats['total_views']}")
        
        # Save to CSV
        output_file = config.STATS_FILE
        print(f"Saving data to {output_file}...")
        
        # If file exists, we might want to append, but for simplicity and avoiding dupes, 
        # overwriting with last 30 days is safer for this 'insight' window. 
        # Or we could load existing and merge. 
        # For now, let's overwrite to ensure clean data for the dashboard.
        analytics_df.to_csv(output_file, index=False)
        
        # Save Top Videos
        top_videos_file = config.TOP_VIDEOS_FILE
        print(f"Saving top videos to {top_videos_file}...")
        top_videos_df.to_csv(top_videos_file, index=False)
        
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
