"""
skills/weather_skill.py
DNA Weather Skill — OpenWeatherMap free API (1000 calls/day)

Capabilities:
  1. get_weather(city)      - current weather for a city
  2. get_forecast(city)     - 3-day forecast
  3. morning_weather()      - compact weather for default city (startup use)
"""

import logging
import os

import requests

from config import WEATHER_API_KEY, WEATHER_DEFAULT_CITY

logger = logging.getLogger('dna.skill.weather')

# ── Constants ─────────────────────────────────────────────────────────────────

OWM_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
OWM_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _direction(deg: float) -> str:
    """Convert wind degrees to compass direction."""
    dirs = ["north", "northeast", "east", "southeast",
            "south", "southwest", "west", "northwest"]
    idx = int((deg + 22.5) / 45) % 8
    return dirs[idx]


def _describe_conditions(weather_list: list) -> str:
    """Build a human-friendly weather description."""
    if not weather_list:
        return "unknown conditions"
    descriptions = [w.get("description", "") for w in weather_list]
    return " and ".join(descriptions)


# ── Main Tools ────────────────────────────────────────────────────────────────

def get_weather(city: str = "") -> str:
    """
    Get current weather for a city.
    If no city specified, uses default from config.
    """
    city = city.strip() if city else WEATHER_DEFAULT_CITY

    if not WEATHER_API_KEY:
        return ("Weather is not configured yet. "
                "Add your OpenWeatherMap API key as WEATHER_API_KEY in the .env file. "
                "It is free at openweathermap.org.")

    try:
        resp = requests.get(OWM_CURRENT_URL, params={
            "q": city,
            "appid": WEATHER_API_KEY,
            "units": "metric",
        }, timeout=8)

        if resp.status_code == 404:
            return f"I could not find weather data for {city}. Check the city name."
        resp.raise_for_status()

        data = resp.json()

        temp      = round(data["main"]["temp"])
        feels     = round(data["main"]["feels_like"])
        humidity  = data["main"]["humidity"]
        desc      = _describe_conditions(data.get("weather", []))
        wind_speed = round(data["wind"]["speed"] * 3.6)   # m/s to km/h
        wind_dir  = _direction(data["wind"].get("deg", 0))
        city_name = data.get("name", city)

        response = (
            f"Currently in {city_name}, it is {temp} degrees celsius "
            f"with {desc}. "
            f"Feels like {feels} degrees. "
            f"Humidity is {humidity} percent. "
            f"Wind is blowing {wind_dir} at {wind_speed} kilometers per hour."
        )

        # Add rain info if present
        rain = data.get("rain", {})
        if rain:
            mm = rain.get("1h", rain.get("3h", 0))
            if mm:
                response += f" There has been {mm} millimeters of rain recently."

        return response

    except requests.RequestException as e:
        logger.error("Weather API failed: %s", e)
        return f"Could not fetch weather right now: {str(e)}"
    except Exception as e:
        logger.error("Weather parsing failed: %s", e)
        return f"Weather data was unclear: {str(e)}"


def get_forecast(city: str = "") -> str:
    """Get a 3-day weather forecast for a city."""
    city = city.strip() if city else WEATHER_DEFAULT_CITY

    if not WEATHER_API_KEY:
        return "Weather is not configured. Add WEATHER_API_KEY to your .env file."

    try:
        resp = requests.get(OWM_FORECAST_URL, params={
            "q": city,
            "appid": WEATHER_API_KEY,
            "units": "metric",
            "cnt": 24,  # 3-hour intervals × 8 = 24 hours, ×3 = 72h
        }, timeout=8)

        if resp.status_code == 404:
            return f"Could not find forecast for {city}."
        resp.raise_for_status()

        data = resp.json()
        forecasts = data.get("list", [])

        if not forecasts:
            return f"No forecast data available for {city}."

        # Group by day (take noon reading for each day)
        day_forecasts = {}
        for item in forecasts:
            dt_txt = item.get("dt_txt", "")
            date_part = dt_txt.split(" ")[0]
            hour = dt_txt.split(" ")[1] if " " in dt_txt else ""

            # Prefer 12:00 or 15:00 reading for each day
            if date_part not in day_forecasts or "12:00" in hour:
                day_forecasts[date_part] = item

        city_name = data.get("city", {}).get("name", city)
        response = f"Here is the forecast for {city_name}. "

        from datetime import datetime
        today = datetime.now().strftime("%Y-%m-%d")
        count = 0

        for date_str, item in sorted(day_forecasts.items()):
            if count >= 3:
                break
            if date_str == today:
                continue  # skip today, already covered by get_weather

            temp = round(item["main"]["temp"])
            desc = _describe_conditions(item.get("weather", []))
            humidity = item["main"]["humidity"]

            # Format date
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d")
                day_name = dt.strftime("%A")
            except Exception:
                day_name = date_str

            response += f"{day_name}: {temp} degrees, {desc}, humidity {humidity} percent. "
            count += 1

        if count == 0:
            response += "No future forecast data available yet."

        return response

    except Exception as e:
        logger.error("Forecast failed: %s", e)
        return f"Could not fetch the forecast: {str(e)}"


def morning_weather() -> str:
    """
    Compact weather for morning briefing.
    Returns a short one-liner for the default city.
    """
    if not WEATHER_API_KEY:
        return ""  # silent if not configured

    try:
        resp = requests.get(OWM_CURRENT_URL, params={
            "q": WEATHER_DEFAULT_CITY,
            "appid": WEATHER_API_KEY,
            "units": "metric",
        }, timeout=6)

        if resp.status_code != 200:
            return ""

        data = resp.json()
        temp = round(data["main"]["temp"])
        desc = _describe_conditions(data.get("weather", []))
        city = data.get("name", WEATHER_DEFAULT_CITY)

        return f"It is currently {temp} degrees and {desc} in {city}."

    except Exception:
        return ""  # silent on failure


# ── Skill Contract ────────────────────────────────────────────────────────────

TOOLS = {
    "get_weather":    get_weather,
    "get_forecast":   get_forecast,
    "morning_weather": morning_weather,
}
