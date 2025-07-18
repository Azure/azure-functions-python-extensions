"""
Modern Weather Agent using the Azure Functions Agent Framework

This example demonstrates the Azure Functions Agent Framework with:
- Clean, modern agent architecture
- Proper error handling and retry logic
- Environment-based configuration
- Real weather data integration
- Azure Functions HTTP triggers
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, Tuple

import aiohttp

from azurefunctions.agents import Agent, AgentFunctionApp
from azurefunctions.agents.types import LLMConfig, LLMProvider

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OPENWEATHER_BASE_URL = "http://api.openweathermap.org"
GEOCODING_BASE_URL = "http://api.openweathermap.org/geo/1.0"


class WeatherAPIError(Exception):
    """Custom exception for weather API errors."""


class LocationNotFoundError(Exception):
    """Raised when a location cannot be found."""


# System instructions for the weather agent
WEATHER_AGENT_INSTRUCTIONS = """
You are WeatherBot, a helpful and friendly weather assistant powered by Azure Functions and AI.

Your capabilities include:
- Getting current weather conditions using real-time data from OpenWeatherMap
- Providing weather-appropriate clothing and activity advice
- Converting between temperature units (Celsius/Fahrenheit)
- Giving practical travel and outdoor activity recommendations

IMPORTANT TOOL USAGE PATTERNS:
When users ask for weather information for a location, ALWAYS follow this sequence:
1. First, call get_current_weather to get the actual current conditions
2. Then, use the weather data to call get_weather_advice with the actual conditions and temperature
3. ALWAYS provide a comprehensive final response combining both weather data and practical advice

Example workflow for "What's the weather advice for Austin?":
1. Call get_current_weather(location="Austin", units="celsius")
2. Call get_weather_advice(condition="clear", temperature=25) using the actual data from step 1
3. Provide a complete response like: "Based on the current weather in Austin (25°C, Clear Sky), here's my advice: [clothing recommendations] [activity suggestions] [precautions]"

CRITICAL: After calling tools, you MUST provide a helpful summary response to the user. Never leave the response empty.

