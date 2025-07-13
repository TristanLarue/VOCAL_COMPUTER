# weather.py - V2
# Enhanced weather information with unified interface
# Simplified interface with consistent keywords

import os
import json
import requests
from datetime import datetime
from utils import log

def run(action="current", return_data=False, **kwargs):
    """
    Unified weather information interface
    Actions: current, now, forecast, today, tomorrow, weekly, search, location
    Returns: Direct data or file-based response
    """
    try:
        action = action.lower()
        
        # Route to appropriate function
        if action in ['current', 'now', 'present']:
            return handle_current_weather(return_data, **kwargs)
        elif action in ['forecast', 'future', 'upcoming']:
            return handle_weather_forecast(return_data, **kwargs)
        elif action in ['today', 'daily']:
            return handle_today_weather(return_data, **kwargs)
        elif action in ['tomorrow', 'next']:
            return handle_tomorrow_weather(return_data, **kwargs)
        elif action in ['weekly', 'week', '7day']:
            return handle_weekly_forecast(return_data, **kwargs)
        elif action in ['search', 'location', 'find']:
            return handle_location_weather(return_data, **kwargs)
        else:
            # Default to current weather
            return handle_current_weather(return_data, **kwargs)
            
    except Exception as e:
        error_msg = f"Error in weather module: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_current_weather(return_data, **kwargs):
    """Get current weather conditions"""
    try:
        location = kwargs.get('location') or kwargs.get('city') or kwargs.get('place')
        
        if location:
            lat, lon, city = get_coordinates_from_location(location)
        else:
            lat, lon, city = get_current_location()
        
        if not lat or not lon:
            return create_response(False, "Could not determine location", return_data)
        
        weather_data = get_current_weather(lat, lon, city)
        if not weather_data:
            return create_response(False, "Could not retrieve weather data", return_data)
        
        # Format response message
        current = weather_data["current"]
        temp = current["temperature"]
        unit = current["temperature_unit"]
        desc = current["weather_description"]
        
        message = f"Current weather in {city}: {temp}{unit}, {desc}"
        
        return create_response(True, message, return_data, weather_data)
        
    except Exception as e:
        error_msg = f"Error getting current weather: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_weather_forecast(return_data, **kwargs):
    """Get weather forecast"""
    try:
        location = kwargs.get('location') or kwargs.get('city') or kwargs.get('place')
        days = kwargs.get('days', 5)
        
        try:
            days = int(days)
            if days < 1 or days > 14:
                days = 5
        except (ValueError, TypeError):
            days = 5
        
        if location:
            lat, lon, city = get_coordinates_from_location(location)
        else:
            lat, lon, city = get_current_location()
        
        if not lat or not lon:
            return create_response(False, "Could not determine location", return_data)
        
        forecast_data = get_weather_forecast(lat, lon, city, days)
        if not forecast_data:
            return create_response(False, "Could not retrieve forecast data", return_data)
        
        message = f"{days}-day weather forecast for {city} retrieved"
        
        return create_response(True, message, return_data, forecast_data)
        
    except Exception as e:
        error_msg = f"Error getting weather forecast: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_today_weather(return_data, **kwargs):
    """Get today's weather summary"""
    try:
        location = kwargs.get('location') or kwargs.get('city') or kwargs.get('place')
        
        if location:
            lat, lon, city = get_coordinates_from_location(location)
        else:
            lat, lon, city = get_current_location()
        
        if not lat or not lon:
            return create_response(False, "Could not determine location", return_data)
        
        # Get both current and today's forecast
        current_data = get_current_weather(lat, lon, city)
        forecast_data = get_weather_forecast(lat, lon, city, 1)
        
        if not current_data or not forecast_data:
            return create_response(False, "Could not retrieve weather data", return_data)
        
        # Combine current + today's forecast
        today_data = {
            "action": "today",
            "location": city,
            "coordinates": {"lat": lat, "lon": lon},
            "current": current_data["current"],
            "today_forecast": forecast_data["daily"][0] if forecast_data.get("daily") else None,
            "timestamp": datetime.now().isoformat()
        }
        
        message = f"Today's weather summary for {city}"
        
        return create_response(True, message, return_data, today_data)
        
    except Exception as e:
        error_msg = f"Error getting today's weather: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_tomorrow_weather(return_data, **kwargs):
    """Get tomorrow's weather forecast"""
    try:
        location = kwargs.get('location') or kwargs.get('city') or kwargs.get('place')
        
        if location:
            lat, lon, city = get_coordinates_from_location(location)
        else:
            lat, lon, city = get_current_location()
        
        if not lat or not lon:
            return create_response(False, "Could not determine location", return_data)
        
        forecast_data = get_weather_forecast(lat, lon, city, 2)
        if not forecast_data or len(forecast_data.get("daily", [])) < 2:
            return create_response(False, "Could not retrieve tomorrow's forecast", return_data)
        
        tomorrow_data = {
            "action": "tomorrow",
            "location": city,
            "coordinates": {"lat": lat, "lon": lon},
            "forecast": forecast_data["daily"][1],
            "timestamp": datetime.now().isoformat()
        }
        
        tomorrow = forecast_data["daily"][1]
        temp_max = tomorrow.get("temperature_max", "N/A")
        temp_min = tomorrow.get("temperature_min", "N/A")
        desc = tomorrow.get("weather_description", "N/A")
        
        message = f"Tomorrow's weather in {city}: {temp_max}°C/{temp_min}°C, {desc}"
        
        return create_response(True, message, return_data, tomorrow_data)
        
    except Exception as e:
        error_msg = f"Error getting tomorrow's weather: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_weekly_forecast(return_data, **kwargs):
    """Get weekly weather forecast"""
    try:
        location = kwargs.get('location') or kwargs.get('city') or kwargs.get('place')
        
        if location:
            lat, lon, city = get_coordinates_from_location(location)
        else:
            lat, lon, city = get_current_location()
        
        if not lat or not lon:
            return create_response(False, "Could not determine location", return_data)
        
        forecast_data = get_weather_forecast(lat, lon, city, 7)
        if not forecast_data:
            return create_response(False, "Could not retrieve weekly forecast", return_data)
        
        message = f"7-day weather forecast for {city}"
        
        return create_response(True, message, return_data, forecast_data)
        
    except Exception as e:
        error_msg = f"Error getting weekly forecast: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

