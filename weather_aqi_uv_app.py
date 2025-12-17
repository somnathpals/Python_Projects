import streamlit as st
import requests
import pandas as pd
import altair as alt
import folium
from streamlit_folium import st_folium
from datetime import datetime

# ============================================================
# PAGE CONFIG (MOBILE FRIENDLY)
# ============================================================
st.set_page_config(
    page_title="Weather + AQI Dashboard",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("🌤️ Weather + AQI Dashboard")

# ============================================================
# SESSION STATE
# ============================================================
if "run" not in st.session_state:
    st.session_state.run = False
if "city" not in st.session_state:
    st.session_state.city = ""

# ============================================================
# API KEYS & ENDPOINTS
# ============================================================
WEATHER_API_KEY = "9da2d5cbd6e548b1aa7171028250912"
WAQI_TOKEN = "ac73ef45573497db6e37f3135880f86ba063caf1"

W_CURRENT = "http://api.weatherapi.com/v1/current.json"
W_FORECAST = "http://api.weatherapi.com/v1/forecast.json"
W_ASTRO = "http://api.weatherapi.com/v1/astronomy.json"
WAQI_API = "https://api.waqi.info/feed/"
WAQI_TILE = f"https://tiles.waqi.info/tiles/usepa-aqi/{{z}}/{{x}}/{{y}}.png?token={WAQI_TOKEN}"

# ============================================================
# HELPERS
# ============================================================
@st.cache_data(ttl=1800)
def get_weather_current(city):
    return requests.get(
        f"{W_CURRENT}?key={WEATHER_API_KEY}&q={city}&aqi=yes",
        timeout=10
    ).json()

@st.cache_data(ttl=1800)
def get_weather_hourly(city):
    return requests.get(
        f"{W_FORECAST}?key={WEATHER_API_KEY}&q={city}&days=2&aqi=yes",
        timeout=10
    ).json()

@st.cache_data(ttl=1800)
def get_astronomy(city, date):
    return requests.get(
        f"{W_ASTRO}?key={WEATHER_API_KEY}&q={city}&dt={date}",
        timeout=10
    ).json()

@st.cache_data(ttl=1800)
def get_aqi_data(city):
    return requests.get(
        f"{WAQI_API}{city}/?token={WAQI_TOKEN}",
        timeout=10
    ).json()

def aqi_category(aqi):
    aqi = int(aqi)
    if aqi <= 50: return ("Good", "green")
    if aqi <= 100: return ("Moderate", "yellow")
    if aqi <= 150: return ("Sensitive", "orange")
    if aqi <= 200: return ("Unhealthy", "red")
    if aqi <= 300: return ("Very Unhealthy", "purple")
    return ("Hazardous", "maroon")

def uv_category(uv):
    if uv <= 2: return ("Low", "#2ECC71")
    if uv <= 5: return ("Moderate", "#F1C40F")
    if uv <= 7: return ("High", "#E67E22")
    if uv <= 10: return ("Very High", "#E74C3C")
    return ("Extreme", "#8E44AD")

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.header("⚙️ Settings")
    unit = st.selectbox("Temperature Unit", ["Celsius", "Fahrenheit"])
    city_input = st.text_input("City name")

    if st.button("📍 Get Weather"):
        if city_input.strip():
            st.session_state.city = city_input.strip()
            st.session_state.run = True

    if st.button("🔄 Reset"):
        st.session_state.run = False
        st.session_state.city = ""
        st.rerun()

# ============================================================
# MAIN DASHBOARD
# ============================================================
if st.session_state.run:
    city = st.session_state.city
    weather = get_weather_current(city)

    if "current" not in weather:
        st.error("City not found or API error")
        st.stop()

    loc = weather["location"]["name"]
    country = weather["location"]["country"]
    localtime = weather["location"]["localtime"]

    temp = weather["current"]["temp_c"] if unit == "Celsius" else weather["current"]["temp_f"]
    feels = weather["current"]["feelslike_c"] if unit == "Celsius" else weather["current"]["feelslike_f"]
    humidity = weather["current"]["humidity"]
    wind = weather["current"]["wind_kph"]
    vis = weather["current"]["vis_km"]
    uv = weather["current"]["uv"]
    icon = "https:" + weather["current"]["condition"]["icon"]
    cond = weather["current"]["condition"]["text"]

    uv_label, uv_color = uv_category(uv)

    st.subheader(f"📍 {loc}, {country}")
    st.caption(f"🕒 {localtime}")

    st.image(icon, width=80)
    st.metric("🌡️ Temperature", f"{temp}° {unit[0]}")
    st.metric("🤔 Feels Like", f"{feels}° {unit[0]}")

    col1, col2 = st.columns(2)
    col1.metric("💧 Humidity", f"{humidity}%")
    col2.metric("💨 Wind", f"{wind} km/h")

    col1, col2 = st.columns(2)
    col1.metric("👁️ Visibility", f"{vis} km")
    col2.metric("☀️ UV Index", uv)

    st.markdown(
        f"<div style='background:{uv_color};padding:12px;border-radius:10px;text-align:center;color:white;'>"
        f"<b>UV Risk:</b> {uv_label}</div>",
        unsafe_allow_html=True
    )

    # ========================================================
    # HOURLY FORECAST (MOBILE HEIGHT)
    # ========================================================
    hourly = get_weather_hourly(city)
    rows = []

    for day in hourly["forecast"]["forecastday"]:
        for h in day["hour"]:
            rows.append({
                "time": h["time"],
                "temp": h["temp_c"] if unit == "Celsius" else h["temp_f"],
                "humidity": h["humidity"]
            })

    df = pd.DataFrame(rows)
    df["time"] = pd.to_datetime(df["time"])

    st.markdown("### 🕒 Hourly Temperature")
    chart = alt.Chart(df).mark_line(point=True).encode(
        x="time:T",
        y="temp:Q",
        tooltip=["time", "temp", "humidity"]
    ).properties(height=220)

    st.altair_chart(chart, use_container_width=True)

    # ========================================================
    # AQI
    # ========================================================
    st.markdown("### 🌫️ Air Quality Index")
    aqi_data = get_aqi_data(city)

    if aqi_data.get("status") == "ok":
        aqi = aqi_data["data"]["aqi"]
        label, color = aqi_category(aqi)

        st.markdown(
            f"<div style='background:{color};padding:16px;border-radius:12px;text-align:center;color:white;'>"
            f"<h2>AQI {aqi}</h2><p>{label}</p></div>",
            unsafe_allow_html=True
        )

    # ========================================================
    # MAP (MOBILE HEIGHT)
    # ========================================================
    st.markdown("### 🌍 AQI Map")
    lat = weather["location"]["lat"]
    lon = weather["location"]["lon"]

    m = folium.Map(location=[lat, lon], zoom_start=5)
    folium.TileLayer(WAQI_TILE, attr="WAQI").add_to(m)
    folium.Marker([lat, lon], tooltip=city).add_to(m)

    st_folium(m, height=350, width="100%")

    st.caption("Data: WeatherAPI + WAQI")
