"""
Multi-Agent Travel Planning System using Azure Functions Agent Framework

This example demonstrates a collaborative multi-agent system with:
- Specialized agents for different travel planning tasks
- Agent-to-agent communication and workflow coordination
- Real Azure Functions endpoints
- Proper error handling and logging
"""

import logging
import os
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta

import azure.functions as func
from azure.functions import AuthLevel

from azurefunctions.agents import Agent, AgentFunctionApp
from azurefunctions.agents.types import LLMConfig, LLMProvider

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flight Search Agent Tools
def search_flights(origin: str, destination: str, date: str, passengers: int = 1) -> Dict[str, Any]:
    """
    Search for available flights between two locations.
    
    Args:
        origin: Departure city or airport code
        destination: Destination city or airport code  
        date: Travel date in YYYY-MM-DD format
        passengers: Number of passengers (default: 1)
    
    Returns:
        Dictionary containing flight search results
    """
    logger.info(f"Searching flights: {origin} -> {destination} on {date} for {passengers} passengers")
    
    # Mock flight data (in real implementation, this would call a flight API)
    flights = [
        {
            "flight_number": "AA123",
            "airline": "American Airlines",
            "departure_time": "08:00",
            "arrival_time": "11:30",
            "duration": "3h 30m",
            "price": 299,
            "stops": 0,
            "aircraft": "Boeing 737"
        },
        {
            "flight_number": "UA456", 
            "airline": "United Airlines",
            "departure_time": "14:15",
            "arrival_time": "17:45",
            "duration": "3h 30m", 
            "price": 315,
            "stops": 0,
            "aircraft": "Airbus A320"
        },
        {
            "flight_number": "DL789",
            "airline": "Delta Air Lines", 
            "departure_time": "19:20",
            "arrival_time": "22:50", 
            "duration": "3h 30m",
            "price": 289,
            "stops": 0,
            "aircraft": "Boeing 737"
        }
    ]
    
    return {
        "origin": origin,
        "destination": destination,
        "date": date,
        "passengers": passengers,
        "flights_found": len(flights),
        "flights": flights,
        "search_timestamp": datetime.now().isoformat(),
        "summary": f"Found {len(flights)} flights from {origin} to {destination} on {date}"
    }

def compare_flight_prices(flights_data: str) -> Dict[str, Any]:
    """
    Analyze and compare flight prices to find the best deals.
    
    Args:
        flights_data: JSON string containing flight search results
        
    Returns:
        Dictionary with price comparison analysis
    """
    try:
        if isinstance(flights_data, str):
            data = json.loads(flights_data)
        else:
            data = flights_data
            
        flights = data.get("flights", [])
        
        if not flights:
            return {"error": "No flights data provided for comparison"}
        
        # Sort flights by price
        flights_by_price = sorted(flights, key=lambda x: x["price"])
        cheapest = flights_by_price[0]
        most_expensive = flights_by_price[-1]
        
        # Calculate average price
        avg_price = sum(f["price"] for f in flights) / len(flights)
        
        return {
            "total_flights_analyzed": len(flights),
            "cheapest_flight": {
                "flight_number": cheapest["flight_number"],
                "airline": cheapest["airline"],
                "price": cheapest["price"],
                "departure_time": cheapest["departure_time"]
            },
            "most_expensive_flight": {
                "flight_number": most_expensive["flight_number"],
                "airline": most_expensive["airline"], 
                "price": most_expensive["price"],
                "departure_time": most_expensive["departure_time"]
            },
            "average_price": round(avg_price, 2),
            "price_range": most_expensive["price"] - cheapest["price"],
            "recommendation": f"Best value: {cheapest['flight_number']} at ${cheapest['price']}",
            "analysis_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error comparing flight prices: {str(e)}")
        return {"error": f"Failed to compare prices: {str(e)}"}

