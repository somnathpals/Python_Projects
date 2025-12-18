import streamlit as st
import requests
import pandas as pd
import altair as alt
import folium
from streamlit_folium import st_folium

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Weather + AQI Dashboard",
    layout="centered"
)

st.title("🌤️ Weather + AQI Dashboard")

# ============================================================
# SESSION STATE
# ============================================================
if "city" not in st.session_state:
    st.session_state.city = None
if "unit" not in st.session_state:
    st.session_state.unit = "Celsius"

# ============================================================
# API CONFIG
# ============================================================
WEATHER_API_KEY = "9da2d5cbd6e548b1aa7171028250912"
WAQI_TOKEN = "ac73ef45573497db6e37f3135880f86ba063caf1"

W_CURRENT = "https://api.weatherapi.com/v1/current.json"
W_FORECAST = "https://api.weatherapi.com/v1/forecast.json"
W_ASTRO = "https://api.weatherapi.com/v1/astronomy.json"
WAQI_API = "https://api.waqi.info/feed/"
WAQI_TILE = f"https://tiles.waqi.info/tiles/usepa-aqi/{{z}}/{{x}}/{{y}}.png?token={WAQI_TOKEN}"

# ============================================================
# HELPERS
# ============================================================
@st.cache_data(ttl=1800)
def get_current(city):
    return requests.get(
        f"{W_CURRENT}?key={WEATHER_API_KEY}&q={city}&aqi=yes",
        timeout=10
    ).json()

@st.cache_data(ttl=1800)
def get_forecast(city):
    return requests.get(
        f"{W_FORECAST}?key={WEATHER_API_KEY}&q={city}&days=2",
        timeout=10
    ).json()

@st.cache_data(ttl=1800)
def get_astronomy(city):
    return requests.get(
        f"{W_ASTRO}?key={WEATHER_API_KEY}&q={city}",
        timeout=10
    ).json()

@st.cache_data(ttl=1800)
def get_aqi(city):
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

def aqi_health_alert(aqi):
    aqi = int(aqi)
    if aqi <= 50:
        return ("🟢 Air quality is good. Ideal for outdoor activities.", "success")
    if aqi <= 100:
        return ("🟡 Moderate air quality. Sensitive individuals should monitor symptoms.", "info")
    if aqi <= 150:
        return ("🟠 Unhealthy for sensitive groups. Reduce prolonged outdoor exertion.", "warning")
    if aqi <= 200:
        return ("🔴 Unhealthy air quality. Everyone should limit outdoor activities.", "error")
    if aqi <= 300:
        return ("🟣 Very unhealthy air. Avoid outdoor activity.", "error")
    return ("☠️ Hazardous air quality. Stay indoors with air purification.", "error")

def uv_health_alert(uv):
    if uv <= 2:
        return ("🟢 Low UV risk. No protection needed.", "success")
    if uv <= 5:
        return ("🟡 Moderate UV. Wear sunscreen and sunglasses.", "info")
    if uv <= 7:
        return ("🟠 High UV. Avoid sun between 11 AM – 4 PM.", "warning")
    if uv <= 10:
        return ("🔴 Very high UV. Protective clothing strongly advised.", "error")
    return ("☠️ Extreme UV. Stay indoors if possible.", "error")


# ============================================================
# INPUT FORM
# ============================================================
with st.form("city_form"):
    city_input = st.text_input("📍 Enter City", value=st.session_state.city or "")
    unit_input = st.selectbox(
        "🌡 Temperature Unit",
        ["Celsius", "Fahrenheit"],
        index=0 if st.session_state.unit == "Celsius" else 1
    )
    submit = st.form_submit_button("Get Weather")

if submit and city_input:
    st.session_state.city = city_input
    st.session_state.unit = unit_input

