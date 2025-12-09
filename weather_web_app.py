import streamlit as st
import requests
import pandas as pd
import altair as alt

# -------------------------------------
# STREAMLIT CONFIG
# -------------------------------------
st.set_page_config(page_title='Weather App', layout='centered')
st.title('Weather App')

api_key = "9da2d5cbd6e548b1aa7171028250912"

current_url = "http://api.weatherapi.com/v1/current.json"
forecast_url = "http://api.weatherapi.com/v1/forecast.json"
astro_url = "http://api.weatherapi.com/v1/astronomy.json"

# -------------------------------------
# CACHING (prevents repeated API calls)
# -------------------------------------
@st.cache_data(show_spinner=True, ttl=3600)  # cache for 1 hour
def get_current_weather(city):
    url = f"{current_url}?key={api_key}&q={city}&aqi=yes"
    return requests.get(url).json()

@st.cache_data(show_spinner=True, ttl=3600)
def get_forecast(city, days=7):
    url = f"{forecast_url}?key={api_key}&q={city}&days={days}&aqi=no&alerts=no"
    return requests.get(url).json()

@st.cache_data(show_spinner=True, ttl=3600)
def get_astro(city, date):
    url = f"{astro_url}?key={api_key}&q={city}&dt={date}"
    return requests.get(url).json()


# -------------------------------------
# SIDEBAR SETTINGS
# -------------------------------------
st.sidebar.header("Settings")
unit = st.sidebar.selectbox("Temperature Unit:", ["Celsius", "Fahrenheit"])
show_humidity = st.sidebar.checkbox("Show Humidity", value=True)
show_wind = st.sidebar.checkbox("Show Wind Speed", value=True)

city = st.text_input("Enter City Name:")

# -------------------------------------
# MAIN PROCESS
# -------------------------------------
if st.button("Get Weather") and city:

    # ------------------- CURRENT WEATHER -------------------
    data = get_current_weather(city)

    if "error" in data:
        st.error("City Not Found")
        st.write("API Response:", data)
        st.stop()

    loc = data['location']['name']
    country = data['location']['country']
    local_dt = data['location']['localtime']
    local_date = local_dt.split(" ")[0]

    temp_c = data['current']['temp_c']
    temp_f = data['current']['temp_f']
    temp = temp_c if unit == "Celsius" else temp_f

    humidity = data['current']['humidity']
    visibility = data['current']['vis_km']
    wind = data['current']['wind_kph']
    cond = data['current']['condition']['text']
    icon = "https:" + data['current']['condition']['icon']

    # Display
    st.subheader(f"{loc}, {country}")
    st.image(icon, width=80)

    col1, col2 = st.columns(2)
    with col1:
        st.write(f"📅 **Date & Time:** {local_dt}")
        st.write(f"🌡️ **Temperature:** {temp}° {unit[0]}")
        st.write(f"👁️ **Visibility:** {visibility} km")
    with col2:
        st.write(f"🌤️ **Condition:** {cond}")

    if show_humidity:
        st.write(f"💧 **Humidity:** {humidity}%")
    if show_wind:
        st.write(f"💨 **Wind Speed:** {wind} km/h")

    # ------------------- SUNRISE & SUNSET -------------------
    astro = get_astro(city, local_date)
    sunrise = astro['astronomy']['astro']['sunrise']
    sunset = astro['astronomy']['astro']['sunset']

    st.markdown("### 🌅 Astronomical Information")
    st.write(f"🌄 **Sunrise:** {sunrise}")
    st.write(f"🌇 **Sunset:** {sunset}")

    # ------------------- 7-DAY FORECAST -------------------
    forecast_data = get_forecast(city, days=7)

    if "forecast" in forecast_data:
        st.markdown("## 📆 7-Day Weather Forecast")

        forecast_days = forecast_data['forecast']['forecastday']

        # Build DataFrame for charts
        df = pd.DataFrame([
            {
                "date": day["date"],
                "temp_c": day["day"]["avgtemp_c"],
                "temp_f": day["day"]["avgtemp_f"],
                "humidity": day["day"]["avghumidity"],
                "wind_kph": day["day"]["maxwind_kph"],
                "condition": day["day"]["condition"]["text"]
            } for day in forecast_days
        ])

        # Cards Display
        for day in forecast_days:
            st.write(f"### 📅 {day['date']}")
            st.write(f"🌡️ Avg Temp: {day['day']['avgtemp_c']}°C / {day['day']['avgtemp_f']}°F")
            st.write(f"💧 Humidity: {day['day']['avghumidity']}%")
            st.write(f"💨 Max Wind: {day['day']['maxwind_kph']} km/h")
            st.write("---")

        # ------------------- CHARTS -------------------
        st.markdown("## 📊 Weather Trends (7 Days)")

        # Temperature Chart
        temp_col = "temp_c" if unit == "Celsius" else "temp_f"
        temp_chart = (
            alt.Chart(df)
            .mark_line(point=True)
            .encode(
                x="date:T",
                y=alt.Y(temp_col, title=f"Temperature ({unit[0]})"),
                tooltip=["date", temp_col]
            )
            .properties(title="Temperature Trend", height=300)
        )
        st.altair_chart(temp_chart, width='stretch')

        # Humidity Chart
        humidity_chart = (
            alt.Chart(df)
            .mark_line(point=True, color="blue")
            .encode(
                x="date:T",
                y=alt.Y("humidity", title="Humidity (%)"),
                tooltip=["date", "humidity"]
            )
            .properties(title="Humidity Trend", height=300)
        )
        st.altair_chart(humidity_chart, width='stretch')

        # Wind Chart
        wind_chart = (
            alt.Chart(df)
            .mark_line(point=True, color="green")
            .encode(
                x="date:T",
                y=alt.Y("wind_kph", title="Wind Speed (km/h)"),
                tooltip=["date", "wind_kph"]
            )
            .properties(title="Wind Speed Trend", height=300)
        )
        st.altair_chart(wind_chart, width='stretch')

    else:
        st.warning("Forecast data unavailable.")
