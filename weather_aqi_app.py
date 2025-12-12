import streamlit as st
import requests
import pandas as pd
import altair as alt
import folium
from streamlit_folium import st_folium
from datetime import datetime

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Weather + AQI Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.title('Weather + AQI Dashboard')

# ============================================================
# SESSION STATE
# ============================================================
if "run" not in st.session_state: st.session_state.run = False
if "city" not in st.session_state: st.session_state.city = ""

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
# API HELPERS
# ============================================================
@st.cache_data(ttl=1800)
def get_weather_current(city):
    try:
        return requests.get(f"{W_CURRENT}?key={WEATHER_API_KEY}&q={city}&aqi=yes", timeout=10).json()
    except:
        return {"error": "Failed to fetch weather data."}

@st.cache_data(ttl=1800)
def get_weather_hourly(city):
    try:
        return requests.get(f"{W_FORECAST}?key={WEATHER_API_KEY}&q={city}&days=2&aqi=yes", timeout=10).json()
    except:
        return {"error": "Failed to fetch hourly forecast."}

@st.cache_data(ttl=1800)
def get_astronomy(city, date):
    try:
        return requests.get(f"{W_ASTRO}?key={WEATHER_API_KEY}&q={city}&dt={date}", timeout=10).json()
    except:
        return {"error": "Failed to fetch astronomy data."}

@st.cache_data(ttl=1800)
def get_aqi_data(city):
    try:
        return requests.get(f"{WAQI_API}{city}/?token={WAQI_TOKEN}", timeout=10).json()
    except:
        return {"status": "error", "data": "failed"}

def aqi_category(aqi):
    aqi = int(aqi)
    if aqi <= 50: return ("Good", "green")
    if aqi <= 100: return ("Moderate", "yellow")
    if aqi <= 150: return ("Unhealthy for Sensitive Groups", "orange")
    if aqi <= 200: return ("Unhealthy", "red")
    if aqi <= 300: return ("Very Unhealthy", "purple")
    return ("Hazardous", "maroon")

# ============================================================
# SIDEBAR INPUT
# ============================================================
st.sidebar.header("Settings")
unit = st.sidebar.selectbox("Temperature Unit", ["Celsius", "Fahrenheit"])
city_input = st.sidebar.text_input("Enter city for Weather + AQI")

if st.sidebar.button("Fetch Weather + AQI"):
    if city_input.strip() == "":
        st.warning("Please enter a city name")
    else:
        st.session_state.run = True
        st.session_state.city = city_input.strip()

if st.sidebar.button("Reset"):
    st.session_state.run = False
    st.session_state.city = ""
    st.rerun()

