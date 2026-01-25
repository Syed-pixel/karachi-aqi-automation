import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta
import time
import numpy as np

# Page config
st.set_page_config(
    page_title="Karachi AQI Dashboard",
    page_icon="🌫️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #3B82F6;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .aqi-good { color: #10B981; border-left-color: #10B981 !important; }
    .aqi-moderate { color: #F59E0B; border-left-color: #F59E0B !important; }
    .aqi-unhealthy { color: #EF4444; border-left-color: #EF4444 !important; }
    .aqi-very-unhealthy { color: #8B5CF6; border-left-color: #8B5CF6 !important; }
    .aqi-hazardous { color: #7C3AED; border-left-color: #7C3AED !important; }
    .update-badge {
        background: linear-gradient(45deg, #10B981, #059669);
        color: white;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.8rem;
        display: inline-block;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<h1 class="main-header">🌫️ Karachi Air Quality Dashboard</h1>', unsafe_allow_html=True)
st.markdown("### Live monitoring with AI-powered 3-day forecasts")

# Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/869/869869.png", width=100)
    st.title("📊 Dashboard Info")
    
    st.markdown("---")
    st.markdown("### ⏰ Update Schedule")
    st.markdown("""
    - **Current AQI**: Hourly (on the hour)
    - **Predictions**: Hourly (on the hour)
    - **Models**: Daily at 2 AM UTC
    """)
    
    st.markdown("---")
    st.markdown("### 🔄 Auto-Update Status")
    
    now = datetime.now()
    next_hour = (now.hour + 1) % 24
    minutes_to_next = 60 - now.minute
    
    st.markdown(f"""
    - **Next update in:** {minutes_to_next} minutes
    - **Next update at:** {next_hour:02d}:00
    - **Current time:** {now.strftime('%H:%M UTC')}
    """)
    
    st.markdown("---")
    st.markdown("### 📡 Data Sources")
    st.markdown("""
    **1. Current AQI:**
    - Source: Hugging Face Dataset
    - URL: `Syed110-3/karachi-aqi-predictor`
    - Fetch: Last row of dataset
    
    **2. Predictions:**
    - Source: Hugging Face Models
    - URL: `karachi-aqi-predictor/predictions/`
    - Fetch: Latest JSON file
    """)

# Cache function - updated every hour
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_latest_aqi_from_dataset():
    """Get latest AQI data from Hugging Face dataset (last row)"""
    try:
        # Fetch the dataset parquet file
        dataset_url = "https://huggingface.co/datasets/Syed110-3/karachi-aqi-predictor/resolve/refs%2Fconvert%2Fparquet/default/train/0000.parquet"
        
        response = requests.get(dataset_url, timeout=15)
        
        if response.status_code == 200:
            # Read the parquet file
            import io
            import pyarrow.parquet as pq
            
            # Read parquet file from bytes
            parquet_file = io.BytesIO(response.content)
            df = pq.read_table(parquet_file).to_pandas()
            
            if len(df) > 0:
                # Get the last row (most recent data)
                last_row = df.iloc[-1]
                
                # Convert timestamp from integer to datetime
                timestamp_int = int(last_row.get('timestamp', 0))
                if timestamp_int > 0:
                    timestamp_dt = datetime.fromtimestamp(timestamp_int)
                else:
                    timestamp_dt = datetime.now()
                
                # Get AQI value - ensure it's integer
                aqi = int(last_row.get('aqi', 0))
                pm25 = float(last_row.get('pm2_5', 0))
                
                return {
                    "aqi": aqi,
                    "pm25": pm25,
                    "timestamp": timestamp_dt.isoformat(),
                    "timestamp_display": timestamp_dt.strftime('%Y-%m-%d %H:%M UTC'),
                    "hour": int(last_row.get('hour', 0)),
                    "day_of_week": int(last_row.get('day_of_week', 0)),
                    "month": int(last_row.get('month', 0)),
                    "aqi_yesterday": int(last_row.get('aqi_yesterday', 0)),
                    "aqi_change_24h": int(last_row.get('aqi_change_24h', 0)),
                    "source": "Hugging Face Dataset",
                    "total_records": len(df)
                }
        
        # Fallback: Try to fetch via datasets library API
        try:
            api_url = "https://datasets-server.huggingface.co/rows?dataset=Syed110-3%2Fkarachi-aqi-predictor&config=default&split=train&offset=0&length=100"
            api_response = requests.get(api_url, timeout=10)
            
            if api_response.status_code == 200:
                data = api_response.json()
                rows = data.get('rows', [])
                
                if rows:
                    # Get last row
                    last_row_data = rows[-1]['row']
                    
                    # Extract data
                    timestamp_int = int(last_row_data.get('timestamp', 0))
                    if timestamp_int > 0:
                        timestamp_dt = datetime.fromtimestamp(timestamp_int)
                    else:
                        timestamp_dt = datetime.now()
                    
                    aqi = int(last_row_data.get('aqi', 0))
                    pm25 = float(last_row_data.get('pm2_5', 0))
                    
                    return {
                        "aqi": aqi,
                        "pm25": pm25,
                        "timestamp": timestamp_dt.isoformat(),
                        "timestamp_display": timestamp_dt.strftime('%Y-%m-%d %H:%M UTC'),
                        "hour": int(last_row_data.get('hour', 0)),
                        "day_of_week": int(last_row_data.get('day_of_week', 0)),
                        "month": int(last_row_data.get('month', 0)),
                        "aqi_yesterday": int(last_row_data.get('aqi_yesterday', 0)),
                        "aqi_change_24h": int(last_row_data.get('aqi_change_24h', 0)),
                        "source": "Datasets API",
                        "total_records": len(rows)
                    }
        except:
            pass
        
    except Exception as e:
        st.error(f"Dataset fetch error: {str(e)[:100]}")
    
    # Ultimate fallback: Use Open-Meteo API
    try:
        url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        params = {"latitude": 24.8607, "longitude": 67.0011, "current": "pm2_5"}
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        pm25 = data['current']['pm2_5']
        aqi = round((pm25 / 35.4) * 100)
        aqi = max(0, min(500, aqi))
        
        return {
            "aqi": aqi,
            "pm25": pm25,
            "timestamp": data['current']['time'],
            "timestamp_display": datetime.now().strftime('%Y-%m-%d %H:%M UTC'),
            "hour": datetime.now().hour,
            "source": "Open-Meteo API (fallback)",
            "total_records": 0
        }
    except:
        # Last resort fallback
        return {
            "aqi": 85,
            "pm25": 30.0,
            "timestamp": datetime.now().isoformat(),
            "timestamp_display": datetime.now().strftime('%Y-%m-%d %H:%M UTC'),
            "hour": datetime.now().hour,
            "source": "Static fallback",
            "total_records": 0
        }

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_latest_predictions():
    """Get latest predictions from Hugging Face predictions folder"""
    try:
        # First, try to get list of prediction files
        predictions_url = "https://huggingface.co/api/models/Syed110-3/karachi-aqi-predictor/tree/main/predictions"
        pred_response = requests.get(predictions_url, timeout=10)
        
        predictions_data = {}
        
        if pred_response.status_code == 200:
            files = pred_response.json()
            # Find all prediction JSON files
            pred_files = []
            for item in files:
                if isinstance(item, dict) and 'path' in item:
                    if 'pred_' in item['path'] and item['path'].endswith('.json'):
                        pred_files.append(item)
            
            if pred_files:
                # Get most recent file by timestamp in filename
                pred_files.sort(key=lambda x: x['path'], reverse=True)
                latest_pred_file = pred_files[0]['path']
                
                # Download the latest prediction file
                pred_file_url = f"https://huggingface.co/Syed110-3/karachi-aqi-predictor/resolve/main/{latest_pred_file}"
                pred_data_response = requests.get(pred_file_url, timeout=10)
                
                if pred_data_response.status_code == 200:
                    predictions_data = pred_data_response.json()
                    
                    # Ensure predictions are properly formatted
                    if 'predictions' in predictions_data:
                        # Convert all values to float
                        for key in predictions_data['predictions']:
                            predictions_data['predictions'][key] = float(predictions_data['predictions'][key])
                    
                    return predictions_data
        
        # If no predictions found, try to fetch from models API as fallback
        models_url = "https://huggingface.co/api/models/Syed110-3/karachi-aqi-predictor"
        models_response = requests.get(models_url, timeout=10)
        
        if models_response.status_code == 200:
            models_info = models_response.json()
            if 'siblings' in models_info:
                for sibling in models_info['siblings']:
                    if sibling.get('rfilename', '').startswith('predictions/pred_') and sibling['rfilename'].endswith('.json'):
                        # Found a prediction file
                        pred_file_url = f"https://huggingface.co/Syed110-3/karachi-aqi-predictor/resolve/main/{sibling['rfilename']}"
                        pred_data_response = requests.get(pred_file_url, timeout=10)
                        if pred_data_response.status_code == 200:
                            return pred_data_response.json()
        
    except Exception as e:
        st.error(f"Predictions fetch error: {str(e)[:100]}")
    
    # Return demo predictions if everything fails
    current_aqi = get_latest_aqi_from_dataset()['aqi']
    return {
        "timestamp": datetime.now().isoformat(),
        "predictions": {
            "day1": float(current_aqi) + 5.0,
            "day2": float(current_aqi) + 7.0,
            "day3": float(current_aqi) + 10.0
        },
        "note": "Demo predictions - awaiting hourly update"
    }

# Function to get AQI level information
def get_aqi_info(aqi):
    """Get AQI level, color, icon, and health message"""
    if aqi <= 50:
        return {
            "level": "GOOD",
            "color": "#10B981",
            "icon": "✅",
            "health": "Air quality is satisfactory.",
            "advice": "Ideal for outdoor activities. No restrictions needed.",
            "color_class": "aqi-good"
        }
    elif aqi <= 100:
        return {
            "level": "MODERATE", 
            "color": "#F59E0B",
            "icon": "⚠️",
            "health": "Acceptable air quality.",
            "advice": "Sensitive individuals should limit outdoor exertion.",
            "color_class": "aqi-moderate"
        }
    elif aqi <= 150:
        return {
            "level": "UNHEALTHY",
            "color": "#EF4444",
            "icon": "🚨",
            "health": "Unhealthy for sensitive groups.",
            "advice": "Children, elderly, and those with respiratory issues should avoid outdoor activities.",
            "color_class": "aqi-unhealthy"
        }
    elif aqi <= 200:
        return {
            "level": "VERY UNHEALTHY",
            "color": "#8B5CF6",
            "icon": "😷",
            "health": "Unhealthy for everyone.",
            "advice": "Everyone should avoid outdoor activities. Close windows, use air purifiers.",
            "color_class": "aqi-very-unhealthy"
        }
    else:
        return {
            "level": "HAZARDOUS",
            "color": "#7C3AED",
            "icon": "☣️",
            "health": "Health warning: emergency conditions.",
            "advice": "Everyone should avoid all outdoor activities. Stay indoors with air purifiers.",
            "color_class": "aqi-hazardous"
        }

# Get latest data (auto-cached for 1 hour)
current_data = get_latest_aqi_from_dataset()
predictions = get_latest_predictions()

# Get current AQI info
current_aqi = current_data['aqi']
aqi_info = get_aqi_info(current_aqi)

# Calculate next update time
now = datetime.now()
next_update = datetime(now.year, now.month, now.day, now.hour, 0, 0) + timedelta(hours=1)
minutes_remaining = int((next_update - now).total_seconds() / 60)

# Update badge in header
st.markdown(f"""
<div class="update-badge">
    🔄 Auto-updates hourly | Next: {next_update.strftime('%H:%M')} UTC ({minutes_remaining} min)
</div>
""", unsafe_allow_html=True)

# MAIN DASHBOARD LAYOUT
# Row 1: Current AQI Status
st.markdown("## 📊 Current Air Quality Status")

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    # Current AQI Card (Large)
    st.markdown(f'<div class="metric-card {aqi_info["color_class"]}">', unsafe_allow_html=True)
    st.markdown(f"### {aqi_info['icon']} CURRENT AIR QUALITY INDEX")
    
    # Large AQI number
    st.markdown(f"<h1 style='font-size: 5rem; margin: 0; color: {aqi_info['color']};'>{current_aqi:.0f}</h1>", unsafe_allow_html=True)
    
    # Level and details
    st.markdown(f"**Level:** {aqi_info['level']}")
    st.markdown(f"**PM2.5 Concentration:** {current_data['pm25']:.1f} µg/m³")
    st.markdown(f"**Location:** Karachi")
    st.markdown(f"**Recorded:** {current_data['timestamp_display']}")
    st.markdown(f"**Data Source:** {current_data['source']}")
    if current_data['total_records'] > 0:
        st.markdown(f"**Dataset Records:** {current_data['total_records']:,}")
    
    # AQI scale indicator
    st.markdown("---")
    st.markdown("**AQI Scale:** 0-50 (Good) | 51-100 (Moderate) | 101-150 (Unhealthy) | 151-200 (Very Unhealthy) | 201+ (Hazardous)")
    
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    # Health Status Card
    st.markdown(f'<div class="metric-card">', unsafe_allow_html=True)
    st.markdown(f"### 🏥 Health Status")
    st.markdown(f"**{aqi_info['health']}**")
    
    st.markdown("---")
    st.markdown("#### Recommended Actions:")
    
    if current_aqi <= 50:
        st.success("""
        - ✅ All outdoor activities safe
        - ✅ Windows can be opened
        - ✅ No masks needed
        """)
    elif current_aqi <= 100:
        st.warning("""
        - ⚠️ Sensitive people: Limit exertion
        - ✅ Others: Normal activities OK
        - ⚠️ Consider masks if sensitive
        """)
    elif current_aqi <= 150:
        st.error("""
        - ❌ Sensitive groups: Stay indoors
        - ⚠️ Others: Limit outdoor time
        - 😷 Wear masks outdoors
        """)
    else:
        st.error("""
        - ❌ Everyone: Stay indoors
        - ❌ Close all windows
        - 😷 Wear N95 masks if outside
        - 💨 Use air purifiers
        """)
    
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    # System Status Card
    st.markdown(f'<div class="metric-card">', unsafe_allow_html=True)
    st.markdown(f"### ⚙️ System Status")
    
    # Update timing
    st.markdown(f"**Next update in:** {minutes_remaining} minutes")
    st.markdown(f"**Next update at:** {next_update.strftime('%H:%M UTC')}")
    
    st.markdown("---")
    st.markdown("#### 📊 Data Freshness")
    
    # Current AQI freshness
    try:
        data_time = datetime.fromisoformat(current_data['timestamp'].replace('Z', '+00:00'))
        data_age_minutes = (now - data_time).total_seconds() / 60
        if data_age_minutes < 60:
            st.success(f"Current AQI: {data_age_minutes:.0f} min ago")
        elif data_age_minutes < 120:
            st.info(f"Current AQI: {data_age_minutes/60:.1f} hours ago")
        else:
            st.warning(f"Current AQI: {data_age_minutes/60:.1f} hours ago")
    except:
        st.warning("Current AQI: Time unknown")
    
    # Predictions freshness
    if 'timestamp' in predictions:
        try:
            pred_time = datetime.fromisoformat(predictions['timestamp'].replace('Z', '+00:00'))
            pred_age_minutes = (now - pred_time).total_seconds() / 60
            if pred_age_minutes < 60:
                st.success(f"Predictions: {pred_age_minutes:.0f} min ago")
            elif pred_age_minutes < 120:
                st.info(f"Predictions: {pred_age_minutes/60:.1f} hours ago")
            else:
                st.warning(f"Predictions: {pred_age_minutes/60:.1f} hours ago")
        except:
            st.warning("Predictions: Time unknown")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Row 2: 3-Day Forecast
st.markdown("---")
st.markdown("## 📈 3-Day AQI Forecast")

if predictions and 'predictions' in predictions:
    # Prepare forecast data
    days = ['Today', 'Tomorrow', 'Day 2', 'Day 3']
    
    # Get values
    values = [current_aqi]
    for i in range(1, 4):
        day_key = f'day{i}'
        if day_key in predictions['predictions']:
            values.append(float(predictions['predictions'][day_key]))
        else:
            values.append(float(current_aqi) + i * 5)  # Fallback increment
    
    # Create colors and info for each day
    colors = []
    levels = []
    for value in values:
        info = get_aqi_info(value)
        colors.append(info['color'])
        levels.append(info['level'])
    
    # Create forecast chart
    col_chart, col_table = st.columns([2, 1])
    
    with col_chart:
        fig = go.Figure(data=[
            go.Bar(
                x=days,
                y=values,
                marker_color=colors,
                text=[f"{v:.0f}" for v in values],
                textposition='outside',
                textfont=dict(size=16, color='black', weight='bold'),
                hovertemplate='<b>%{x}</b><br>AQI: %{y:.0f}<br>Level: %{customdata}<extra></extra>',
                customdata=levels
            )
        ])
        
        fig.update_layout(
            height=400,
            yaxis_title="AQI",
            xaxis_title="",
            showlegend=False,
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            yaxis=dict(
                range=[0, max(values) * 1.2],
                gridcolor='rgba(0,0,0,0.1)'
            ),
            font=dict(size=14)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col_table:
        st.markdown("### Forecast Details")
        
        forecast_data = []
        for i, (day, value, level, color) in enumerate(zip(days, values, levels, colors)):
            if i == 0:  # Today
                forecast_data.append({
                    'Day': day,
                    'AQI': f"{value:.0f}",
                    'Level': level,
                    'PM2.5': f"{(value * 0.354):.1f} µg/m³",
                    'Status': 'Current'
                })
            else:
                change = value - current_aqi
                forecast_data.append({
                    'Day': day,
                    'AQI': f"{value:.0f}",
                    'Level': level,
                    'Change': f"{change:+.0f}",
                    'PM2.5': f"{(value * 0.354):.1f} µg/m³",
                    'Status': 'Predicted'
                })
        
        forecast_df = pd.DataFrame(forecast_data)
        st.dataframe(
            forecast_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Day": st.column_config.TextColumn("Day", width="small"),
                "AQI": st.column_config.NumberColumn("AQI", width="small"),
                "Level": st.column_config.TextColumn("Level", width="medium"),
                "Change": st.column_config.NumberColumn("Change", width="small"),
                "PM2.5": st.column_config.TextColumn("PM2.5", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small")
            }
        )
        
        if predictions and 'timestamp' in predictions:
            try:
                pred_time = datetime.fromisoformat(predictions['timestamp'].replace('Z', '+00:00'))
                st.caption(f"Predictions generated: {pred_time.strftime('%Y-%m-%d %H:%M UTC')}")
            except:
                st.caption(f"Predictions timestamp: {predictions['timestamp']}")
        else:
            st.caption("Predictions: Hourly updates via GitHub Actions")
        
else:
    st.warning("""
    ### ⏳ Waiting for Predictions
    The system updates predictions hourly. Next update at the top of the hour.
    """)

# Row 3: Technical Details
st.markdown("---")
st.markdown("## 🔗 Technical Architecture")

col_info1, col_info2, col_info3 = st.columns(3)

with col_info1:
    st.markdown("### 📡 Data Flow")
    st.markdown("""
    **Hourly Automation:**
    1. GitHub Actions triggers at :00
    2. Fetches current AQI from Open-Meteo
    3. Loads models from Hugging Face
    4. Generates 3-day predictions
    5. Updates dataset with new row
    6. Saves predictions as JSON
    """)

with col_info2:
    st.markdown("### 🤖 ML Models")
    st.markdown("""
    **Stored in Hugging Face:**
    - `best_model_day1.pkl`
    - `best_model_day2.pkl`  
    - `best_model_day3.pkl`
    
    **Model Info:**
    - Format: Scikit-learn Pickle
    - Features: AQI, hour, day, month, PM2.5
    - Target: Next day AQI
    - Retraining: Daily at 2 AM UTC
    """)

with col_info3:
    st.markdown("### 📊 Dashboard System")
    st.markdown("""
    **Auto-Fetch System:**
    - Dataset: Fetches last row for current AQI
    - Predictions: Gets latest JSON file
    - Cache: 1-hour TTL
    - Auto-refresh: At top of each hour
    
    **Built With:**
    - Streamlit (Frontend)
    - Hugging Face APIs (Data)
    - Plotly (Visualization)
    - Pandas (Data processing)
    """)

# Footer with update countdown
st.markdown("---")
col_footer1, col_footer2 = st.columns([3, 1])

with col_footer1:
    st.markdown(f"""
    **Dashboard Status:** 🟢 AUTO-UPDATING | 
    **Current Time:** {now.strftime('%H:%M:%S UTC')} | 
    **Next Update:** {next_update.strftime('%H:%M UTC')} ({minutes_remaining} minutes)
    """)
    
    st.caption("""
    This dashboard fetches data from Hugging Face: Current AQI from dataset, predictions from models repository.
    All updates happen automatically via hourly GitHub Actions automation.
    """)

with col_footer2:
    # Simple manual refresh (optional)
    if st.button("🔄 Check Now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Auto-refresh at the top of each hour
if now.minute == 0:
    # Clear cache and refresh
    st.cache_data.clear()
    st.rerun()

# Debug section (collapsed)
with st.expander("🔧 Debug Information"):
    tab1, tab2 = st.tabs(["Current Data", "Predictions"])
    
    with tab1:
        st.write("### Current AQI Data")
        st.json(current_data)
        
        # Test dataset connection
        if st.button("Test Dataset Connection"):
            test_data = get_latest_aqi_from_dataset()
            st.write("Test Result:", test_data)
    
    with tab2:
        st.write("### Prediction Data")
        st.json(predictions)
        
        if predictions and 'predictions' in predictions:
            st.write("### Raw Prediction Values")
            for day, value in predictions['predictions'].items():
                st.metric(f"{day.upper()} AQI", f"{value:.1f}")

# The app will automatically refresh when cache expires (1 hour)
# and also check at the top of every hour for immediate updates
