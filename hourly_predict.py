import requests
import pandas as pd
import joblib
import json
from datetime import datetime, timedelta
from huggingface_hub import login, HfApi, hf_hub_download
from datasets import load_dataset, Dataset
import os
from dotenv import load_dotenv
import numpy as np

# Load environment variables
load_dotenv()

# Get HF_TOKEN from environment variable
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise ValueError("HF_TOKEN not found. Create .env file with HF_TOKEN=your_token")

REPO_ID = "Syed110-3/karachi-aqi-predictor"
login(token=HF_TOKEN)

def get_current_aqi():
    url = "https://air-quality-api.open-meteo.com/v1/air-quality"
    params = {"latitude": 24.8607, "longitude": 67.0011, "current": "pm2_5"}
    
    try:
        data = requests.get(url, params=params, timeout=5).json()
        pm25 = data['current']['pm2_5']
        timestamp = data['current']['time']
        aqi = round((pm25 / 35.4) * 100)
        return max(0, min(500, aqi)), timestamp, pm25
    except:
        return 100, datetime.now().isoformat(), 35.4

def get_yesterday_aqi():
    try:
        dataset = load_dataset(REPO_ID)
        df = dataset['train'].to_pandas()
        if len(df) >= 24:
            return df['aqi'].iloc[-24]
        return None
    except:
        return None

def create_features():
    current_aqi, current_time, pm25 = get_current_aqi()
    dt = pd.to_datetime(current_time)
    
    yesterday_aqi = get_yesterday_aqi() or current_aqi
    
    features = {
        'timestamp': dt.isoformat(),
        'aqi': int(current_aqi),  # Convert to int
        'pm2_5': float(pm25),     # Convert to float
        'hour': int(dt.hour),
        'day_of_week': int(dt.weekday()),
        'month': int(dt.month),
        'year': int(dt.year),
        'aqi_yesterday': int(yesterday_aqi),
        'aqi_change_24h': int(current_aqi - yesterday_aqi)
    }
    
    return features

def load_model(day_num):
    try:
        model_path = hf_hub_download(
            repo_id=REPO_ID,
            filename=f"models/best_model_day{day_num}.pkl",
            token=HF_TOKEN
        )
        return joblib.load(model_path)
    except:
        return None

def fill_previous_targets(df, current_aqi):
    """Fill target_day1, target_day2, target_day3 for old records"""
    now = datetime.now()
    current_ts = int(now.timestamp())
    updated = 0
    
    for idx, row in df.iterrows():
        # FIX: Handle different timestamp formats
        row_ts = row['timestamp']
        
        # Convert to integer timestamp
        if isinstance(row_ts, (pd.Timestamp, datetime)):
            row_ts = int(row_ts.timestamp())
        elif isinstance(row_ts, str):
            try:
                row_ts = int(float(row_ts))
            except:
                continue
        else:
            # Assume it's already integer/float
            try:
                row_ts = int(row_ts)
            except:
                continue
        
        hours_ago = (current_ts - row_ts) / 3600
        
        # Fill target_day1 for records ~24 hours old
        if 23 <= hours_ago <= 25:
            if pd.isna(row.get('target_day1')):
                df.at[idx, 'target_day1'] = float(current_aqi)
                updated += 1
        
        # Fill target_day2 for records ~48 hours old
        elif 47 <= hours_ago <= 49:
            if pd.isna(row.get('target_day2')):
                df.at[idx, 'target_day2'] = float(current_aqi)
                updated += 1
        
        # Fill target_day3 for records ~72 hours old
        elif 71 <= hours_ago <= 73:
            if pd.isna(row.get('target_day3')):
                df.at[idx, 'target_day3'] = float(current_aqi)
                updated += 1
    
    if updated > 0:
        print(f"Filled {updated} target values from past records")
    
    return df, updated

def predict():
    features = create_features()
    current_aqi = features['aqi']
    
    # Prepare input for model
    input_df = pd.DataFrame([{
        'hour': features['hour'],
        'day_of_week': features['day_of_week'],
        'month': features['month'],
        'aqi': features['aqi'],
        'aqi_yesterday': features['aqi_yesterday'],
        'aqi_change_24h': features['aqi_change_24h'],
        'pm2_5': features['pm2_5']
    }])
    
    predictions = {}
    for day in [1, 2, 3]:
        model = load_model(day)
        if model:
            pred = model.predict(input_df)[0]
            predictions[f'day{day}'] = float(pred)
        else:
            predictions[f'day{day}'] = float(features['aqi'])
    
    # Load dataset and fill previous targets
    dataset = load_dataset(REPO_ID)
    df = dataset['train'].to_pandas()
    
    # Fill target values for old records
    df, updated_count = fill_previous_targets(df, current_aqi)
    
    # Convert timestamp to integer for consistent storage
    dt = pd.to_datetime(features['timestamp'])
    timestamp_int = int(dt.timestamp())
    
    new_row = {
        'id': int(len(df)),
        'timestamp': int(timestamp_int),  # Store as int
        'aqi': int(features['aqi']),
        'pm2_5': float(features['pm2_5']),
        'hour': int(features['hour']),
        'day_of_week': int(features['day_of_week']),
        'month': int(features['month']),
        'year': int(features['year']),
        'aqi_yesterday': int(features['aqi_yesterday']),
        'aqi_change_24h': int(features['aqi_change_24h']),
        'target_day1': None,
        'target_day2': None,
        'target_day3': None
    }
    
    # FIXED: Use pd.concat instead of append
    new_df = pd.DataFrame([new_row])
    df = pd.concat([df, new_df], ignore_index=True)
    
    # Convert to dataset and push
    dataset = Dataset.from_pandas(df)
    dataset.push_to_hub(REPO_ID)
    
    # Save predictions - convert all numpy types to Python native types
    pred_data = {
        'timestamp': str(features['timestamp']),  # Keep as string
        'predictions': {k: float(v) for k, v in predictions.items()},
        'features': features,
        'targets_updated': updated_count
    }
    
    api = HfApi()
    api.upload_file(
        path_or_fileobj=json.dumps(pred_data, indent=2).encode(),
        path_in_repo=f"predictions/pred_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
        repo_id=REPO_ID,
        repo_type="model"
    )
    
    print(f"Hourly update: {features['timestamp']}")
    print(f"Current AQI: {features['aqi']}")
    print(f"PM2.5: {features['pm2_5']:.1f}")
    print(f"Predictions: Day1={predictions['day1']:.1f}, Day2={predictions['day2']:.1f}, Day3={predictions['day3']:.1f}")
    print(f"Updated {updated_count} target values from past records")
    
    return predictions

if __name__ == "__main__":
    predict()
