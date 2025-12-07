import pandas as pd
import json
import numpy as np
from sklearn.linear_model import LinearRegression
import config
from datetime import datetime, timedelta

def load_data():
    if not config.STATS_FILE.exists():
        print(f"Data file {config.STATS_FILE} not found.")
        return None
    return pd.read_csv(config.STATS_FILE)

def calculate_growth(df):
    if len(df) < 2:
        return 0, 0
    
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    views_growth = ((latest['views'] - prev['views']) / prev['views']) * 100 if prev['views'] > 0 else 0
    
    # Subscribers might not change daily, look for total change in period or last day
    # API returns 'subscribersGained', so we can just sum it or take latest.
    # We'll use the daily gain for growth comparison
    subs_growth = 0 # Placeholder if 0
    if prev['subscribersGained'] > 0:
        subs_growth = ((latest['subscribersGained'] - prev['subscribersGained']) / prev['subscribersGained']) * 100
        
    return views_growth, subs_growth

def predict_metric(df, metric='views', days=7):
    # Prepare data for regression
    df['day_ordinal'] = pd.to_datetime(df['day']).map(datetime.toordinal)
    X = df['day_ordinal'].values.reshape(-1, 1)
    y = df[metric].values
    
    model = LinearRegression()
    model.fit(X, y)
    
    last_day = pd.to_datetime(df['day'].iloc[-1])
    future_dates = [last_day + timedelta(days=i) for i in range(1, days + 1)]
    future_X = np.array([d.toordinal() for d in future_dates]).reshape(-1, 1)
    
    predictions = model.predict(future_X)
    
    return future_dates, predictions

def main():
    df = load_data()
    if df is None or df.empty:
        print("No data to analyze.")
        return

    # Basic Stats
    total_views = df['views'].sum() # This is sum of daily views in period
    total_revenue = df['estimatedRevenue'].sum()
    total_subs_gained = df['subscribersGained'].sum()
    
    views_growth, subs_growth = calculate_growth(df)
    
    # Prediction
    future_dates, view_predictions = predict_metric(df, 'views')
    
    # Prepare JSON structure
    dashboard_data = {
        "summary": {
            "total_views_30d": int(total_views),
            "estimated_revenue_30d": round(float(total_revenue), 2),
            "subs_gained_30d": int(total_subs_gained),
            "views_growth": round(views_growth, 2),
            "subs_growth": round(subs_growth, 2),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "chart_data": {
            "labels": df['day'].tolist() + [d.strftime("%Y-%m-%d") for d in future_dates],
            "historical": df['views'].tolist(),
            "predicted": [None]*len(df) + [round(p) for p in view_predictions]
        },
        "top_videos": [] # We could add this if we fetched video list, skipping for now based on API simplicity
    }
    
    # Save JSON
    with open(config.DASHBOARD_DATA_FILE, 'w') as f:
        json.dump(dashboard_data, f, indent=4)
    
    print(f"Dashboard data saved to {config.DASHBOARD_DATA_FILE}")

if __name__ == "__main__":
    main()