# Hotel Search Agent Tools  
def search_hotels(location: str, checkin_date: str, checkout_date: str, guests: int = 2) -> Dict[str, Any]:
    """
    Search for hotels in a specific location.
    
    Args:
        location: City or area to search for hotels
        checkin_date: Check-in date in YYYY-MM-DD format
        checkout_date: Check-out date in YYYY-MM-DD format
        guests: Number of guests (default: 2)
        
    Returns:
        Dictionary containing hotel search results
    """
    logger.info(f"Searching hotels in {location} for {guests} guests ({checkin_date} to {checkout_date})")
    
    # Mock hotel data
    hotels = [
        {
            "hotel_name": "Grand Plaza Hotel",
            "rating": 4.5,
            "price_per_night": 180,
            "location": "Downtown",
            "amenities": ["WiFi", "Pool", "Gym", "Restaurant"],
            "distance_to_center": "0.5 miles"
        },
        {
            "hotel_name": "Budget Inn & Suites",
            "rating": 3.8,
            "price_per_night": 89,
            "location": "Airport Area", 
            "amenities": ["WiFi", "Parking", "Continental Breakfast"],
            "distance_to_center": "12 miles"
        },
        {
            "hotel_name": "Luxury Resort & Spa",
            "rating": 4.9,
            "price_per_night": 350,
            "location": "Beachfront",
            "amenities": ["WiFi", "Pool", "Spa", "Beach Access", "Fine Dining"],
            "distance_to_center": "8 miles"
        }
    ]
    
    # Calculate total stay cost
    checkin = datetime.strptime(checkin_date, "%Y-%m-%d")
    checkout = datetime.strptime(checkout_date, "%Y-%m-%d")
    nights = (checkout - checkin).days
    
    for hotel in hotels:
        hotel["total_cost"] = hotel["price_per_night"] * nights
        hotel["nights"] = nights
    
    return {
        "location": location,
        "checkin_date": checkin_date,
        "checkout_date": checkout_date,
        "nights": nights,
        "guests": guests,
        "hotels_found": len(hotels),
        "hotels": hotels,
        "search_timestamp": datetime.now().isoformat()
    }

def calculate_trip_budget(flights_data: str, hotels_data: str, daily_budget: float = 100.0) -> Dict[str, Any]:
    """
    Calculate total trip budget including flights, accommodation, and daily expenses.
    
    Args:
        flights_data: JSON string with selected flight information
        hotels_data: JSON string with selected hotel information
        daily_budget: Estimated daily spending budget (default: $100)
        
    Returns:
        Dictionary with comprehensive budget breakdown
    """
    try:
        # Parse flight data
        if isinstance(flights_data, str):
            flight_info = json.loads(flights_data)
        else:
            flight_info = flights_data
            
        # Parse hotel data  
        if isinstance(hotels_data, str):
            hotel_info = json.loads(hotels_data)
        else:
            hotel_info = hotels_data
        
        # Extract costs
        flight_cost = flight_info.get("price", 0) if "price" in flight_info else 0
        hotel_total = hotel_info.get("total_cost", 0) if "total_cost" in hotel_info else 0
        nights = hotel_info.get("nights", 1) if "nights" in hotel_info else 1
        
        daily_expenses = daily_budget * nights
        
        # Calculate totals
        subtotal = flight_cost + hotel_total + daily_expenses
        tax_rate = 0.08  # 8% estimated tax
        taxes = subtotal * tax_rate
        total_cost = subtotal + taxes
        
        return {
            "budget_breakdown": {
                "flights": flight_cost,
                "accommodation": hotel_total,
                "daily_expenses": daily_expenses,
                "subtotal": round(subtotal, 2),
                "taxes_and_fees": round(taxes, 2),
                "total_cost": round(total_cost, 2)
            },
            "trip_details": {
                "nights": nights,
                "daily_budget": daily_budget
            },
            "budget_tips": [
                "Book flights and hotels in advance for better rates",
                "Consider traveling on weekdays for lower costs",
                "Look for package deals combining flights and hotels",
                "Set aside 10-15% extra for unexpected expenses"
            ],
            "calculation_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error calculating trip budget: {str(e)}")
        return {"error": f"Failed to calculate budget: {str(e)}"}

# Agent System Instructions
FLIGHT_AGENT_INSTRUCTIONS = """
You are a specialized Flight Search Agent that helps users find and compare flights.

Capabilities:
- Search for flights between any two locations
- Compare prices and find best deals
- Provide flight recommendations based on user preferences
- Handle complex itineraries and multi-city trips

Always use the search_flights and compare_flight_prices tools when users ask about flights.
Be helpful in explaining flight options, pricing, and timing considerations.
"""

HOTEL_AGENT_INSTRUCTIONS = """
You are a Hotel Search Agent specializing in accommodation booking and recommendations.

Capabilities:
- Search for hotels in any location
- Compare hotel amenities, ratings, and prices
- Provide accommodation recommendations based on budget and preferences
- Calculate total stay costs

Use the search_hotels tool when users need accommodation options.
Consider factors like location, amenities, and budget when making recommendations.
"""

