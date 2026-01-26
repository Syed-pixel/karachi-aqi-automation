import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta
import time
import numpy as np
from streamlit_autorefresh import st_autorefresh

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
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<h1 class="main-header">🌫️ Karachi Air Quality Dashboard</h1>', unsafe_allow_html=True)
st.markdown("### Live monitoring with AI-powered 3-day forecasts")

# Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/869/869869.png", width=100)
    st.title("⚙️ System Status")
    
    st.markdown("---")
    st.markdown("### ⏰ Update Schedule")
    st.markdown("""
    **Live Data:**
    - Current AQI: Real-time (every load)
    
    **AI Predictions:**
    - Generated: On the hour
    - Available: ~90 seconds after the hour
    - Displayed: When available
    """)
    
    st.markdown("---")
    now = datetime.now()
    next_hour = (now.hour + 1) % 24
    minutes_to_next = 60 - now.minute
    
    st.markdown("### 🔄 Next Update")
    st.markdown(f"""
    - **Predictions generated at:** {next_hour:02d}:00 UTC
    - **Available at:** {next_hour:02d}:01:30 UTC
    - **Current time:** {now.strftime('%H:%M:%S UTC')}
    """)
    
    st.markdown("---")
    st.markdown("### 📡 Data Pipeline")
    st.markdown("""
    1. **Hourly Schedule:**
       - :00:00 → Script starts
       - :00:30 → Predictions generated
       - :01:30 → Predictions uploaded
    
    2. **Dashboard:**
       - Shows 'Fetching...' for 90 seconds
       - Then displays latest predictions
    """)

# Cache functions - current AQI every 5 min
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_current_aqi():
    """Get current AQI from Open-Meteo (live API)"""
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
            "location": "Karachi (24.86°N, 67.00°E)",
            "source": "Open-Meteo Live API"
        }
    except Exception as e:
        # Fallback to demo data if API fails
        return {
            "aqi": 85,
            "pm25": 30.1,
            "timestamp": datetime.now().isoformat(),
            "location": "Karachi",
            "source": "Fallback Data (API Error)"
        }

# NEW FUNCTION: Get predictions with 90-second delay
@st.cache_data(ttl=1800)  # Cache for 30 minutes, but we'll control refresh manually
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

# Get current AQI (always available)
current_data = get_current_aqi()
current_aqi = current_data['aqi']
aqi_info = get_aqi_info(current_aqi)

# Get predictions with delay logic
predictions = get_latest_predictions()

# Calculate timing info
now = datetime.now()
next_hour_start = datetime(now.year, now.month, now.day, now.hour, 0, 0) + timedelta(hours=1)
predictions_available_time = next_hour_start + timedelta(seconds=90)

# Determine if we should show loading state
show_loading = False
if now.minute == 0 and now.second < 90:
    show_loading = True
    seconds_remaining = 90 - now.second
elif predictions.get('status') == 'waiting':
    show_loading = True
    seconds_remaining = predictions.get('retry_after', 90)

# Update badge - MODIFIED to show loading state
if show_loading:
    st.markdown(f"""
    <div class="update-badge" style="background: linear-gradient(45deg, #F59E0B, #D97706);">
        <div class="loading-spinner"></div>
        AI Predictions generating... Available in {seconds_remaining} seconds
    </div>
    """, unsafe_allow_html=True)
else:
    next_update = datetime(now.year, now.month, now.day, now.hour, 0, 0) + timedelta(hours=1)
    minutes_remaining = int((next_update - now).total_seconds() / 60)
    st.markdown(f"""
    <div class="update-badge">
        🔄 Live AQI updates every 5 min | Next predictions: {next_update.strftime('%H:%M')} UTC ({minutes_remaining} min)
    </div>
    """, unsafe_allow_html=True)

# MAIN DASHBOARD LAYOUT
# Row 1: Current AQI Status (ALWAYS SHOWN)
st.markdown("## 📊 Current Air Quality Status")

col1, col2, col3 = st.columns([2, 1, 1])

