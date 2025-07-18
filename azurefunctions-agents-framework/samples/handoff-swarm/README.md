# Weather Advisory System - Swarm Pattern

This sample demonstrates the **SWARM handoff pattern** where agents collaborate peer-to-peer and results bubble up to the user. Agents can call each other directly in a decentralized manner.

## Architecture

```text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Weather Agent  │◄──►│ Temp Converter  │◄──►│ Weather Advisor │
│                 │    │                 │    │                 │
│ • Get weather   │    │ • Convert temps │    │ • Give advice   │
│ • Coordinate    │    │ • Handle units  │    │ • Recommend     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                        ▲                        ▲
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                            ┌─────▼─────┐
                            │   User    │
                            │ Request   │
                            └───────────┘
```

## Agents

### Weather Agent

- **Role**: Main coordinator in the swarm
- **Capabilities**: Gets weather data, coordinates handoffs
- **Handoffs**: Can hand off to temperature converter and weather advisor

### Temperature Converter

- **Role**: Temperature conversion specialist
- **Capabilities**: Converts between Celsius and Fahrenheit
- **Handoffs**: Can hand back to weather agent or forward to advisor

### Weather Advisor

- **Role**: Provides practical weather advice
- **Capabilities**: Recommends clothing and activities based on conditions
- **Handoffs**: Can hand back to other agents as needed

## Key Features

### Swarm Collaboration

- Agents can call each other directly
- No central orchestrator - peer-to-peer communication
- Results bubble up naturally to the user
- Dynamic conversation flows

### Intelligent Handoffs

- Context-aware agent selection
- Automatic conversation tracking
- Loop detection and prevention
- Graceful error handling

### Real Weather Intelligence

- Mock weather API integration
- Temperature unit conversions
- Personalized recommendations
- Activity suggestions

## API Endpoints

### Standard Agent Endpoints

```bash
# Chat with weather agent (main entry point)
POST /api/agents/weather/chat

# Chat with temperature converter directly
POST /api/agents/temperature_converter/chat

# Chat with weather advisor directly
POST /api/agents/weather_advisor/chat

# List all agents
GET /api/agents

# Get agent information
GET /api/agents/{agent_name}/info
```

### Demo Endpoint

```bash
# Demonstrates swarm pattern with direct runner handoffs
POST /api/weather-swarm

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

### 3. Test the Swarm

#### Basic Weather Request

```bash
curl -X POST http://localhost:7071/api/agents/weather/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What should I wear in Seattle today?"
  }'
```

#### Direct Agent Communication

```bash
# Temperature conversion
curl -X POST http://localhost:7071/api/agents/temperature_converter/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Convert 22 degrees Celsius to Fahrenheit"
  }'

# Weather advice
curl -X POST http://localhost:7071/api/agents/weather_advisor/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What should I wear if it is 22°C and partly cloudy?"
  }'
```

#### Swarm Demo (Direct Runner Handoffs)

```bash
curl -X POST http://localhost:7071/api/weather-swarm \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Give me complete weather advice for Tokyo",
    "location": "Tokyo"
  }'
```

## Example Conversations

### Swarm Weather Advice

```json
{
  "message": "What should I wear in London today?"
}
```

**Response Flow:**

1. Weather agent gets London weather data
2. Hands off to temperature converter for unit conversion
3. Hands off to weather advisor for clothing recommendations
4. Results bubble up with comprehensive advice

### Cross-Agent Collaboration

```json
{
  "message": "Convert the temperature in Seattle to Fahrenheit and give me activity suggestions"
}
```

**Response Flow:**

1. Weather agent gets Seattle weather (22°C)
2. Hands off to temperature converter (22°C → 72°F)
3. Hands off to weather advisor for activity suggestions
4. Consolidated response returned

## Expected Response Format

```json
{
  "pattern": "swarm",
  "location": "Seattle",
  "weather_data": {
    "temperature_celsius": 22,
    "condition": "partly cloudy",
    "description": "It's currently 22°C (72°F) and partly cloudy in Seattle"
  },
  "temperature_conversion": {
    "conversion": "22°C = 72°F"
  },
  "weather_advice": {
    "advice_summary": "Perfect weather for outdoor activities!",
    "recommended_clothing": ["light clothing", "comfortable shoes"],
    "suggested_activities": ["picnic", "hiking", "cycling"]
  },
  "handoff_path": ["weather", "temperature_converter", "weather_advisor"],
  "conversation_id": "swarm-demo-xyz"
}
```

## Key Benefits

### Decentralized Intelligence

- No single point of failure
- Agents adapt conversation flow dynamically
- Natural peer-to-peer collaboration

### Flexibility

- Agents can be called directly or through handoffs
- Multiple entry points into the system
- Easy to add new agents to the swarm

### Scalability

- Each agent is independently deployable
- Horizontal scaling of individual capabilities
- Load distribution across agents

## Customization

### Adding New Agents

```python
new_agent = Agent(
    name="new_specialist",
    instructions="Your specialization here",
    tools=[your_tools],
    handoff_config=HandoffConfig(
        mode=HandoffMode.SWARM,
        targets=[
            HandoffTarget(agent_name="weather"),
            HandoffTarget(agent_name="temperature_converter")
        ]
    )
)
```

### Custom Handoff Logic

```python
def custom_condition(request_data):
    """Custom logic for when to hand off."""
    return "urgent" in request_data.get("message", "").lower()

HandoffTarget(
    agent_name="emergency_weather",
    condition=custom_condition,
    description="Hand off for urgent weather requests"
)
```

## Production Deployment

This sample is production-ready and can be deployed to Azure Functions:

```bash
# Deploy to Azure
func azure functionapp publish YourFunctionAppName
```

The swarm pattern is ideal for:

- **Collaborative workflows** where multiple specialists contribute
- **Flexible conversation flows** that adapt to user needs
- **Scalable systems** where agents can be independently managed
- **Resilient architectures** with no central bottleneck

## Troubleshooting

### Common Issues

1. **Handoff loops**: Framework automatically detects and prevents infinite loops
2. **Missing agents**: Handoffs are validated before execution
3. **Context loss**: Use conversation IDs to maintain state across handoffs
4. **API rate limits**: Configure appropriate delays and retries

### Debug Mode

Enable detailed logging in `local.settings.json`:

```json
{
  "Values": {
    "AZURE_FUNCTIONS_ENVIRONMENT": "Development"
  }
}
```

## Next Steps

- Try the [Coordinator Pattern Sample](../handoff-coordinator/) for centralized orchestration
- Explore [Conditional Handoffs](../handoff-conditional/) for dynamic routing
- Build your own swarm with domain-specific agents
