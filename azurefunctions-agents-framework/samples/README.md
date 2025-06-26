# Azure Functions Agent Framework - Samples

This directory contains curated examples demonstrating various features and use cases of the Azure Functions Agent Framework.

## 📁 Directory Structure

```text
samples/
├── single-agent/           # Single agent Azure Function
│   ├── function_app.py     # Weather bot Function App
│   ├── host.json           # Azure Functions configuration
│   ├── requirements.txt    # Python dependencies
│   ├── local.settings.json.template # Environment template
│   └── README.md           # Sample-specific documentation
├── multi-agent/           # Multi-agent Azure Function system
│   ├── function_app.py     # Travel planner Function App
│   ├── host.json           # Azure Functions configuration
│   ├── requirements.txt    # Python dependencies
│   ├── local.settings.json.template # Environment template
│   └── README.md           # Sample-specific documentation
├── providers/             # LLM provider examples
│   ├── anthropic_claude.py # Anthropic Claude integration
│   └── google_gemini.py   # Google Gemini integration
├── mcp-integration/       # Model Context Protocol examples
│   └── weather_mcp_agent.py # Weather agent with MCP server
├── advanced-features/     # Advanced functionality examples
│   └── streaming_responses.py # Server-sent events (SSE) streaming
└── .env.example          # Global environment template
```

## 🚀 Getting Started

### Prerequisites

1. **Python 3.9+** installed
2. **Azure Functions Core Tools** installed:

   ```bash
   npm install -g azure-functions-core-tools@4
   ```

3. **Framework installed**:

   ```bash
   pip install azurefunctions-agent-framework[all]
   ```

### Environment Setup

Create a `.env` file in any sample directory:

```bash
# Required: Choose your LLM provider
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key  
GOOGLE_API_KEY=your-google-api-key

# Optional: Azure services
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id

# Optional: External APIs (for weather examples)
OPENWEATHER_API_KEY=your-openweather-api-key
```

### Running a Sample

1. **Navigate to a sample directory**:

   ```bash
   cd samples/single-agent
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt  # if present
   ```

3. **Run locally**:

   ```bash
   func start
   ```

4. **Test the agent**:

   ```bash
   # Single agent
   curl -X POST http://localhost:7071/api/WeatherBot/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "What is the weather in Seattle?"}'

   # Multi-agent  
   curl -X POST http://localhost:7071/api/agents/WeatherAgent/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Plan a trip to Tokyo next week"}'
   ```

## 📋 Sample Descriptions

### Single Agent Examples

#### Weather Bot Function App

- **Purpose**: Complete Azure Functions weather assistant with real-time data
- **Features**: OpenWeatherMap API, temperature conversion, weather advice, health monitoring
- **Endpoints**: `/api/WeatherBot/chat`, `/api/WeatherBot/info`, `/api/health`
- **Use Case**: Production-ready single-agent Azure Function

### Multi-Agent Examples

#### Travel Planner Function App

- **Purpose**: Multi-agent collaborative travel planning system
- **Agents**: FlightAgent, HotelAgent, BudgetAgent with coordination
- **Features**: Flight search, hotel booking, budget analysis, agent coordination
- **Endpoints**: `/api/{AgentName}/chat`, `/api/agents`, `/api/plan-trip`
- **Use Case**: Complex multi-agent workflows in Azure Functions

### Provider Examples

#### `anthropic_claude.py`

- **Purpose**: Demonstrates Anthropic Claude integration
- **Features**: Claude-specific configurations, best practices
- **Model**: claude-3-sonnet-20240229
- **Use Case**: Leveraging Claude's strengths for specific tasks

#### `google_gemini.py`

- **Purpose**: Shows Google Gemini integration
- **Features**: Gemini Pro model, Google AI configuration
- **Model**: gemini-pro
- **Use Case**: Using Google's multimodal capabilities

### MCP Integration Examples

#### `weather_mcp_agent.py`

- **Purpose**: Model Context Protocol server integration
- **Features**: External MCP server communication, tool discovery
- **Requirements**: MCP server running separately
- **Use Case**: Extending agent capabilities with external tools

### Advanced Features Examples

#### `streaming_responses.py`

- **Purpose**: Real-time streaming responses
- **Features**: Server-sent events (SSE), incremental responses
- **Endpoints**: Streaming-enabled chat endpoints
- **Use Case**: Real-time user experiences, long-running tasks

## 🛠️ Customizing Samples

### Adding Your Own Tools

```python
def my_custom_tool(param1: str, param2: int = 10) -> str:
    """
    Description of what your tool does.
    
    Args:
        param1: Description of parameter
        param2: Optional parameter with default
        
    Returns:
        Description of return value
    """
    # Your implementation
    return f"Result: {param1} with {param2}"

# Add to agent
agent = Agent(
    name="MyAgent",
    instructions="Use the custom tool when appropriate.",
    tools=[my_custom_tool],  # Add your tool here
    llm_config=llm_config
)
```

### Switching LLM Providers

```python
# OpenAI
llm_config = LLMConfig(
    provider=LLMProvider.OPENAI,
    model_name="gpt-4",
    api_key=os.getenv("OPENAI_API_KEY")
)

# Anthropic Claude
llm_config = LLMConfig(
    provider=LLMProvider.ANTHROPIC,
    model_name="claude-3-sonnet-20240229", 
    api_key=os.getenv("ANTHROPIC_API_KEY")
)

# Google Gemini
llm_config = LLMConfig(
    provider=LLMProvider.GOOGLE,
    model_name="gemini-pro",
    api_key=os.getenv("GOOGLE_API_KEY")
)
```

### Adding Configuration Files

Each sample can include these optional files:

- `requirements.txt` - Python dependencies
- `host.json` - Azure Functions configuration
- `local.settings.json` - Local development settings
- `.env` - Environment variables
- `README.md` - Sample-specific documentation

## 🔧 Troubleshooting

### Common Issues

1. **Missing API Keys**
   - Ensure all required API keys are set in environment variables
   - Check `.env` file is properly formatted

2. **Tool Import Errors**
   - Verify all dependencies are installed: `pip install -r requirements.txt`
   - Check Python path and virtual environment

3. **Function App Startup Issues**
   - Ensure Azure Functions Core Tools are installed and updated
   - Check `host.json` configuration
   - Verify Python version compatibility (3.9+)

4. **LLM Provider Errors**
   - Validate API keys and endpoints
   - Check rate limits and quotas
   - Ensure model names are correct

### Getting Help

- Check the main [README.md](../README.md) for framework documentation
- Review individual sample code for inline comments
- Open issues on the [GitHub repository](https://github.com/Azure/azure-functions-python-extensions/issues)

## 🤝 Contributing Samples

We welcome new sample contributions! Please:

1. Follow the existing code structure and patterns
2. Include comprehensive documentation and comments
3. Add appropriate error handling and logging
4. Test thoroughly with different scenarios
5. Include a sample-specific README.md if complex

## 📄 License

These samples are licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

---

Happy building with Azure Functions Agent Framework! 🚀
