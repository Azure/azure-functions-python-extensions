# Custom Triggers with Azure Functions Agent Framework

This sample demonstrates how to use the Azure Functions Agent Framework with custom triggers by setting `create_triggers=False` and using the `Runner` abstraction for manual agent execution.

## Overview

The Azure Functions Agent Framework supports two integration modes:

1. **Automatic Mode** (default): `create_triggers=True` - Framework automatically creates HTTP endpoints
2. **Custom Mode**: `create_triggers=False` - You create your own triggers and use the `Runner` for agent execution

## When to Use Custom Triggers

Use custom triggers when you need:

- **Non-HTTP triggers**: Service Bus, Event Grid, Cosmos DB, Blob Storage, Timer, etc.
- **Custom HTTP logic**: Advanced authentication, request preprocessing, custom routing
- **Integration with existing systems**: Legacy endpoints, middleware, custom protocols
- **Fine-grained control**: Custom error handling, logging, metrics, response formatting

## Key Concepts

### AgentFunctionApp with Custom Triggers

```python
from azurefunctions.agents import Agent, AgentFunctionApp

# Create your agent
agent = Agent(name="my-agent", instructions="You are helpful", tools=[...])

# Create AgentFunctionApp with create_triggers=False
app = AgentFunctionApp(
    agents=[agent],
    create_triggers=False  # Key: No automatic HTTP endpoints
)

# Get runner for manual execution
runner = app.get_single_runner()  # For single agent
# Or: runner = app.get_runner("agent-name")  # For specific agent
```

### Runner Class

The `Runner` class is your interface for agent execution:

```python
# Async execution
response = await runner.run("Hello, agent!")
response = await runner.run({"message": "Hello", "context": {...}})

# Sync execution  
response = runner.run_sync("Hello, agent!")

# Utilities
agent_info = await runner.get_agent_info()
http_response = runner.to_http_response(response_data)
```

## Trigger Examples

### 1. Custom HTTP Trigger

```python
@app.route(route="custom/chat", methods=["POST"])
async def custom_chat(req: HttpRequest) -> HttpResponse:
    try:
        # Custom preprocessing
        request_data = req.get_json()
        request_data["context"] = {"ip": req.headers.get("X-Forwarded-For")}
        
        # Execute agent
        response = await runner.run(request_data)
        
        # Custom response formatting
        return runner.to_http_response({
            "agent": runner.agent_name,
            "response": response["response"],
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return runner.to_http_response(
            {"error": str(e)}, 
            status_code=500
        )
```

### 2. Service Bus Trigger

```python
@app.service_bus_queue_trigger(
    arg_name="msg", 
    queue_name="agent-requests",
    connection="ServiceBusConnection"
)
async def process_queue_message(msg: func.ServiceBusMessage):
    try:
        message_data = json.loads(msg.get_body().decode('utf-8'))
        response = await runner.run(message_data)
        
        # Process response (send to another queue, database, etc.)
        logger.info(f"Processed: {response['response']}")
    except Exception as e:
        logger.error(f"Queue processing error: {e}")
```

### 3. Timer Trigger

```python
@app.timer_trigger(
    arg_name="timer", 
    schedule="0 0 8 * * *"  # Daily at 8 AM
)
async def daily_summary(timer: func.TimerRequest):
    request = "Generate a daily summary report"
    response = await runner.run(request)
    
    # Send summary via email, save to storage, etc.
    await send_summary_email(response["response"])
```

### 4. Blob Trigger

```python
@app.blob_trigger(
    arg_name="blob",
    path="documents/{name}",
    connection="AzureWebJobsStorage"
)
async def process_document(blob: func.InputStream):
    content = blob.read().decode('utf-8')
    
    request = f"Analyze this document: {content}"
    response = await runner.run(request)
    
    # Save analysis results
    await save_analysis(blob.name, response["response"])
```

## Runner Request Formats

The `Runner` accepts flexible request formats:

### Simple String

```python
response = await runner.run("What's the weather?")
```

### Dictionary Format

```python
response = await runner.run({
    "message": "What's the weather?",
    "context": {"user_id": "123", "location": "NYC"}
})
```

### OpenAI Messages Format

```python
response = await runner.run({
    "messages": [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "What's the weather?"}
    ]
})
```

### MessageRequest Object

