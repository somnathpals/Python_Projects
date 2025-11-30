import streamlit as st
import requests

# --- Configuration ---
# ⚠️ IMPORTANT: Replace 'YOUR_API_TOKEN' with your actual token from a service like aqicn.org
API_TOKEN = 'ac73ef45573497db6e37f3135880f86ba063caf1'
BASE_URL = "https://api.waqi.info/feed/"

# --- Functions ---

@st.cache_data(ttl=600)  # Cache the result for 10 minutes to avoid hitting API limits
def get_aqi_data(city_name):
    """Fetches AQI data for a given city using the WAQI API."""
    if not API_TOKEN or API_TOKEN == 'YOUR_API_TOKEN':
        return {"error": "API Token is missing. Please replace 'YOUR_API_TOKEN' in the code."}

    # The API query uses the city name directly
    api_url = f"{BASE_URL}{city_name}/?token={API_TOKEN}"
    
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        data = response.json()
        
        if data.get("status") == "ok" and data.get("data", {}).get("aqi") is not None:
            return data["data"]
        elif data.get("status") == "ok" and data.get("data", {}).get("aqi") == '-':
            return {"error": f"AQI data not available for '{city_name}'. The station might not be reporting the main AQI."}
        elif data.get("status") == "error":
             return {"error": f"API Error: {data.get('data')} for city '{city_name}'"}
        else:
            return {"error": f"City '{city_name}' not found or no AQI data available."}

    except requests.exceptions.Timeout:
        return {"error": "API request timed out."}
    except requests.exceptions.RequestException as e:
        return {"error": f"An error occurred during the API request: {e}"}

def get_aqi_category(aqi_value):
    """Determines the AQI health category and color based on the US EPA standard."""
    if aqi_value <= 50:
        return ("Good", "green")
    elif aqi_value <= 100:
        return ("Moderate", "yellow")
    elif aqi_value <= 150:
        return ("Unhealthy for Sensitive Groups", "orange")
    elif aqi_value <= 200:
        return ("Unhealthy", "red")
    elif aqi_value <= 300:
        return ("Very Unhealthy", "purple")
    else:
        return ("Hazardous", "maroon")

# --- Streamlit App Layout ---

st.set_page_config(
    page_title="City AQI Viewer",
    page_icon="💨"
)

st.title("💨 Air Quality Index (AQI) Viewer")

st.markdown("""
Enter a city name to see its current Air Quality Index (AQI). 
Data provided by the World Air Quality Index Project.
""")

# Input field for the city name
city_input = st.text_input(
    "Enter City Name (e.g., London, Beijing, New Delhi)", 
#    "London"
).strip()

# Button to trigger the data fetch
if st.button("Get AQI"):
    if not city_input:
        st.error("Please enter a city name.")
    else:
        # Display a loading spinner while fetching data
        with st.spinner(f"Fetching AQI for **{city_input}**..."):
            aqi_data = get_aqi_data(city_input)

            if "error" in aqi_data:
                st.error(aqi_data["error"])
            else:
                # Extract main data
                aqi = aqi_data["aqi"]
                category, color = get_aqi_category(int(aqi))
                station_name = aqi_data.get("city", {}).get("name", "N/A")
                pollutants = aqi_data.get("iaqi", {})
                
                st.success(f"✅ Data fetched successfully for **{station_name}**")
                st.write("---")

                # Display the main AQI in a large, colored metric box
                st.subheader(f"Current AQI: {category}")
                st.markdown(
                    f"<div style='background-color:{color}; color:white; padding: 20px; border-radius: 10px; text-align: center;'>"
                    f"<h1>{aqi}</h1>"
                    f"</div>",
                    unsafe_allow_html=True
                )
                

#[Image of Air Quality Index (AQI) color categories chart]

                
                # Display individual pollutant levels
                st.subheader("Individual Pollutant Levels")
                col1, col2, col3 = st.columns(3)
                cols = [col1, col2, col3]
                
                pollutant_names = {
                    'p2': 'PM2.5', 'p1': 'PM10', 'o3': 'Ozone (O₃)', 
                    'no2': 'Nitrogen Dioxide (NO₂)', 'so2': 'Sulfur Dioxide (SO₂)', 
                    'co': 'Carbon Monoxide (CO)'
                }

                for i, (key, value) in enumerate(pollutants.items()):
                    if key in pollutant_names:
                         cols[i % 3].metric(
                            label=pollutant_names[key], 
                            value=f"{value['v']} µg/m³"
                        )
                
                st.write("---")
                st.info(
                    f"Last reported measurement time: **{aqi_data.get('time', {}).get('s', 'N/A')}**"
                )