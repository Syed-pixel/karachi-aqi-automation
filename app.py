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
        return {"aqi": 100, "pm25": 35.4, "timestamp": datetime.now().isoformat(), "location": "Karachi"}

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_latest_predictions():
    """Get latest predictions from Hugging Face"""
    try:
        # Get list of prediction files
        api_url = "https://huggingface.co/api/datasets/Syed110-3/karachi-aqi-predictor/tree/main/predictions"
        response = requests.get(api_url, timeout=10)
        files = response.json()
        
        # Find latest prediction file
        pred_files = [f for f in files if f['type'] == 'file' and f['path'].startswith('predictions/pred_')]
        if pred_files:
            latest_file = max(pred_files, key=lambda x: x['lastCommit']['date'])
            file_url = f"https://huggingface.co/datasets/Syed110-3/karachi-aqi-predictor/raw/main/{latest_file['path']}"
            
            pred_response = requests.get(file_url, timeout=10)
            return pred_response.json()
    except Exception as e:
        st.error(f"Error loading predictions: {e}")
    return None

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_historical_data():
    """Get historical data from Hugging Face"""
    try:
        # Load the dataset
        dataset_url = "https://huggingface.co/datasets/Syed110-3/karachi-aqi-predictor/raw/main/data/train-00000-of-00001.parquet"
        df = pd.read_parquet(dataset_url)
        
        # Convert timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
        df = df.sort_values('timestamp')
        
        return df
    except:
        return pd.DataFrame()

# Get data
current_data = get_current_aqi()
predictions = get_latest_predictions()
history_df = get_historical_data()

# MAIN DASHBOARD
# Row 1: Key Metrics
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric(
        label="🌤️ CURRENT AQI",
        value=f"{current_data['aqi']}",
        delta=None
    )
    st.progress(min(current_data['aqi'] / 200, 1.0))
    st.caption(f"PM2.5: {current_data['pm25']:.1f} µg/m³")
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    if predictions:
        next_aqi = predictions['predictions']['day1']
        st.metric(
            label="📈 TOMORROW",
            value=f"{next_aqi:.0f}",
            delta=f"{(next_aqi - current_data['aqi']):+.0f}",
            delta_color="inverse"
        )
    else:
        st.metric(label="📈 TOMORROW", value="--", delta="--")
    st.caption("AI Prediction")
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    # AQI Level
    aqi = current_data['aqi']
    if aqi <= 50:
        level = "GOOD"
        color_class = "aqi-good"
        icon = "✅"
    elif aqi <= 100:
        level = "MODERATE"
        color_class = "aqi-moderate"
        icon = "⚠️"
    elif aqi <= 150:
        level = "UNHEALTHY"
        color_class = "aqi-unhealthy"
        icon = "🚨"
    elif aqi <= 200:
        level = "VERY UNHEALTHY"
        color_class = "aqi-very-unhealthy"
        icon = "😷"
    else:
        level = "HAZARDOUS"
        color_class = "aqi-hazardous"
        icon = "☣️"
    
    st.markdown(f"### {icon} {level}")
    st.markdown(f'<span class="{color_class}">AQI Index: {aqi}</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with col4:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    if not history_df.empty:
        # Calculate 24h change
        last_24h = history_df[history_df['timestamp'] >= datetime.now() - timedelta(days=1)]
        if len(last_24h) > 1:
            change = last_24h['aqi'].iloc[-1] - last_24h['aqi'].iloc[0]
            st.metric(
                label="🕐 24H CHANGE",
                value=f"{change:+.0f}",
                delta=None
            )
        else:
            st.metric(label="🕐 24H CHANGE", value="--", delta=None)
    else:
        st.metric(label="🕐 24H CHANGE", value="--", delta=None)
    st.caption("From historical data")
    st.markdown('</div>', unsafe_allow_html=True)

# Row 2: Charts
st.markdown("---")
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📊 3-Day Forecast")
    
    if predictions:
        # Forecast chart
        days = ['Today', 'Tomorrow', 'Day 2', 'Day 3']
        values = [
            current_data['aqi'],
            predictions['predictions']['day1'],
            predictions['predictions']['day2'],
            predictions['predictions']['day3']
        ]
        
        fig1 = go.Figure(data=[
            go.Bar(
                x=days,
                y=values,
                text=[f"{v:.0f}" for v in values],
                textposition='auto',
                marker_color=['#3B82F6', '#10B981', '#F59E0B', '#EF4444']
            )
        ])
        
        fig1.update_layout(
            height=400,
            yaxis_title="AQI",
            showlegend=False
        )
        
        st.plotly_chart(fig1, use_container_width=True)
        
        # Forecast table
        forecast_df = pd.DataFrame({
            'Day': ['Tomorrow', 'Day 2', 'Day 3'],
            'Predicted AQI': [f"{predictions['predictions']['day1']:.0f}", 
                             f"{predictions['predictions']['day2']:.0f}", 
                             f"{predictions['predictions']['day3']:.0f}"],
            'PM2.5 (est)': [f"{predictions['predictions']['day1']*0.354:.1f}", 
                           f"{predictions['predictions']['day2']*0.354:.1f}", 
                           f"{predictions['predictions']['day3']*0.354:.1f}"] + ' µg/m³'
        })
        
        st.dataframe(forecast_df, use_container_width=True, hide_index=True)
    else:
        st.info("Waiting for prediction data...")

with col_right:
    st.subheader("📈 Historical Trends")
    
    if not history_df.empty:
        # Last 7 days
        last_week = history_df[history_df['timestamp'] >= datetime.now() - timedelta(days=7)]
        
        if not last_week.empty:
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=last_week['timestamp'],
                y=last_week['aqi'],
                mode='lines+markers',
                name='AQI',
                line=dict(color='#8B5CF6', width=2),
                fill='tozeroy',
                fillcolor='rgba(139, 92, 246, 0.1)'
            ))
            
            fig2.update_layout(
                height=400,
                xaxis_title="Date",
                yaxis_title="AQI",
                hovermode='x unified'
            )
            
            st.plotly_chart(fig2, use_container_width=True)
            
            # Statistics
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric("7-Day Avg", f"{last_week['aqi'].mean():.0f}")
            with col_stat2:
                st.metric("7-Day High", f"{last_week['aqi'].max():.0f}")
            with col_stat3:
                st.metric("7-Day Low", f"{last_week['aqi'].min():.0f}")
        else:
            st.info("No historical data available for the last 7 days")
    else:
        st.info("Historical data loading...")

