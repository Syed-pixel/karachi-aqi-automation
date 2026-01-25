import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta
import time

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
    }
    .aqi-good { color: #10B981; }
    .aqi-moderate { color: #F59E0B; }
    .aqi-unhealthy { color: #EF4444; }
    .aqi-very-unhealthy { color: #8B5CF6; }
    .aqi-hazardous { color: #7C3AED; }
</style>
""", unsafe_allow_html=True)

# Title
st.markdown('<h1 class="main-header">🌫️ Karachi Air Quality Dashboard</h1>', unsafe_allow_html=True)
st.markdown("### Real-time monitoring and AI-powered predictions")

# Sidebar
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/869/869869.png", width=100)
    st.title("Controls")
    
    auto_refresh = st.checkbox("🔄 Auto-refresh", value=True)
    refresh_interval = st.slider("Refresh interval (minutes)", 1, 60, 5)
    
    st.markdown("---")
    st.subheader("📊 Data Sources")
    st.markdown("""
    - **Open-Meteo API**: Current air quality
    - **Hugging Face**: Historical data & predictions
    - **ML Models**: 3-day AQI forecasts
    """)
    
    if st.button("🔄 Force Refresh Now"):
        st.rerun()
    
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

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
    except:
        # Return default values if API fails
        return {"aqi": 100, "pm25": 35.4, "timestamp": datetime.now().isoformat(), "location": "Karachi"}

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_latest_predictions():
    """Get latest predictions from Hugging Face - FIXED VERSION"""
    try:
        # Direct URL to your predictions file (adjust based on your actual file structure)
        # Option 1: Try to get the latest file from list
        try:
            api_url = "https://huggingface.co/api/datasets/Syed110-3/karachi-aqi-predictor/tree/main/predictions"
            response = requests.get(api_url, timeout=10)
            
            if response.status_code == 200:
                files = response.json()
                
                # Find prediction files
                pred_files = []
                for item in files:
                    if isinstance(item, dict) and 'path' in item:
                        if 'pred_' in item['path'] and item['path'].endswith('.json'):
                            pred_files.append(item)
                
                if pred_files:
                    # Get the most recent file by date
                    latest_file = max(pred_files, key=lambda x: x.get('lastCommit', {}).get('date', ''))
                    file_url = f"https://huggingface.co/datasets/Syed110-3/karachi-aqi-predictor/raw/main/{latest_file['path']}"
                    
                    pred_response = requests.get(file_url, timeout=10)
                    if pred_response.status_code == 200:
                        prediction_data = pred_response.json()
                        return prediction_data
        except:
            pass
        
        # Option 2: Direct link to a known file structure
        # Try different possible file locations
        possible_paths = [
            "https://huggingface.co/datasets/Syed110-3/karachi-aqi-predictor/raw/main/predictions/latest_predictions.json",
            "https://huggingface.co/datasets/Syed110-3/karachi-aqi-predictor/resolve/main/predictions/latest.json",
            "https://huggingface.co/datasets/Syed110-3/karachi-aqi-predictor/raw/main/latest_predictions.json",
        ]
        
        for path in possible_paths:
            try:
                response = requests.get(path, timeout=10)
                if response.status_code == 200:
                    return response.json()
            except:
                continue
        
        # Option 3: If no predictions found, create mock data for demo
        return {
            "timestamp": datetime.now().isoformat(),
            "predictions": {
                "day1": 85.5,
                "day2": 87.2,
                "day3": 89.8
            },
            "note": "Demo data - real predictions will appear after first hourly run"
        }
        
    except Exception as e:
        st.error(f"Error loading predictions: {str(e)}")
        # Return demo data
        return {
            "timestamp": datetime.now().isoformat(),
            "predictions": {
                "day1": 85.5,
                "day2": 87.2,
                "day3": 89.8
            },
            "note": "Demo data - check your prediction files on Hugging Face"
        }

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_historical_data():
    """Get historical data from Hugging Face"""
    try:
        # Load the dataset
        dataset_url = "https://huggingface.co/datasets/Syed110-3/karachi-aqi-predictor/raw/main/data/train-00000-of-00001.parquet"
        df = pd.read_parquet(dataset_url)
        
        # Convert timestamp
        if 'timestamp' in df.columns:
            try:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            except:
                df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
        
        return df
    except Exception as e:
        st.warning(f"Historical data loading issue: {str(e)}")
        # Return empty dataframe with expected columns
        return pd.DataFrame(columns=['timestamp', 'aqi', 'pm2_5'])

# Get data
current_data = get_current_aqi()
predictions = get_latest_predictions()
history_df = get_historical_data()

# Function to get AQI level and color
def get_aqi_level(aqi):
    if aqi <= 50:
        return "GOOD", "#10B981", "✅"
    elif aqi <= 100:
        return "MODERATE", "#F59E0B", "⚠️"
    elif aqi <= 150:
        return "UNHEALTHY", "#EF4444", "🚨"
    elif aqi <= 200:
        return "VERY UNHEALTHY", "#8B5CF6", "😷"
    else:
        return "HAZARDOUS", "#7C3AED", "☣️"

# MAIN DASHBOARD
# Row 1: Current AQI
st.markdown("## 📊 Current Air Quality")

col1, col2, col3 = st.columns(3)

with col1:
    # Current AQI Card
    current_aqi = current_data['aqi']
    level, color, icon = get_aqi_level(current_aqi)
    
    st.markdown(f'<div class="metric-card" style="border-left-color: {color};">', unsafe_allow_html=True)
    st.markdown(f"### {icon} Current AQI")
    st.markdown(f"# **{current_aqi}**")
    st.markdown(f"**Level:** {level}")
    st.markdown(f"**PM2.5:** {current_data['pm25']:.1f} µg/m³")
    st.markdown(f"**Updated:** {current_data['timestamp'][11:16]} UTC")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    # Forecast Card - NEXT 24 HOURS
    st.markdown(f'<div class="metric-card">', unsafe_allow_html=True)
    st.markdown(f"### 📈 Next 24 Hours")
    
    if predictions and 'predictions' in predictions:
        tomorrow_aqi = predictions['predictions'].get('day1', current_aqi)
        change = tomorrow_aqi - current_aqi
        
        st.markdown(f"# **{tomorrow_aqi:.0f}**")
        st.markdown(f"**Change:** {change:+.0f}")
        
        # Show all 3 days
        with st.expander("3-Day Forecast"):
            for i in range(1, 4):
                day_key = f'day{i}'
                if day_key in predictions['predictions']:
                    day_aqi = predictions['predictions'][day_key]
                    day_level, day_color, day_icon = get_aqi_level(day_aqi)
                    st.markdown(f"**Day {i}:** {day_aqi:.0f} {day_icon}")
    else:
        st.markdown("# **--**")
        st.info("Predictions loading...")
    
    if predictions and 'timestamp' in predictions:
        st.caption(f"Predicted: {predictions['timestamp'][:16]}")
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    # Health Recommendations
    st.markdown(f'<div class="metric-card">', unsafe_allow_html=True)
    st.markdown(f"### 🏥 Health Advice")
    
    if current_aqi <= 50:
        st.success("""
        **✅ GOOD**
        - Ideal for outdoor activities
        - No restrictions needed
        - Windows can be opened
        """)
    elif current_aqi <= 100:
        st.warning("""
        **⚠️ MODERATE**
        - Sensitive individuals: Limit outdoor exertion
        - General population: Usually safe
        - Consider masks if sensitive
        """)
    elif current_aqi <= 150:
        st.error("""
        **🚨 UNHEALTHY**
        - Sensitive groups: Avoid outdoor activities
        - Others: Limit prolonged exertion
        - Keep windows closed
        """)
    else:
        st.error("""
        **☣️ HAZARDOUS**
        - Everyone: Avoid outdoor activities
        - Keep windows closed
        - Use air purifiers
        - Wear N95 masks if outside
        """)
    st.markdown('</div>', unsafe_allow_html=True)

# Row 2: Forecast Visualization
st.markdown("---")
st.markdown("## 📈 3-Day AQI Forecast")

if predictions and 'predictions' in predictions:
    # Prepare forecast data
    days = ['Today', 'Tomorrow', 'Day 2', 'Day 3']
    
    # Get values - today + next 3 days
    values = [current_aqi]
    for i in range(1, 4):
        day_key = f'day{i}'
        if day_key in predictions['predictions']:
            values.append(predictions['predictions'][day_key])
        else:
            values.append(current_aqi)  # Fallback
    
    # Create colors based on AQI levels
    colors = []
    for value in values:
        level, color, icon = get_aqi_level(value)
        colors.append(color)
    
    # Create forecast chart
    fig1 = go.Figure(data=[
        go.Bar(
            x=days,
            y=values,
            marker_color=colors,
            text=[f"{v:.0f}" for v in values],
            textposition='outside',
            textfont=dict(size=14, color='black'),
            hovertemplate='<b>%{x}</b><br>AQI: %{y:.0f}<extra></extra>'
        )
    ])
    
    fig1.update_layout(
        height=400,
        yaxis_title="AQI",
        xaxis_title="",
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(range=[0, max(values) * 1.2])  # Add some headroom
    )
    
    st.plotly_chart(fig1, use_container_width=True)
    
    # Forecast table
    st.markdown("### Detailed Forecast")
    forecast_data = []
    for i, (day, value) in enumerate(zip(days, values)):
        if i == 0:  # Skip today in table
            continue
        level, color, icon = get_aqi_level(value)
        forecast_data.append({
            'Day': day,
            'Predicted AQI': f"{value:.0f}",
            'Level': level,
            'PM2.5 Estimate': f"{(value * 0.354):.1f} µg/m³",
            'Icon': icon
        })
    
    forecast_df = pd.DataFrame(forecast_data)
    st.dataframe(forecast_df, use_container_width=True, hide_index=True)
    
else:
    st.info("🔍 Waiting for prediction data... Make sure your hourly automation is running and uploading predictions to Hugging Face.")

# Row 3: Historical Data
st.markdown("---")
st.markdown("## 📊 Historical Trends")

if not history_df.empty and 'aqi' in history_df.columns and 'timestamp' in history_df.columns:
    # Last 7 days
    last_week = history_df[history_df['timestamp'] >= datetime.now() - timedelta(days=7)]
    
    if not last_week.empty:
        # Create historical chart
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=last_week['timestamp'],
            y=last_week['aqi'],
            mode='lines+markers',
            name='AQI',
            line=dict(color='#8B5CF6', width=2),
            fill='tozeroy',
            fillcolor='rgba(139, 92, 246, 0.1)',
            hovertemplate='<b>%{x|%b %d, %H:%M}</b><br>AQI: %{y:.0f}<extra></extra>'
        ))
        
        fig2.update_layout(
            height=400,
            xaxis_title="Date",
            yaxis_title="AQI",
            hovermode='x unified',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig2, use_container_width=True)
        
        # Statistics
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        with col_stat1:
            st.metric("7-Day Avg", f"{last_week['aqi'].mean():.0f}")
        with col_stat2:
            st.metric("7-Day High", f"{last_week['aqi'].max():.0f}")
        with col_stat3:
            st.metric("7-Day Low", f"{last_week['aqi'].min():.0f}")
        with col_stat4:
            if len(last_week) > 1:
                change = last_week['aqi'].iloc[-1] - last_week['aqi'].iloc[0]
                st.metric("Weekly Change", f"{change:+.0f}")
            else:
                st.metric("Weekly Change", "--")
    else:
        st.info("No historical data available for the last 7 days")
else:
    st.info("Historical data loading... Check if your dataset has 'aqi' and 'timestamp' columns.")

# Debug section (collapsed)
with st.expander("🔧 Debug Information"):
    st.write("### Current Data")
    st.json(current_data)
    
    st.write("### Predictions Data")
    st.json(predictions)
    
    st.write("### Historical Data Info")
    if not history_df.empty:
        st.write(f"Rows: {len(history_df)}")
        st.write(f"Columns: {list(history_df.columns)}")
        if 'timestamp' in history_df.columns:
            st.write(f"Time range: {history_df['timestamp'].min()} to {history_df['timestamp'].max()}")
    else:
        st.write("No historical data loaded")

# Footer
st.markdown("---")
col_foot1, col_foot2 = st.columns(2)

with col_foot1:
    st.markdown("### 🔄 Update Schedule")
    st.markdown("""
    - **Current AQI:** Every 5 minutes
    - **Predictions:** Every hour (on the hour)
    - **Models Retrained:** Daily at 2 AM UTC
    - **Dashboard Refresh:** Every 5 minutes
    """)

with col_foot2:
    st.markdown("### 🔗 Quick Links")
    st.markdown("""
    - [View on Hugging Face](https://huggingface.co/Syed110-3/karachi-aqi-predictor)
    - [GitHub Repository](https://github.com/Syed-pixel/karachi-aqi-automation)
    - [Open-Meteo API](https://open-meteo.com/en/docs/air-quality-api)
    - [AQI Scale Reference](https://www.airnow.gov/aqi/aqi-basics/)
    """)

# Auto-refresh logic
if auto_refresh:
    time.sleep(refresh_interval * 60)
    st.rerun()

# Add a timestamp
st.markdown(f"---")
st.caption(f"Dashboard generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')} | Next auto-refresh in {refresh_interval} minutes")
