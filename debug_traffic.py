import os
import datetime
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import config

def get_credentials():
    creds = None
    if os.path.exists(config.TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(config.TOKEN_FILE, config.SCOPES)
    return creds

def test_range(analytics, start, end, label):
    print(f"--- {label}: {start} to {end} ---")
    try:
        request = analytics.reports().query(
            ids="channel==MINE",
            startDate=start,
            endDate=end,
            metrics="views",
            dimensions="insightTrafficSourceType",
            sort="-views"
        )
        response = request.execute()
        rows = response.get('rows', [])
        print(f"Rows: {len(rows)}")
        for row in rows:
            print(row)
        if not rows:
            print("No data.")
    except Exception as e:
        print(f"Error: {e}")

def main():
    creds = get_credentials()
    if not creds:
        print("No creds found")
        return

    analytics = build('youtubeAnalytics', 'v2', credentials=creds)
    
    today = datetime.date.today()
    
    # 1. Last 30 Days (T-3)
    end = (today - datetime.timedelta(days=3)).strftime("%Y-%m-%d")
    start = (today - datetime.timedelta(days=33)).strftime("%Y-%m-%d")
    test_range(analytics, start, end, "Last 30 Days")

    # 2. Last 365 Days
    start_365 = (today - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
    test_range(analytics, start_365, end, "Last 365 Days")
    
    # 3. Fixed Range (Nov 1 - Dec 14) - The period user mentioned
    test_range(analytics, "2024-11-01", "2024-12-14", "Nov 1 - Dec 14")

if __name__ == "__main__":
    main()
