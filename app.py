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
    page_title="KARACHI AQI PROTOCOL",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Cyberpunk CSS with neon effects, glitch animations, and 3D elements
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Share+Tech+Mono&display=swap');
    
    * {
        font-family: 'Share Tech Mono', monospace;
    }
    
    .main {
        background: linear-gradient(180deg, #0a0a0a 0%, #1a0a2e 50%, #0a0a0a 100%);
        position: relative;
        overflow: hidden;
    }
    
    /* Animated grid background */
    .main::before {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-image: 
            linear-gradient(rgba(0, 255, 65, 0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 255, 65, 0.1) 1px, transparent 1px);
        background-size: 50px 50px;
        animation: gridMove 20s linear infinite;
        pointer-events: none;
        z-index: 0;
    }
    
    @keyframes gridMove {
        0% { transform: perspective(500px) rotateX(60deg) translateY(0); }
        100% { transform: perspective(500px) rotateX(60deg) translateY(50px); }
    }
    
    /* Scan line effect */
    .main::after {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: linear-gradient(90deg, transparent, rgba(0, 255, 255, 0.8), transparent);
        animation: scan 4s linear infinite;
        pointer-events: none;
        z-index: 1000;
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.8);
    }
    
    @keyframes scan {
        0% { top: 0; }
        100% { top: 100%; }
    }
    
    /* Glitch effect */
    @keyframes glitch {
        0% { transform: translate(0); text-shadow: 2px 2px #ff00ff, -2px -2px #00ffff; }
        25% { transform: translate(-2px, 2px); text-shadow: -2px -2px #ff00ff, 2px 2px #00ffff; }
        50% { transform: translate(2px, -2px); text-shadow: 2px -2px #ff00ff, -2px 2px #00ffff; }
        75% { transform: translate(-2px, -2px); text-shadow: -2px 2px #ff00ff, 2px -2px #00ffff; }
        100% { transform: translate(0); text-shadow: 2px 2px #ff00ff, -2px -2px #00ffff; }
    }
    
    .glitch {
        animation: glitch 0.3s infinite;
    }
    
    /* Main header */
    .cyber-header {
        font-family: 'Orbitron', sans-serif;
        font-size: 4rem;
        font-weight: 900;
        text-align: center;
        margin: 2rem 0;
        background: linear-gradient(45deg, #00ffff, #ff00ff, #ffff00, #00ffff);
        background-size: 300% 300%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: neonGlow 3s ease infinite, textShift 5s ease infinite;
        text-shadow: 0 0 30px rgba(0, 255, 255, 0.8);
        position: relative;
        z-index: 10;
    }
    
    @keyframes neonGlow {
        0%, 100% { filter: brightness(1) drop-shadow(0 0 20px #00ffff); }
        50% { filter: brightness(1.5) drop-shadow(0 0 40px #ff00ff); }
    }
    
    @keyframes textShift {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }
    
    /* Metric cards with neon borders */
    .cyber-card {
        background: rgba(10, 10, 30, 0.9);
        padding: 2rem;
        border-radius: 10px;
        border: 2px solid;
        margin-bottom: 1rem;
        position: relative;
        overflow: hidden;
        backdrop-filter: blur(10px);
        box-shadow: 0 0 30px rgba(0, 255, 255, 0.3);
        transition: all 0.3s ease;
    }
    
    .cyber-card:hover {
        transform: translateY(-5px) scale(1.02);
        box-shadow: 0 0 50px rgba(0, 255, 255, 0.6);
    }
    
    /* Corner brackets */
    .cyber-card::before,
    .cyber-card::after {
        content: '';
        position: absolute;
        width: 20px;
        height: 20px;
        border: 2px solid;
        border-color: inherit;
    }
    
    .cyber-card::before {
        top: 0;
        left: 0;
        border-right: none;
        border-bottom: none;
    }
    
    .cyber-card::after {
        bottom: 0;
        right: 0;
        border-left: none;
        border-top: none;
    }
    
    /* AQI Level Colors */
    .aqi-good { 
        border-color: #00ff41 !important; 
        box-shadow: 0 0 30px rgba(0, 255, 65, 0.5) !important;
    }
    .aqi-moderate { 
        border-color: #ffff00 !important; 
        box-shadow: 0 0 30px rgba(255, 255, 0, 0.5) !important;
    }
    .aqi-unhealthy { 
        border-color: #ff6b00 !important; 
        box-shadow: 0 0 30px rgba(255, 107, 0, 0.5) !important;
    }
    .aqi-very-unhealthy { 
        border-color: #ff00ff !important; 
        box-shadow: 0 0 30px rgba(255, 0, 255, 0.5) !important;
    }
    .aqi-hazardous { 
        border-color: #ff0040 !important; 
        box-shadow: 0 0 30px rgba(255, 0, 64, 0.5) !important;
    }
    
    /* Neon text colors */
    .text-good { color: #00ff41; text-shadow: 0 0 10px #00ff41; }
    .text-moderate { color: #ffff00; text-shadow: 0 0 10px #ffff00; }
    .text-unhealthy { color: #ff6b00; text-shadow: 0 0 10px #ff6b00; }
    .text-very-unhealthy { color: #ff00ff; text-shadow: 0 0 10px #ff00ff; }
    .text-hazardous { color: #ff0040; text-shadow: 0 0 10px #ff0040; }
    .text-cyan { color: #00ffff; text-shadow: 0 0 10px #00ffff; }
    .text-purple { color: #9d00ff; text-shadow: 0 0 10px #9d00ff; }
    
    /* Giant AQI number */
    .aqi-giant {
        font-family: 'Orbitron', sans-serif;
        font-size: 10rem;
        font-weight: 900;
        text-align: center;
        line-height: 1;
        margin: 1rem 0;
        animation: pulse 2s ease-in-out infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.8; transform: scale(1.05); }
    }
    
    /* Progress bars with neon glow */
    .neon-progress {
        height: 30px;
        background: rgba(20, 20, 40, 0.8);
        border-radius: 15px;
        overflow: hidden;
        position: relative;
        border: 1px solid rgba(0, 255, 255, 0.3);
        box-shadow: inset 0 0 10px rgba(0, 0, 0, 0.5);
    }
    
    .neon-progress-bar {
        height: 100%;
        border-radius: 15px;
        position: relative;
        transition: width 1s ease;
        animation: shimmer 2s infinite;
    }
    
    @keyframes shimmer {
        0% { filter: brightness(1); }
        50% { filter: brightness(1.3); }
        100% { filter: brightness(1); }
    }
    
    /* Threat level badge */
    .threat-badge {
        display: inline-block;
        padding: 0.5rem 1.5rem;
        border: 2px solid;
        border-radius: 5px;
        font-weight: bold;
        font-size: 1.5rem;
        margin: 1rem 0;
        animation: blink 2s infinite;
    }
    
    @keyframes blink {
        0%, 49%, 100% { opacity: 1; }
        50%, 99% { opacity: 0.6; }
    }
    
    /* Sidebar styling */
    .css-1d391kg, [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0a1a 0%, #1a0a2e 100%);
        border-right: 2px solid #00ffff;
        box-shadow: 0 0 30px rgba(0, 255, 255, 0.3);
    }
    
    /* Button styling */
    .stButton > button {
        background: linear-gradient(45deg, #00ffff, #ff00ff);
        color: #000;
        border: none;
        border-radius: 5px;
        padding: 0.75rem 2rem;
        font-weight: bold;
        font-family: 'Orbitron', sans-serif;
        transition: all 0.3s ease;
        box-shadow: 0 0 20px rgba(0, 255, 255, 0.5);
    }
    
    .stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 0 40px rgba(255, 0, 255, 0.8);
    }
    
    /* Data tables */
    .dataframe {
        background: rgba(10, 10, 30, 0.9) !important;
        color: #00ffff !important;
        border: 1px solid #00ffff !important;
    }
    
    /* Metric styling */
    [data-testid="stMetricValue"] {
        font-family: 'Orbitron', sans-serif;
        font-size: 3rem;
        color: #00ffff;
        text-shadow: 0 0 20px #00ffff;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Terminal-style text */
    .terminal-text {
        font-family: 'Share Tech Mono', monospace;
        color: #00ff41;
        background: rgba(0, 0, 0, 0.8);
        padding: 1rem;
        border-left: 3px solid #00ff41;
        margin: 1rem 0;
        box-shadow: 0 0 10px rgba(0, 255, 65, 0.3);
    }
    
    /* Hologram effect */
    .hologram {
        position: relative;
        animation: hologramFlicker 0.1s infinite alternate;
    }
    
    @keyframes hologramFlicker {
        0% { opacity: 0.95; }
        100% { opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)

# Title with cyberpunk styling
st.markdown('<div class="cyber-header">◢ KARACHI AQI PROTOCOL ◣</div>', unsafe_allow_html=True)
st.markdown('<div style="text-align: center; color: #00ffff; font-size: 1.2rem; margin-bottom: 2rem;">⚡ ATMOSPHERIC MONITORING SYSTEM // NEURAL PREDICTIONS ACTIVE ⚡</div>', unsafe_allow_html=True)

# Sidebar with cyberpunk theme
with st.sidebar:
    st.markdown('<div style="text-align: center;">', unsafe_allow_html=True)
    st.markdown('# ⚙️ SYSTEM CONTROLS', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown('<p class="text-cyan" style="font-weight: bold;">🔄 AUTO-REFRESH PROTOCOL</p>', unsafe_allow_html=True)
    auto_refresh = st.checkbox("Enable Auto-Refresh", value=True, help="Automatically refresh atmospheric data")
    refresh_interval = st.slider("Refresh Interval (minutes)", 1, 60, 10, help="Update frequency")
    
    if st.button("⚡ MANUAL REFRESH", use_container_width=True, type="primary"):
        st.rerun()
    
    st.markdown("---")
    st.markdown('<p class="text-purple" style="font-weight: bold;">📡 DATA UPLINKS</p>', unsafe_allow_html=True)
    st.markdown("""
    <div class="terminal-text">
    > Current AQI: Open-Meteo API<br>
    > Predictions: Neural Networks<br>
    > Storage: Hugging Face Dataset<br>
    > Status: ● ONLINE
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown('<p class="text-good" style="font-weight: bold;">⏰ SCAN SCHEDULE</p>', unsafe_allow_html=True)
    st.markdown("""
    <div class="terminal-text">
    > Live Data: Real-time<br>
    > Predictions: Hourly (XX:00)<br>
    > Model Retrain: Daily 02:00 UTC<br>
    > Neural Net: ACTIVE
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    current_time = datetime.now().strftime('%H:%M:%S')
    st.markdown(f'<p class="text-cyan" style="text-align: center;">TIMESTAMP: {current_time}</p>', unsafe_allow_html=True)

# Cache functions for performance
@st.cache_data(ttl=300)
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
            "location": "KARACHI_SECTOR_7"
        }
    except Exception as e:
        return {
            "aqi": 100,
            "pm25": 35.4,
            "timestamp": datetime.now().isoformat(),
            "location": "KARACHI_SECTOR_7",
            "note": "Using fallback data"
        }

@st.cache_data(ttl=300)
def get_latest_predictions():
    """Get latest predictions from Hugging Face"""
    try:
        api_url = "https://huggingface.co/api/datasets/Syed110-3/karachi-aqi-predictor/tree/main/predictions"
        response = requests.get(api_url, timeout=10)
        
        if response.status_code == 200:
            files = response.json()
            pred_files = []
            for item in files:
                if isinstance(item, dict) and 'path' in item:
                    if 'pred_' in item['path'] and item['path'].endswith('.json'):
                        pred_files.append(item)
            
            if pred_files:
                latest_file = max(pred_files, key=lambda x: x.get('lastCommit', {}).get('date', ''))
                file_url = f"https://huggingface.co/datasets/Syed110-3/karachi-aqi-predictor/raw/main/{latest_file['path']}"
                
                pred_response = requests.get(file_url, timeout=10)
                if pred_response.status_code == 200:
                    return pred_response.json()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "predictions": {"day1": 85.5, "day2": 87.2, "day3": 89.8},
            "note": "Demo predictions - awaiting first neural scan"
        }
        
    except Exception as e:
        return {
            "timestamp": datetime.now().isoformat(),
            "predictions": {"day1": 85.5, "day2": 87.2, "day3": 89.8},
            "note": f"Error: {str(e)[:50]}..."
        }

def get_aqi_info(aqi):
    """Get AQI level, color, and threat information"""
    if aqi <= 50:
        return {
            "level": "OPTIMAL",
            "color": "#00ff41",
            "threat": "MINIMAL",
            "class": "aqi-good",
            "text_class": "text-good",
            "icon": "✅",
            "advice": "All systems nominal. Outdoor activities cleared."
        }
    elif aqi <= 100:
        return {
            "level": "ACCEPTABLE",
            "color": "#ffff00",
            "threat": "LOW",
            "class": "aqi-moderate",
            "text_class": "text-moderate",
            "icon": "⚠️",
            "advice": "Caution advised for sensitive units."
        }
    elif aqi <= 150:
        return {
            "level": "HAZARDOUS",
            "color": "#ff6b00",
            "threat": "MEDIUM",
            "class": "aqi-unhealthy",
            "text_class": "text-unhealthy",
            "icon": "🚨",
            "advice": "Warning: Sensitive groups should minimize exposure."
        }
    elif aqi <= 200:
        return {
            "level": "CRITICAL",
            "color": "#ff00ff",
            "threat": "HIGH",
            "class": "aqi-very-unhealthy",
            "text_class": "text-very-unhealthy",
            "icon": "😷",
            "advice": "Alert: All units limit outdoor operations."
        }
    else:
        return {
            "level": "TOXIC",
            "color": "#ff0040",
            "threat": "EXTREME",
            "class": "aqi-hazardous",
            "text_class": "text-hazardous",
            "icon": "☣️",
            "advice": "Emergency: Seek shelter immediately. Deploy filtration."
        }

# Get current data
current_data = get_current_aqi()
predictions = get_latest_predictions()

current_aqi = current_data['aqi']
aqi_info = get_aqi_info(current_aqi)

# MAIN DASHBOARD LAYOUT
st.markdown("## 📊 ATMOSPHERIC STATUS // REAL-TIME")

# Row 1: Main AQI Display
col1, col2, col3 = st.columns([3, 2, 2])

with col1:
    st.markdown(f'<div class="cyber-card {aqi_info["class"]} hologram">', unsafe_allow_html=True)
    
    # Threat level badge
    st.markdown(f'''
    <div style="text-align: center;">
        <div class="threat-badge {aqi_info["class"]} {aqi_info["text_class"]}">
            {aqi_info["icon"]} THREAT LEVEL: {aqi_info["threat"]}
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    # Giant AQI number
    st.markdown(f'''
    <div class="aqi-giant {aqi_info["text_class"]}">
        {current_aqi}
    </div>
    ''', unsafe_allow_html=True)
    
    # Level indicator
    st.markdown(f'''
    <div style="text-align: center; font-size: 2rem; font-weight: bold;" class="{aqi_info["text_class"]}">
        [ {aqi_info["level"]} ]
    </div>
    ''', unsafe_allow_html=True)
    
    # Progress bars
    st.markdown(f'''
    <div style="margin-top: 2rem;">
        <div style="color: #00ffff; font-size: 0.9rem; margin-bottom: 0.5rem;">
            PM2.5 CONCENTRATION: {current_data["pm25"]:.1f} µg/m³
        </div>
        <div class="neon-progress">
            <div class="neon-progress-bar" style="width: {min(100, (current_data["pm25"]/100)*100)}%; background: linear-gradient(90deg, {aqi_info["color"]}, {aqi_info["color"]}80); box-shadow: 0 0 20px {aqi_info["color"]};"></div>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    st.markdown(f'''
    <div style="margin-top: 1rem;">
        <div style="color: #00ffff; font-size: 0.9rem; margin-bottom: 0.5rem;">
            ATMOSPHERIC TOXICITY: {((current_aqi/500)*100):.0f}%
        </div>
        <div class="neon-progress">
            <div class="neon-progress-bar" style="width: {(current_aqi/500)*100}%; background: linear-gradient(90deg, #00ff41, {aqi_info["color"]}); box-shadow: 0 0 20px {aqi_info["color"]};"></div>
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown(f'<div class="cyber-card" style="border-color: #ff00ff;">', unsafe_allow_html=True)
    st.markdown('<h3 class="text-purple">🏥 HEALTH PROTOCOL</h3>', unsafe_allow_html=True)
    
    st.markdown(f'''
    <div class="terminal-text">
    <strong>ADVISORY:</strong><br>
    {aqi_info["advice"]}
    </div>
    ''', unsafe_allow_html=True)
    
    if current_aqi <= 50:
        st.success("✅ All outdoor activities approved\n\n✅ Ventilation systems: OPEN\n\n✅ Protection: NOT REQUIRED")
    elif current_aqi <= 100:
        st.warning("⚠️ Sensitive units: Limit exertion\n\n✅ Standard units: Normal ops\n\n⚠️ Masks: Recommended for sensitive")
    elif current_aqi <= 150:
        st.error("❌ Sensitive groups: INDOOR ONLY\n\n⚠️ Others: Minimize exposure\n\n😷 Masks: REQUIRED outdoors")
    else:
        st.error("❌ All units: SEEK SHELTER\n\n❌ Seal all entry points\n\n😷 N95 masks: MANDATORY\n\n💨 Air filtration: DEPLOY")
    
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown(f'<div class="cyber-card" style="border-color: #00ffff;">', unsafe_allow_html=True)
    st.markdown('<h3 class="text-cyan">🔮 NEXT SCAN</h3>', unsafe_allow_html=True)
    
    now = datetime.now()
    next_hour = (now.hour + 1) % 24
    
    st.markdown(f'''
    <div class="terminal-text">
    > Next Prediction: {next_hour:02d}:00 UTC<br>
    > Model Update: 02:00 UTC<br>
    > Location: {current_data["location"]}<br>
    > Timestamp: {current_data["timestamp"][11:19]} UTC
    </div>
    ''', unsafe_allow_html=True)
    
    st.markdown('<h4 class="text-good">🚀 SYSTEM STATUS</h4>', unsafe_allow_html=True)
    
    if 'note' in predictions and 'Demo' in predictions.get('note', ''):
        st.warning("⏳ Awaiting first neural scan")
    else:
        st.success("✅ Neural networks: ACTIVE")
    
    if predictions and 'timestamp' in predictions:
        pred_time = datetime.fromisoformat(predictions['timestamp'].replace('Z', '+00:00'))
        time_diff = (now - pred_time).total_seconds() / 3600
        
        if time_diff < 2:
            st.success(f"✅ Predictions: {time_diff:.1f}h ago")
        elif time_diff < 6:
            st.warning(f"⚠️ Predictions: {time_diff:.1f}h ago")
        else:
            st.error(f"❌ Predictions: {time_diff:.1f}h ago")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Row 2: 3-Day Forecast
st.markdown("---")
st.markdown('<h2 style="color: #9d00ff; text-shadow: 0 0 20px #9d00ff;">📈 PREDICTIVE ANALYSIS // 72H FORECAST</h2>', unsafe_allow_html=True)

if predictions and 'predictions' in predictions:
    days = ['NOW', 'T+24H', 'T+48H', 'T+72H']
    values = [current_aqi]
    
    for i in range(1, 4):
        day_key = f'day{i}'
        if day_key in predictions['predictions']:
            values.append(predictions['predictions'][day_key])
        else:
            values.append(current_aqi)
    
    # Create forecast visualization
    col_chart, col_table = st.columns([2, 1])
    
    with col_chart:
        colors = [get_aqi_info(v)['color'] for v in values]
        levels = [get_aqi_info(v)['level'] for v in values]
        
        fig = go.Figure()
        
        # Add bars
        fig.add_trace(go.Bar(
            x=days,
            y=values,
            marker=dict(
                color=colors,
                line=dict(color='#ffffff', width=2),
                pattern=dict(shape='/')
            ),
            text=[f"{v:.0f}" for v in values],
            textposition='outside',
            textfont=dict(size=20, color='white', family='Orbitron'),
            hovertemplate='<b>%{x}</b><br>AQI: %{y:.0f}<br><extra></extra>',
            name=''
        ))
        
        # Add glow effect line
        fig.add_trace(go.Scatter(
            x=days,
            y=values,
            mode='lines+markers',
            line=dict(color='#00ffff', width=3, shape='spline'),
            marker=dict(size=12, color='#00ffff', line=dict(color='white', width=2)),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        fig.update_layout(
            height=450,
            plot_bgcolor='rgba(10,10,30,0.9)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Orbitron', color='#00ffff'),
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(0,255,255,0.2)',
                title='',
                tickfont=dict(size=14)
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(0,255,255,0.2)',
                title='AQI LEVEL',
                range=[0, max(values) * 1.3],
                tickfont=dict(size=12)
            ),
            margin=dict(t=20, b=20, l=50, r=20)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col_table:
        st.markdown('<div class="cyber-card" style="border-color: #9d00ff;">', unsafe_allow_html=True)
        st.markdown('<h3 class="text-purple">📋 FORECAST DATA</h3>', unsafe_allow_html=True)
        
        for i, (day, value) in enumerate(zip(days, values)):
            info = get_aqi_info(value)
            change = value - current_aqi if i > 0 else 0
            change_symbol = "+" if change > 0 else ""
            
            st.markdown(f'''
            <div style="border-left: 3px solid {info["color
