import json
import os
import requests
import traceback
from utils import log

def send_weather_api_request(service, endpoint=None, params=None):
    """Send requests to weather-related APIs"""
    try:
        service_urls = {
            'ipapi': 'https://ipapi.co/json/',
            'openmeteo': 'https://api.open-meteo.com/v1',
            'nominatim': 'https://nominatim.openstreetmap.org'
        }
        
        if service not in service_urls:
            log(f"Unsupported weather service: {service}", "ERROR")
            return None
        
        if endpoint:
            url = f"{service_urls[service]}/{endpoint}"
        else:
            url = service_urls[service]
        
        headers = {
            "User-Agent": "VocalComputer/1.0 (contact: user@example.com)"
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        log(f"Weather API request failed for {service}: {e}\n{traceback.format_exc()}", "ERROR")
        return None

def get_ip_location():
    """Get current location using IP geolocation service"""
    return send_weather_api_request('ipapi')

def get_location_coordinates(location_name):
    """Get coordinates for a location name using Nominatim"""
    params = {
        "q": location_name,
        "format": "json",
        "limit": 1
    }
    return send_weather_api_request('nominatim', 'search', params)

def api_get_weather_forecast(lat, lon, params=None):
    """Get weather forecast using Open-Meteo API"""
    if not params:
        params = {}
    params.update({
        "latitude": lat,
        "longitude": lon
    })
    return send_weather_api_request('openmeteo', 'forecast', params)

def run(action=None, location=None, **kwargs):
    """
    Weather module using free APIs and automatic location detection
    
    Actions:
    - current: Get current weather
    - forecast: Get 5-day forecast
    - today: Get today's weather summary
    """
    script_name = "weather.py"
    
    if not action:
        action = "current"  # Default action
    
    try:
        # Get location (either provided or auto-detect)
        if not location:
            lat, lon, city = get_current_location()
            if not lat or not lon:
                log(f"[weather.py] Could not determine location", level="ERROR", script=script_name)
                return
        else:
            lat, lon, city = get_coordinates_from_location(location)
            if not lat or not lon:
                log(f"[weather.py] Could not find coordinates for: {location}", level="ERROR", script=script_name)
                return
        
        if action == "current":
            weather_data = get_current_weather(lat, lon, city)
            filename = kwargs.get('filename', 'current_weather.json')
            save_weather_to_temp(weather_data, filename)
            return f"Current weather data retrieved and saved to {filename}."
            
        elif action == "forecast":
            forecast_data = get_weather_forecast(lat, lon, city)
            filename = kwargs.get('filename', 'weather_forecast.json')
            save_weather_to_temp(forecast_data, filename)
            return f"Weather forecast data retrieved and saved to {filename}."
            
        elif action == "today":
            weather_data = get_current_weather(lat, lon, city)
            forecast_data = get_weather_forecast(lat, lon, city)
            filename = kwargs.get('filename', 'today_weather.json')
            
            # Combine current + today's forecast
            today_data = {
                "current": weather_data,
                "today_forecast": forecast_data["daily"][0] if forecast_data.get("daily") else None
            }
            save_weather_to_temp(today_data, filename)
            return f"Today's weather data retrieved and saved to {filename}."
            
        else:
            log(f"Unknown action: {action}", "ERROR", script="weather.py")
            return f"Unknown weather action: {action}. Use current, forecast, or today."
            
    except Exception as e:
        log(f"Error in weather operation: {e}", "ERROR", script="weather.py")

def get_current_location():
    """
    Auto-detect current location using IP geolocation (free service)
    """
    try:
        data = get_ip_location()
        if not data:
            return None, None, None
        
        lat = data.get("latitude")
        lon = data.get("longitude")
        city = f"{data.get('city', 'Unknown')}, {data.get('country_name', 'Unknown')}"
        
        return lat, lon, city
        
    except Exception as e:
        log(f"Error auto-detecting location: {e}", "ERROR", script="weather.py")
        return None, None, None

def get_coordinates_from_location(location):
    """
    Get coordinates from location name using free geocoding service
    """
    try:
        data = get_location_coordinates(location)
        if not data or not isinstance(data, list) or len(data) == 0:
            return None, None, None
        
        result = data[0]
        lat = float(result["lat"])
        lon = float(result["lon"])
        city = result["display_name"]
        
        return lat, lon, city
        
    except Exception as e:
        log(f"Error geocoding location: {e}", "ERROR", script="weather.py")
        return None, None, None

def get_current_weather(lat, lon, city):
    """
    Get current weather using Open-Meteo API (free, no API key required)
    """
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": "true",
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,weather_code",
            "timezone": "auto"
        }
        
        data = api_get_weather_forecast(lat, lon, params)
        if not data:
            return None
        
        current = data.get("current_weather", {})
        
        # Format the weather data
        weather_data = {
            "location": city,
            "coordinates": {"lat": lat, "lon": lon},
            "current": {
                "temperature": current.get("temperature"),
                "temperature_unit": data.get("current_weather_units", {}).get("temperature", "°C"),
                "wind_speed": current.get("windspeed"),
                "wind_direction": current.get("winddirection"),
                "weather_code": current.get("weathercode"),
                "weather_description": get_weather_description(current.get("weathercode")),
                "time": current.get("time")
            },
            "timezone": data.get("timezone"),
            "update_time": current.get("time")
        }
        
        return weather_data
        
    except Exception as e:
        log(f"[weather.py] Error fetching current weather: {e}", level="ERROR", script="weather.py")
        return None

def get_weather_forecast(lat, lon, city):
    """
    Get weather forecast using Open-Meteo API
    """
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
            "timezone": "auto",
            "forecast_days": 5
        }
        
        data = api_get_weather_forecast(lat, lon, params)
        if not data:
            return None
        
        daily = data.get("daily", {})
        
        # Format forecast data
        forecast_data = {
            "location": city,
            "coordinates": {"lat": lat, "lon": lon},
            "daily": []
        }
        
        if daily.get("time"):
            for i, date in enumerate(daily["time"]):
                day_forecast = {
                    "date": date,
                    "temperature_max": daily.get("temperature_2m_max", [])[i] if i < len(daily.get("temperature_2m_max", [])) else None,
                    "temperature_min": daily.get("temperature_2m_min", [])[i] if i < len(daily.get("temperature_2m_min", [])) else None,
                    "precipitation": daily.get("precipitation_sum", [])[i] if i < len(daily.get("precipitation_sum", [])) else None,
                    "wind_speed": daily.get("wind_speed_10m_max", [])[i] if i < len(daily.get("wind_speed_10m_max", [])) else None,
                    "weather_code": daily.get("weather_code", [])[i] if i < len(daily.get("weather_code", [])) else None,
                    "weather_description": get_weather_description(daily.get("weather_code", [])[i] if i < len(daily.get("weather_code", [])) else None)
                }
                forecast_data["daily"].append(day_forecast)
        
        return forecast_data
        
    except Exception as e:
        log(f"[weather.py] Error fetching weather forecast: {e}", level="ERROR", script="weather.py")
        return None

def get_weather_description(weather_code):
    """
    Convert weather code to description (WMO Weather interpretation codes)
    """
    weather_codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Thunderstorm with heavy hail"
    }
    
    return weather_codes.get(weather_code, f"Unknown weather (code: {weather_code})")

def save_weather_to_temp(weather_data, filename):
    """Save weather data to temp folder for AI analysis"""
    try:
        temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../temp'))
        os.makedirs(temp_dir, exist_ok=True)
        
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(weather_data, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        log(f"Error saving weather data: {e}", "ERROR", script="weather.py")
