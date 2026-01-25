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
    .refresh-button {
        background: linear-gradient(45deg, #3B82F6, #1D4ED8);
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 5px;
        cursor: pointer;
        font-weight: bold;
    }
    .refresh-button:hover {
        background: linear-gradient(45deg, #2563EB, #1E40AF);
    }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<h1 class="main-header">🌫️ Karachi Air Quality Dashboard</h1>', unsafe_allow_html=True)
st.markdown("### Real-time monitoring and AI-powered 3-day forecasts")

# Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/869/869869.png", width=100)
    st.title("⚙️ Dashboard Controls")
    
    st.markdown("### Auto-Refresh")
    auto_refresh = st.checkbox("Enable auto-refresh", value=True, help="Automatically refresh data")
    refresh_interval = st.slider("Refresh every (minutes)", 1, 60, 10, help="How often to update data")
    
    if st.button("🔄 Refresh Data Now", use_container_width=True, type="primary"):
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📡 Data Sources")
    st.markdown("""
    - **Current AQI**: Open-Meteo API
    - **Predictions**: Your ML Models
    - **Storage**: Hugging Face Dataset
    """)
    
    st.markdown("---")
    st.markdown("### ⏰ Update Schedule")
    st.markdown("""
    - **Current AQI**: Live (every refresh)
    - **Predictions**: Hourly (on the hour)
    - **Models**: Daily at 2 AM UTC
    """)
    
    st.caption(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")

# Cache functions for performance
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_current_aqi():
    """Get current AQI from Open-Meteo"""
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
            "location": "Karachi (24.86°N, 67.00°E)"
        }
    except Exception as e:
        # Return default values if API fails
        return {
            "aqi": 100,
            "pm25": 35.4,
            "timestamp": datetime.now().isoformat(),
            "location": "Karachi",
            "note": "Using fallback data"
        }

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_latest_predictions():
    """Get latest predictions from Hugging Face"""
    try:
        # Try to find prediction files
        try:
            # Get list of files in predictions folder
            api_url = "https://huggingface.co/api/datasets/Syed110-3/karachi-aqi-predictor/tree/main/predictions"
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                files = response.json()
                
                # Find prediction JSON files
                pred_files = []
                for item in files:
                    if isinstance(item, dict) and 'path' in item:
                        if 'pred_' in item['path'] and item['path'].endswith('.json'):
                            pred_files.append(item)
                
                if pred_files:
                    # Get the most recent file
                    latest_file = max(pred_files, key=lambda x: x.get('lastCommit', {}).get('date', ''))
                    file_url = f"https://huggingface.co/datasets/Syed110-3/karachi-aqi-predictor/raw/main/{latest_file['path']}"
                    
                    pred_response = requests.get(file_url, timeout=10)
                    if pred_response.status_code == 200:
                        prediction_data = pred_response.json()
                        return prediction_data
        except:
            pass
        
        # If no predictions found, check for any JSON file in root
        try:
            root_files_url = "https://huggingface.co/api/datasets/Syed110-3/karachi-aqi-predictor/tree/main"
            response = requests.get(root_files_url, timeout=10)
            
            if response.status_code == 200:
                files = response.json()
                json_files = [f for f in files if isinstance(f, dict) and f.get('path', '').endswith('.json')]
                
                if json_files:
                    # Try each JSON file
                    for file_info in json_files:
                        try:
                            file_url = f"https://huggingface.co/datasets/Syed110-3/karachi-aqi-predictor/raw/main/{file_info['path']}"
                            pred_response = requests.get(file_url, timeout=10)
                            data = pred_response.json()
                            if 'predictions' in data:
                                return data
                        except:
                            continue
        except:
            pass
        
        # If still no predictions, create demo data
        return {
            "timestamp": datetime.now().isoformat(),
            "predictions": {
                "day1": 85.5,
                "day2": 87.2,
                "day3": 89.8
            },
            "note": "Demo predictions - real data will appear after first hourly run"
        }
        
    except Exception as e:
        # Return demo data on error
        return {
            "timestamp": datetime.now().isoformat(),
            "predictions": {
                "day1": 85.5,
                "day2": 87.2,
                "day3": 89.8
            },
            "note": f"Error: {str(e)[:50]}..."
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

# Get current data
current_data = get_current_aqi()
predictions = get_latest_predictions()

# Get current AQI info
current_aqi = current_data['aqi']
aqi_info = get_aqi_info(current_aqi)

# MAIN DASHBOARD LAYOUT
# Row 1: Current AQI Status
st.markdown("## 📊 Current Air Quality Status")

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    # Current AQI Card (Large)
    st.markdown(f'<div class="metric-card {aqi_info["color_class"]}">', unsafe_allow_html=True)
    st.markdown(f"### {aqi_info['icon']} CURRENT AIR QUALITY INDEX")
    
    # Large AQI number
    st.markdown(f"<h1 style='font-size: 5rem; margin: 0; color: {aqi_info['color']};'>{current_aqi}</h1>", unsafe_allow_html=True)
    
    # Level and details
    st.markdown(f"**Level:** {aqi_info['level']}")
    st.markdown(f"**PM2.5 Concentration:** {current_data['pm25']:.1f} µg/m³")
    st.markdown(f"**Location:** {current_data['location']}")
    st.markdown(f"**Last Updated:** {current_data['timestamp'][11:19]} UTC")
    
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
    # Next Update Info
    st.markdown(f'<div class="metric-card">', unsafe_allow_html=True)
    st.markdown(f"### ⏰ Next Updates")
    
    now = datetime.now()
    next_hour = (now.hour + 1) % 24
    next_daily = "02:00"  # 2 AM UTC
    
    st.markdown(f"**Next Prediction:** {next_hour:02d}:00 UTC")
    st.markdown(f"**Next Model Update:** {next_daily} UTC")
    
    st.markdown("---")
    st.markdown("#### 🚀 Automation Status")
    
    if 'note' in predictions and 'Demo' in predictions['note']:
        st.warning("Waiting for first prediction run")
    else:
        st.success("✅ Automation Active")
    
    if predictions and 'timestamp' in predictions:
        pred_time = datetime.fromisoformat(predictions['timestamp'].replace('Z', '+00:00'))
        time_diff = (now - pred_time).total_seconds() / 3600
        
        if time_diff < 2:
            st.success(f"Predictions: {time_diff:.1f} hours ago")
        elif time_diff < 6:
            st.warning(f"Predictions: {time_diff:.1f} hours ago")
        else:
            st.error(f"Predictions: {time_diff:.1f} hours ago")
    
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
            values.append(predictions['predictions'][day_key])
        else:
            values.append(current_aqi)  # Fallback
    
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
                hovertemplate='<b>%{x}</b><br>AQI: %{y:.0f}<br>Level: ' + 
                             ['Today: ' + levels[0], 'Tomorrow: ' + levels[1], 
                              'Day 2: ' + levels[2], 'Day 3: ' + levels[3]] + 
                             '<extra></extra>'
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
            pred_time = datetime.fromisoformat(predictions['timestamp'].replace('Z', '+00:00'))
            st.caption(f"Predictions generated: {pred_time.strftime('%Y-%m-%d %H:%M UTC')}")
        
else:
    # No predictions available yet
    st.warning("""
    ### ⏳ Waiting for Predictions
    
    Your hourly automation needs to run at least once to generate predictions.
    
    **What's happening:**
    1. Your GitHub Actions workflow runs every hour
    2. It fetches current AQI and makes predictions
    3. It saves predictions to Hugging Face
    4. This dashboard will automatically show them here
    
    **Check:**
    - Is your hourly workflow running?
    - Are predictions being saved to Hugging Face?
    - Check the next hour (:00) for updates
    """)

# Row 3: Data Sources and Info
st.markdown("---")
st.markdown("## 🔗 Data & System Information")

col_info1, col_info2, col_info3 = st.columns(3)

with col_info1:
    st.markdown("### 📡 Live Data Sources")
    st.markdown("""
    **Current AQI:**
    - Source: Open-Meteo Air Quality API
    - Update: Real-time (every refresh)
    - Location: Karachi (24.86°N, 67.00°E)
    - Metric: PM2.5 → AQI conversion
    
    **Predictions:**
    - Source: Your trained ML models
    - Update: Hourly (on the hour)
    - Models: RandomForest, XGBoost, Ridge
    - Storage: Hugging Face dataset
    """)

with col_info2:
    st.markdown("### ⚙️ Automation System")
    st.markdown("""
    **GitHub Actions:**
    - Hourly: Fetch AQI + Make predictions
    - Daily: Retrain models (2 AM UTC)
    - Auto: Push to Hugging Face
    
    **ML Pipeline:**
    - Features: Hour, Day, AQI history, PM2.5
    - Target: AQI for next 72 hours
    - Best model: Selected by lowest MAE
    
    **Tech Stack:**
    - Python, Scikit-learn, XGBoost
    - GitHub Actions, Hugging Face
    - Streamlit (this dashboard)
    """)

with col_info3:
    st.markdown("### 📊 AQI Reference")
    st.markdown("""
    **AQI Levels:**
    - **0-50 (Good):** ✅ Air quality satisfactory
    - **51-100 (Moderate):** ⚠️ Acceptable quality
    - **101-150 (Unhealthy):** 🚨 Sensitive groups affected
    - **151-200 (Very Unhealthy):** 😷 Everyone affected
    - **201+ (Hazardous):** ☣️ Health warnings
    
    **PM2.5 to AQI:**
    - Formula: AQI = (PM2.5 / 35.4) × 100
    - Standard: US EPA AQI scale
    - Health: Based on 24-hour exposure
    """)

# Footer
st.markdown("---")
col_footer1, col_footer2 = st.columns([3, 1])

with col_footer1:
    st.markdown(f"""
    **Dashboard Status:** {'🟢 LIVE' if current_data['aqi'] > 0 else '🟡 LOADING'} | 
    **Last Refresh:** {datetime.now().strftime('%H:%M:%S UTC')} | 
    **Next Auto-Refresh:** {refresh_interval} minutes
    """)
    
    st.caption("""
    This dashboard shows real-time Air Quality Index (AQI) for Karachi with AI-powered 3-day forecasts.
    Data updates automatically via your GitHub Actions automation pipeline.
    """)

with col_footer2:
    if st.button("🔄 Manual Refresh", use_container_width=True):
        st.rerun()

# Debug section (collapsed by default)
with st.expander("🔧 Debug & Raw Data"):
    tab1, tab2 = st.tabs(["Current Data", "Predictions"])
    
    with tab1:
        st.write("### Current AQI Data")
        st.json(current_data)
        
        st.write("### API Response Time")
        start_time = time.time()
        test_response = requests.get("https://air-quality-api.open-meteo.com/v1/air-quality?latitude=24.8607&longitude=67.0011&current=pm2_5", timeout=5)
        response_time = (time.time() - start_time) * 1000
        st.metric("API Response Time", f"{response_time:.0f} ms")
    
    with tab2:
        st.write("### Prediction Data")
        st.json(predictions)
        
        if predictions and 'predictions' in predictions:
            st.write("### Prediction Values")
            for day, value in predictions['predictions'].items():
                st.metric(f"{day.upper()} AQI", f"{value:.1f}")

# Auto-refresh logic
if auto_refresh:
    time.sleep(refresh_interval * 60)
    st.rerun()
