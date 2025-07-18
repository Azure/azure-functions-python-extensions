# Single Agent Weather Bot Sample

A complete Azure Functions application demonstrating a single agent architecture using the Azure Functions Agent Framework.

## Features

- **Real Weather Data**: Integration with OpenWeatherMap API
- **Temperature Conversion**: Convert between Celsius and Fahrenheit
- **Weather Advice**: Clothing and activity recommendations
- **Error Handling**: Robust retry logic and graceful error handling
- **Health Check**: Built-in health monitoring endpoint

## Quick Start

### Prerequisites

1. **Azure Functions Core Tools**:

   ```bash
   npm install -g azure-functions-core-tools@4
   ```

2. **Python 3.9+** with pip

3. **OpenWeather API Key** (free): [Get API Key](https://openweathermap.org/api)

### Setup

1. **Install Dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:

   ```bash
   cp local.settings.json.template local.settings.json
   ```

   Edit `local.settings.json` and add your API keys:

   ```json
   {
     "Values": {
       "OPENAI_API_KEY": "your-openai-api-key",
       "OPENWEATHER_API_KEY": "your-openweather-api-key"
     }
   }
   ```

3. **Run Locally**:

   ```bash
   func start
   ```

## Usage

### Chat with the Weather Bot

```bash
curl -X POST http://localhost:7071/api/WeatherBot/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the weather like in Seattle?"
  }'
```

### Get Agent Information

```bash
curl http://localhost:7071/api/WeatherBot/info
```

### Health Check

```bash
curl http://localhost:7071/api/health
```

## Sample Conversations

**Weather Query:**

```text
User: "What should I wear in Tokyo today?"
Bot: *Uses get_current_weather tool, then provides weather conditions and clothing advice*
```

**Temperature Conversion:**

```text
User: "Convert 25°C to Fahrenheit"
Bot: *Uses convert_temperature tool and explains the conversion*
```

**Weather Advice:**

```text
User: "Is it good weather for a picnic in Central Park?"
Bot: *Gets current weather and provides activity-specific advice*
```

## Available Tools

The WeatherBot has access to these tools:

1. **get_current_weather(location, units)**: Real-time weather data
2. **convert_temperature(temperature, from_unit, to_unit)**: Temperature conversion
3. **get_weather_advice(condition, temperature, activity)**: Weather-appropriate advice

## Configuration Options

Environment variables you can customize:

```json
{
  "LLM_MODEL_NAME": "gpt-4o-mini",
  "LLM_TEMPERATURE": "0.7",
  "LLM_MAX_TOKENS": "1500",
  "OPENAI_API_KEY": "your-key",
  "OPENWEATHER_API_KEY": "your-key"
}
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
     --name myWeatherBotApp \
     --storage-account mystorageaccount
   ```

2. **Configure App Settings**:

   ```bash
   az functionapp config appsettings set \
     --name myWeatherBotApp \
     --resource-group myResourceGroup \
     --settings \
       OPENAI_API_KEY="your-openai-key" \
       OPENWEATHER_API_KEY="your-weather-key"
   ```

3. **Deploy**:

   ```bash
   func azure functionapp publish myWeatherBotApp
   ```

## Architecture

```text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   HTTP Request  │───▶│  WeatherBot     │───▶│   LLM Provider  │
│                 │    │   Agent         │    │   (OpenAI)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │  Weather Tools  │
                       │  - Current Data │
                       │  - Conversion   │
                       │  - Advice       │
                       └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │ OpenWeather API │
                       └─────────────────┘
```

## Troubleshooting

**Common Issues:**

1. **"API Key not configured"**: Make sure `OPENWEATHER_API_KEY` is set in `local.settings.json`

2. **"Location not found"**: Try using a more specific location name or check spelling

3. **Function startup errors**: Ensure Python 3.9+ and all dependencies are installed

4. **CORS issues**: The sample includes CORS configuration for local development

## Next Steps

- Try the [Multi-Agent Travel Planner](../multi-agent/) sample
- Explore [MCP Integration](../mcp-integration/) examples
- Check out [Advanced Features](../advanced-features/) like streaming responses

## Support

- [Azure Functions Python Documentation](https://docs.microsoft.com/azure/azure-functions/functions-reference-python)
- [Framework GitHub Issues](https://github.com/Azure/azure-functions-python-extensions/issues)
- [OpenWeather API Documentation](https://openweathermap.org/api)