# ============================================================
# DASHBOARD
# ============================================================
if st.session_state.city:
    city = st.session_state.city
    unit = st.session_state.unit

    weather = get_current(city)
    if "current" not in weather:
        st.error("City not found or API error")
        st.stop()

    # ---------------- WEATHER ----------------
    loc_data = weather.get("location", {})
    loc = loc_data.get("name", city)
    country = loc_data.get("country", "")
    localtime = loc_data.get("localtime", "N/A")

    temp = weather["current"]["temp_c"] if unit == "Celsius" else weather["current"]["temp_f"]
    feels = weather["current"]["feelslike_c"] if unit == "Celsius" else weather["current"]["feelslike_f"]
    uv = weather["current"]["uv"]
    humidity = weather["current"]["humidity"]
    visibility = weather["current"].get("vis_km", "N/A")
    pressure = weather["current"].get("pressure_mb", "N/A")
    wind = weather["current"]["wind_kph"]
    icon = "https:" + weather["current"]["condition"]["icon"]
    condition = weather["current"]["condition"]["text"]
   
    uv_label, uv_color = uv_category(uv)

    # ---------------- ASTRONOMY ----------------
    astro = get_astronomy(city)
    sunrise = astro.get("astronomy", {}).get("astro", {}).get("sunrise", "N/A")
    sunset = astro.get("astronomy", {}).get("astro", {}).get("sunset", "N/A")

    st.subheader(f"🌤️ Weather in 🌍 {loc}, {country}\n 📅 **Current Date / Time**: {localtime}")

    st.image(icon, width=80)
    st.markdown(f"### {condition}")
    st.metric("🌡️ Temperature", f"{temp}° {unit[0]}")
    st.metric("🤔 Feels Like", f"{feels}° {unit[0]}")
    
    col1, col2 = st.columns(2)
    col1.metric("💧 Humidity", f"{humidity}%")
    col2.metric("💨 Wind", f"{wind} km/h")
    
    col1, col2 = st.columns(2)
    col1.metric("🌅 Sunrise", sunrise)
    col2.metric("🌇 Sunset", sunset)

    col1.metric("👁️ Visibility", f"{visibility} km")
    col2.metric("🧭 Pressure", f"{pressure} mb")

    st.markdown(
        f"<div style='background:{uv_color};padding:12px;border-radius:10px;text-align:center;color:white;'>"
        f"<b>☀️ UV Index:</b> {uv} ({uv_label})</div>",
        unsafe_allow_html=True
    )

    # ========================================================
    # HOURLY CHART
    # ========================================================
    forecast = get_forecast(city)
    rows = []
    for day in forecast["forecast"]["forecastday"]:
        for h in day["hour"]:
            rows.append({
                "time": h["time"],
                "temp": h["temp_c"] if unit == "Celsius" else h["temp_f"]
            })

    df = pd.DataFrame(rows)
    df["time"] = pd.to_datetime(df["time"])

    st.markdown("### 🕒 Hourly Temperature (48 Hours)")
    st.altair_chart(
        alt.Chart(df).mark_line(point=True).encode(
            x="time:T", y="temp:Q", tooltip=["time", "temp"]
        ).properties(height=220),
        width='stretch'
    )

    # ========================================================
    # AQI DASHBOARD
    # ========================================================
    st.markdown("### 🌫 Air Quality Index")

    # ================= AQI DATA =================
    aqi_data = get_aqi(city)

    if aqi_data.get("status") == "ok":
        aqi = aqi_data["data"]["aqi"]
        label, color = aqi_category(aqi)

        st.markdown(
            f"<div style='background:{color};padding:16px;border-radius:12px;text-align:center;color:white;'>"
            f"<h2>AQI {aqi}</h2><p>{label}</p></div>",
            unsafe_allow_html=True
        )

        pollutants = aqi_data["data"].get("iaqi", {})

        pollutant_map = {
            "pm25": "PM2.5",
            "pm10": "PM10",
            "o3": "Ozone (O₃)",
            "no2": "Nitrogen Dioxide (NO₂)",
            "so2": "Sulfur Dioxide (SO₂)",
            "co": "Carbon Monoxide (CO)"
        }

        st.markdown("#### 🧪 Pollutant Concentrations")
        cols = st.columns(2)
        for i, (key, label) in enumerate(pollutant_map.items()):
            value = pollutants.get(key, {}).get("v", "N/A")
            cols[i % 2].metric(label, f"{value} µg/m³")

    # ========================================================
    # HEALTH ALERTS
    # ========================================================
    st.markdown("## 🩺 Health Alerts")

    # AQI Alert
    if aqi_data.get("status") == "ok":
        aqi_val = aqi_data["data"]["aqi"]
        msg, level = aqi_health_alert(aqi_val)
        getattr(st, level)(f"🌫️ AQI Alert: {msg}")

    # UV Alert
    uv_msg, uv_level = uv_health_alert(uv)
    getattr(st, uv_level)(f"☀️ UV Alert: {uv_msg}")

    # ========================================================
    # MAP
    # ========================================================
    lat = weather["location"]["lat"]
    lon = weather["location"]["lon"]

    st.markdown("### 🌍 Interactive AQI Map")
    m = folium.Map(location=[lat, lon], zoom_start=5)
    folium.TileLayer(WAQI_TILE, attr="WAQI").add_to(m)
    folium.Marker([lat, lon], tooltip=city).add_to(m)
    st_folium(m, height=350, width="100%")

# Footer
    st.info(
        "🌐 Data Source: Global AQI tiles from [WAQI](https://waqi.info/). "
        "Weather data powered by [WeatherAPI](https://www.weatherapi.com/)."
    )
    st.caption(
    "⚠️ Health alerts are informational only and not a substitute for medical advice."
    )    
