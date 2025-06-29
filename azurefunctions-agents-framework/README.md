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

# For Azure services integration (Key Vault, etc.)
pip install azurefunctions-agent-framework[azure]

# Install all LLM providers
pip install azurefunctions-agent-framework[openai,anthropic,google,ollama]

# Install everything (all providers + Azure services)
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

### Standard Agent Deployments

All standard agent deployments (single and multi-agent) use the same consistent API pattern:

```bash
POST /api/agents/{agent_name}/chat    # Chat with any agent
GET  /api/agents/{agent_name}/info    # Get agent information  
GET  /api/agents                      # List all available agents
GET  /api/health                      # Health check
```

### A2A Protocol Deployments

Agent-to-Agent (A2A) protocol deployments use A2A specification-compliant endpoints:

```bash
POST /api/{agent_name}/chat           # Chat with the agent (A2A spec)
GET  /api/{agent_name}/info           # Get agent information (A2A spec)
GET  /api/agents                      # List all available agents
GET  /api/health                      # Health check
```

### Single Agent Example (Weather Bot)

```bash
# Chat with the agent
curl -X POST http://localhost:7071/api/agents/WeatherBot/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the weather in Tokyo?"}'

# Get agent info
curl http://localhost:7071/api/agents/WeatherBot/info

# List agents (will show 1 agent)
curl http://localhost:7071/api/agents

# Health check
curl http://localhost:7071/api/health
```

### Multi-Agent Example (Travel Planner)

```bash
# Chat with flight agent
curl -X POST http://localhost:7071/api/agents/FlightAgent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Find flights from Seattle to Tokyo"}'

# Chat with hotel agent
curl -X POST http://localhost:7071/api/agents/HotelAgent/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Find hotels in Tokyo"}'

# List all agents (will show multiple agents)
curl http://localhost:7071/api/agents

# Health check
curl http://localhost:7071/api/health
```

**Benefits of Unified Routing:**
- Same API pattern works for single and multi-agent deployments
- Easy to migrate from single to multi-agent (just add more agents)
- Predictable and consistent for developers
- Tools and integrations work across different deployment modes

## 🏗️ Framework Architecture

The Azure Functions Agent Framework follows a clean, modular architecture that separates concerns and enables flexible deployment patterns.

### Core Components

#### 1. **AgentFunctionApp** - The Function Host

`AgentFunctionApp` is the Azure Functions hosting layer that manages HTTP endpoints, routing, and agent lifecycle:

```python
from azurefunctions.agents import AgentFunctionApp, AgentMode

# Single-agent deployment
app = AgentFunctionApp(
    agents={"WeatherBot": weather_agent},
    mode=AgentMode.AZURE_FUNCTION_AGENT
)

# Multi-agent deployment  
app = AgentFunctionApp(
    agents={
        "FlightAgent": flight_agent,
        "HotelAgent": hotel_agent,
        "WeatherAgent": weather_agent
    },
    mode=AgentMode.AZURE_FUNCTION_AGENT
)
```

**Key Responsibilities:**
- **HTTP Endpoint Management**: Automatically registers routes based on deployment mode
- **Request Routing**: Routes incoming requests to appropriate agents
- **Authentication**: Handles Azure Functions authentication levels
- **Agent Lifecycle**: Manages agent initialization and cleanup
- **Error Handling**: Provides consistent error responses across all endpoints

**Deployment Modes:**

- `AZURE_FUNCTION_AGENT`: Standard HTTP endpoints for agent communication
- `A2A`: Agent-to-Agent protocol endpoints (single-agent only)

#### 2. **Agent** - The Core Agent Class

`Agent` is the base class that represents a single AI agent with its capabilities:

```python
from azurefunctions.agents import Agent

agent = Agent(
    name="MyAgent",
    instructions="You are a helpful assistant",
    tools=[custom_tool],
    mcp_servers=[mcp_server],
    llm_config=llm_config,
    enable_conversational_agent=True
)
```

**Key Responsibilities:**

