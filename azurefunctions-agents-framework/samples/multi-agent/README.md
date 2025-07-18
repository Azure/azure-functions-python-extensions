# Multi-Agent Travel Planner Sample

A comprehensive Azure Functions application demonstrating multi-agent collaboration using the Azure Functions Agent Framework.

## Features

- **Specialized Agents**: Flight search, hotel booking, and budget planning agents
- **Agent Collaboration**: Coordinated workflows between multiple agents
- **Real-time Data**: Mock travel data with realistic pricing and availability
- **Budget Analysis**: Comprehensive cost breakdowns and money-saving tips
- **RESTful API**: Clean endpoints for each agent and coordination

## Architecture

```text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  FlightAgent    │    │   HotelAgent    │    │  BudgetAgent    │
│                 │    │                 │    │                 │
│ - Search Flights│    │ - Search Hotels │    │ - Calculate Costs│
│ - Compare Prices│    │ - Rate Analysis │    │ - Budget Tips    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                           ┌─────────────────┐
                           │  Coordination   │
                           │   Endpoint      │
                           └─────────────────┘
```

## Quick Start

### Prerequisites

1. **Azure Functions Core Tools**:

   ```bash
   npm install -g azure-functions-core-tools@4
   ```

2. **Python 3.9+** with pip

### Setup

1. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:

```bash
   cp local.settings.json.template local.settings.json
   ```

   Edit `local.settings.json` and add your OpenAI API key:

```json
   {
     "Values": {
       "OPENAI_API_KEY": "your-openai-api-key"
     }
   }
   ```

3. **Run Locally**:

   ```bash
func start
   ```

## Usage

### Individual Agent Endpoints

**Flight Search Agent:**

```bash
curl -X POST http://localhost:7071/api/FlightAgent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find flights from Seattle to Tokyo for March 15th"
  }'
```

**Hotel Search Agent:**

```bash
curl -X POST http://localhost:7071/api/HotelAgent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Find hotels in Tokyo for 3 nights starting March 15th"
  }'
```

**Budget Planning Agent:**

```bash
curl -X POST http://localhost:7071/api/BudgetAgent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Calculate budget for a Tokyo trip with $300 flight and $180/night hotel for 3 nights"
  }'
```

### Coordination Endpoint

**Plan Complete Trip:**

```bash
curl -X POST http://localhost:7071/api/plan-trip \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "Seattle",
    "destination": "Tokyo",
    "travel_date": "2024-03-15",
    "return_date": "2024-03-18",
    "budget": 2000
  }'
```

### System Health

```bash
curl http://localhost:7071/api/health
```

## Available Agents

### 1. FlightAgent

**Tools:**
- `search_flights(origin, destination, date, passengers)`: Find available flights
- `compare_flight_prices(flights_data)`: Analyze and compare flight prices

**Sample Interaction:**

```text
User: "I need a flight from New York to London on April 10th"
Agent: *Searches flights, compares prices, recommends best options*
```

### 2. HotelAgent

**Tools:**
- `search_hotels(location, checkin_date, checkout_date, guests)`: Find hotels

**Sample Interaction:**

```text
User: "Find me a good hotel in downtown London for 2 nights"
Agent: *Searches hotels, compares amenities and prices, provides recommendations*
```

### 3. BudgetAgent

**Tools:**
- `calculate_trip_budget(flights_data, hotels_data, daily_budget)`: Calculate total costs

**Sample Interaction:**

```text
User: "What's my total budget for the London trip?"
Agent: *Calculates comprehensive budget breakdown with tips for saving money*
```

## Sample Workflow

Here's how the agents work together for trip planning:

1. **Flight Search**: Use FlightAgent to find and compare flights
2. **Hotel Search**: Use HotelAgent to find accommodation options
3. **Budget Planning**: Use BudgetAgent to calculate total costs
4. **Coordination**: Use the plan-trip endpoint for guided workflow

## API Endpoints

### Agent Endpoints
- `POST /api/FlightAgent/chat` - Chat with flight search agent
- `POST /api/HotelAgent/chat` - Chat with hotel search agent
- `POST /api/BudgetAgent/chat` - Chat with budget planning agent
- `GET /api/agents` - List all available agents

### Coordination Endpoints
- `POST /api/plan-trip` - Create coordinated travel plan
- `GET /api/health` - System health check

## Configuration

Environment variables you can customize:

```json
{
  "LLM_MODEL_NAME": "gpt-4o-mini",
  "LLM_TEMPERATURE": "0.7",
  "LLM_MAX_TOKENS": "1500",
  "OPENAI_API_KEY": "your-key"
}
```

## Advanced Usage

### Agent Coordination

The system demonstrates how multiple agents can work together:

```python
# Example coordination flow
flight_results = await flight_agent.search_flights("NYC", "LON", "2024-04-10")
hotel_results = await hotel_agent.search_hotels("London", "2024-04-10", "2024-04-12")
budget_analysis = await budget_agent.calculate_budget(flight_results, hotel_results)
```

### Custom Agent Creation

You can easily add new agents to the system:

```python
restaurant_agent = Agent(
    name="RestaurantAgent",
    instructions="Help users find restaurants and make reservations",
    tools=[search_restaurants, make_reservation],
    llm_config=llm_config
)

# Add to the app
app = AgentFunctionApp(agents=[flight_agent, hotel_agent, budget_agent, restaurant_agent])
```

## Deployment

### Deploy to Azure

1. **Create Function App**:

   ```bash
   az functionapp create \
     --resource-group myResourceGroup \
     --consumption-plan-location westus \
     --runtime python \
     --runtime-version 3.11 \
     --functions-version 4 \
     --name myTravelPlannerApp \
     --storage-account mystorageaccount
   ```

2. **Configure App Settings**:

```bash
   az functionapp config appsettings set \
     --name myTravelPlannerApp \
     --resource-group myResourceGroup \
     --settings OPENAI_API_KEY="your-openai-key"
   ```

3. **Deploy**:

   ```bash
func azure functionapp publish myTravelPlannerApp
   ```

## Extending the System

### Adding Real Data Sources

Replace mock data with real APIs:

```python
# Example: Real flight API integration
async def search_flights_real(origin, destination, date):
    async with aiohttp.ClientSession() as session:
        # Integrate with Amadeus, Sabre, or other flight APIs
        api_url = f"https://api.amadeus.com/v2/shopping/flight-offers"
        # ... implementation
```

### Adding New Agent Types

Consider adding these specialized agents:

- **WeatherAgent**: Weather information for destination
- **CurrencyAgent**: Exchange rates and currency conversion
- **ActivityAgent**: Local attractions and activities
- **TransportAgent**: Local transportation options

## Troubleshooting

**Common Issues:**

1. **Agent not responding**: Check that all required environment variables are set
2. **Tool execution errors**: Verify tool function signatures match agent expectations
3. **Coordination failures**: Ensure agents are properly registered in the AgentFunctionApp

## Next Steps

- Explore [MCP Integration](../mcp-integration/) for external tool integration
- Try [Advanced Features](../advanced-features/) like streaming responses
- Check out the [Single Agent](../single-agent/) example for simpler use cases

## Support

- [Azure Functions Documentation](https://docs.microsoft.com/azure/azure-functions/)
- [Framework GitHub Issues](https://github.com/Azure/azure-functions-python-extensions/issues)
