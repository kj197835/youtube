import os
from pathlib import Path

# Base Directory
BASE_DIR = Path(__file__).parent.absolute()

# Data Directory
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Secrets Paths
CLIENT_SECRET_FILE = BASE_DIR / "client_secret_917351306092-1vs8a1qgfhth96kcqk6lqq7tu8ctfla9.apps.googleusercontent.com.json"
TOKEN_FILE = BASE_DIR / "credentials.json"

# API Scopes
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly"
]

# Output Files
STATS_FILE = DATA_DIR / "youtube_stats.csv"
TOP_VIDEOS_FILE = DATA_DIR / "top_videos.csv"
DASHBOARD_DATA_FILE = BASE_DIR / "dashboard_data.json"