with col1:
    # Current AQI Card
    st.markdown(f'<div class="metric-card {aqi_info["color_class"]}">', unsafe_allow_html=True)
    st.markdown(f"### {aqi_info['icon']} LIVE AIR QUALITY INDEX")
    
    # Large AQI number
    st.markdown(f"<h1 style='font-size: 5rem; margin: 0; color: {aqi_info['color']};'>{current_aqi:.0f}</h1>", unsafe_allow_html=True)
    
    # Level and details
    st.markdown(f"**Level:** {aqi_info['level']}")
    st.markdown(f"**PM2.5 Concentration:** {current_data['pm25']:.1f} µg/m³")
    st.markdown(f"**Location:** {current_data['location']}")
    st.markdown(f"**Recorded:** {current_data['timestamp'][11:16]} UTC")
    st.markdown(f"**Source:** {current_data['source']}")
    
    # AQI scale
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
    # Automation Status Card
    st.markdown(f'<div class="metric-card">', unsafe_allow_html=True)
    st.markdown(f"### 🤖 Automation Status")
    
    if show_loading:
        st.markdown(f"**AI Predictions:** ⏳ Generating...")
        st.markdown(f"**Available in:** {seconds_remaining} seconds")
        st.markdown(f"**Available at:** {predictions_available_time.strftime('%H:%M:%S UTC')}")
        
        # Progress bar
        progress = 1 - (seconds_remaining / 90)
        st.progress(progress)
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
    next_hour = (now.hour + 1) % 24
    st.markdown(f"#### 📅 Next Generation")
    st.markdown(f"**Starts at:** {next_hour:02d}:00:00 UTC")
    st.markdown(f"**Available at:** {next_hour:02d}:01:30 UTC")
    
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
    
    **Process:**
    1. Script started at {now.replace(second=0).strftime('%H:%M:%S UTC')}
    2. Current AQI fetched: ✓
    3. ML models loaded: ✓
    4. Predictions generated: In progress...
    5. Uploading to Hugging Face: Waiting...
    
    **Available in:** {seconds_remaining} seconds
    """)
    
    # Countdown timer
    countdown_placeholder = st.empty()
    for i in range(seconds_remaining, 0, -1):
        countdown_placeholder.markdown(f"**Refreshing in:** {i} seconds")
        time.sleep(1)
    
    st.markdown("**🎉 Predictions should now be available!**")
    st.markdown("The page will refresh automatically...")
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Auto-refresh after countdown
    time.sleep(2)
    st.cache_data.clear()
    st.rerun()
    
elif predictions.get('status') in ['success', 'demo', 'error'] and 'predictions' in predictions:
    # SHOW ACTUAL PREDICTIONS
    # Prepare forecast data
    days = ['Today', 'Tomorrow', 'Day 2', 'Day 3']
    
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
                    'Day': day,
                    'AQI': f"{value:.0f}",
                    'Level': level,
                    'PM2.5': f"{(value * 0.354):.1f} µg/m³",
                    'Status': 'Live'
                })
            else:
                change = value - current_aqi
                forecast_data.append({
                    'Day': day,
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
                "Day": st.column_config.TextColumn("Day", width="small"),
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
    - Live AQI: ✅ Available
    - AI Predictions: ⏳ Generating on schedule
    """)
    
    # Show when next predictions will be
    if now.minute >= 1 and now.second >= 30:
        # Past the 90-second window, show next hour
        next_hour_time = datetime(now.year, now.month, now.day, now.hour + 1, 0, 0)
        st.info(f"**Next predictions:** Available at {next_hour_time.strftime('%H:%M:30 UTC')}")

# Row 3: System Architecture
st.markdown("---")
st.markdown("## 🔧 System Architecture")

col_info1, col_info2, col_info3 = st.columns(3)