def handle_location_weather(return_data, **kwargs):
    """Get weather for a specific location"""
    try:
        location = kwargs.get('location') or kwargs.get('city') or kwargs.get('place') or kwargs.get('query')
        
        if not location:
            return create_response(False, "Location is required", return_data)
        
        lat, lon, city = get_coordinates_from_location(location)
        if not lat or not lon:
            return create_response(False, f"Could not find location: {location}", return_data)
        
        # Get current weather for the location
        weather_data = get_current_weather(lat, lon, city)
        if not weather_data:
            return create_response(False, "Could not retrieve weather data", return_data)
        
        # Add location search info
        weather_data["search_query"] = location
        weather_data["found_location"] = city
        
        current = weather_data["current"]
        temp = current["temperature"]
        unit = current["temperature_unit"]
        desc = current["weather_description"]
        
        message = f"Weather in {city}: {temp}{unit}, {desc}"
        
        return create_response(True, message, return_data, weather_data)
        
    except Exception as e:
        error_msg = f"Error getting location weather: {str(e)}"
        log(error_msg, "ERROR")
        return create_response(False, error_msg, return_data)

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
        log(f"Weather API request failed for {service}: {e}", "ERROR")
        return None

def get_current_location():
    """Get current location using IP geolocation"""
    try:
        data = send_weather_api_request('ipapi')
        if not data:
            return None, None, None
        
        lat = data.get("latitude")
        lon = data.get("longitude")
        city = f"{data.get('city', 'Unknown')}, {data.get('country_name', 'Unknown')}"
        
        return lat, lon, city
        
    except Exception as e:
        log(f"Error auto-detecting location: {e}", "ERROR")
        return None, None, None

def get_coordinates_from_location(location):
    """Get coordinates from location name"""
    try:
        params = {
            "q": location,
            "format": "json",
            "limit": 1
        }
        data = send_weather_api_request('nominatim', 'search', params)
        
        if not data or not isinstance(data, list) or len(data) == 0:
            return None, None, None
        
        result = data[0]
        lat = float(result["lat"])
        lon = float(result["lon"])
        city = result["display_name"]
        
        return lat, lon, city
        
    except Exception as e:
        log(f"Error geocoding location: {e}", "ERROR")
        return None, None, None

def get_current_weather(lat, lon, city):
    """Get current weather using Open-Meteo API"""
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": "true",
            "hourly": "temperature_2m,relative_humidity_2m,precipitation,weather_code",
            "timezone": "auto"
        }
        
        data = send_weather_api_request('openmeteo', 'forecast', params)
        if not data:
            return None
        
        current = data.get("current_weather", {})
        
        weather_data = {
            "action": "current",
            "location": city,
            "coordinates": {"lat": lat, "lon": lon},
            "current": {
                "temperature": current.get("temperature"),
                "temperature_unit": "°C",
                "wind_speed": current.get("windspeed"),
                "wind_direction": current.get("winddirection"),
                "weather_code": current.get("weathercode"),
                "weather_description": get_weather_description(current.get("weathercode")),
                "time": current.get("time")
            },
            "timezone": data.get("timezone"),
            "timestamp": datetime.now().isoformat()
        }
        
        return weather_data
        
    except Exception as e:
        log(f"Error fetching current weather: {e}", "ERROR")
        return None

def get_weather_forecast(lat, lon, city, days=5):
    """Get weather forecast using Open-Meteo API"""
    try:
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
            "timezone": "auto",
            "forecast_days": min(days, 14)
        }
        
        data = send_weather_api_request('openmeteo', 'forecast', params)
        if not data:
            return None
        
        daily = data.get("daily", {})
        
        forecast_data = {
            "action": "forecast",
            "location": city,
            "coordinates": {"lat": lat, "lon": lon},
            "daily": [],
            "forecast_days": days,
            "timestamp": datetime.now().isoformat()
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
        log(f"Error fetching weather forecast: {e}", "ERROR")
        return None

def get_weather_description(weather_code):
    """Convert weather code to description (WMO Weather interpretation codes)"""
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

def create_response(success, message, return_data, data=None):
    """Create standardized response"""
    response = {
        "success": success,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "module": "weather"
    }
    
    if data:
        response.update(data)
    
    if return_data:
        return response
    else:
        # Save to file
        filename = f"weather_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        save_to_temp(response, filename)
        return message

def save_to_temp(data, filename):
    """Save data to temp folder"""
    try:
        temp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../temp'))
        os.makedirs(temp_dir, exist_ok=True)
        
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        log(f"Weather data saved to {filename}", "INFO")
        
    except Exception as e:
        log(f"Error saving to temp: {e}", "ERROR")
