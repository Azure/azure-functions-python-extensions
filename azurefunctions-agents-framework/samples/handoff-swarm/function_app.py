"""
Weather Advisory System - Swarm Pattern Example

This sample demonstrates the SWARM handoff pattern where agents collaborate
peer-to-peer and results bubble up to the user. Agents can call each other
directly and the final result is returned to the user.

Architecture:
- Weather Agent: Gets weather data and coordinates with other agents
- Temperature Converter: Converts temperatures between units
- Weather Advisor: Provides weather-based recommendations

Flow:
1. User asks for weather advice
2. Weather agent gets weather data
3. Weather agent hands off to temperature converter (if needed)
4. Weather agent hands off to advisor for recommendations
5. Results bubble up to user
"""

import asyncio
import json
import logging
import azure.functions as func
from typing import Dict, Any

from azurefunctions.agents import Agent, AgentFunctionApp
from azurefunctions.agents.handoff import (
    HandoffConfig, HandoffTarget, HandoffMode, ControlReturn
)
from azurefunctions.agents.types import LLMConfig, LLMProvider

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Mock weather API
async def get_weather(location: str) -> Dict[str, Any]:
    """Get weather information for a location."""
    # Simulated weather data
    weather_data = {
        "location": location,
        "temperature_celsius": 22,
        "temperature_fahrenheit": 72,
        "condition": "partly cloudy",
        "humidity": 65,
        "wind_speed": 10,
        "description": f"It's currently 22°C (72°F) and partly cloudy in {location}"
    }
    logging.info(f"Weather data for {location}: {weather_data}")
    return weather_data

async def convert_temperature(temperature: float, from_unit: str, to_unit: str) -> Dict[str, Any]:
    """Convert temperature between Celsius and Fahrenheit."""
    if from_unit.lower() == "celsius" and to_unit.lower() == "fahrenheit":
        converted = (temperature * 9/5) + 32
    elif from_unit.lower() == "fahrenheit" and to_unit.lower() == "celsius":
        converted = (temperature - 32) * 5/9
    else:
        converted = temperature
    
    result = {
        "original_temperature": temperature,
        "original_unit": from_unit,
        "converted_temperature": round(converted, 1),
        "converted_unit": to_unit,
        "conversion": f"{temperature}°{from_unit[0].upper()} = {round(converted, 1)}°{to_unit[0].upper()}"
    }
    logging.info(f"Temperature conversion: {result}")
    return result

async def get_weather_advice(weather_data: Dict[str, Any]) -> Dict[str, Any]:
    """Provide weather-based advice and recommendations."""
    temp_c = weather_data.get("temperature_celsius", 20)
    condition = weather_data.get("condition", "").lower()
    
    advice = []
    clothing = []
    activities = []
    
    # Temperature-based advice
    if temp_c < 0:
        clothing.extend(["heavy winter coat", "gloves", "warm hat"])
        advice.append("Bundle up! It's freezing outside.")
        activities.append("indoor activities recommended")
    elif temp_c < 10:
        clothing.extend(["warm jacket", "long pants"])
        advice.append("Dress warmly, it's quite cold.")
        activities.extend(["hot drinks", "cozy indoor venues"])
    elif temp_c < 20:
        clothing.extend(["light jacket", "layers"])
        advice.append("Perfect weather for a walk!")
        activities.extend(["walking", "outdoor dining"])
    elif temp_c < 30:
        clothing.extend(["light clothing", "comfortable shoes"])
        advice.append("Great weather for outdoor activities!")
        activities.extend(["picnic", "hiking", "cycling"])
    else:
        clothing.extend(["lightweight clothing", "sun hat", "sunglasses"])
        advice.append("Stay cool and hydrated!")
        activities.extend(["swimming", "water sports", "early morning walks"])
    
    # Condition-based advice
    if "rain" in condition or "storm" in condition:
        clothing.append("umbrella or raincoat")
        advice.append("Don't forget your umbrella!")
        activities = ["indoor activities", "museums", "shopping"]
    elif "snow" in condition:
        clothing.extend(["waterproof boots", "warm layers"])
        advice.append("Watch out for slippery conditions!")
        activities.extend(["skiing", "snowball fights", "hot chocolate"])
    elif "sunny" in condition:
        clothing.extend(["sunscreen", "sunglasses"])
        advice.append("Don't forget sunscreen!")
    
    result = {
        "advice_summary": " ".join(advice),
        "recommended_clothing": clothing,
        "suggested_activities": activities,
        "weather_context": {
            "temperature": f"{temp_c}°C",
            "condition": condition
        }
    }
    logging.info(f"Weather advice generated: {result}")
    return result

# Configure LLM
llm_config = LLMConfig(
    provider=LLMProvider.OPENAI,
    model_name="gpt-4",
    api_key_env_var="OPENAI_API_KEY"
)

