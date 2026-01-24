import requests
import pandas as pd
import joblib
import json
from datetime import datetime
from huggingface_hub import login, HfApi, hf_hub_download
from datasets import load_dataset, Dataset
import os
from dotenv import load_dotenv

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
        'aqi': current_aqi,
        'pm2_5': pm25,
        'hour': dt.hour,
        'day_of_week': dt.weekday(),
        'month': dt.month,
        'year': dt.year,
        'aqi_yesterday': yesterday_aqi,
        'aqi_change_24h': current_aqi - yesterday_aqi
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

def predict():
    features = create_features()
    
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
            predictions[f'day{day}'] = features['aqi']
    
    # Save new data
    dataset = load_dataset(REPO_ID)
    df = dataset['train'].to_pandas()
    
    # Convert timestamp to integer for consistent storage
    dt = pd.to_datetime(features['timestamp'])
    timestamp_int = int(dt.timestamp())
    
    new_row = {
        'id': len(df),
        'timestamp': timestamp_int,  # Store as integer timestamp
        'aqi': features['aqi'],
        'pm2_5': features['pm2_5'],
        'hour': features['hour'],
        'day_of_week': features['day_of_week'],
        'month': features['month'],
        'year': features['year'],
        'aqi_yesterday': features['aqi_yesterday'],
        'aqi_change_24h': features['aqi_change_24h'],
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
    
    # Save predictions
    pred_data = {
        'timestamp': features['timestamp'],
        'predictions': predictions,
        'features': features
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
    print(f"PM2.5: {features['pm2_5']}")
    print(f"Predictions: Day1={predictions['day1']:.1f}, Day2={predictions['day2']:.1f}, Day3={predictions['day3']:.1f}")
    
    return predictions

if __name__ == "__main__":
    predict()
