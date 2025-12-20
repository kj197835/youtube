import os
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import config

def get_credentials():
    creds = None
    if os.path.exists(config.TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(config.TOKEN_FILE, config.SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print("Need to re-auth (not handled in debug script)")
            return None
    return creds

def main():
    creds = get_credentials()
    if not creds:
        print("No valid creds")
        return

    analytics = build('youtubeAnalytics', 'v2', credentials=creds)
    
    end_date = datetime.date.today().strftime("%Y-%m-%d")
    start_date = "2020-01-01"
    
    print(f"Querying Traffic Sources from {start_date} to {end_date}")
    
    try:
        request = analytics.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics="views",
            dimensions="insightTrafficSourceType",
            sort="-views"
        )
        response = request.execute()
        print("Response:")
        print(response)
        
        if 'rows' in response:
            print(f"Row count: {len(response['rows'])}")
        else:
            print("No rows found")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