- **Tool Management**: Registers and executes function tools and MCP tools
- **LLM Integration**: Handles communication with language model providers
- **MCP Integration**: Connects to Model Context Protocol servers
- **Request Processing**: Processes chat requests and manages conversation flow
- **Privacy Controls**: Manages information exposure via GET endpoints

#### 3. **ReflectionAgent** - Advanced Self-Improving Agent

`ReflectionAgent` extends the base `Agent` with self-evaluation and improvement capabilities:

```python
from azurefunctions.agents import ReflectionAgent

reflection_agent = ReflectionAgent(
    name="SmartAgent",
    instructions="You are an AI that reflects on and improves responses",
    llm_config=llm_config,
    # Reflection-specific parameters
    max_reflection_iterations=3,
    reflection_threshold=0.8,
    enable_self_evaluation=True
)
```

**Advanced Capabilities:**
- **Self-Evaluation**: Automatically assesses response quality using configurable criteria
- **Iterative Improvement**: Refines responses through reflection loops
- **Quality Thresholds**: Stops improvement when quality targets are met
- **Custom Evaluation**: Supports custom evaluation functions and prompts
- **Reflection Tracking**: Maintains history of improvement iterations

#### 4. **Runner** - Agent Execution Abstraction

`Runner` provides a clean, framework-agnostic abstraction for executing agents programmatically. It handles request normalization and response generation without any HTTP or Azure Functions dependencies:

```python
from azurefunctions.agents.runner import Runner
from azurefunctions.agents.types import ChatRequest

# Create a runner for an agent
runner = Runner(agent)

# Execute with different input types
response = await runner.run("Simple string message")
response = await runner.run({"message": "Dictionary input"})

# Use structured requests (recommended)
chat_request = ChatRequest(
    message="What's the weather?",
    user_id="user-123",
    session_id="session-456",
    context={"location": "Seattle"}
)
response = await runner.run(chat_request)
```

**Key Responsibilities:**
- **Input Normalization**: Accepts strings, dicts, or structured Request objects
- **Agent Execution**: Runs agents and handles async/sync execution patterns
- **Response Generation**: Returns structured Response objects
- **Framework Agnostic**: No HTTP, Azure Functions, or web-specific dependencies

#### 5. **Request/Response Abstractions**

The framework provides clean abstractions for agent input and output that separate business logic from transport concerns:

```python
from azurefunctions.agents.types import ChatRequest, ChatResponse

# Structured request with rich metadata
request = ChatRequest(
    message="What's the weather in Seattle?",
    user_id="user-123",
    session_id="session-456",
    context={"preferred_units": "fahrenheit"}
)

# Process and get structured response
response = await runner.run(request)

# Response contains rich information
print(f"Status: {response.status}")
print(f"Response: {response.response}")
print(f"Context: {response.context}")
print(f"Error: {response.error}")  # If any

# Convert to different formats
response_dict = response.to_dict()
```

**Benefits:**
- **Type Safety**: Full type hints and validation
- **Clean Separation**: Business logic separate from HTTP/transport concerns
- **Testability**: Easy to test without HTTP infrastructure
- **Flexibility**: Support different transport mechanisms (HTTP, message queues, etc.)

### Architecture Patterns

#### Single-Agent Pattern
**Best for:** Focused, specialized applications

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  HTTP Request   │───▶│ AgentFunctionApp │───▶│  Single Agent   │
│                 │    │   (Routing)     │    │   (Processing)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │   Tools & MCP   │
                                               │    Servers      │
                                               └─────────────────┘
```

**Endpoints Generated:**

- `POST /api/agents/{AgentName}/chat` - Chat with the agent
- `GET /api/agents/{AgentName}/info` - Get agent information

#### Multi-Agent Pattern
**Best for:** Complex workflows requiring specialized agents

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  HTTP Request   │───▶│ AgentFunctionApp │───▶│  Agent Router   │
│                 │    │   (Multi-mode)  │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                    ┌───────────────────┼───────────────────┐
                                    ▼                   ▼                   ▼
                           ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
                           │  Flight Agent   │ │  Hotel Agent    │ │ Weather Agent   │
                           │                 │ │                 │ │                 │
                           └─────────────────┘ └─────────────────┘ └─────────────────┘
```

