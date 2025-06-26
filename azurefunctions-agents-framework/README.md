# Azure Functions Agent Framework

A powerful, production-ready framework for building AI agents in Azure Functions with Python. Deploy scalable single agents or collaborative multi-agent systems to Azure with enterprise-grade reliability.

## 🚀 Features

- **Production-Ready Azure Functions**: Deploy agents as scalable Azure Functions with full HTTP API support
- **Single & Multi-Agent Architecture**: Build focused single agents or collaborative multi-agent systems
- **Multiple LLM Providers**: OpenAI, Anthropic Claude, Google Gemini, Ollama, Azure OpenAI
- **Model Context Protocol (MCP)**: Integrate with MCP servers for enhanced tool capabilities
- **Real-time Streaming**: Server-sent events (SSE) support for live responses
- **Enterprise Integration**: Built-in Azure services support, Key Vault, monitoring, and logging
- **Developer Experience**: Complete samples, local development tools, and comprehensive documentation

## 📦 Installation

```bash
pip install azurefunctions-agent-framework
```

### Optional Dependencies

Choose the LLM providers you need:

```bash
# For OpenAI
pip install azurefunctions-agent-framework[openai]

# For Anthropic Claude
pip install azurefunctions-agent-framework[anthropic]

# For Google Gemini
pip install azurefunctions-agent-framework[google]

# For Ollama (local models)
pip install azurefunctions-agent-framework[ollama]

# For Azure AI services
pip install azurefunctions-agent-framework[azure]

# Install everything
pip install azurefunctions-agent-framework[all]
```

## 🏃‍♂️ Quick Start

The fastest way to get started is with our production-ready samples:

### 1. Try the Weather Bot (Single Agent)

```bash
# Clone and setup
cd samples/single-agent
cp local.settings.json.template local.settings.json
# Add your OPENAI_API_KEY and OPENWEATHER_API_KEY

# Install and run
pip install -r requirements.txt
func start

# Test it
curl -X POST http://localhost:7071/api/WeatherBot/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the weather in Seattle?"}'
```

### 2. Try the Travel Planner (Multi-Agent)

```bash
# Setup multi-agent system
cd samples/multi-agent
cp local.settings.json.template local.settings.json
# Add your API keys

# Install and run
pip install -r requirements.txt
func start

# Test different agents
curl -X POST http://localhost:7071/api/agents/FlightAgent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Find flights from NYC to LAX"}'
```

### 3. Build Your Own Agent

```python
import azure.functions as func
from azurefunctions.agents import Agent, AgentFunctionApp
from azurefunctions.agents.types import LLMConfig, LLMProvider

def my_tool(query: str) -> str:
    """Your custom tool implementation."""
    return f"Processed: {query}"

# Configure LLM
llm_config = LLMConfig(
    provider=LLMProvider.OPENAI,
    model_name="gpt-4",
    api_key="your-openai-api-key"
)

# Create agent
my_agent = Agent(
    name="MyAgent",
    instructions="You are a helpful assistant with custom tools.",
    tools=[my_tool],
    llm_config=llm_config
)

# Deploy as Azure Function
app = AgentFunctionApp(agents={"MyAgent": my_agent})
```

## 🔧 API Endpoints

### Single Agent Mode

When deploying a single agent, you get clean, focused endpoints:

```bash
POST /api/{AgentName}/chat        # Chat with the agent
GET  /api/{AgentName}/info        # Get agent information  
GET  /api/health                  # Health check
```

**Example (Weather Bot):**

```bash
curl -X POST http://localhost:7071/api/WeatherBot/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the weather in Tokyo?"}'
```

### Multi-Agent Mode

Multi-agent systems provide specialized endpoints for each agent:

```bash
POST /api/agents/{agent_name}/chat   # Chat with specific agent
GET  /api/agents                     # List all available agents
POST /api/plan-trip                  # Coordinate multiple agents (custom endpoint)
GET  /api/health                     # System health check
```

**Example (Travel Planner):**

```bash
# Talk to flight agent
curl -X POST http://localhost:7071/api/agents/FlightAgent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Find flights from Seattle to Tokyo"}'

# List all agents
curl http://localhost:7071/api/agents
```

## 🌐 Supported LLM Providers

### OpenAI

```python
from azurefunctions.agents.types import LLMConfig, LLMProvider

llm_config = LLMConfig(
    provider=LLMProvider.OPENAI,
    model_name="gpt-4",
    api_key="your-api-key"
)
```

### Anthropic Claude

```python
llm_config = LLMConfig(
    provider=LLMProvider.ANTHROPIC,
    model_name="claude-3-sonnet-20240229",
    api_key="your-anthropic-api-key"
)
```

### Google Gemini

```python
llm_config = LLMConfig(
    provider=LLMProvider.GOOGLE,
    model_name="gemini-pro",
    api_key="your-google-api-key"
)
```

### Azure OpenAI

```python
llm_config = LLMConfig(
    provider=LLMProvider.AZURE_OPENAI,
    model_name="gpt-4",
    endpoint="https://your-resource.openai.azure.com/",
    api_key="your-azure-openai-key"
)
```

## 🔗 Model Context Protocol (MCP) Integration

Connect your agents to MCP servers for enhanced capabilities:

