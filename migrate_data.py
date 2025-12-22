import json
import os
import pandas as pd
from datetime import datetime
from database import init_db, get_session, Channel, DailyStat, Video, VideoStat
import config

def migrate():
    print("Starting migration...")
    
    # Initialize DB
    init_db()
    session = get_session()
    
    # 1. Load Channel Info
    channel_id = "UNKNOWN_CHANNEL_ID"
    channel_name = "AI Sound Lab"
    profile_image = ""
    
    # Try to get real ID from channel_stats.json if it exists
    channel_stats_path = config.DATA_DIR / "channel_stats.json"
    if os.path.exists(channel_stats_path):
        try:
            with open(channel_stats_path, 'r') as f:
                stats = json.load(f)
                channel_id = stats.get("channel_id", channel_id)
                channel_name = stats.get("channel_name", channel_name)
                profile_image = stats.get("profile_image", profile_image)
        except Exception as e:
            print(f"Error reading channel_stats.json: {e}")

    # Check if channel exists
    channel = session.query(Channel).filter_by(id=channel_id).first()
    if not channel:
        print(f"Creating channel: {channel_name} ({channel_id})")
        channel = Channel(
            id=channel_id,
            name=channel_name,
            profile_image=profile_image,
            last_updated=datetime.utcnow()
        )
        session.add(channel)
        session.commit()
    
    # 2. Load Dashboard Data (Trends & Videos)
    dashboard_path = config.DASHBOARD_DATA_FILE
    if os.path.exists(dashboard_path):
        try:
            with open(dashboard_path, 'r') as f:
                data = json.load(f)
            
            # A. Daily Stats
            trends = data.get("trends", {}).get("daily", {})
            dates = trends.get("dates", [])
            views = trends.get("views", [])
            subs = trends.get("subscribers", [])
            revenue = trends.get("revenue", [])
            # watchTime and engagement might not be arrays in the older JSON, but let's check
            # Based on inspection, dashboard_data.json has views, revenue, subscribers, etc. as arrays
            
            print(f"Migrating {len(dates)} daily stat records...")
            for i, date_str in enumerate(dates):
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                    
                    # Check if exists
                    stat = session.query(DailyStat).filter_by(channel_id=channel_id, date=date_obj).first()
                    if not stat:
                        stat = DailyStat(channel_id=channel_id, date=date_obj)
                        session.add(stat)
                    
                    # Update fields
                    stat.views = int(views[i]) if i < len(views) else 0
                    stat.subscribers = int(subs[i]) if i < len(subs) else 0
                    stat.revenue = float(revenue[i]) if i < len(revenue) else 0.0
                    # Note: video_count query is not in trends, skipping
                    
                except Exception as e:
                    print(f"Skipping date {date_str}: {e}")
            
            # B. Top Videos
            top_videos = data.get("top_videos", [])
            print(f"Migrating {len(top_videos)} videos...")
            
            for v_data in top_videos:
                vid = v_data.get("video")
                if not vid: continue
                
                # Video Entry
                video = session.query(Video).filter_by(id=vid).first()
                if not video:
                    video = Video(id=vid, channel_id=channel_id)
                    session.add(video)
                
                video.title = v_data.get("title", "Unknown")
                video.thumbnail_url = v_data.get("thumbnail", "")
                
                # Video Stat Entry (Snapshot for today)
                # We interpret this as "latest" stat
                v_stat = session.query(VideoStat).filter_by(video_id=vid, date=datetime.utcnow().date()).first()
                if not v_stat:
                    v_stat = VideoStat(video_id=vid, date=datetime.utcnow().date())
                    session.add(v_stat)
                
                v_stat.views = int(v_data.get("views", 0))
                v_stat.likes = int(v_data.get("likes", 0))
                v_stat.dislikes = int(v_data.get("dislikes", 0))
                v_stat.comments = int(v_data.get("comments", 0))
                v_stat.revenue = float(v_data.get("estimatedRevenue", 0.0))
            
            session.commit()
            print("Migration complete!")
            
        except Exception as e:
            print(f"Error reading dashboard_data.json: {e}")
            session.rollback()
    else:
        print("dashboard_data.json not found.")

if __name__ == "__main__":
    migrate()
