# Travel Coordinator - Coordinator Pattern

This sample demonstrates the **COORDINATOR handoff pattern** where one central agent orchestrates multiple specialist agents and returns a consolidated response. The coordinator manages the entire workflow and combines results from all specialists.

## Architecture

```text
                    ┌─────────────────┐
                    │ Travel Request  │
                    │     (User)      │
                    └─────────┬───────┘
                              │
                    ┌─────────▼───────┐
                    │     Travel      │
                    │   Coordinator   │◄─── Central Orchestrator
                    │   (Manager)     │
                    └─────┬───┬───┬───┘
                          │   │   │
            ┌─────────────┘   │   └─────────────┐
            │                 │                 │
    ┌───────▼───────┐ ┌───────▼───────┐ ┌───────▼───────┐
    │ Flight Agent  │ │ Hotel Agent   │ │ Weather Agent │
    │               │ │               │ │               │
    │ • Search      │ │ • Find hotels │ │ • Get weather │
    │   flights     │ │ • Compare     │ │ • Forecast    │
    │ • Compare     │ │   amenities   │ │ • Clothing    │
    │   prices      │ │ • Location    │ │   advice      │
    └───────────────┘ └───────────────┘ └───────────────┘
                              │
                    ┌─────────▼───────┐
                    │ Restaurant Agent│
                    │                 │
                    │ • Find dining   │
                    │ • Local cuisine │
                    │ • Reservations  │
                    └─────────────────┘
```

## Agents

### Travel Coordinator (Manager)

- **Role**: Central orchestrator and workflow manager
- **Capabilities**: Analyzes requests, coordinates specialists, consolidates results
- **Pattern**: Manages handoffs to all specialists and returns unified travel plan

### Flight Agent (Specialist)

- **Role**: Transportation search specialist
- **Capabilities**: Searches flights, compares prices, provides recommendations
- **Focus**: Flight schedules, pricing, airline options

### Hotel Agent (Specialist)

- **Role**: Accommodation search specialist
- **Capabilities**: Finds hotels, compares amenities, location analysis
- **Focus**: Hotel ratings, pricing, location convenience

### Weather Agent (Specialist)

- **Role**: Weather forecast and travel advice specialist
- **Capabilities**: Weather forecasts, packing recommendations, activity suggestions
- **Focus**: Weather conditions, seasonal advice, clothing recommendations

### Restaurant Agent (Specialist)

- **Role**: Dining and cuisine specialist
- **Capabilities**: Restaurant recommendations, local cuisine, dining experiences
- **Focus**: Food options, local specialties, restaurant reservations

## Key Features

### Centralized Orchestration

- Single coordinator manages entire workflow
- Specialists focus on their expertise
- Consolidated response with all travel components
- Coordinated execution with dependency management

### Comprehensive Travel Planning

- Flight search and comparison
- Hotel accommodation options
- Weather-based recommendations
- Restaurant and dining guide
- Complete cost estimation

### Intelligent Coordination

- Parallel processing of independent tasks
- Sequential processing for dependent tasks
- Context sharing between specialists
- Quality assurance and validation

## API Endpoints

### Standard Agent Endpoints

```bash
# Chat with travel coordinator (main orchestrator)
POST /api/agents/travel_coordinator/chat

# Chat with individual specialists
POST /api/agents/flight_agent/chat
POST /api/agents/hotel_agent/chat  
POST /api/agents/weather_agent/chat
POST /api/agents/restaurant_agent/chat

# List all agents
GET /api/agents

# Get agent information
GET /api/agents/{agent_name}/info
```

### Demo Endpoint

```bash
# Demonstrates coordinator pattern with centralized orchestration
POST /api/travel-coordinator

# Health check
GET /api/health
```

## Quick Start

### 1. Setup

```bash
# Copy and configure settings
cp local.settings.json.template local.settings.json

# Add your OpenAI API key to local.settings.json:
{
  "Values": {
    "OPENAI_API_KEY": "your-openai-api-key-here"
  }
}
```

### 2. Install and Run

```bash
pip install -r requirements.txt
func start
```

### 3. Test the Coordinator

#### Complete Travel Planning Example

```bash
curl -X POST http://localhost:7071/api/agents/travel_coordinator/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Plan a complete trip from Seattle to Tokyo for 2 people, departing June 15 and returning June 22"
  }'
```

#### Individual Specialist Queries

```bash
# Flight search only
curl -X POST http://localhost:7071/api/agents/flight_agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find flights from Seattle to Tokyo on June 15"
  }'

# Hotel search only
curl -X POST http://localhost:7071/api/agents/hotel_agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find hotels in Tokyo for June 15-22, 2 guests"
  }'
```

#### Coordinator Demo (Direct Orchestration)

```bash
curl -X POST http://localhost:7071/api/travel-coordinator \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "Seattle",
    "destination": "Tokyo", 
    "departure_date": "2024-06-15",
    "return_date": "2024-06-22",
    "guests": 2
  }'
```