# Row 3: Health Recommendations & Data Table
st.markdown("---")
tab1, tab2 = st.tabs(["🏥 Health Recommendations", "📋 Raw Data"])

with tab1:
    col_rec1, col_rec2 = st.columns(2)
    
    with col_rec1:
        st.subheader("Current Recommendations")
        
        if aqi <= 50:
            st.success("""
            ### ✅ GOOD AIR QUALITY
            **For Everyone:**
            - Ideal for outdoor activities
            - No restrictions needed
            - Windows can be opened for ventilation
            
            **Outdoor Activities:** All activities are safe
            """)
        elif aqi <= 100:
            st.warning("""
            ### ⚠️ MODERATE AIR QUALITY
            **For Sensitive Groups** (children, elderly, asthma):
            - Consider reducing intense outdoor activities
            
            **For General Public:**
            - Usually safe for outdoor activities
            - Consider masks if sensitive
            
            **Outdoor Activities:** Limit prolonged exertion
            """)
        elif aqi <= 150:
            st.error("""
            ### 🚨 UNHEALTHY for Sensitive Groups
            **For Sensitive Groups:**
            - Avoid outdoor activities
            - Keep windows closed
            - Use air purifiers
            
            **For Others:**
            - Limit prolonged outdoor exertion
            - Consider wearing masks
            
            **Outdoor Activities:** Not recommended for sensitive groups
            """)
        else:
            st.error("""
            ### ☣️ UNHEALTHY for Everyone
            **For Everyone:**
            - Avoid all outdoor activities
            - Keep windows closed
            - Use air purifiers
            - Wear N95 masks if going outside
            
            **Outdoor Activities:** Avoid all outdoor activities
            """)
    
    with col_rec2:
        st.subheader("Preventive Measures")
        st.markdown("""
        ### 🌿 General Tips:
        
        **At Home:**
        - Use air purifiers with HEPA filters
        - Keep windows closed during high pollution
        - Clean floors with wet mop
        - Avoid burning candles or incense
        
        **Outdoors:**
        - Check AQI before going out
        - Wear N95 masks in high pollution
        - Avoid exercise near busy roads
        - Stay hydrated
        
        **For Sensitive Groups:**
        - Keep medications handy
        - Have asthma action plan
        - Monitor symptoms closely
        """)

with tab2:
    st.subheader("Latest Data Points")
    if not history_df.empty:
        # Show last 24 hours
        recent = history_df[history_df['timestamp'] >= datetime.now() - timedelta(days=1)]
        if not recent.empty:
            display_df = recent[['timestamp', 'aqi', 'pm2_5', 'hour', 'day_of_week']].copy()
            display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M')
            st.dataframe(display_df.sort_values('timestamp', ascending=False), 
                        use_container_width=True, 
                        height=300)
        else:
            st.info("No recent data available")
    else:
        st.info("Data loading...")

# Footer
st.markdown("---")
col_foot1, col_foot2, col_foot3 = st.columns(3)

with col_foot1:
    st.markdown("**🕐 Update Schedule**")
    st.markdown("""
    - **Current AQI:** Every 5 minutes
    - **Predictions:** Every hour (on the hour)
    - **Models:** Daily at 2 AM
    """)

with col_foot2:
    st.markdown("**🔗 Data Sources**")
    st.markdown("""
    - [Open-Meteo API](https://open-meteo.com)
    - [Hugging Face Dataset](https://huggingface.co/Syed110-3)
    - GitHub Actions Automation
    """)

with col_foot3:
    st.markdown("**ℹ️ About**")
    st.markdown("""
    This dashboard shows real-time AQI for Karachi
    with AI-powered 3-day predictions.
    
    Last prediction: {}
    """.format(predictions['timestamp'][:16] if predictions else "N/A"))

# Auto-refresh logic
if auto_refresh:
    time.sleep(refresh_interval * 60)
    st.rerun()