```python
from azurefunctions.agents.mcp import MCPConfig

# Configure MCP server
mcp_config = MCPConfig(
    server_name="weather-mcp",
    server_path="/path/to/mcp/server",
    tools=["get_weather", "get_forecast"]
)

# Add to agent
weather_agent = Agent(
    name="WeatherBot",
    instructions="Use MCP tools for weather data.",
    mcp_config=mcp_config,
    llm_config=llm_config
)
```

## 📊 Streaming Responses

Enable real-time streaming for better user experience:

```python
# Enable streaming in your agent
weather_agent = Agent(
    name="WeatherBot",
    instructions="Provide weather updates with streaming responses.",
    tools=[get_weather],
    llm_config=llm_config,
    streaming=True  # Enable SSE streaming
)
```

## 🧪 Testing Your Agents

```python
# Test your agent locally
async def test_agent():
    response = await weather_agent.chat("What's the weather in Seattle?")
    print(response)

# Run the test
import asyncio
asyncio.run(test_agent())
```

## 📁 Project Structure

```text
my-agent-app/
├── function_app.py          # Your main Function App
├── agents/
│   ├── __init__.py
│   ├── weather_agent.py     # Weather agent definition
│   └── tools/
│       └── weather_tools.py # Agent tools
├── host.json               # Azure Functions configuration
├── local.settings.json     # Local development settings
├── requirements.txt        # Python dependencies
└── .env                   # Environment variables
```

## 🔧 Configuration

### Environment Variables

```bash
# LLM Provider API Keys
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
GOOGLE_API_KEY=your-google-key

# Azure Services (optional)
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id

# MCP Configuration (optional)
MCP_SERVER_PATH=/path/to/mcp/server
```

### Local Development

```json
// local.settings.json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "OPENAI_API_KEY": "your-openai-api-key"
  }
}
```

## 🚀 Deployment

Deploy to Azure Functions:

```bash
# Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4

# Create a Function App
func init my-agent-app --python
cd my-agent-app

# Add your agent code
# Deploy to Azure
func azure functionapp publish my-agent-app
```

## 📚 Production-Ready Samples

Our [`samples/`](./samples/) directory contains complete, deployable Azure Functions examples:

### 🌤️ Single Agent - Weather Bot

**Location**: [`samples/single-agent/`](./samples/single-agent/)

A production-ready weather bot with:

- **Real Weather Data**: OpenWeatherMap API integration
- **Error Handling**: Comprehensive error handling and logging
- **Health Checks**: Built-in health monitoring endpoints
- **Azure Functions**: Complete function_app.py with HTTP triggers
- **Security**: API key management and rate limiting ready

```bash
cd samples/single-agent && func start
# POST /api/WeatherBot/chat - Chat with the weather bot
# GET /api/WeatherBot/info - Get agent information
# GET /api/health - Health check endpoint
```

### ✈️ Multi-Agent - Travel Planner

**Location**: [`samples/multi-agent/`](./samples/multi-agent/)

A collaborative multi-agent system featuring:

- **FlightAgent**: Flight search and booking assistance
- **HotelAgent**: Hotel recommendations and reservations  
- **BudgetAgent**: Cost analysis and budget optimization
- **Inter-Agent Communication**: Agents can collaborate on complex requests
- **Scalable Architecture**: Each agent handles specialized tasks

```bash
cd samples/multi-agent && func start
# POST /api/agents/FlightAgent/chat - Flight-specific queries
# POST /api/agents/HotelAgent/chat - Hotel-specific queries
# POST /api/agents/BudgetAgent/chat - Budget analysis
# GET /api/agents - List all available agents
```

### 🔌 Provider Examples

**Location**: [`samples/providers/`](./samples/providers/)

Ready-to-use integrations with major LLM providers:

- **Anthropic Claude**: [`anthropic_claude.py`](./samples/providers/anthropic_claude.py)
- **Google Gemini**: [`google_gemini.py`](./samples/providers/google_gemini.py)
- **Azure OpenAI**: Complete configuration examples in sample templates

### 🛠️ MCP Integration

**Location**: [`samples/mcp-integration/`](./samples/mcp-integration/)

Model Context Protocol server integration:

- **Weather MCP Agent**: [`weather_mcp_agent.py`](./samples/mcp-integration/weather_mcp_agent.py)
- External tool server connections
- Enhanced capabilities through MCP protocol

### ⚡ Advanced Features

**Location**: [`samples/advanced-features/`](./samples/advanced-features/)

Advanced functionality demonstrations:

- **Streaming Responses**: [`streaming_responses.py`](./samples/advanced-features/streaming_responses.py) - Server-sent events implementation
- Real-time agent interactions
- Performance optimization techniques

### 🚀 Quick Testing

Follow our [Quick Test Guide](./samples/QUICK_TEST.md) to get any sample running in under 5 minutes:

```bash
# Test single agent
cd samples/single-agent
cp local.settings.json.template local.settings.json
# Add your API keys, then:
func start

# Test multi-agent system  
cd samples/multi-agent
cp local.settings.json.template local.settings.json
# Add your API keys, then:
func start
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Related Projects

- [Azure Functions Python Library](https://github.com/Azure/azure-functions-python-library)
- [Model Context Protocol](https://github.com/modelcontextprotocol)
- [A2A SDK](https://github.com/microsoft/a2a-sdk)

## 📞 Support

- [GitHub Issues](https://github.com/Azure/azure-functions-python-extensions/issues)
- [Azure Functions Documentation](https://docs.microsoft.com/azure/azure-functions/)
- [Community Discord](https://discord.gg/azure-functions)

---

Built with ❤️ by the Azure Functions team