**Endpoints Generated:**

- `POST /api/agents/{agent_name}/chat` - Chat with specific agent
- `GET /api/agents` - List all agents
- Custom application endpoints (optional)

### Component Interaction Flow

#### 1. Request Processing Flow

```
HTTP Request → AgentFunctionApp → Agent.process_request() → LLM + Tools → Response
```

#### 2. Tool Execution Flow

```
Agent → ToolRegistry → [FunctionTool | MCPTool] → Result → LLM → Final Response
```

#### 3. Reflection Flow (ReflectionAgent)

```
Initial Response → Self-Evaluation → Reflection → Improvement → Quality Check → Final Response
```

### Extensibility Points

#### Custom Agent Types
Extend the base `Agent` class to create specialized agent behaviors:

```python
class CustomAgent(Agent):
    async def process_request(self, request_data):
        # Custom pre-processing
        result = await super().process_request(request_data)
        # Custom post-processing
        return result
```

#### Custom Tools
Register functions as tools using the decorator pattern:

```python
@agent.tool
def my_custom_tool(param: str) -> str:
    """My custom tool description."""
    return f"Processed: {param}"
```

#### MCP Server Integration
Connect to external MCP servers for enhanced capabilities:

```python
agent.add_mcp_server(MCPServer(
    name="MyMCPServer",
    mode=MCPServerMode.SSE,
    params=MCPServerSseParams(url="http://localhost:8080/mcp")
))
```

This architecture provides clear separation of concerns, enabling you to build everything from simple single-purpose agents to complex multi-agent systems with enterprise-grade reliability and scalability.

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
    api_key="your-azure-openai-key",
    api_version="2024-02-15-preview"  # or your preferred API version
)
```

## 🔗 Model Context Protocol (MCP) Integration

Connect your agents to MCP servers for enhanced capabilities:

```python
from azurefunctions.agents import Agent, MCPServer, MCPServerMode
from azurefunctions.agents import MCPServerSseParams

# Configure MCP server (SSE mode example)
mcp_server = MCPServer(
    name="CodeExecutionMCPServer",
    mode=MCPServerMode.SSE,
    params=MCPServerSseParams(
        url="http://localhost:7072/runtime/webhooks/mcp/sse",
        headers={
            "Authorization": "Bearer your-mcp-api-token"
        },
        timeout=5.0,
        sse_read_timeout=300.0
    ),
    cache_tools_list=False
)

# Add to agent
code_agent = Agent(
    name="CodeExecutionAgent", 
    instructions="You are a code execution agent that can run Python code to perform tasks.",
    mcp_servers=[mcp_server],
    llm_config=llm_config,
    description="A code execution agent that can run Python code to perform tasks."
)
```

### MCP Server Modes

The unified `MCPServer` supports three communication modes:

**STDIO Mode** (subprocess communication):

```python
from azurefunctions.agents import MCPServerStdioParams

mcp_server = MCPServer(
    name="MyStdioServer",
    mode=MCPServerMode.STDIO,
    params=MCPServerStdioParams(
        command="python",
        args=["my_mcp_server.py"],
        env={"API_KEY": "your-key"}
    )
)
```

**SSE Mode** (Server-Sent Events):

```python
from azurefunctions.agents import MCPServerSseParams

mcp_server = MCPServer(
    name="MySSEServer", 
    mode=MCPServerMode.SSE,
    params=MCPServerSseParams(
        url="http://localhost:8080/sse",
        headers={"Authorization": "Bearer token"}
    )
)
```

**Streamable HTTP Mode**:

```python
from azurefunctions.agents import MCPServerStreamableHttpParams

mcp_server = MCPServer(
    name="MyHttpServer",
    mode=MCPServerMode.STREAMABLE_HTTP,
    params=MCPServerStreamableHttpParams(
        session_url="http://localhost:8080/session"
    )
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

# Azure OpenAI (alternative to OpenAI)
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Azure Services (optional - for Key Vault, etc.)
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
