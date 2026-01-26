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

# Custom CSS - ADD LOADING ANIMATION
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
    .pipeline-step {
        background: #F1F5F9;
        padding: 10px;
        border-radius: 8px;
        margin: 5px 0;
        border-left: 4px solid #3B82F6;
    }
    .loading-spinner {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 3px solid #f3f3f3;
        border-top: 3px solid #3B82F6;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin-right: 10px;
    }
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
    .prediction-loading {
        background: linear-gradient(45deg, #f0f9ff, #e0f2fe);
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin: 20px 0;
        border: 2px dashed #3B82F6;
    }
    .hourly-badge {
        background: linear-gradient(45deg, #3B82F6, #1D4ED8);
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
st.markdown("### Hourly updates with AI-powered 3-day forecasts")

# Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/869/869869.png", width=100)
    st.title("⚙️ System Status")
    
    st.markdown("---")
    st.markdown("### ⏰ Hourly Update Schedule")
    st.markdown("""
    **All Updates Hourly:**
    - Live AQI: Updated at :00:00 of each hour
    - AI Predictions: Available at :01:30 of each hour
    
    **Dashboard Behavior:**
    - Current AQI: Shows last hourly reading
    - AI Predictions: Shows when available
    - Both update on the same hourly schedule
    """)
    
    st.markdown("---")
    now = datetime.now()
    next_hour = (now.hour + 1) % 24
    minutes_to_next = 60 - now.minute
    
    st.markdown("### 🔄 Next Hourly Update")
    st.markdown(f"""
    - **AQI & Predictions refresh at:** {next_hour:02d}:00:00 UTC
    - **Predictions available at:** {next_hour:02d}:01:30 UTC
    - **Current time:** {now.strftime('%H:%M:%S UTC')}
    - **Minutes until next update:** {minutes_to_next}
    """)
    
    st.markdown("---")
    st.markdown("### 📡 Data Pipeline (Hourly)")
    st.markdown("""
    **:00:00 - Hourly Process Starts:**
    1. Fetch latest AQI from Open-Meteo
    2. Start ML prediction script
    3. Generate 3-day forecasts
    
    **:01:30 - Process Complete:**
    1. Upload predictions to Hugging Face
    2. Dashboard fetches both AQI and predictions
    3. Full update displayed to users
    """)

# Cache functions - BOTH update hourly
@st.cache_data(ttl=3600)  # Cache for 1 hour - AQI updates hourly
def get_current_aqi():
    """Get current AQI from Open-Meteo (hourly API)"""
    try:
        url = "https://air-quality-api.open-meteo.com/v1/air-quality"
        params = {
            "latitude": 24.8607, 
            "longitude": 67.0011, 
            "current": "pm2_5",
            "timezone": "auto"
        }
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        
        pm25 = data['current']['pm2_5']
        aqi = round((pm25 / 35.4) * 100)
        aqi = max(0, min(500, aqi))
        
        # Get timestamp and round to nearest hour for consistency
        timestamp_str = data['current']['time']
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        rounded_timestamp = timestamp.replace(minute=0, second=0, microsecond=0)
        
        return {
            "aqi": aqi,
            "pm25": pm25,
            "timestamp": rounded_timestamp.isoformat(),
            "display_time": rounded_timestamp.strftime('%H:00 UTC'),
            "location": "Karachi (24.86°N, 67.00°E)",
            "source": "Open-Meteo API (Hourly)"
        }
    except Exception as e:
        # Fallback to demo data if API fails
        now_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        return {
            "aqi": 85,
            "pm25": 30.1,
            "timestamp": now_hour.isoformat(),
            "display_time": now_hour.strftime('%H:00 UTC'),
            "location": "Karachi",
            "source": "Fallback Data (API Error)"
        }

# Predictions function with 90-second delay (KEPT SAME)
@st.cache_data(ttl=3600)  # Cache for 1 hour - predictions update hourly
def get_latest_predictions():
    """Get latest predictions from Hugging Face with delay check"""
    now = datetime.now()
    
    # Check if we should wait (if it's within 90 seconds of the hour)
    if now.minute == 0 and now.second < 90:
        return {"status": "waiting", "message": "Predictions being generated...", "retry_after": 90 - now.second}
    
    try:
        # Try to get the latest.json file first
        latest_url = "https://huggingface.co/Syed110-3/karachi-aqi-predictor/resolve/main/predictions/latest.json"
        
        try:
            response = requests.get(latest_url, timeout=15)
            if response.status_code == 200:
                prediction_data = response.json()
                
                # Check if predictions are fresh (within last 2 hours)
                if 'prediction_timestamp' in prediction_data:
                    pred_time = datetime.fromisoformat(prediction_data['prediction_timestamp'].replace('Z', '+00:00'))
                    hours_old = (now - pred_time).total_seconds() / 3600
                    
                    if hours_old < 2:
                        # Ensure all values are proper floats
                        if 'predictions' in prediction_data:
                            for key in prediction_data['predictions']:
                                prediction_data['predictions'][key] = float(prediction_data['predictions'][key])
                        prediction_data['status'] = "success"
                        return prediction_data
                
                # If no timestamp or old, fall through to search for latest
        except:
            pass
        
        # Fallback: Search for most recent prediction file
        api_url = "https://huggingface.co/api/models/Syed110-3/karachi-aqi-predictor/tree/main/predictions"
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            files = response.json()
            
            # Find all prediction JSON files
            pred_files = []
            for item in files:
                if isinstance(item, dict) and 'path' in item:
                    if 'pred_' in item['path'] and item['path'].endswith('.json'):
                        pred_files.append(item)
            
            if pred_files:
                # Get most recent file (sorted by filename which contains timestamp)
                pred_files.sort(key=lambda x: x['path'], reverse=True)
                latest_file = pred_files[0]['path']
                
                # Download the latest prediction file
                file_url = f"https://huggingface.co/Syed110-3/karachi-aqi-predictor/resolve/main/{latest_file}"
                pred_response = requests.get(file_url, timeout=10)
                
                if pred_response.status_code == 200:
                    prediction_data = pred_response.json()
                    prediction_data['status'] = "success"
                    return prediction_data
        
        # If everything fails, return demo data
        return {
            "status": "demo",
            "timestamp": now.isoformat(),
            "predictions": {
                "day1": 88.5,
                "day2": 90.2,
                "day3": 92.8
            },
            "message": "Using demo predictions - check back after the hour"
        }
                
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error: {str(e)[:100]}",
            "timestamp": now.isoformat(),
            "predictions": {
                "day1": 85.0,
                "day2": 86.0,
                "day3": 87.0
            }
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

# Get current AQI (hourly)
current_data = get_current_aqi()
current_aqi = current_data['aqi']
aqi_info = get_aqi_info(current_aqi)

# Get predictions with delay logic
predictions = get_latest_predictions()

# Calculate timing info
now = datetime.now()
current_hour_start = datetime(now.year, now.month, now.day, now.hour, 0, 0)
next_hour_start = current_hour_start + timedelta(hours=1)
predictions_available_time = next_hour_start + timedelta(seconds=90)

# Determine if we should show loading state for predictions
show_loading = False
if now.minute == 0 and now.second < 90:
    show_loading = True
    seconds_remaining = 90 - now.second
elif predictions.get('status') == 'waiting':
    show_loading = True
    seconds_remaining = predictions.get('retry_after', 90)

# Hourly update badge
minutes_until_next_hour = 60 - now.minute
st.markdown(f"""
<div class="hourly-badge">
    ⏰ Hourly Updates | Current AQI as of {current_data['display_time']} | 
    Next update: {next_hour_start.strftime('%H:00 UTC')} ({minutes_until_next_hour} min)
</div>
""", unsafe_allow_html=True)

# MAIN DASHBOARD LAYOUT
# Row 1: Current AQI Status (ALWAYS SHOWN)
st.markdown("## 📊 Current Air Quality Status")

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    # Current AQI Card
    st.markdown(f'<div class="metric-card {aqi_info["color_class"]}">', unsafe_allow_html=True)
    st.markdown(f"### {aqi_info['icon']} HOURLY AIR QUALITY INDEX")
    
    # Large AQI number
    st.markdown(f"<h1 style='font-size: 5rem; margin: 0; color: {aqi_info['color']};'>{current_aqi:.0f}</h1>", unsafe_allow_html=True)
    
    # Level and details
    st.markdown(f"**Level:** {aqi_info['level']}")
    st.markdown(f"**PM2.5 Concentration:** {current_data['pm25']:.1f} µg/m³")
    st.markdown(f"**Location:** {current_data['location']}")
    st.markdown(f"**Recorded:** {current_data['display_time']}")
    st.markdown(f"**Source:** {current_data['source']}")
    
    # Update schedule
    st.markdown("---")
    st.markdown(f"**⏰ Next AQI Update:** {next_hour_start.strftime('%H:00 UTC')} ({minutes_until_next_hour} minutes)")
    
    # AQI scale
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
    # Automation Status Card
    st.markdown(f'<div class="metric-card">', unsafe_allow_html=True)
    st.markdown(f"### 🤖 System Status")
    
    # AQI Update Status
    st.markdown(f"**AQI Updates:** ✅ Hourly")
    st.markdown(f"**Last Update:** {current_data['display_time']}")
    st.markdown(f"**Next Update:** {next_hour_start.strftime('%H:00')} UTC")
    
    st.markdown("---")
    
    # Predictions Status
    if show_loading:
        st.markdown(f"**AI Predictions:** ⏳ Generating...")
        st.markdown(f"**Available in:** {seconds_remaining} seconds")
        st.markdown(f"**Available at:** {predictions_available_time.strftime('%H:%M:%S UTC')}")
        
        # Progress bar
        progress = 1 - (seconds_remaining / 90)
        st.progress(progress, text=f"Generating... {seconds_remaining}s remaining")
    else:
        if predictions.get('status') == 'success' and 'prediction_timestamp' in predictions:
            pred_time = datetime.fromisoformat(predictions['prediction_timestamp'].replace('Z', '+00:00'))
            minutes_old = int((now - pred_time).total_seconds() / 60)
            st.markdown(f"**AI Predictions:** ✅ Available")
            st.markdown(f"**Generated:** {pred_time.strftime('%H:%M:%S UTC')}")
            st.markdown(f"**Age:** {minutes_old} minutes")
        else:
            st.markdown(f"**AI Predictions:** ℹ️ Demo/Historical")
    
    st.markdown("---")
    st.markdown(f"#### 📅 Next Full Update")
    st.markdown(f"**AQI at:** {next_hour_start.strftime('%H:00:00 UTC')}")
    st.markdown(f"**Predictions at:** {next_hour_start.strftime('%H:01:30 UTC')}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Row 2: 3-Day Forecast - WITH LOADING STATE
st.markdown("---")
st.markdown("## 📈 3-Day AQI Forecast")

if show_loading:
    # SHOW LOADING STATE FOR PREDICTIONS
    st.markdown('<div class="prediction-loading">', unsafe_allow_html=True)
    st.markdown(f"### <div class='loading-spinner'></div> AI Predictions Generating")
    
    st.markdown(f"""
    **Status:** Your predictions are being generated right now!
    
    **Hourly Process (starting at {now.replace(second=0).strftime('%H:00:00 UTC')}):**
    1. Fetch latest AQI: ✓
    2. Load ML models: In progress...
    3. Generate predictions: In progress...
    4. Upload to Hugging Face: Waiting...
    
    **Available in:** {seconds_remaining} seconds
    
    **Note:** The page will refresh automatically when ready.
    """)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
elif predictions.get('status') in ['success', 'demo', 'error'] and 'predictions' in predictions:
    # SHOW ACTUAL PREDICTIONS
    # Prepare forecast data
    days = ['Current Hour', 'Next 24h', 'Next 48h', 'Next 72h']
    
    # Get values
    values = [current_aqi]
    for i in range(1, 4):
        day_key = f'day{i}'
        if day_key in predictions['predictions']:
            values.append(float(predictions['predictions'][day_key]))
        else:
            values.append(float(current_aqi) + i * 3)
    
    # Create colors and info for each day
    colors = []
    levels = []
    for value in values:
        info = get_aqi_info(value)
        colors.append(info['color'])
        levels.append(info['level'])
    
    # Forecast chart
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
            if i == 0:
                forecast_data.append({
                    'Period': day,
                    'AQI': f"{value:.0f}",
                    'Level': level,
                    'PM2.5': f"{(value * 0.354):.1f} µg/m³",
                    'Status': 'Current Hourly'
                })
            else:
                change = value - current_aqi
                forecast_data.append({
                    'Period': day,
                    'AQI': f"{value:.0f}",
                    'Level': level,
                    'Change': f"{change:+.0f}",
                    'PM2.5': f"{(value * 0.354):.1f} µg/m³",
                    'Status': 'AI Forecast'
                })
        
        forecast_df = pd.DataFrame(forecast_data)
        st.dataframe(
            forecast_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Period": st.column_config.TextColumn("Period", width="small"),
                "AQI": st.column_config.NumberColumn("AQI", width="small"),
                "Level": st.column_config.TextColumn("Level", width="medium"),
                "Change": st.column_config.NumberColumn("Change", width="small"),
                "PM2.5": st.column_config.TextColumn("PM2.5", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small")
            }
        )
        
        # Show prediction source and timestamp
        if predictions.get('status') == 'success' and 'prediction_timestamp' in predictions:
            pred_time = datetime.fromisoformat(predictions['prediction_timestamp'].replace('Z', '+00:00'))
            st.success(f"✅ AI Forecast generated: {pred_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        elif predictions.get('status') == 'demo':
            st.warning("ℹ️ Using demo forecasts - AI predictions available at :01:30 after each hour")
        elif predictions.get('status') == 'error':
            st.error("⚠️ Error loading AI forecasts - showing demo data")
        else:
            st.info("ℹ️ AI Forecast updates hourly at :01:30")
else:
    # No predictions available at all
    st.warning("""
    ### ⏳ AI Forecast Not Available
    
    **Next forecast generation:**
    - **Starts:** On the next hour (:00:00 UTC)
    - **Available:** ~90 seconds later (:01:30 UTC)
    
    **Current status:**
    - Current AQI: ✅ Available (hourly)
    - AI Predictions: ⏳ Generating on schedule
    """)

# Row 3: System Architecture
st.markdown("---")
st.markdown("## 🔧 System Architecture")

col_info1, col_info2, col_info3 = st.columns(3)

with col_info1:
    st.markdown("### 📡 Hourly Data Pipeline")
    st.markdown("""
    <div class="pipeline-step">
    1. **Hourly Trigger (:00:00)**
    • Fetch latest AQI from Open-Meteo
    • Start ML prediction process
    </div>
    <div class="pipeline-step">
    2. **AI Processing (:00:05 - :01:20)**
    • Load ML models
    • Generate 3-day forecasts
    • Package predictions
    </div>
    <div class="pipeline-step">
    3. **Upload & Availability (:01:30)**
    • Upload to Hugging Face
    • Both AQI and predictions ready
    • Dashboard updates complete
    </div>
    """, unsafe_allow_html=True)

with col_info2:
    st.markdown("### ⏰ Synchronized Updates")
    st.markdown("""
    **Why Hourly Updates?**
    - AQI: Changes gradually over hours
    - Predictions: Based on latest AQI
    - Both need to be synchronized
    
    **Delay Strategy:**
    - AQI fetched at :00:00
    - Predictions ready at :01:30
    - Dashboard shows both together
    - 90-second buffer ensures sync
    
    **User Experience:**
    - Clear loading states
    - No confusing mismatches
    - Predictions always match AQI
    """)

with col_info3:
    st.markdown("### 🚀 System Features")
    st.markdown("""
    **Data Sources:**
    - AQI: Open-Meteo API (hourly)
    - Predictions: Custom ML models
    - Storage: Hugging Face Hub
    
    **Automation:**
    - GitHub Actions hourly triggers
    - Auto-deploy predictions
    - Cache management
    
    **Dashboard:**
    - Real-time status monitoring
    - Health recommendations
    - Forecast visualizations
    - Auto-refresh logic
    """)

# Footer
st.markdown("---")
col_footer1, col_footer2 = st.columns([3, 1])

with col_footer1:
    if show_loading:
        st.markdown(f"""
        **System Status:** ⏳ AI PREDICTIONS GENERATING | 
        **Current AQI:** {current_aqi} ({current_data['display_time']}) | 
        **Predictions available in:** {seconds_remaining} seconds | 
        **System Time:** {now.strftime('%H:%M:%S UTC')}
        """)
    else:
        minutes_until_next = 60 - now.minute
        st.markdown(f"""
        **System Status:** 🟢 HOURLY UPDATES ACTIVE | 
        **Current AQI:** {current_aqi} ({current_data['display_time']}) | 
        **Next full update:** {next_hour_start.strftime('%H:00 UTC')} ({minutes_until_next} min) | 
        **System Time:** {now.strftime('%H:%M:%S UTC')}
        """)
    
    st.caption("""
    Hourly AQI from Open-Meteo API | AI Forecasts from Hugging Face ML Models | 
    Fully automated via GitHub Actions | AQI and predictions synchronized hourly
    """)

# Remove refresh button entirely - updates are hourly only

# Add auto-refresh logic for the loading window
if show_loading:
    # Set a timer to auto-refresh after the waiting period
    if seconds_remaining <= 10:
        # If less than 10 seconds remaining, refresh now
        time.sleep(2)
        st.cache_data.clear()
        st.rerun()

# Debug section
with st.expander("🔧 Debug & Raw Data"):
    tab1, tab2, tab3 = st.tabs(["Hourly AQI", "Predictions", "System"])
    
    with tab1:
        st.write("### Hourly AQI Data")
        st.json(current_data)
        
        st.write("### Timing Info")
        st.write(f"Current time: {now}")
        st.write(f"Current hour start: {current_hour_start}")
        st.write(f"Next hour start: {next_hour_start}")
        st.write(f"Cache TTL: 3600 seconds (1 hour)")
        
        # Test API
        if st.button("Test Open-Meteo API"):
            test_url = "https://air-quality-api.open-meteo.com/v1/air-quality?latitude=24.8607&longitude=67.0011&current=pm2_5&timezone=auto"
            response = requests.get(test_url, timeout=5)
            st.write("Status:", response.status_code)
            st.json(response.json())
    
    with tab2:
        st.write("### AI Forecast Data")
        st.json(predictions)
        
        st.write("### Prediction Timing")
        st.write(f"Show loading: {show_loading}")
        if show_loading:
            st.write(f"Seconds remaining: {seconds_remaining}")
        
        if 'predictions' in predictions:
            st.write("### Forecast Values")
            for day, value in predictions['predictions'].items():
                st.metric(f"{day.upper()} AQI", f"{value:.1f}")
    
    with tab3:
        st.write("### System Info")
        st.metric("Current Time UTC", now.strftime('%Y-%m-%d %H:%M:%S'))
        st.metric("Current Hour Start", current_hour_start.strftime('%H:%M:%S'))
        st.metric("Next Hour Start", next_hour_start.strftime('%H:%M:%S'))
        st.metric("Minutes Until Next", minutes_until_next_hour)
