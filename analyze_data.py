import pandas as pd
import json
import numpy as np
from sklearn.linear_model import LinearRegression
import config
from datetime import datetime, timedelta, timezone

# KST Timezone helper
def get_kst_now():
    return datetime.now(timezone.utc) + timedelta(hours=9)

def load_data():
    if not config.STATS_FILE.exists():
        print(f"Data file {config.STATS_FILE} not found.")
        return None
    df = pd.read_csv(config.STATS_FILE)
    df['day'] = pd.to_datetime(df['day'])
    
    # Ensure full 365-day range coverage
    end_date = pd.Timestamp.now().normalize()
    start_date = end_date - pd.Timedelta(days=365)
    full_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Reindex to full range, filling missing stats with 0
    df = df.set_index('day').reindex(full_range).fillna(0).reset_index().rename(columns={'index': 'day'})
    
    # Fill NaN for new columns if they don't exist in old rows
    cols_to_fill = ['likes', 'dislikes', 'comments', 'shares', 'averageViewDuration', 'views', 'estimatedRevenue', 'subscribersGained']
    for col in cols_to_fill:
        if col not in df.columns:
            df[col] = 0
            
    return df.sort_values('day')

def load_demographics():
    if not config.DEMOGRAPHICS_FILE.exists():
        return {}
    with open(config.DEMOGRAPHICS_FILE, 'r') as f:
        return json.load(f)

def load_traffic_sources():
    if not config.TRAFFIC_SOURCES_FILE.exists():
        return []
    df = pd.read_csv(config.TRAFFIC_SOURCES_FILE)
    return df.to_dict('records')

def load_top_videos():
    if not config.TOP_VIDEOS_FILE.exists():
        return []
    df = pd.read_csv(config.TOP_VIDEOS_FILE)
    # Convert numeric columns safely
    df['views'] = pd.to_numeric(df['views'], errors='coerce').fillna(0)
    df['estimatedRevenue'] = pd.to_numeric(df['estimatedRevenue'], errors='coerce').fillna(0)
    return df.to_dict('records')

def aggregate_data(df, freq):
    # Resample daily data to weekly/monthly
    # Sum metric columns
    agg_df = df.set_index('day').resample(freq).sum().reset_index()
    agg_df['day'] = agg_df['day'].dt.strftime('%Y-%m-%d')
    return agg_df

def predict_metric(df, metric='views', days=7):
    if len(df) < 2:
        return [], []
        
    # Prepare data for regression
    df = df.copy()
    df['day_ordinal'] = pd.to_datetime(df['day']).map(datetime.toordinal)
    X = df['day_ordinal'].values.reshape(-1, 1)
    y = df[metric].values
    
    model = LinearRegression()
    model.fit(X, y)
    
    last_day = pd.to_datetime(df['day'].iloc[-1])
    future_dates = [last_day + timedelta(days=i) for i in range(1, days + 1)]
    future_X = np.array([d.toordinal() for d in future_dates]).reshape(-1, 1)
    
    predictions = model.predict(future_X)
    
    return [d.strftime('%Y-%m-%d') for d in future_dates], [round(p) if p > 0 else 0 for p in predictions]

