import pandas as pd
import joblib
import json
from huggingface_hub import login, HfApi
from datasets import load_dataset
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
import xgboost as xgb
from datetime import datetime
import os

# Get HF_TOKEN from environment variable
HF_TOKEN = os.getenv("HF_TOKEN")
if not HF_TOKEN:
    raise ValueError("HF_TOKEN environment variable not set")
    
REPO_ID = "Syed110-3/karachi-aqi-predictor"
login(token=HF_TOKEN)

def prepare_data():
    dataset = load_dataset(REPO_ID)
    df = dataset['train'].to_pandas()
    
    for i in range(len(df)):
        if i + 24 < len(df):
            df.loc[i, 'target_day1'] = df.loc[i + 24, 'aqi']
        
        if i + 48 < len(df):
            df.loc[i, 'target_day2'] = df.loc[i + 48, 'aqi']
        
        if i + 72 < len(df):
            df.loc[i, 'target_day3'] = df.loc[i + 72, 'aqi']
    
    df = df.dropna(subset=['target_day1', 'target_day2', 'target_day3'])
    
    print(f"Training on {len(df)} rows with complete targets")
    return df

def train_models():
    df = prepare_data()
    
    X = df[['hour', 'day_of_week', 'month', 'aqi', 'aqi_yesterday', 'aqi_change_24h', 'pm2_5']]
    
    api = HfApi()
    
    for day_num in [1, 2, 3]:
        target_col = f'target_day{day_num}'
        y = df[target_col]
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        models = {
            'RandomForest': RandomForestRegressor(n_estimators=100, random_state=42),
            'Ridge': Ridge(alpha=1.0, random_state=42),
            'XGBoost': xgb.XGBRegressor(n_estimators=100, random_state=42)
        }
        
        best_model = None
        best_name = ""
        best_mae = float('inf')
        
        for name, model in models.items():
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            mae = mean_absolute_error(y_test, y_pred)
            
            if mae < best_mae:
                best_mae = mae
                best_r2 = r2_score(y_test, y_pred)
                best_model = model
                best_name = name
        
        model_filename = f'best_model_day{day_num}.pkl'
        joblib.dump(best_model, model_filename)
        
        api.upload_file(
            path_or_fileobj=model_filename,
            path_in_repo=f"models/best_model_day{day_num}.pkl",
            repo_id=REPO_ID,
            repo_type="model"
        )
        
        model_info = {
            'model_name': best_name,
            'mae': float(best_mae),
            'r2': float(best_r2),
            'features': ['hour', 'day_of_week', 'month', 'aqi', 'aqi_yesterday', 'aqi_change_24h', 'pm2_5'],
            'target': f'target_day{day_num}',
            'trained_at': datetime.now().isoformat(),
            'training_samples': len(df)
        }
        
        info_filename = f'model_info_day{day_num}.json'
        with open(info_filename, 'w') as f:
            json.dump(model_info, f, indent=2)
        
        api.upload_file(
            path_or_fileobj=info_filename,
            path_in_repo=f"models/model_info_day{day_num}.json",
            repo_id=REPO_ID,
            repo_type="model"
        )
        
        print(f"Day {day_num}: {best_name}, MAE={best_mae:.2f}")
    
    print("All models updated in Hugging Face")

if __name__ == "__main__":
    train_models()