```python
request = runner.create_message_request(
    message="What's the weather?",
    context={"user_id": "123"}
)
response = await runner.run(request)
```

## Runner Utilities

### HTTP Response Helper

```python
# Automatically creates proper Azure Functions HttpResponse
http_response = runner.to_http_response(response_data, status_code=200)
```

### Agent Information

```python
# Get agent metadata
info = await runner.get_agent_info()
# Returns: {"name": "...", "description": "...", "tools": [...], ...}
```

### Synchronous Execution

```python
# For non-async contexts
response = runner.run_sync("Hello, agent!")
```

## Multi-Agent Custom Triggers

For multiple agents, use `get_runner(agent_name)`:

```python
app = AgentFunctionApp(
    agents=[weather_agent, travel_agent],
    create_triggers=False
)

@app.route(route="weather/chat", methods=["POST"])
async def weather_endpoint(req: HttpRequest):
    runner = app.get_runner("weather-agent")
    response = await runner.run(req.get_json())
    return runner.to_http_response(response)

@app.route(route="travel/chat", methods=["POST"])  
async def travel_endpoint(req: HttpRequest):
    runner = app.get_runner("travel-agent")
    response = await runner.run(req.get_json())
    return runner.to_http_response(response)
```

## Error Handling Patterns

### Validation and Error Responses

```python
@app.route(route="safe-chat", methods=["POST"])
async def safe_chat(req: HttpRequest) -> HttpResponse:
    try:
        request_data = req.get_json() or {}
        
        # Validate request
        if not request_data.get("message"):
            return runner.to_http_response(
                {"error": "Message is required"}, 
                status_code=400
            )
        
        # Process request
        response = await runner.run(request_data)
        
        return runner.to_http_response({
            "success": True,
            "response": response["response"]
        })
        
    except ValueError as e:
        return runner.to_http_response(
            {"error": "Invalid request", "message": str(e)},
            status_code=400
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return runner.to_http_response(
            {"error": "Internal server error"},
            status_code=500
        )
```

## Testing Custom Triggers

### Local Testing

```python
# For testing runner logic locally
async def test_runner():
    response = await runner.run("Test message")
    print(f"Response: {response}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_runner())
```

### Unit Testing

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_custom_chat_endpoint():
    # Mock the runner
    mock_runner = AsyncMock()
    mock_runner.run.return_value = {"response": "Test response"}
    
    # Test your endpoint logic
    # ...
```

## Configuration and Deployment

### Local Settings

```json
// local.settings.json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "...",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "ServiceBusConnection": "...",
    "OPENAI_API_KEY": "..."
  }
}
```

### Host Configuration

```json
// host.json
{
  "version": "2.0",
  "functionTimeout": "00:05:00",
  "extensions": {
    "serviceBus": {
      "maxConcurrentCalls": 16,
      "prefetchCount": 100
    }
  }
}
```

## Best Practices

1. **Always use try-catch**: Wrap agent execution in proper error handling
2. **Validate inputs**: Check request format before processing
3. **Add context**: Include trigger-specific metadata in requests
4. **Log appropriately**: Log both successes and failures
5. **Handle timeouts**: Set appropriate function timeouts for long-running agents
6. **Resource management**: Be mindful of memory and compute limits
7. **Security**: Validate and sanitize all inputs

## Migration from Automatic Mode

If you're migrating from automatic mode (`create_triggers=True`) to custom mode:

### Before (Automatic)

```python
app = AgentFunctionApp(agents=[agent])  # create_triggers=True by default
# Framework creates /api/{agent-name}/chat automatically
```

### After (Custom)

```python
app = AgentFunctionApp(agents=[agent], create_triggers=False)
runner = app.get_single_runner()

@app.route(route="chat", methods=["POST"])
async def chat(req: HttpRequest) -> HttpResponse:
    response = await runner.run(req.get_json())
    return runner.to_http_response(response)
```

## Complete Example

See `custom_triggers_example.py` for a complete working example demonstrating:
- Custom HTTP triggers with enhanced logic
- Service Bus message processing
- Timer-based scheduled execution
- Blob storage file processing
- Comprehensive error handling
- Manual runner usage patterns

## Next Steps

- Explore the complete example in `custom_triggers_example.py`
- Try different trigger types based on your use case
- Implement custom business logic around agent execution
- Add monitoring and metrics to your custom triggers