def main():
    df = load_data()
    if df is None or df.empty:
        print("No data to analyze.")
        return

    # Basic Stats (Summary based on last 30 days or total range? User wants "past records")
    # Let's keep summary for "Last 30 Days" as a KPI
    last_30_days = df[df['day'] > (datetime.now() - timedelta(days=30))]
    
    total_views_30d = last_30_days['views'].sum()
    total_revenue_30d = last_30_days['estimatedRevenue'].sum()
    total_subs_30d = last_30_days['subscribersGained'].sum()
    
    # Aggregations
    daily_df = df.copy()
    daily_df['day'] = daily_df['day'].dt.strftime('%Y-%m-%d')
    weekly_df = aggregate_data(df, 'W-MON')
    monthly_df = aggregate_data(df, 'ME')
    
    # Predictions (Weekly Forecast)
    pred_dates, pred_views = predict_metric(df, 'views', 7)
    
    # Top Videos
    # Top Videos
    top_videos = load_top_videos()
    
    # Demographics & Traffic
    demographics = load_demographics()
    traffic_sources = load_traffic_sources()

    # Prepare JSON structure
    # Load Realtime Stats if available
    channel_stats = {}
    channel_stats_file = config.DATA_DIR / "channel_stats.json"
    if channel_stats_file.exists():
        with open(channel_stats_file, 'r') as f:
            channel_stats = json.load(f)

    # Calculate fallback totals from Top Videos
    top_videos_views = sum(v.get('views', 0) for v in top_videos)
    top_videos_revenue = sum(v.get('estimatedRevenue', 0) for v in top_videos)
    
    # Calculate fallback totals from Traffic Sources (Most reliable in this case)
    traffic_sources = load_traffic_sources()
    traffic_views = sum(int(t.get('views', 0)) for t in traffic_sources)
    traffic_minutes = sum(float(t.get('estimatedMinutesWatched', 0)) for t in traffic_sources)

    # Use Realtime stats for Summary if available
    summary_views = int(channel_stats.get('total_views', total_views_30d))
    
    # Logic: Fallback cascade
    if summary_views == 0:
        if top_videos_views > 0:
            summary_views = top_videos_views
        elif traffic_views > 0:
             summary_views = traffic_views

    summary_subs = int(channel_stats.get('subscribers', total_subs_30d))
    
    # Revenue fallback
    summary_revenue = round(float(total_revenue_30d), 2)
    if summary_revenue == 0 and top_videos_revenue > 0:
        summary_revenue = round(float(top_videos_revenue), 2)
        
    # Calculate Watch Time (Hours)
    # 1. From Channel Stats? No.
    # 2. From Daily Trends?
    summary_watch_hours = 0
    if not daily_df.empty and 'estimatedMinutesWatched' in daily_df.columns:
        summary_watch_hours = round(daily_df['estimatedMinutesWatched'].sum() / 60)
    
    # Fallback Watch Time
    if summary_watch_hours == 0 and traffic_minutes > 0:
        summary_watch_hours = round(traffic_minutes / 60)
        
    # Calculate Engagement Rate Fallback (Likes + Comments / Views * 100)
    # 1. From Daily Trends
    trends_likes = daily_df['likes'].sum() if 'likes' in daily_df.columns else 0
    trends_comments = daily_df['comments'].sum() if 'comments' in daily_df.columns else 0
    trends_views = daily_df['views'].sum() if 'views' in daily_df.columns else 0
    
    engagement_rate = 0
    if trends_views > 0:
        engagement_rate = ((trends_likes + trends_comments) / trends_views) * 100
        
    # 2. Fallback from Top Videos
    if engagement_rate == 0 and top_videos_views > 0:
        top_likes = sum(v.get('likes', 0) for v in top_videos)
        top_comments = sum(v.get('comments', 0) for v in top_videos)
        engagement_rate = ((top_likes + top_comments) / top_videos_views) * 100

    dashboard_data = {
        "summary": {
            "channel_name": channel_stats.get('channel_name', 'Unknown'),
            "profile_image": channel_stats.get('profile_image', ''),
            "total_views_30d": summary_views,
            "estimated_revenue_30d": summary_revenue,
            "subs_gained_30d": summary_subs,
            "total_watch_time_hours_30d": summary_watch_hours,
            "avg_engagement_rate_30d": round(engagement_rate, 2),
            "last_updated": get_kst_now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "trends": {
            "daily": {
                "dates": daily_df['day'].tolist(),
                "views": daily_df['views'].tolist(),
                "revenue": daily_df['estimatedRevenue'].tolist(),
                "subscribers": daily_df['subscribersGained'].tolist(),
                "likes": daily_df['likes'].tolist(),
                "dislikes": daily_df['dislikes'].tolist(),
                "comments": daily_df['comments'].tolist(),
                "shares": daily_df['shares'].tolist(),
                "averageViewDuration": daily_df['averageViewDuration'].tolist()
            },
            "weekly": {
                "dates": weekly_df['day'].tolist(),
                "views": weekly_df['views'].tolist(),
                "revenue": weekly_df['estimatedRevenue'].tolist(),
                "subscribers": weekly_df['subscribersGained'].tolist(),
                "likes": weekly_df['likes'].tolist(),
                "dislikes": weekly_df['dislikes'].tolist(),
                "comments": weekly_df['comments'].tolist(),
                "shares": weekly_df['shares'].tolist(),
                "averageViewDuration": weekly_df['averageViewDuration'].tolist()
            },
            "monthly": {
                "dates": monthly_df['day'].tolist(),
                "views": monthly_df['views'].tolist(),
                "revenue": monthly_df['estimatedRevenue'].tolist(),
                "subscribers": monthly_df['subscribersGained'].tolist(),
                "likes": monthly_df['likes'].tolist(),
                "dislikes": monthly_df['dislikes'].tolist(),
                "comments": monthly_df['comments'].tolist(),
                "shares": monthly_df['shares'].tolist(),
                "averageViewDuration": monthly_df['averageViewDuration'].tolist()
            }
        },
        "prediction": {
            "dates": pred_dates,
            "views": pred_views
        },
        "top_videos": top_videos,
        "demographics": demographics,
        "traffic_sources": traffic_sources
    }
    
    # Save JSON
    with open(config.DASHBOARD_DATA_FILE, 'w') as f:
        json.dump(dashboard_data, f, indent=4)
    print(f"Dashboard data saved to {config.DASHBOARD_DATA_FILE}")

    # Save JS (for local file:// access support)
    js_content = f"window.dashboardData = {json.dumps(dashboard_data, indent=4)};"
    js_file = config.DASHBOARD_DATA_FILE.with_suffix('.js')
    with open(js_file, 'w') as f:
        f.write(js_content)
    print(f"Dashboard data JS saved to {js_file}")

if __name__ == "__main__":
    main()