# ============================================================
# MAIN DASHBOARD
# ============================================================
if st.session_state.run:
    city_selected = st.session_state.city

    # ---------- WEATHER DATA ----------
    weather = get_weather_current(city_selected)
    if "error" in weather or "current" not in weather:
        st.error(f"City '{city_selected}' not found or API error.")
        st.stop()

    loc_data = weather.get("location", {})
    loc = loc_data.get("name", city_selected)
    country = loc_data.get("country", "")
    localtime = loc_data.get("localtime", "N/A")
    temp_c = weather["current"].get("temp_c", "N/A")
    temp_f = weather["current"].get("temp_f", "N/A")
    temp = temp_c if unit=="Celsius" else temp_f
    icon = "https:" + weather["current"]["condition"].get("icon", "")
    cond = weather["current"]["condition"].get("text", "N/A")
    humidity = weather["current"].get("humidity", "N/A")
    wind = weather["current"].get("wind_kph", "N/A")
    visibility = weather["current"].get("vis_km", "N/A")
    feels_c = weather["current"].get("feelslike_c", "N/A")
    feels_f = weather["current"].get("feelslike_f", "N/A")
    feels = feels_c if unit=="Celsius" else feels_f

    # ---------- ASTRONOMY ----------
    date_today = localtime.split(" ")[0]
    astro = get_astronomy(city_selected, date_today)
    sunrise = astro.get("astronomy", {}).get("astro", {}).get("sunrise", "N/A")
    sunset = astro.get("astronomy", {}).get("astro", {}).get("sunset", "N/A")

    st.subheader(f"🌤️ Weather in 🌍 {loc}, {country}\n 📅 **Current Date / Time**: {localtime}")
    
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        if icon: st.image(icon, width=80)
        st.metric("Temperature", f"{temp}° {unit[0]}")
        st.metric("Feels Like", f"{feels}° {unit[0]}")
    with col2:
        st.write(f"💧 Humidity: {humidity}%")
        st.write(f"💨 Wind: {wind} km/h")
        st.write(f"👁️ Visibility: {visibility} km")
    with col3:
        st.write(f"🌤 Condition: {cond}")
        st.write(f"🌄 Sunrise: {sunrise}")
        st.write(f"🌇 Sunset: {sunset}")

    # ---------- HOURLY WEATHER CHARTS ----------
    hourly_data = get_weather_hourly(city_selected)
    if "forecast" in hourly_data:
        df_hours = []
        for day in hourly_data["forecast"]["forecastday"]:
            for h in day["hour"]:
                df_hours.append({
                    "time": h.get("time"),
                    "temp_c": h.get("temp_c","N/A"),
                    "temp_f": h.get("temp_f","N/A"),
                    "humidity": h.get("humidity","N/A"),
                    "wind_kph": h.get("wind_kph","N/A"),
                    "feels_c": h.get("feelslike_c","N/A"),
                    "feels_f": h.get("feelslike_f","N/A"),
                    "condition": h["condition"].get("text","N/A")
                })
        df = pd.DataFrame(df_hours)
        df["time"] = pd.to_datetime(df["time"])
        temp_col = "temp_c" if unit=="Celsius" else "temp_f"
        feels_col = "feels_c" if unit=="Celsius" else "feels_f"

        st.markdown("### 🕒 Hourly Weather (Next 24–48 hours)")
        temp_chart = alt.Chart(df).mark_line(point=True).encode(
            x="time:T", y=alt.Y(temp_col, title=f"Temperature ({unit[0]})"),
            tooltip=["time", temp_col, feels_col, "condition"]
        ).properties(height=250, title="Temperature Trend")
        st.altair_chart(temp_chart, width='stretch')

        humidity_chart = alt.Chart(df).mark_line(point=True, color="blue").encode(
            x="time:T", y=alt.Y("humidity", title="Humidity (%)"), tooltip=["time", "humidity"]
        ).properties(height=200, title="Humidity Trend")
        st.altair_chart(humidity_chart, width='stretch')

        wind_chart = alt.Chart(df).mark_line(point=True, color="green").encode(
            x="time:T", y=alt.Y("wind_kph", title="Wind Speed (km/h)"), tooltip=["time", "wind_kph"]
        ).properties(height=200, title="Wind Speed Trend")
        st.altair_chart(wind_chart, width='stretch')

    # ---------- AQI DASHBOARD ----------
    st.markdown("---")
    st.subheader("🌫️ Air Quality Index (AQI)")
    try:
        aqi_data = get_aqi_data(city_selected)
        if aqi_data.get("status") != "ok":
            st.warning(f"AQI data unavailable for '{city_selected}'.")
        else:
            aqi_value = aqi_data["data"].get("aqi")
            if aqi_value in [None,"-",""]:
                st.warning(f"AQI value not available for '{city_selected}'.")
            else:
                category, color = aqi_category(int(aqi_value))
                st.markdown(
                    f"<div style='background-color:{color}; color:white; padding:20px; border-radius:10px; text-align:center;'>"
                    f"<h1>Current AQI: {aqi_value}</h1>"
                    f"<h3>{category}</h3></div>", unsafe_allow_html=True
                )
                pollutants = aqi_data["data"].get("iaqi", {})
                pollutant_names = {
                    'pm25':'PM2.5','pm10':'PM10','o3':'Ozone (O₃)',
                    'no2':'Nitrogen Dioxide (NO₂)','so2':'Sulfur Dioxide (SO₂)',
                    'co':'Carbon Monoxide (CO)'
                }
                st.markdown("### Individual Pollutant Levels")
                cols = st.columns(3)
                for i,(key,label) in enumerate(pollutant_names.items()):
                    val = pollutants.get(key, {}).get("v","N/A")
                    cols[i%3].metric(label, f"{val} µg/m³")
                last_time = aqi_data["data"].get("time", {}).get("s","N/A")
                st.info(f"Last reported measurement: **{last_time}**")
    except Exception as e:
        st.error(f"Error fetching AQI: {e}")

    # ---------- GLOBAL AQI HEATMAP ----------
    st.markdown("---")
    st.subheader("🌍 Interactive Global AQI Heatmap")
    default_lat = loc_data.get("lat",0)
    default_lon = loc_data.get("lon",0)
    m = folium.Map(location=[default_lat, default_lon], zoom_start=3, tiles=None, control_scale=True)
    folium.TileLayer(tiles=WAQI_TILE, attr="WAQI.org", name="WAQI AQI Heatmap", overlay=True, control=True).add_to(m)
    folium.TileLayer("OpenStreetMap", name="OSM Base", control=True).add_to(m)
    folium.Marker(location=[default_lat, default_lon],
                  popup=f"{city_selected} — AQI: {aqi_data['data'].get('aqi','N/A') if 'data' in aqi_data else 'N/A'}",
                  icon=folium.Icon(color="red", icon="cloud")).add_to(m)
    folium.LayerControl().add_to(m)
    st_folium(m, width="100%", height=500)

# Footer
    st.info(
        "🌐 Data Source: Global AQI tiles from [WAQI](https://waqi.info/). "
        "Weather data powered by [WeatherAPI](https://www.weatherapi.com/)."
    )