# Weather Agent - Main coordinator in swarm
weather_agent = Agent(
    name="weather",
    instructions="""You are a weather information agent. You can:
1. Get weather data for any location
2. Hand off to temperature converter for unit conversions
3. Hand off to weather advisor for clothing and activity recommendations

When users ask for weather information, get the data and then coordinate with other agents as needed.
Use handoffs to provide comprehensive weather advice including temperature conversions and recommendations.
""",
    tools=[get_weather],
    llm_config=llm_config,
    handoff_config=HandoffConfig(
        mode=HandoffMode.SWARM,
        targets=[
            HandoffTarget(
                agent_name="temperature_converter",
                description="Convert temperatures between Celsius and Fahrenheit"
            ),
            HandoffTarget(
                agent_name="weather_advisor", 
                description="Get clothing and activity recommendations based on weather"
            )
        ]
    )
)

# Temperature Converter Agent
temperature_converter = Agent(
    name="temperature_converter",
    instructions="""You are a temperature conversion specialist. You convert temperatures between Celsius and Fahrenheit.
When you receive weather data, extract the temperature and convert it as requested.
You can hand back to the weather agent or advisor as needed in the swarm.
""",
    tools=[convert_temperature],
    llm_config=llm_config,
    handoff_config=HandoffConfig(
        mode=HandoffMode.SWARM,
        targets=[
            HandoffTarget(
                agent_name="weather",
                description="Hand back to weather agent for coordination"
            ),
            HandoffTarget(
                agent_name="weather_advisor",
                description="Hand off to advisor with converted temperature data"
            )
        ]
    )
)

# Weather Advisor Agent
weather_advisor = Agent(
    name="weather_advisor",
    instructions="""You are a weather advisory specialist. You provide clothing recommendations and activity suggestions based on weather conditions.
When you receive weather data, analyze it and provide practical advice for what to wear and what activities to do.
You can hand back to other agents in the swarm as needed.
""",
    tools=[get_weather_advice],
    llm_config=llm_config,
    handoff_config=HandoffConfig(
        mode=HandoffMode.SWARM,
        targets=[
            HandoffTarget(
                agent_name="weather",
                description="Hand back to weather agent for coordination" 
            ),
            HandoffTarget(
                agent_name="temperature_converter",
                description="Hand off for temperature conversions"
            )
        ]
    )
)

# Create the multi-agent function app with handoff system
agent_app = AgentFunctionApp(
    agents=[weather_agent, temperature_converter, weather_advisor]
)

# Manual function to demonstrate direct runner usage
@app.route(route="weather-swarm", methods=["POST"])
async def weather_swarm_demo(req: func.HttpRequest) -> func.HttpResponse:
    """
    Demonstrate the swarm pattern with direct runner handoffs.
    This shows how agents collaborate peer-to-peer.
    """
    try:
        req_body = req.get_json()
        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "Request body is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        user_message = req_body.get("message", "")
        location = req_body.get("location", "Seattle")
        
        logging.info(f"Swarm demo request: {user_message} for {location}")
        
        # Get runners
        weather_runner = agent_app.runners["weather"]
        temp_runner = agent_app.runners["temperature_converter"] 
        advisor_runner = agent_app.runners["weather_advisor"]
        
        # Start with weather agent
        weather_response = await weather_runner.run({
            "message": f"Get weather for {location}",
            "location": location
        })
        
        # Demonstrate swarm handoffs
        conversation_id = f"swarm-demo-{asyncio.current_task().get_name()}"
        
        # Weather agent hands off to temperature converter
        temp_response = await weather_runner.handoff_to(
            target_agent="temperature_converter",
            input_data={
                "temperature": 22,
                "from_unit": "celsius", 
                "to_unit": "fahrenheit"
            },
            conversation_id=conversation_id,
            reason="User wants temperature in Fahrenheit"
        )
        
        # Weather agent hands off to advisor
        advice_response = await weather_runner.handoff_to(
            target_agent="weather_advisor",
            input_data={
                "weather_data": {
                    "location": location,
                    "temperature_celsius": 22,
                    "condition": "partly cloudy",
                    "humidity": 65
                }
            },
            conversation_id=conversation_id,
            reason="User needs weather advice and recommendations"
        )
        
        # Combine results (in swarm pattern, results bubble up)
        result = {
            "pattern": "swarm",
            "location": location,
            "weather_data": weather_response.content,
            "temperature_conversion": temp_response.content,
            "weather_advice": advice_response.content,
            "handoff_path": ["weather", "temperature_converter", "weather_advisor"],
            "conversation_id": conversation_id,
            "summary": f"Complete weather analysis for {location} using swarm collaboration"
        }
        
        return func.HttpResponse(
            json.dumps(result, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in weather swarm demo: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

# Health check
@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint."""
    return func.HttpResponse(
        json.dumps({
            "status": "healthy",
            "sample": "handoff-swarm",
            "agents": ["weather", "temperature_converter", "weather_advisor"],
            "pattern": "swarm - peer-to-peer collaboration"
        }),
        status_code=200,
        mimetype="application/json"
    )