BUDGET_AGENT_INSTRUCTIONS = """
You are a Travel Budget Agent that helps users plan and manage trip expenses.

Capabilities:
- Calculate comprehensive trip budgets
- Provide cost breakdowns for flights, hotels, and daily expenses
- Offer money-saving tips and budget optimization advice
- Handle currency conversions and tax calculations

Use the calculate_trip_budget tool to provide detailed budget analysis.
Always include practical advice for saving money and staying within budget.
"""

# Configure LLM
llm_config = LLMConfig(
    provider=LLMProvider.OPENAI,
    model_name=os.getenv("LLM_MODEL_NAME", "gpt-4o-mini"),
    temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
    max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1500")),
)

# Create specialized agents
flight_agent = Agent(
    name="FlightAgent",
    instructions=FLIGHT_AGENT_INSTRUCTIONS,
    tools=[search_flights, compare_flight_prices],
    llm_config=llm_config,
    enable_conversational_agent=True,
    description="Specialized agent for flight search and booking assistance"
)

hotel_agent = Agent(
    name="HotelAgent", 
    instructions=HOTEL_AGENT_INSTRUCTIONS,
    tools=[search_hotels],
    llm_config=llm_config,
    enable_conversational_agent=True,
    description="Specialized agent for hotel search and accommodation recommendations"
)

budget_agent = Agent(
    name="BudgetAgent",
    instructions=BUDGET_AGENT_INSTRUCTIONS,
    tools=[calculate_trip_budget],
    llm_config=llm_config,
    enable_conversational_agent=True,
    description="Specialized agent for travel budget planning and cost analysis"
)

# Create multi-agent Function App
app = AgentFunctionApp(agents={
    "FlightAgent": flight_agent,
    "HotelAgent": hotel_agent, 
    "BudgetAgent": budget_agent
})

# Health check endpoint
@app.route(route="health", auth_level=AuthLevel.ANONYMOUS, methods=["GET"])
async def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint for the multi-agent travel system."""
    
    health_info = {
        "status": "healthy",
        "system_name": "Multi-Agent Travel Planner",
        "version": "2.0.0",
        "agents": [
            {
                "name": "FlightAgent",
                "description": "Flight search and price comparison",
                "status": "active"
            },
            {
                "name": "HotelAgent", 
                "description": "Hotel search and accommodation recommendations",
                "status": "active"
            },
            {
                "name": "BudgetAgent",
                "description": "Travel budget planning and cost analysis", 
                "status": "active"
            }
        ],
        "llm_provider": llm_config.provider.value,
        "llm_model": llm_config.model_name,
        "features": [
            "Multi-agent collaboration",
            "Flight search and comparison",
            "Hotel recommendations", 
            "Budget planning and optimization",
            "Real-time cost calculations"
        ],
        "timestamp": datetime.now().isoformat(),
    }
    
    return func.HttpResponse(
        json.dumps(health_info, indent=2),
        status_code=200,
        headers={"Content-Type": "application/json"},
    )

# Agent coordination endpoint (optional - for demonstrating agent collaboration)
@app.route(route="plan-trip", auth_level=AuthLevel.ANONYMOUS, methods=["POST"])
async def plan_trip(req: func.HttpRequest) -> func.HttpResponse:
    """
    Coordinate multiple agents to create a complete travel plan.
    This demonstrates how agents can work together on complex tasks.
    """
    try:
        req_body = req.get_json()
        
        origin = req_body.get("origin")
        destination = req_body.get("destination") 
        travel_date = req_body.get("travel_date")
        return_date = req_body.get("return_date")
        budget = req_body.get("budget", 1000)
        
        if not all([origin, destination, travel_date]):
            return func.HttpResponse(
                json.dumps({"error": "Missing required parameters: origin, destination, travel_date"}),
                status_code=400,
                headers={"Content-Type": "application/json"}
            )
        
        # This would coordinate between agents in a full implementation
        trip_plan = {
            "trip_summary": {
                "origin": origin,
                "destination": destination,
                "travel_date": travel_date,
                "return_date": return_date,
                "budget": budget
            },
            "status": "plan_created",
            "message": "Trip plan created successfully. Use individual agent endpoints for detailed planning.",
            "next_steps": [
                f"Use /api/FlightAgent/chat to search for flights from {origin} to {destination}",
                f"Use /api/HotelAgent/chat to find accommodation in {destination}",
                "Use /api/BudgetAgent/chat to calculate total trip costs"
            ],
            "timestamp": datetime.now().isoformat()
        }
        
        return func.HttpResponse(
            json.dumps(trip_plan, indent=2),
            status_code=200,
            headers={"Content-Type": "application/json"}
        )
        
    except Exception as e:
        logger.error(f"Error planning trip: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Failed to plan trip: {str(e)}"}),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )
