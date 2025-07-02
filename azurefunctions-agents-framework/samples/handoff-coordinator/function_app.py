"""
Travel Coordinator - Coordinator Pattern Example

This sample demonstrates the COORDINATOR handoff pattern where one central agent
orchestrates multiple specialist agents and returns a consolidated response.
The coordinator manages the workflow and combines results from specialists.

Architecture:
- Travel Coordinator: Central orchestrator that manages the workflow
- Flight Agent: Searches for flights
- Hotel Agent: Searches for hotels  
- Weather Agent: Provides weather information
- Restaurant Agent: Finds dining recommendations

Flow:
1. User requests travel planning
2. Coordinator analyzes request and creates workflow
3. Coordinator hands off to specialists in parallel or sequence
4. Coordinator consolidates all responses
5. Single comprehensive response returned to user
"""

import asyncio
import json
import logging
import azure.functions as func
from datetime import datetime, timedelta
from typing import Dict, Any, List

from azurefunctions.agents import Agent, AgentFunctionApp
from azurefunctions.agents.handoff import (
    HandoffConfig, HandoffTarget, HandoffMode, ControlReturn
)
from azurefunctions.agents.types import LLMConfig, LLMProvider

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Mock travel APIs
async def search_flights(origin: str, destination: str, departure_date: str, return_date: str = None) -> Dict[str, Any]:
    """Search for flights between two cities."""
    flights = [
        {
            "flight_id": "FL001",
            "airline": "SkyLine Airways",
            "origin": origin,
            "destination": destination,
            "departure_time": "08:00",
            "arrival_time": "14:30",
            "price": 450,
            "duration": "6h 30m",
            "stops": 0
        },
        {
            "flight_id": "FL002", 
            "airline": "Global Wings",
            "origin": origin,
            "destination": destination,
            "departure_time": "15:15",
            "arrival_time": "21:45",
            "price": 380,
            "duration": "6h 30m",
            "stops": 1
        }
    ]
    
    result = {
        "search_criteria": {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "return_date": return_date
        },
        "flights_found": len(flights),
        "flights": flights,
        "best_price": min(f["price"] for f in flights),
        "recommendations": {
            "cheapest": flights[1],
            "fastest": flights[0]
        }
    }
    logging.info(f"Flight search completed: {origin} → {destination}")
    return result

async def search_hotels(location: str, checkin_date: str, checkout_date: str, guests: int = 2) -> Dict[str, Any]:
    """Search for hotels in a location."""
    hotels = [
        {
            "hotel_id": "HT001",
            "name": "Grand Plaza Hotel",
            "location": location,
            "rating": 4.5,
            "price_per_night": 180,
            "amenities": ["pool", "gym", "wifi", "restaurant"],
            "distance_to_center": "0.5 km",
            "room_type": "Deluxe Double"
        },
        {
            "hotel_id": "HT002",
            "name": "City Center Inn", 
            "location": location,
            "rating": 4.0,
            "price_per_night": 120,
            "amenities": ["wifi", "breakfast", "parking"],
            "distance_to_center": "1.2 km",
            "room_type": "Standard Double"
        },
        {
            "hotel_id": "HT003",
            "name": "Luxury Suites",
            "location": location,
            "rating": 5.0,
            "price_per_night": 280,
            "amenities": ["spa", "pool", "concierge", "wifi", "restaurant"],
            "distance_to_center": "0.3 km",
            "room_type": "Executive Suite"
        }
    ]
    
    result = {
        "search_criteria": {
            "location": location,
            "checkin_date": checkin_date,
            "checkout_date": checkout_date,
            "guests": guests
        },
        "hotels_found": len(hotels),
        "hotels": hotels,
        "price_range": {
            "min": min(h["price_per_night"] for h in hotels),
            "max": max(h["price_per_night"] for h in hotels)
        },
        "recommendations": {
            "best_value": hotels[1],
            "highest_rated": hotels[2],
            "budget_friendly": hotels[1]
        }
    }
    logging.info(f"Hotel search completed for {location}")
    return result

async def get_destination_weather(location: str, travel_date: str) -> Dict[str, Any]:
    """Get weather forecast for travel destination."""
    weather_data = {
        "location": location,
        "travel_date": travel_date,
        "temperature": {
            "high": 25,
            "low": 18,
            "unit": "celsius"
        },
        "condition": "partly cloudy",
        "precipitation_chance": 20,
        "humidity": 65,
        "wind_speed": 12,
        "forecast": {
            "today": "Partly cloudy with comfortable temperatures",
            "tomorrow": "Sunny with light winds",
            "week": "Generally pleasant with occasional light rain"
        },
        "recommendations": {
            "clothing": ["light layers", "comfortable walking shoes", "light jacket for evening"],
            "activities": ["outdoor sightseeing", "walking tours", "outdoor dining"]
        }
    }
    logging.info(f"Weather forecast retrieved for {location}")
    return weather_data

async def find_restaurants(location: str, cuisine_type: str = "local", budget: str = "medium") -> Dict[str, Any]:
    """Find restaurant recommendations for the destination."""
    restaurants = [
        {
            "restaurant_id": "RT001",
            "name": "Local Flavors Bistro",
            "cuisine": "local",
            "rating": 4.6,
            "price_range": "$$",
            "location": f"Downtown {location}",
            "specialties": ["local seafood", "regional wines", "seasonal menu"],
            "atmosphere": "casual fine dining",
            "reservation_recommended": True
        },
        {
            "restaurant_id": "RT002", 
            "name": "Street Food Market",
            "cuisine": "international",
            "rating": 4.3,
            "price_range": "$",
            "location": f"Central Market, {location}",
            "specialties": ["diverse food stalls", "authentic local dishes", "budget-friendly"],
            "atmosphere": "vibrant market",
            "reservation_recommended": False
        },
        {
            "restaurant_id": "RT003",
            "name": "Rooftop Fine Dining",
            "cuisine": "contemporary",
            "rating": 4.8,
            "price_range": "$$$",
            "location": f"Luxury District, {location}",
            "specialties": ["tasting menu", "wine pairing", "city views"],
            "atmosphere": "upscale romantic",
            "reservation_recommended": True
        }
    ]
    
    result = {
        "search_criteria": {
            "location": location,
            "cuisine_type": cuisine_type,
            "budget": budget
        },
        "restaurants_found": len(restaurants),
        "restaurants": restaurants,
        "recommendations": {
            "best_rated": restaurants[2],
            "best_value": restaurants[1],
            "most_authentic": restaurants[0]
        },
        "dining_tips": [
            f"Make reservations early for popular spots in {location}",
            "Try the local specialties for authentic experience",
            "Check opening hours as they may vary by season"
        ]
    }
    logging.info(f"Restaurant search completed for {location}")
    return result

# Configure LLM
llm_config = LLMConfig(
    provider=LLMProvider.OPENAI,
    model_name="gpt-4",
    api_key_env_var="OPENAI_API_KEY"
)

# Travel Coordinator - Central orchestrator
travel_coordinator = Agent(
    name="travel_coordinator",
    instructions="""You are a travel planning coordinator. You orchestrate multiple specialist agents to create comprehensive travel plans.

Your workflow:
1. Analyze the user's travel request
2. Determine which specialists are needed
3. Hand off to flight agent for transportation
4. Hand off to hotel agent for accommodation
5. Hand off to weather agent for destination conditions
6. Hand off to restaurant agent for dining recommendations
7. Consolidate all information into a comprehensive travel plan

You coordinate the entire travel planning process and return consolidated results to the user.
Always provide a complete travel plan with all necessary details.
""",
    llm_config=llm_config,
    handoff_config=HandoffConfig(
        mode=HandoffMode.COORDINATOR,
        targets=[
            HandoffTarget(
                agent_name="flight_agent",
                description="Search for flights and transportation options"
            ),
            HandoffTarget(
                agent_name="hotel_agent", 
                description="Search for hotels and accommodation"
            ),
            HandoffTarget(
                agent_name="weather_agent",
                description="Get weather forecast for destination"
            ),
            HandoffTarget(
                agent_name="restaurant_agent",
                description="Find dining and restaurant recommendations"
            )
        ]
    )
)

# Flight Agent - Transportation specialist
flight_agent = Agent(
    name="flight_agent",
    instructions="""You are a flight search specialist. You search for flights and provide transportation recommendations.
When you receive travel requests, extract the origin, destination, and dates, then search for the best flight options.
Provide detailed flight information including prices, schedules, and recommendations.
""",
    tools=[search_flights],
    llm_config=llm_config,
    handoff_config=HandoffConfig(
        mode=HandoffMode.COORDINATOR,  # Specialist in coordinator pattern
        targets=[]  # Specialists typically don't hand off to others
    )
)

# Hotel Agent - Accommodation specialist  
hotel_agent = Agent(
    name="hotel_agent",
    instructions="""You are a hotel search specialist. You find the best accommodation options for travelers.
When you receive requests, extract the location, dates, and guest count, then search for suitable hotels.
Provide detailed hotel information including amenities, prices, and location recommendations.
""",
    tools=[search_hotels],
    llm_config=llm_config,
    handoff_config=HandoffConfig(
        mode=HandoffMode.COORDINATOR,
        targets=[]
    )
)

# Weather Agent - Weather specialist
weather_agent = Agent(
    name="weather_agent",
    instructions="""You are a travel weather specialist. You provide weather forecasts and travel recommendations.
When you receive destination and travel date requests, provide detailed weather information and packing recommendations.
Include clothing suggestions and activity recommendations based on weather conditions.
""",
    tools=[get_destination_weather],
    llm_config=llm_config,
    handoff_config=HandoffConfig(
        mode=HandoffMode.COORDINATOR,
        targets=[]
    )
)

# Restaurant Agent - Dining specialist
restaurant_agent = Agent(
    name="restaurant_agent",
    instructions="""You are a restaurant and dining specialist. You find the best dining options for travelers.
When you receive location requests, provide restaurant recommendations with diverse options for different budgets and preferences.
Include local specialties and dining tips for the destination.
""",
    tools=[find_restaurants],
    llm_config=llm_config,
    handoff_config=HandoffConfig(
        mode=HandoffMode.COORDINATOR,
        targets=[]
    )
)

# Create the multi-agent function app with coordinator pattern
agent_app = AgentFunctionApp(
    agents=[travel_coordinator, flight_agent, hotel_agent, weather_agent, restaurant_agent]
)

# Manual function to demonstrate coordinator pattern
@app.route(route="travel-coordinator", methods=["POST"])
async def travel_coordinator_demo(req: func.HttpRequest) -> func.HttpResponse:
    """
    Demonstrate the coordinator pattern with centralized orchestration.
    The coordinator manages the entire workflow and consolidates results.
    """
    try:
        req_body = req.get_json()
        if not req_body:
            return func.HttpResponse(
                json.dumps({"error": "Request body is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Extract travel details
        origin = req_body.get("origin", "Seattle")
        destination = req_body.get("destination", "Tokyo")
        departure_date = req_body.get("departure_date", "2024-06-15")
        return_date = req_body.get("return_date", "2024-06-22")
        guests = req_body.get("guests", 2)
        
        logging.info(f"Coordinator demo: {origin} → {destination}, {departure_date} to {return_date}")
        
        # Get coordinator runner
        coordinator_runner = agent_app.runners["travel_coordinator"]
        
        conversation_id = f"travel-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Coordinator orchestrates all specialists
        travel_plan = {}
        
        # 1. Flight search
        logging.info("Coordinator handing off to flight agent")
        flight_response = await coordinator_runner.handoff_to(
            target_agent="flight_agent",
            input_data={
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date,
                "return_date": return_date
            },
            conversation_id=conversation_id,
            reason="Search for flights for travel plan"
        )
        travel_plan["flights"] = flight_response.content
        
        # 2. Hotel search
        logging.info("Coordinator handing off to hotel agent")
        hotel_response = await coordinator_runner.handoff_to(
            target_agent="hotel_agent",
            input_data={
                "location": destination,
                "checkin_date": departure_date,
                "checkout_date": return_date,
                "guests": guests
            },
            conversation_id=conversation_id,
            reason="Search for hotels for travel plan"
        )
        travel_plan["hotels"] = hotel_response.content
        
        # 3. Weather forecast
        logging.info("Coordinator handing off to weather agent")
        weather_response = await coordinator_runner.handoff_to(
            target_agent="weather_agent",
            input_data={
                "location": destination,
                "travel_date": departure_date
            },
            conversation_id=conversation_id,
            reason="Get weather forecast for travel destination"
        )
        travel_plan["weather"] = weather_response.content
        
        # 4. Restaurant recommendations
        logging.info("Coordinator handing off to restaurant agent")
        restaurant_response = await coordinator_runner.handoff_to(
            target_agent="restaurant_agent",
            input_data={
                "location": destination,
                "cuisine_type": "local",
                "budget": "medium"
            },
            conversation_id=conversation_id,
            reason="Find dining recommendations for travel destination"
        )
        travel_plan["restaurants"] = restaurant_response.content
        
        # Coordinator consolidates all results
        consolidated_plan = {
            "pattern": "coordinator",
            "travel_summary": {
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date,
                "return_date": return_date,
                "guests": guests,
                "duration": "7 days"
            },
            "coordinated_plan": travel_plan,
            "recommendations": {
                "recommended_flight": travel_plan["flights"].get("recommendations", {}).get("best_price"),
                "recommended_hotel": travel_plan["hotels"].get("recommendations", {}).get("best_value"),
                "weather_advice": travel_plan["weather"].get("recommendations", {}),
                "must_try_restaurant": travel_plan["restaurants"].get("recommendations", {}).get("most_authentic")
            },
            "estimated_total_cost": {
                "flight": travel_plan["flights"].get("best_price", 0) * 2,  # Round trip
                "hotel": travel_plan["hotels"].get("price_range", {}).get("min", 0) * 7,  # 7 nights
                "meals": 50 * 7 * guests,  # Estimated meal costs
                "total": "Calculated based on selections"
            },
            "handoff_path": ["travel_coordinator", "flight_agent", "hotel_agent", "weather_agent", "restaurant_agent"],
            "conversation_id": conversation_id,
            "coordinator_summary": f"Complete travel plan coordinated for {destination} trip"
        }
        
        return func.HttpResponse(
            json.dumps(consolidated_plan, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Error in travel coordinator demo: {str(e)}")
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
            "sample": "handoff-coordinator",
            "agents": ["travel_coordinator", "flight_agent", "hotel_agent", "weather_agent", "restaurant_agent"],
            "pattern": "coordinator - centralized orchestration"
        }),
        status_code=200,
        mimetype="application/json"
    )
