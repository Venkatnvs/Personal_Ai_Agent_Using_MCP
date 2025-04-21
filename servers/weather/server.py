from dataclasses import dataclass
import os
import requests
import logging
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Weather Tool")

@dataclass
class WeatherInput:
    """
    Input parameters for fetching weather.
    Either a city name must be provided or both latitude and longitude.
    - units: 'metric', 'imperial', or 'standard'
    """
    city: str = None
    lat: float = None
    lon: float = None
    units: str = "metric"

@mcp.tool()
def get_weather(input_data: WeatherInput):
    """
    Retrieve current weather information from OpenWeatherMap API.
    Provide either a city name or latitude and longitude.
    """
    API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
    if not API_KEY:
        return {"status": "error", "message": "Weather API key is required."}
        
    base_url = "https://api.openweathermap.org/data/2.5/weather"
    query_params = {
        "appid": API_KEY,
        "units": input_data.units
    }
    
    if input_data.city:
        query_params["q"] = input_data.city
    elif input_data.lat is not None and input_data.lon is not None:
        query_params["lat"] = input_data.lat
        query_params["lon"] = input_data.lon
    else:
        return {"status": "error", "message": "Provide a city name or latitude/longitude coordinates."}
    
    try:
        response = requests.get(base_url, params=query_params)
        response.raise_for_status()
        data = response.json()
        weather_info = {
            "status": "success",
            "location": data.get("name"),
            "country": data.get("sys", {}).get("country"),
            "temperature": data.get("main", {}).get("temp"),
            "feels_like": data.get("main", {}).get("feels_like"),
            "conditions": data.get("weather", [{}])[0].get("description", "N/A"),
            "humidity": data.get("main", {}).get("humidity"),
            "wind_speed": data.get("wind", {}).get("speed"),
            "units": input_data.units
        }
        logging.info(f"Weather fetched for {weather_info.get('location')}")
        return weather_info
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logging.warning("Location not found.")
            return {"status": "error", "message": "Location not found."}
        elif e.response.status_code == 401:
            logging.error("Authentication failed for weather API.")
            return {"status": "error", "message": "Weather API authentication failed."}
        else:
            logging.error(f"HTTP error: {e}")
            return {"status": "error", "message": f"Weather API error: {e}"}
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        return {"status": "error", "message": f"Unexpected error: {e}"}

if __name__ == "__main__":
    mcp.run(transport='stdio')