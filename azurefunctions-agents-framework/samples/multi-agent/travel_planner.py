#!/usr/bin/env python3
"""
Example: Clean Multi-Agent Architecture (Version 2)
Shows the simplified endpoint structure with no legacy endpoints.

Multi-agent endpoints:
- POST /api/agents/{name}/chat - Chat with specific agent
- GET /api/agents - List all agents
- POST /api/workflows - Create workflow (future)
- GET /api/workflows - List workflows (future)
- GET /api/workflow/{id} - Get workflow status (future)

This removes all the legacy /actions endpoints and provides a clean,
RESTful API structure.
"""

import json
import asyncio
from typing import Dict, Any, List

from azurefunctions.agents import Agent, AgentFunctionApp
from azurefunctions.agents.types import LLMConfig, LLMProvider


# Flight Search Agent Tools
def search_flights(origin: str, destination: str, date: str) -> str:
    """Search for available flights."""
    return f"Found 3 flights from {origin} to {destination} on {date}: Flight AA123 ($299), Flight UA456 ($315), Flight DL789 ($289)"


def compare_prices(flights_data: str) -> str:
    """Compare flight prices and find best deals."""
    return "Best value: DL789 ($289), Premium option: AA123 ($299), Most availability: UA456 ($315)"


# Extraction Agent Tool
def extract_flight_info(search_results: str) -> str:
    """Extract key information from flight search results."""
    return "Extracted: 3 flights available, price range $289-$315, carriers: AA, UA, DL"


# Seat Selection Agent Tool  
def find_available_seats(flight_number: str, preferences: str = "window") -> str:
    """Find available seats on a flight."""
    return f"Available window seats on {flight_number}: 12A, 15F, 23A (all $25 extra)"


# Booking Agent Tool
def book_flight(flight_number: str, seat: str, passenger: str) -> str:
    """Book a flight with specific seat."""
    return f"✅ Booked {flight_number}, seat {seat} for {passenger}. Confirmation: ABC123"


async def main():
    print("=== Testing Clean Multi-Agent Architecture V2 ===\n")

    # Create LLM config (mock for demo)
    llm_config = LLMConfig(
        provider=LLMProvider.OPENAI,
        model_name="gpt-4",
        api_key="mock-key-for-demo"
    )

    # Create specialized agents
    search_agent = Agent(
        name="search",
        instructions="You specialize in finding flights. Search comprehensively and provide detailed results.",
        tools=[search_flights, compare_prices],
        llm_config=llm_config,
        description="Flight search specialist"
    )

    extraction_agent = Agent(
        name="extraction",
        instructions="You extract and summarize key information from search results. Be concise and highlight important details.",
        tools=[extract_flight_info],
        llm_config=llm_config,
        description="Information extraction specialist"
    )

    seats_agent = Agent(
        name="seats",
        instructions="You help find and recommend seats based on passenger preferences.",
        tools=[find_available_seats],
        llm_config=llm_config,
        description="Seat selection specialist"
    )

    booking_agent = Agent(
        name="booking",
        instructions="You handle final booking confirmations. Be accurate and provide clear confirmation details.",
        tools=[book_flight],
        llm_config=llm_config,
        description="Flight booking specialist"
    )

    # Create Function App with multiple agents
    agents_dict = {
        "search": search_agent,
        "extraction": extraction_agent,
        "seats": seats_agent,
        "booking": booking_agent
    }
    app = AgentFunctionApp(agents=agents_dict)

    print("1. Testing individual agents:")
    search_result = search_flights("Seattle", "New York", "2025-07-01")
    print(f"Search Agent: {search_result}")
    
    extraction_result = extract_flight_info(search_result)
    print(f"Extraction: {extraction_result}")
    
    seats_result = find_available_seats("AA123", "window")
    print(f"Seat Agent: {seats_result}")
    
    booking_result = book_flight("AA123", "12A", "John Doe")
    print(f"Booking Agent: {booking_result}")
    print()

    print("2. Testing agent info:")
    agents_info = []
    for agent_name, agent in app.agents.items():
        info = await agent.get_agent_info()
        agents_info.append(info)
        print(f"Agent '{agent_name}': {info['description']}, Tools: {len(info['tools'])}")
    print()

    print("3. Simulating workflow (matching your mermaid diagram):")
    
    # Simulate the complex workflow
    workflow_steps = [
        ("START", "search_agent", "Search flights"),
        ("search_agent", "extraction_agent", "Extract info"),
        ("human_confirm", "find_seat_agent", "User confirms, find seats"),
        ("human_seat_choice", "booking_agent", "User picks seat 12A"),
        ("", "SUCCESS", "")
    ]

    for i, (from_step, to_step, description) in enumerate(workflow_steps):
        if from_step == "START":
            result = search_flights("Seattle", "New York", "2025-07-01")
            print(f"START → search_agent: {description}")
            print(f"  Result: {result}")
        elif from_step == "search_agent":
            result = extract_flight_info(search_result)
            print(f"search_agent → extraction_agent: {description}")
            print(f"  Result: {result}")
        elif from_step == "human_confirm":
            result = find_available_seats("AA123", "window")
            print(f"human_confirm → find_seat_agent: {description}")
            print(f"  Result: {result}")
        elif from_step == "human_seat_choice":
            result = book_flight("AA123", "12A", "John Doe")
            print(f"human_seat_choice → booking_agent: {description}")
            print(f"  Result: {result}")
        elif to_step == "SUCCESS":
            print(f"→ SUCCESS")

    print()
    print("✅ Clean multi-agent setup completed!")
    print()
    print("🎉 NEW CLEAN ENDPOINTS:")
    print("- POST /api/agents/{name}/chat - Chat with specific agent")
    print("- GET /api/agents - List all agents")
    print("- POST /api/workflows - Create workflow (future)")
    print("- GET /api/workflows - List workflows (future)")
    print("- GET /api/workflow/{id} - Get workflow status (future)")
    print()
    print("🔥 Benefits:")
    print("- No legacy /actions endpoints")
    print("- Clean, RESTful API design")
    print("- Clear agent identification")
    print("- Extensible for workflow engines")
    print("- Consistent patterns across single/multi-agent")

    # Simulate a complete workflow
    print("\n=== Simulating Complex Flight Booking Workflow ===\n")
    
    steps = [
        ("1. START → search_agent", lambda: search_flights("Seattle", "New York", "2025-07-01")),
        ("2. search_agent → extraction_agent", lambda: extract_flight_info("flight search results")),
        ("3. extraction_agent → human_confirm", lambda: "yes"),
        ("4. human_confirm → find_seat_agent", lambda: find_available_seats("AA123", "window")),
        ("5. find_seat_agent → human_seat_choice", lambda: "12A"),
        ("6. human_seat_choice → booking_agent", lambda: book_flight("AA123", "12A", "John Doe")),
        ("7. booking_agent → SUCCESS", lambda: "✅ Flight booking workflow completed successfully!")
    ]
    
    for step_desc, step_func in steps:
        result = step_func()
        if "human" in step_desc:
            print(f"{step_desc}")
            print(f"   Human {'confirms' if 'confirm' in step_desc else 'chooses seat'}: {result}")
        else:
            print(f"{step_desc}")
            if "→ SUCCESS" not in step_desc:
                if callable(step_func):
                    result = step_func()
                print(f"   {'Search results' if 'search_agent' in step_desc else 'Extracted' if 'extraction' in step_desc else 'Available seats' if 'seat_agent' in step_desc else 'Booking result'}: {result}")
            else:
                print(f"   {result}")
        print()


if __name__ == "__main__":
    asyncio.run(main())