## Example Conversations

### Complete Travel Planning

```json
{
  "message": "Plan a 7-day trip to Barcelona for 2 people with flights from New York"
}
```

**Coordinator Flow:**

1. Analyzes travel requirements
2. Hands off to flight agent for NYC → Barcelona flights
3. Hands off to hotel agent for Barcelona accommodations
4. Hands off to weather agent for Barcelona weather forecast
5. Hands off to restaurant agent for dining recommendations
6. Consolidates all responses into comprehensive travel plan

### Specialist Focus

```json
{
  "message": "I need the best flight deals to London next month"
}
```

**Direct to Flight Agent:** Specialized flight search with detailed options and recommendations.

## Expected Response Format

```json
{
  "pattern": "coordinator",
  "travel_summary": {
    "origin": "Seattle",
    "destination": "Tokyo",
    "departure_date": "2024-06-15", 
    "return_date": "2024-06-22",
    "guests": 2,
    "duration": "7 days"
  },
  "coordinated_plan": {
    "flights": {
      "flights_found": 2,
      "best_price": 380,
      "recommendations": {
        "cheapest": "Global Wings FL002",
        "fastest": "SkyLine Airways FL001"
      }
    },
    "hotels": {
      "hotels_found": 3,
      "price_range": {"min": 120, "max": 280},
      "recommendations": {
        "best_value": "City Center Inn",
        "highest_rated": "Luxury Suites"
      }
    },
    "weather": {
      "condition": "partly cloudy",
      "temperature": {"high": 25, "low": 18},
      "recommendations": {
        "clothing": ["light layers", "comfortable shoes"],
        "activities": ["outdoor sightseeing", "walking tours"]
      }
    },
    "restaurants": {
      "restaurants_found": 3,
      "recommendations": {
        "most_authentic": "Local Flavors Bistro",
        "best_value": "Street Food Market"
      }
    }
  },
  "estimated_total_cost": {
    "flight": 760,
    "hotel": 840,
    "meals": 700,
    "total": "Calculated based on selections"
  },
  "handoff_path": ["travel_coordinator", "flight_agent", "hotel_agent", "weather_agent", "restaurant_agent"],
  "coordinator_summary": "Complete travel plan coordinated for Tokyo trip"
}
```

## Key Benefits

### Centralized Management

- Single point of control for complex workflows
- Consistent quality assurance across all components
- Coordinated execution with proper sequencing
- Unified response format

### Specialist Expertise

- Each agent focuses on their domain expertise
- Deep knowledge in specific travel aspects
- Optimized tools and data sources per specialty
- Quality recommendations from domain experts

### Scalability

- Easy to add new specialist agents
- Coordinator handles complexity of orchestration
- Specialists can be independently optimized
- Clear separation of concerns

## Customization

### Adding New Specialists

```python
# Add a new activity planning specialist
activity_agent = Agent(
    name="activity_agent",
    instructions="You specialize in finding activities and attractions",
    tools=[search_activities],
    handoff_config=HandoffConfig(
        mode=HandoffMode.COORDINATOR,
        targets=[]  # Specialists don't hand off to others
    )
)

# Update coordinator to include new specialist
coordinator.handoff_config.targets.append(
    HandoffTarget(
        agent_name="activity_agent",
        description="Find activities and attractions for travelers"
    )
)
```

### Custom Workflow Logic

```python
# Coordinator with conditional handoffs
async def custom_travel_workflow(coordinator_runner, travel_request):
    """Custom travel planning workflow with conditional logic."""
    
    # Always get flights first
    flights = await coordinator_runner.handoff_to("flight_agent", flight_data)
    
    # Only search hotels if flights are available
    if flights.success and flights.content.get("flights_found", 0) > 0:
        hotels = await coordinator_runner.handoff_to("hotel_agent", hotel_data)
    
    # Weather is optional for domestic trips
    if travel_request.get("international", True):
        weather = await coordinator_runner.handoff_to("weather_agent", weather_data)
    
    return consolidate_results(flights, hotels, weather)
```

### Business Logic Integration

```python
# Add business rules to coordinator
def calculate_travel_budget(flights, hotels, duration, guests):
    """Calculate total travel budget with business logic."""
    flight_cost = flights.get("best_price", 0) * guests * 2  # Round trip
    hotel_cost = hotels.get("recommended_price", 0) * duration
    meal_budget = 75 * duration * guests  # Per person per day
    activities = 50 * duration * guests
    
    return {
        "flights": flight_cost,
        "accommodation": hotel_cost, 
        "meals": meal_budget,
        "activities": activities,
        "total": flight_cost + hotel_cost + meal_budget + activities,
        "per_person": (flight_cost + hotel_cost + meal_budget + activities) / guests
    }
```

## Production Deployment

This sample is production-ready and can be deployed to Azure Functions:

```bash
# Deploy to Azure
func azure functionapp publish YourTravelPlannerApp
```

