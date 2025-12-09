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
    return df.sort_values('day')

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
    top_videos = load_top_videos()

    # Prepare JSON structure
    # Load Realtime Stats if available
    channel_stats = {}
    channel_stats_file = config.DATA_DIR / "channel_stats.json"
    if channel_stats_file.exists():
        with open(channel_stats_file, 'r') as f:
            channel_stats = json.load(f)

    # Use Realtime stats for Summary if available, otherwise fallback to 30d sum
    summary_views = int(channel_stats.get('total_views', total_views_30d))
    summary_subs = int(channel_stats.get('subscribers', total_subs_30d))
    # Revenue is not available in realtime stats, so keep 30d sum
    summary_revenue = round(float(total_revenue_30d), 2)

    dashboard_data = {
        "summary": {
            "total_views_30d": summary_views,
            "estimated_revenue_30d": summary_revenue,
            "subs_gained_30d": summary_subs,
            "last_updated": get_kst_now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "trends": {
            "daily": {
                "dates": daily_df['day'].tolist(),
                "views": daily_df['views'].tolist(),
                "revenue": daily_df['estimatedRevenue'].tolist(),
                "subscribers": daily_df['subscribersGained'].tolist(),
                "likes": daily_df['likes'].tolist(),
                "comments": daily_df['comments'].tolist(),
                "shares": daily_df['shares'].tolist()
            },
            "weekly": {
                "dates": weekly_df['day'].tolist(),
                "views": weekly_df['views'].tolist(),
                "revenue": weekly_df['estimatedRevenue'].tolist(),
                "subscribers": weekly_df['subscribersGained'].tolist(),
                "likes": weekly_df['likes'].tolist(),
                "comments": weekly_df['comments'].tolist(),
                "shares": weekly_df['shares'].tolist()
            },
            "monthly": {
                "dates": monthly_df['day'].tolist(),
                "views": monthly_df['views'].tolist(),
                "revenue": monthly_df['estimatedRevenue'].tolist(),
                "subscribers": monthly_df['subscribersGained'].tolist(),
                "likes": monthly_df['likes'].tolist(),
                "comments": monthly_df['comments'].tolist(),
                "shares": monthly_df['shares'].tolist()
            }
        },
        "prediction": {
            "dates": pred_dates,
            "views": pred_views
        },
        "top_videos": top_videos
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
