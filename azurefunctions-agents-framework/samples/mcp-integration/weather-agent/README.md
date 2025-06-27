# Weather MCP Agent Example

This example demonstrates how to create an Azure Functions agent that integrates with a Weather MCP server to provide weather information.

## Features

- **Weather Information**: Get current weather conditions for any location
- **Type-Safe MCP Integration**: Uses the Azure Functions Agent Framework's MCP support
- **Error Handling**: Robust error handling for network and API issues
- **Azure Functions Ready**: Pre-configured for deployment to Azure Functions

## Prerequisites

- Python 3.8+
- Azure Functions Core Tools (for local development)
- OpenAI API key
- Weather API access (the example uses a mock weather service)

## Setup

1. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Settings**:

   ```bash
   cp local.settings.json.template local.settings.json
   # Edit local.settings.json with your API keys
   ```

3. **Set Environment Variables**:
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `WEATHER_API_KEY`: Your weather service API key (if using a real weather API)

## Usage

### Local Development

1. **Start the Function App**:

   ```bash
   func start
   ```

2. **Test the Weather Agent**:

   ```bash
   curl -X POST "http://localhost:7071/api/weather_chat" \
        -H "Content-Type: application/json" \
        -d '{"message": "What is the weather like in San Francisco?"}'
   ```

### Sample Interactions

- "What's the weather in New York?"
- "Is it raining in London?"
- "What's the temperature in Tokyo?"

## Code Structure

- `weather_mcp_agent.py`: Main Azure Function with weather MCP integration
- `host.json`: Azure Functions host configuration
- `local.settings.json.template`: Template for local environment variables
- `requirements.txt`: Python dependencies

## Deployment

Deploy to Azure Functions using:

```bash
func azure functionapp publish <your-function-app-name>
```

## How It Works

1. The Azure Function receives a chat message
2. Creates an MCP server connection to the weather service
3. Uses the agent framework to process the request with weather tools
4. Returns a natural language response with weather information

## Customization

- **Weather Provider**: Replace the mock weather service with a real weather API
- **Additional Tools**: Add more weather-related tools (forecasts, alerts, etc.)
- **Response Format**: Customize the response format for your application needs