The coordinator pattern is ideal for:

- **Complex workflows** requiring multiple specialized capabilities
- **Consistent quality** across all components of a process
- **Centralized business logic** and decision making
- **Consolidated reporting** and response formatting
- **Enterprise applications** with multiple service integrations

## Advanced Features

### Parallel Processing

```python
# Execute independent specialists in parallel
async def parallel_coordination():
    tasks = [
        coordinator_runner.handoff_to("flight_agent", flight_data),
        coordinator_runner.handoff_to("hotel_agent", hotel_data),
        coordinator_runner.handoff_to("weather_agent", weather_data)
    ]
    results = await asyncio.gather(*tasks)
    return consolidate_parallel_results(results)
```

### Error Handling and Fallbacks

```python
# Robust error handling in coordinator
async def robust_coordination():
    try:
        flights = await coordinator_runner.handoff_to("flight_agent", data)
    except Exception as e:
        flights = get_fallback_flight_data()
        logging.warning(f"Flight search failed, using fallback: {e}")
    
    # Continue with other specialists even if one fails
    return create_partial_plan(flights, hotels, weather)
```

### Dynamic Specialist Selection

```python
# Coordinator chooses specialists based on request
def select_specialists(travel_request):
    """Dynamically select which specialists to use."""
    specialists = ["flight_agent"]  # Always need flights
    
    if travel_request.get("need_accommodation"):
        specialists.append("hotel_agent")
    
    if travel_request.get("international") or travel_request.get("check_weather"):
        specialists.append("weather_agent")
        
    if travel_request.get("food_preferences"):
        specialists.append("restaurant_agent")
        
    return specialists
```

## Troubleshooting

### Common Issues

1. **Specialist failures**: Coordinator handles partial failures gracefully
2. **Slow responses**: Use parallel processing for independent tasks
3. **Data consistency**: Coordinator validates data between specialists
4. **Cost calculation**: Business logic centralized in coordinator

### Performance Optimization

- Use async/await for parallel specialist execution
- Cache specialist responses for similar requests
- Implement request batching for high-volume scenarios
- Add circuit breakers for unreliable external services

## Next Steps

- Try the [Swarm Pattern Sample](../handoff-swarm/) for peer-to-peer collaboration
- Explore [Conditional Handoffs](../handoff-conditional/) for dynamic routing
- Build your own coordinator with domain-specific specialists
- Integrate with real travel APIs and external services

## Auto-Registration of Handoff Tools

This sample demonstrates the **automatic handoff tool registration** feature of the Azure Functions Agent Framework. The framework automatically registers handoff tools for agents based on their `HandoffConfig`, eliminating the need to manually write wrapper functions.

### How It Works

When an agent is created with a `HandoffConfig`, the framework automatically:

1. **Auto-registers handoff tools** for each target agent specified in the configuration
2. **Exposes tools to the LLM** with descriptive names like `handoff_to_flight_agent`
3. **Handles tool execution** by delegating to the target agent's chat endpoint
4. **Updates tools dynamically** when the handoff configuration changes

### Before: Manual Wrapper Functions ❌

```python
# OLD WAY: Manual wrapper functions (no longer needed)
async def call_flight_agent(origin: str, destination: str, departure_date: str) -> Dict[str, Any]:
    """Manual wrapper function - NOT NEEDED ANYMORE"""
    # Complex manual implementation...
    pass

travel_coordinator = Agent(
    name="travel_coordinator",
    tools=[call_flight_agent, call_hotel_agent, ...],  # Manual tools
    handoff_config=HandoffConfig(...)
)
```

### After: Automatic Registration ✅

```python
# NEW WAY: Automatic handoff tool registration
travel_coordinator = Agent(
    name="travel_coordinator",
    instructions="Use handoff_to_flight_agent to search flights...",
    tools=[],  # No manual tools needed!
    handoff_config=HandoffConfig(
        mode=HandoffMode.COORDINATOR,
        targets=[
            HandoffTarget(
                agent_name="flight_agent",
                description="Search for flights and transportation options"
            ),
            # Framework automatically creates: handoff_to_flight_agent(message: str)
        ]
    )
)
```

### Automatic Tool Names

The framework automatically creates tools with predictable names:

- `HandoffTarget(agent_name="flight_agent")` → `handoff_to_flight_agent(message: str)`
- `HandoffTarget(agent_name="hotel_agent")` → `handoff_to_hotel_agent(message: str)`
- `HandoffTarget(agent_name="weather_agent")` → `handoff_to_weather_agent(message: str)`

### Benefits

- **🚀 Faster Development**: No need to write manual wrapper functions
- **🔧 Less Boilerplate**: Framework handles tool creation automatically
- **🎯 Consistent API**: Predictable tool names and signatures
- **🔄 Dynamic Updates**: Tools update when handoff config changes
- **📖 Better Documentation**: Tool descriptions come from HandoffTarget descriptions
