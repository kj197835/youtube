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

def fetch_top_videos(analytics):
    print("Fetching top videos (last 90 days)...")
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    # For top videos, 90 days is a good window for "recent popular"
    start_date = (datetime.date.today() - datetime.timedelta(days=90)).strftime("%Y-%m-%d")
    
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
            maxResults=10
        )
        response = request.execute()
        
    headers = [header["name"] for header in response.get("columnHeaders", [])]
    rows = response.get("rows", [])
    
    df = pd.DataFrame(rows, columns=headers)
    
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
    print("Fetching traffic sources (last 30 days)...")
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    start_date = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    
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
        # Since we cannot easily pass arguments to the existing function without refactoring,
        # We will modify the existing fetch_analytics function in-place (conceptually) 
        # But here in 'main', we are calling functions.
        # WAITING: I need to update fetch_analytics to include the extra metrics first!
        # Re-defining fetch_analytics in the replacement chunk below for clarity.
        
        analytics_df = fetch_analytics(analytics) 
        top_videos_df = fetch_top_videos(analytics)
        demographics_data = fetch_demographics(analytics)
        traffic_df = fetch_traffic_sources(analytics)
        interaction_df = fetch_interaction_stats(analytics)
        
        
        if channel_stats:
            print(f"Channel: {channel_stats['channel_name']}")
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
