# Azure Functions Agent Framework

A powerful, modern framework for building AI agents in Azure Functions with Python. Build single agents, multi-agent systems, and integrate with Azure services seamlessly.

## 🚀 Features

- **Single & Multi-Agent Support**: Build focused single agents or collaborative multi-agent systems
- **Multiple LLM Providers**: OpenAI, Anthropic Claude, Google Gemini, Ollama, Azure AI
- **Model Context Protocol (MCP)**: Integrate with MCP servers for enhanced capabilities
- **Agent-to-Agent Communication**: A2A SDK integration for inter-agent workflows
- **Real-time Streaming**: Server-sent events (SSE) support for live responses
- **Azure Integration**: Built-in support for Azure AI services, Key Vault, and more
- **Modern Architecture**: Clean, maintainable code with proper separation of concerns

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

### Simple Weather Agent

```python
import azure.functions as func
from azurefunctions.agents import Agent, AgentFunctionApp
from azurefunctions.agents.types import LLMConfig, LLMProvider

# Define your agent's tools
def get_weather(location: str, units: str = "metric") -> str:
    """Get current weather for a location."""
    # Your weather API integration here
    return f"Weather in {location}: 22°C, Sunny"

# Configure your LLM
llm_config = LLMConfig(
    provider=LLMProvider.OPENAI,
    model_name="gpt-4",
    api_key="your-openai-api-key"
)

# Create your agent
weather_agent = Agent(
    name="WeatherBot",
    instructions="You are a helpful weather assistant. Use the weather tool to provide accurate forecasts.",
    tools=[get_weather],
    llm_config=llm_config
)

# Create the Function App
app = AgentFunctionApp(agents=[weather_agent])
```

### Multi-Agent Travel System

```python
from azurefunctions.agents import Agent, AgentFunctionApp

# Weather Agent
weather_agent = Agent(
    name="WeatherAgent",
    instructions="Provide weather information and travel advice based on conditions.",
    tools=[get_weather, get_weather_forecast],
    llm_config=llm_config
)

# Travel Agent  
travel_agent = Agent(
    name="TravelAgent",
    instructions="Help plan trips, find destinations, and create itineraries.",
    tools=[search_destinations, plan_itinerary],
    llm_config=llm_config
)

# Budget Agent
budget_agent = Agent(
    name="BudgetAgent", 
    instructions="Analyze costs and optimize travel budgets.",
    tools=[calculate_costs, find_deals],
    llm_config=llm_config
)

# Multi-agent app
app = AgentFunctionApp(agents=[weather_agent, travel_agent, budget_agent])
```

## 🔧 API Endpoints

### Single Agent Mode

- `POST /api/{agent_name}/chat` - Chat with the agent
- `GET /api/{agent_name}/info` - Get agent information

### Multi-Agent Mode

- `POST /api/agents/{name}/chat` - Chat with specific agent
- `GET /api/agents` - List all agents
- `POST /api/workflows` - Create agent workflows (coming soon)

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

## 📚 Examples & Samples

Check out the [`samples/`](./samples/) directory for complete examples:

- **Single Agent Examples**: Weather bot, assistant, document processor
- **Multi-Agent Systems**: Travel planner, customer service, research assistant  
- **MCP Integration**: Weather MCP server, external tool integration
- **Provider Examples**: OpenAI, Claude, Gemini, Azure OpenAI
- **Advanced Features**: Streaming, A2A communication, workflows

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
