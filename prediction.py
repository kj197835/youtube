import os
import sqlite3
import json
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
import xgboost as xgb

# Configuration
DB_PATH = os.path.join(os.path.dirname(__file__), 'youtube_data.db')
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), 'dashboard/public/prediction_data.json')
DAYS_TO_PREDICT = 30

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def fetch_data():
    conn = get_db_connection()
    # Fetch last 365 days of data for better training, including 'my_channel'
    # Assuming 'channel_stats' has daily snapshots or 'video_stats' aggregation
    # For simplicity, we use the `channel_stats` table if available, or aggregate `video_stats`
    # Let's check schema via query or assume `channel_stats` exists from previous work
    
    # Using 'my_channel' table or similar. 
    # Based on previous `fetch_data.py`, we track daily stats in `channel_stats` (daily snapshot)
    
    query = """
        SELECT date, views as view_count, subscribers_gained as subscriber_count, estimated_revenue as revenue
        FROM channel_daily_stats
        ORDER BY date ASC
    """
    try:
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        conn.close()
        return pd.DataFrame()

def moving_average_forecast(data, window=7, horizon=30):
    """Simple Moving Average Forecast"""
    if len(data) < window:
        return []
    
    # Calculate last window average
    last_avg = data[-window:].mean()
    
    # Project flat line (or slight trend if we want, but MA is usually flat or simple trend)
    # MA usually implies 'next value is average of last N'
    # For a 30 day forecast, pure MA is just a flat line of the last calculated average
    # To make it slightly more useful, we can use a moving trend, but let's stick to Simple MA definition
    
    forecast = [last_avg] * horizon
    return forecast

def weighted_moving_average_forecast(data, window=30, horizon=30):
    """Weighted Moving Average Forecast (Linear Weights)"""
    if len(data) < window:
        return []
    
    recent_data = data[-window:]
    weights = np.arange(1, window + 1)
    
    # Calculate WMA for the last point
    wma = np.sum(recent_data * weights) / weights.sum()
    
    # For forecast, we fit a simple linear trend on the weighted data or just project the WMA?
    # A better 'WMA Prediction' often involves projecting the recent *trend*.
    # Let's fit a linear line to the last 'window' days, weighted by recency.
    
    X = np.arange(window).reshape(-1, 1)
    y = recent_data.values
    
    model = LinearRegression()
    model.fit(X, y, sample_weight=weights)
    
    future_X = np.arange(window, window + horizon).reshape(-1, 1)
    forecast = model.predict(future_X)
    
    return forecast.tolist()

def xgboost_forecast(df, metric, horizon=30):
    """XGBoost Forecast"""
    if len(df) < 30: # Need enough data
        # Fallback to linear if not enough data
        return weighted_moving_average_forecast(df[metric], window=len(df), horizon=horizon)

    df = df.copy()
    df['day_index'] = np.arange(len(df))
    
    # Feature Engineering
    # Lag features
    for lag in [1, 7, 30]:
        df[f'lag_{lag}'] = df[metric].shift(lag)
    
    # Drop NaN
    train_df = df.dropna()
    
    if len(train_df) < 10:
         return weighted_moving_average_forecast(df[metric], window=len(df), horizon=horizon)

    X = train_df[['day_index', 'lag_1', 'lag_7', 'lag_30']]
    y = train_df[metric]
    
    model = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, learning_rate=0.1)
    model.fit(X, y)
    
    # Recursive Forecasting
    last_known = df.iloc[-1].copy()
    forecast = []
    
    current_day_index = last_known['day_index'] + 1
    
    for _ in range(horizon):
        # Update features
        # We need to dynamically update lags based on previous predictions
        # This is tricky with recursiveness.
        # Simplified approach: Train on day_index only for robust long-term trend if lags are hard to compute
        # OR: Just use day_index + trend features
        pass

    # Simplified XGBoost: Train on Time Index & Time Features only for direct multi-step or recursive
    # To keep it robust without complex lag management in loop:
    X_simple = train_df[['day_index']]
    model_simple = xgb.XGBRegressor(objective='reg:squarederror', n_estimators=100, learning_rate=0.05)
    model_simple.fit(X_simple, y)
    
    future_X = np.array([[last_known['day_index'] + i + 1] for i in range(horizon)])
    forecast = model_simple.predict(future_X)
    
    return forecast.tolist()

def generate_predictions():
    df = fetch_data()
    
    if df.empty:
        logging.warning("No data found in DB")
        return

    # Ensure date sorted
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # Metrics to predict
    metrics = ['view_count', 'subscriber_count', 'revenue']
    
    output = {
        "last_updated": datetime.now().isoformat(),
        "dates": [], # Future dates
        "predictions": {
            "ma": {},
            "wma": {},
            "xgboost": {}
        }
    }
    
    # Generate future dates
    last_date = df['date'].iloc[-1]
    future_dates = [(last_date + timedelta(days=i+1)).strftime('%Y-%m-%d') for i in range(DAYS_TO_PREDICT)]
    output['dates'] = future_dates
    
    for metric in metrics:
        # Pre-process: Handle NaNs, cumulative vs daily?
        # The DB stores Cumulative stats usually.
        # If we predict cumulative, it's easier (always going up).
        # Let's predict cumulative.
        
        series = df[metric].fillna(0)
        
        # 1. MA
        ma_pred = moving_average_forecast(series, window=7, horizon=DAYS_TO_PREDICT)
        output['predictions']['ma'][metric] = [max(0, round(x)) if metric != 'revenue' else max(0, round(x, 2)) for x in ma_pred]
        
        # 2. WMA
        wma_pred = weighted_moving_average_forecast(series, window=30, horizon=DAYS_TO_PREDICT)
        output['predictions']['wma'][metric] = [max(0, round(x)) if metric != 'revenue' else max(0, round(x, 2)) for x in wma_pred]
        
        # 3. XGBoost
        xgb_pred = xgboost_forecast(df, metric, horizon=DAYS_TO_PREDICT)
        output['predictions']['xgboost'][metric] = [max(0, round(x)) if metric != 'revenue' else max(0, round(x, 2)) for x in xgb_pred]

    # Save to JSON
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    logging.info(f"Predictions saved to {OUTPUT_PATH}")

if __name__ == "__main__":
    logging.info("Starting Prediction Engine...")
    generate_predictions()