Key behaviors:
- ALWAYS chain tools together when users ask for weather advice
- ALWAYS provide a final response after tool execution
- Use proper temperature units based on user preference or location
- Provide practical advice (clothing, activities, travel considerations) based on ACTUAL current conditions
- Be friendly and engaging in your responses
- Handle errors gracefully and suggest alternatives
- If a location is ambiguous, ask for clarification or suggest similar locations
"""


async def retry_async_operation(operation, max_retries: int = 3, delay: float = 1.0):
    """Retry an async operation with exponential backoff."""
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await operation()
        except Exception as e:
            last_exception = e
            if attempt == max_retries:
                break

            wait_time = delay * (2**attempt)
            logger.warning(
                f"Operation failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)}. Retrying in {wait_time} seconds..."
            )
            await asyncio.sleep(wait_time)

    raise last_exception


async def get_lat_lng(location: str) -> Tuple[float, float]:
    """Get latitude and longitude coordinates for a location."""
    if not OPENWEATHER_API_KEY:
        raise WeatherAPIError(
            "OpenWeather API key not configured. Please set OPENWEATHER_API_KEY environment variable."
        )

    async def _fetch_coordinates():
        async with aiohttp.ClientSession() as session:
            url = f"{GEOCODING_BASE_URL}/direct"
            params = {"q": location, "limit": 1, "appid": OPENWEATHER_API_KEY}

            async with session.get(url, params=params) as response:
                if response.status != 200:
                    raise WeatherAPIError(
                        f"Geocoding API returned status {response.status}"
                    )

                data = await response.json()
                if not data:
                    raise LocationNotFoundError(f"Could not find location: {location}")

                location_data = data[0]
                return float(location_data["lat"]), float(location_data["lon"])

    return await retry_async_operation(_fetch_coordinates)


async def fetch_weather_data(
    lat: float, lng: float, units: str = "metric"
) -> Dict[str, Any]:
    """Fetch current weather data from OpenWeather API."""
    if not OPENWEATHER_API_KEY:
        raise WeatherAPIError("OpenWeather API key not configured")

    async def _fetch_weather():
        async with aiohttp.ClientSession() as session:
            url = f"{OPENWEATHER_BASE_URL}/data/2.5/weather"
            params = {
                "lat": lat,
                "lon": lng,
                "appid": OPENWEATHER_API_KEY,
                "units": units,
            }

            async with session.get(url, params=params) as response:
                if response.status != 200:
                    raise WeatherAPIError(
                        f"Weather API returned status {response.status}"
                    )
                return await response.json()

    return await retry_async_operation(_fetch_weather)


async def get_current_weather(location: str, units: str = "celsius") -> Dict[str, Any]:
    """
    Get current weather conditions for a specified location using real weather data.

    Args:
        location: The city or location to get weather for (e.g., "Seattle", "New York")
        units: Temperature units - "celsius" or "fahrenheit" (default: celsius)

    Returns:
        Dictionary containing current weather information
    """
    logger.info(f"Getting weather for {location} in {units}")

    try:
        # Convert units to OpenWeather API format
        api_units = "metric" if units.lower() == "celsius" else "imperial"
        temp_symbol = "°C" if units.lower() == "celsius" else "°F"

        # Get coordinates and weather data
        lat, lng = await get_lat_lng(location)
        weather_data = await fetch_weather_data(lat, lng, api_units)

        # Extract relevant information
        main = weather_data["main"]
        weather = weather_data["weather"][0]
        wind = weather_data.get("wind", {})
        visibility = weather_data.get("visibility", 0) / 1000  # Convert to km

        return {
            "location": weather_data["name"],
            "country": weather_data["sys"]["country"],
            "coordinates": {"latitude": lat, "longitude": lng},
            "temperature": round(main["temp"], 1),
            "temperature_unit": units,
            "feels_like": round(main["feels_like"], 1),
            "condition": weather["main"],
            "description": weather["description"].title(),
            "humidity": main["humidity"],
            "pressure": main["pressure"],
            "wind_speed": wind.get("speed", 0),
            "wind_direction": wind.get("deg", 0),
            "visibility": round(visibility, 1),
            "cloudiness": weather_data["clouds"]["all"],
            "sunrise": datetime.fromtimestamp(
                weather_data["sys"]["sunrise"]
            ).isoformat(),
            "sunset": datetime.fromtimestamp(weather_data["sys"]["sunset"]).isoformat(),
            "summary": f"Current weather in {weather_data['name']}: {round(main['temp'], 1)}{temp_symbol}, {weather['description'].title()}",
            "timestamp": datetime.now().isoformat(),
        }

    except LocationNotFoundError as e:
        return {
            "error": str(e),
            "suggestion": "Please check the spelling or try a more specific location",
        }
    except WeatherAPIError as e:
        return {
            "error": f"Weather service error: {str(e)}",
            "suggestion": "Please try again later",
        }
    except Exception as e:
        logger.error(f"Unexpected error getting weather for {location}: {str(e)}")
        return {
            "error": f"Failed to get weather data: {str(e)}",
            "suggestion": "Please try again later",
        }


def convert_temperature(
    temperature: float, from_unit: str, to_unit: str
) -> Dict[str, Any]:
    """
    Convert temperature between Celsius and Fahrenheit.

    Args:
        temperature: Temperature value to convert
        from_unit: Source unit ("celsius" or "fahrenheit")
        to_unit: Target unit ("celsius" or "fahrenheit")

    Returns:
        Dictionary with conversion results
    """
    from_unit = from_unit.lower()
    to_unit = to_unit.lower()

    if from_unit == to_unit:
        return {
            "original_temperature": temperature,
            "original_unit": from_unit,
            "converted_temperature": temperature,
            "converted_unit": to_unit,
            "message": f"No conversion needed - both temperatures are in {from_unit}",
        }

    if from_unit == "celsius" and to_unit == "fahrenheit":
        converted = (temperature * 9 / 5) + 32
        formula = "°F = (°C × 9/5) + 32"
    elif from_unit == "fahrenheit" and to_unit == "celsius":
        converted = (temperature - 32) * 5 / 9
        formula = "°C = (°F - 32) × 5/9"
    else:
        return {
            "error": f"Invalid conversion: {from_unit} to {to_unit}",
            "supported_units": ["celsius", "fahrenheit"],
        }

    converted = round(converted, 2)

    return {
        "original_temperature": temperature,
        "original_unit": from_unit,
        "converted_temperature": converted,
        "converted_unit": to_unit,
        "formula_used": formula,
        "message": f"{temperature}°{from_unit[0].upper()} = {converted}°{to_unit[0].upper()}",
    }


def get_weather_advice(
    condition: str, temperature: float = None, activity: str = None
) -> Dict[str, Any]:
    """
    Get weather-appropriate advice for clothing, activities, and precautions based on specific weather conditions.

    This function should be called AFTER getting current weather data to provide practical advice.
    Use the actual weather condition and temperature from get_current_weather results.

    Args:
        condition: Weather condition from current weather data (e.g., "sunny", "rainy", "cloudy", "clear", "snow")
        temperature: Current temperature to provide temperature-specific advice (required for best advice)
        activity: Optional planned activity to provide activity-specific advice

    Returns:
        Dictionary containing weather-appropriate advice for clothing, activities, and precautions
    """
    condition = condition.lower().strip()

    # Base advice for different conditions
    advice_map = {
        "clear": {
            "clothing": "Light, breathable clothing. Don't forget sunscreen and sunglasses!",
            "activities": "Perfect for outdoor activities like hiking, picnics, or sports",
            "precautions": "Stay hydrated and seek shade during peak sun hours (10 AM - 4 PM)",
        },
        "sunny": {
            "clothing": "Light, breathable clothing. Don't forget sunscreen and sunglasses!",
            "activities": "Perfect for outdoor activities like hiking, picnics, or sports",
            "precautions": "Stay hydrated and seek shade during peak sun hours (10 AM - 4 PM)",
        },
        "clouds": {
            "clothing": "Comfortable layers - easy to adjust if it warms up",
            "activities": "Great for walking, cycling, or any outdoor activities without glare",
            "precautions": "Weather may change, so keep an eye on forecasts",
        },
        "cloudy": {
            "clothing": "Comfortable layers - easy to adjust if it warms up",
            "activities": "Great for walking, cycling, or any outdoor activities without glare",
            "precautions": "Weather may change, so keep an eye on forecasts",
        },
        "rain": {
            "clothing": "Waterproof jacket, umbrella, and non-slip shoes",
            "activities": "Indoor activities recommended, or embrace the rain with proper gear",
            "precautions": "Drive carefully, watch for puddles, and stay warm and dry",
        },
        "rainy": {
            "clothing": "Waterproof jacket, umbrella, and non-slip shoes",
            "activities": "Indoor activities recommended, or embrace the rain with proper gear",
            "precautions": "Drive carefully, watch for puddles, and stay warm and dry",
        },
        "drizzle": {
            "clothing": "Light rain jacket or umbrella, comfortable shoes",
            "activities": "Light outdoor activities are still possible with proper gear",
            "precautions": "Light rain can make surfaces slippery",
        },
        "snow": {
            "clothing": "Warm winter clothing, waterproof boots, hat, and gloves",
            "activities": "Winter sports or cozy indoor activities",
            "precautions": "Drive carefully, watch for icy conditions, dress warmly",
        },
        "thunderstorm": {
            "clothing": "Stay indoors if possible, waterproof gear if you must go out",
            "activities": "Indoor activities strongly recommended",
            "precautions": "Avoid outdoor activities, stay away from windows, unplug electronics",
        },
        "mist": {
            "clothing": "Light layers, visibility may be reduced",
            "activities": "Indoor activities or careful outdoor activities",
            "precautions": "Reduced visibility - drive carefully, use headlights",
        },
        "fog": {
            "clothing": "Light layers, visibility may be reduced",
            "activities": "Indoor activities or careful outdoor activities",
            "precautions": "Severely reduced visibility - avoid driving if possible",
        },
    }

    base_advice = advice_map.get(
        condition,
        {
            "clothing": "Dress appropriately for the weather",
            "activities": "Plan activities based on current conditions",
            "precautions": "Stay weather-aware and be prepared",
        },
    )

    # Temperature-specific adjustments
    temp_advice = ""
    if temperature is not None:
        if temperature < 0:
            temp_advice = "Very cold! Bundle up with warm layers, hat, and gloves."
        elif temperature < 10:
            temp_advice = "Cold weather - wear warm clothing and layers."
        elif temperature < 20:
            temp_advice = "Cool weather - light jacket or sweater recommended."
        elif temperature < 30:
            temp_advice = "Pleasant temperature - comfortable clothing."
        else:
            temp_advice = "Hot weather - stay cool with light, loose clothing."

    return {
        "condition": condition.title(),
        "clothing_advice": base_advice["clothing"],
        "activity_suggestions": base_advice["activities"],
        "precautions": base_advice["precautions"],
        "temperature_advice": (
            temp_advice if temp_advice else "Temperature information not provided"
        ),
        "overall_recommendation": f"Current conditions are {condition} - "
        + base_advice["precautions"],
    }


# Configure LLM
llm_config = LLMConfig(
    provider=LLMProvider.OPENAI,
    model_name=os.getenv("LLM_MODEL_NAME", "gpt-4o-mini"),
    temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
    max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1500")),
)

# Create the Weather Agent
weather_agent = Agent(
    name="WeatherBot",
    instructions=WEATHER_AGENT_INSTRUCTIONS,
    tools=[get_current_weather, convert_temperature, get_weather_advice],
    llm_config=llm_config,
    enable_conversational_agent=True,
    description="A helpful weather assistant agent that provides current conditions and weather advice",
)

# Create Function App
app = AgentFunctionApp(agents={"WeatherBot": weather_agent})