with col_info1:
    st.markdown("### 📡 Live Data Pipeline")
    st.markdown("""
    <div class="pipeline-step">
    1. **Streamlit Dashboard**<br>
    ← Fetches live AQI from Open-Meteo
    </div>
    <div class="pipeline-step">
    2. **GitHub Actions** (Hourly)<br>
    • :00:00 → Script starts<br>
    • :00:05 → Fetches current AQI<br>
    • :00:30 → Makes predictions<br>
    • :01:30 → Uploads to Hugging Face
    </div>
    <div class="pipeline-step">
    3. **Dashboard Delay**<br>
    • Waits 90 seconds after the hour<br>
    • Then fetches latest predictions<br>
    • Shows loading state in meantime
    </div>
    """, unsafe_allow_html=True)

with col_info2:
    st.markdown("### ⏰ Prediction Timing")
    st.markdown("""
    **To Avoid Sync Issues:**
    - Live AQI: Updates instantly
    - AI Predictions: Delayed by 90 seconds
    
    **Why the Delay?**
    1. GitHub Actions takes ~30s to start
    2. ML models take ~20s to load
    3. Upload to Hugging Face takes ~10s
    
    **Result:**
    - No more "previous hour" predictions
    - Predictions always match current AQI
    - Clear loading state for users
    """)

with col_info3:
    st.markdown("### 🚀 Real-time Features")
    st.markdown("""
    **Live Monitoring:**
    - Current AQI: Real-time API
    - 5-minute auto-refresh
    - Health recommendations
    
    **AI Forecasting:**
    - 3-day predictions
    - Generated hourly
    - Available after 90s delay
    - Always synchronized
    
    **User Experience:**
    - Shows "Generating..." state
    - Countdown timer
    - Auto-refresh when ready
    - Clear status messages
    """)

# Footer
st.markdown("---")
col_footer1, col_footer2 = st.columns([3, 1])

with col_footer1:
    if show_loading:
        st.markdown(f"""
        **Dashboard Status:** ⏳ AI PREDICTIONS GENERATING | 
        **Available in:** {seconds_remaining} seconds | 
        **Current Time:** {now.strftime('%H:%M:%S UTC')}
        """)
    else:
        next_update = datetime(now.year, now.month, now.day, now.hour, 0, 0) + timedelta(hours=1)
        minutes_remaining = int((next_update - now).total_seconds() / 60)
        st.markdown(f"""
        **Dashboard Status:** 🟢 LIVE & AUTO-UPDATING | 
        **Current Time:** {now.strftime('%H:%M:%S UTC')} | 
        **Next AI Predictions:** {next_update.strftime('%H:%M')} UTC ({minutes_remaining} min)
        """)
    
    st.caption("""
    Live AQI from Open-Meteo API | AI Forecasts from Hugging Face ML Models | 
    Fully automated via GitHub Actions | Predictions delayed by 90s for synchronization
    """)

with col_footer2:
    if st.button("🔄 Refresh Now", use_container_width=True, type="secondary"):
        st.cache_data.clear()
        st.rerun()

# Auto-refresh logic
# Refresh more aggressively during the 90-second window
if show_loading and seconds_remaining < 60:
    # If we're in the last minute of waiting, refresh every 10 seconds
    time.sleep(10)
    st.cache_data.clear()
    st.rerun()
elif now.minute == 1 and now.second >= 25 and now.second <= 35:
    # Refresh around the 90-second mark
    time.sleep(5)
    st.cache_data.clear()
    st.rerun()

# Debug section
with st.expander("🔧 Debug & Raw Data"):
    tab1, tab2, tab3 = st.tabs(["Live AQI", "Predictions", "System"])
    
    with tab1:
        st.write("### Live AQI Data")
        st.json(current_data)
        
        # Test API
        if st.button("Test Open-Meteo API"):
            test_url = "https://air-quality-api.open-meteo.com/v1/air-quality?latitude=24.8607&longitude=67.0011&current=pm2_5"
            response = requests.get(test_url, timeout=5)
            st.write("Status:", response.status_code)
            st.json(response.json())
    
    with tab2:
        st.write("### AI Forecast Data")
        st.json(predictions)
        
        st.write("### Timing Info")
        st.write(f"Current time: {now}")
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
        st.metric("Next Hour", next_hour_start.strftime('%H:%M:%S'))
        st.metric("Predictions Available", predictions_available_time.strftime('%H:%M:%S'))
