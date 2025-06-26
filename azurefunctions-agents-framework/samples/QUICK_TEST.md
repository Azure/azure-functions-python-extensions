# Quick Test Guide

## Testing the Single Agent Sample

1. **Navigate to the sample directory:**
   ```bash
   cd samples/single-agent
   ```

2. **Create your local settings:**
   ```bash
   cp local.settings.json.template local.settings.json
   ```

3. **Edit local.settings.json and add your API keys:**
   ```json
   {
     "Values": {
       "OPENAI_API_KEY": "your-openai-api-key",
       "OPENWEATHER_API_KEY": "your-openweather-api-key"
     }
   }
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Start the Function App:**
   ```bash
   func start
   ```

6. **Test the agent:**
   ```bash
   curl -X POST http://localhost:7071/api/WeatherBot/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "What is the weather in Seattle?"}'
   ```

## Testing the Multi-Agent Sample

1. **Navigate to the sample directory:**
   ```bash
   cd samples/multi-agent
   ```

2. **Follow the same setup steps 2-5 above**

3. **Test the Flight Agent:**
   ```bash
   curl -X POST http://localhost:7071/api/FlightAgent/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Find flights from Seattle to Tokyo"}'
   ```

4. **List all agents:**
   ```bash
   curl http://localhost:7071/api/agents
   ```

## Expected Endpoints

### Single Agent Sample
- `POST /api/WeatherBot/chat` - Chat with weather bot
- `GET /api/WeatherBot/info` - Get weather bot info
- `GET /api/health` - Health check

### Multi-Agent Sample
- `POST /api/FlightAgent/chat` - Chat with flight agent
- `POST /api/HotelAgent/chat` - Chat with hotel agent
- `POST /api/BudgetAgent/chat` - Chat with budget agent
- `GET /api/agents` - List all agents
- `POST /api/plan-trip` - Coordinate all agents
- `GET /api/health` - Health check

Both samples are production-ready Azure Functions that can be deployed directly to Azure!
