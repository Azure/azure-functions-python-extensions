"""
Comprehensive example demonstrating custom trigger integration with the Azure Functions Agent Framework.

This example shows how to use AgentFunctionApp with create_triggers=False to enable
custom trigger integration while using the new Request/Response abstractions and Runner for agent execution.

Features demonstrated:
- Custom HTTP triggers with new ChatRequest/ChatResponse
- Service Bus triggers
- Timer triggers  
- Blob triggers
- Manual agent execution using Runners and new abstractions
- Error handling and logging
- Clean separation between Runner (agent execution) and HTTP layer
"""

import json
import logging
from datetime import datetime
from typing import Optional

import azure.functions as func
from azure.functions import HttpRequest, HttpResponse

# Import the agent framework
from azurefunctions.agents import Agent, AgentFunctionApp
from azurefunctions.agents.types import LLMConfig, LLMProvider, ChatRequest, ChatResponse
from azurefunctions.agents.runner import Runner

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a simple weather tool
def get_current_weather(location: str, unit: str = "celsius") -> str:
    """Get the current weather for a location."""
    return f"The weather in {location} is 22°{unit[0].upper()} and sunny."

def get_forecast(location: str, days: int = 3) -> str:
    """Get weather forecast for a location."""
    return f"The {days}-day forecast for {location}: Sunny with temperatures ranging from 18-25°C."

# Create the weather agent
weather_agent = Agent(
    name="weather-bot",
    instructions="You are a helpful weather assistant. Use the provided tools to get weather information.",
    tools=[get_current_weather, get_forecast],
    llm_config=LLMConfig(
        provider=LLMProvider.OPENAI,
        model_name="gpt-4o-mini",
    ),
)

# Create AgentFunctionApp with create_triggers=False for custom trigger integration
app = AgentFunctionApp(
    agents=[weather_agent],
    create_triggers=False,  # This is the key - no automatic HTTP triggers
)

# Get the runner for manual agent execution
weather_runner = app.runners["weather-bot"]  # Use the agent name as key


# =============================================================================
# CUSTOM HTTP TRIGGER EXAMPLE - Using New Request/Response Architecture
# =============================================================================

@app.route(route="custom/weather/chat", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
async def custom_weather_chat(req: HttpRequest) -> HttpResponse:
    """
    Custom HTTP trigger for weather agent with enhanced request handling using new abstractions.
    
    This shows how you can add custom logic before/after agent processing while using
    the clean Request/Response abstractions.
    """
    logger.info("Custom weather chat endpoint called")
    
    try:
        # Custom request validation and preprocessing
        request_data = req.get_json() or {}
        
        # Get user info from headers
        user_id = req.headers.get("X-User-ID", "anonymous")
        session_id = req.headers.get("X-Session-ID", f"session-{datetime.utcnow().timestamp()}")
        client_ip = req.headers.get("X-Forwarded-For", "unknown")
        
        # Create structured ChatRequest with custom context
        chat_request = ChatRequest(
            message=request_data.get("message"),
            messages=request_data.get("messages"),
            user_id=user_id,
            session_id=session_id,
            context={
                "client_ip": client_ip,
                "timestamp": datetime.utcnow().isoformat(),
                "endpoint": "custom-weather-chat",
                **request_data.get("context", {})
            }
        )
        
        # Use the runner to process the request - returns ChatResponse
        response = await weather_runner.run(chat_request)
        
        # Add custom metadata to the response
        if not response.metadata:
            response.metadata = {}
        response.metadata.update({
            "request_id": f"custom-{datetime.utcnow().timestamp()}",
            "processing_endpoint": "custom-weather-chat"
        })
        
        # Convert to HTTP response using AgentFunctionApp's HTTP layer
        return app._response_to_http(response, agent_name=weather_runner.agent_name)
        
    except Exception as e:
        logger.error(f"Error in custom weather chat: {e}")
        
        # Create error response using new abstractions
        error_response = ChatResponse(
            status="error",
            error=f"Failed to process weather request: {str(e)}",
            metadata={
                "timestamp": datetime.utcnow().isoformat(),
                "endpoint": "custom-weather-chat"
            }
        )
        return app._response_to_http(error_response, status_code=500)


# =============================================================================
# SERVICE BUS TRIGGER EXAMPLE - Using New Request/Response Architecture
# =============================================================================

@app.service_bus_queue_trigger(
    arg_name="msg", 
    queue_name="weather-requests",
    connection="ServiceBusConnection"
)
async def process_weather_queue_message(msg: func.ServiceBusMessage):
    """
    Service Bus trigger for processing weather requests from a queue using new abstractions.
    
    This demonstrates how to use the agent with asynchronous messaging patterns
    while leveraging the clean Request/Response architecture.
    """
    logger.info("Processing Service Bus message")
    
    try:
        # Parse the message
        message_body = msg.get_body().decode('utf-8')
        request_data = json.loads(message_body)
        
        # Create structured ChatRequest for Service Bus processing
        chat_request = ChatRequest(
            message=request_data.get("message"),
            messages=request_data.get("messages"),
            user_id=request_data.get("user_id", "service-bus-user"),
            session_id=request_data.get("session_id", f"sb-{msg.message_id}"),
            context={
                "source": "service_bus_queue",
                "message_id": msg.message_id,
                "delivery_count": msg.delivery_count,
                "enqueued_time": msg.enqueued_time_utc.isoformat() if msg.enqueued_time_utc else None,
                **request_data.get("context", {})
            }
        )
        
        # Process with the agent - returns ChatResponse
        response = await weather_runner.run(chat_request)
        
        # Log the structured response
        response_dict = response.to_dict()
        logger.info(f"Processed queue message {msg.message_id}: Status={response.status}")
        
        if response.status == "success":
            logger.info(f"Response: {response.response}")
        else:
            logger.warning(f"Error processing message: {response.error}")
        
        # In a real scenario, you might:
        # 1. Send response to another queue
        # 2. Store in database
        # 3. Send notification
        
    except Exception as e:
        logger.error(f"Error processing Service Bus message {msg.message_id}: {e}")
        
        # Optional: Send result to an output queue (would require output binding)
        # await send_to_response_queue(response)
        
    except Exception as e:
        logger.error(f"Error processing Service Bus message {msg.message_id}: {e}")
        # In a real scenario, you might want to dead-letter the message
        raise


# =============================================================================
# TIMER TRIGGER EXAMPLE
# =============================================================================

@app.timer_trigger(
    arg_name="timer", 
    schedule="0 0 8 * * *",  # Daily at 8 AM
    run_on_startup=False
)
async def daily_weather_summary(timer: func.TimerRequest):
    """
    Timer trigger for generating daily weather summaries.
    
    This demonstrates scheduled agent execution for automated reports.
    """
    logger.info("Generating daily weather summary")
    
    try:
        # Create a request for daily summary
        request_data = {
            "message": "Generate a daily weather summary for London, Paris, and New York. Include current weather and forecasts.",
            "context": {
                "source": "timer_trigger",
                "scheduled_time": timer.schedule_status.get("last") if timer.schedule_status else None,
                "trigger_type": "daily_summary"
            }
        }
        
        # Process with the agent
        response = await weather_runner.run(request_data)
        
        # Log the summary (in a real scenario, you might email it or save to storage)
        logger.info(f"Daily weather summary generated: {response.get('response', 'No summary')}")
        
        # Optional: Send summary via email, store in database, etc.
        # await email_summary(response['response'])
        # await store_summary_in_database(response)
        
    except Exception as e:
        logger.error(f"Error generating daily weather summary: {e}")


# =============================================================================
# BLOB TRIGGER EXAMPLE
# =============================================================================

@app.blob_trigger(
    arg_name="blob",
    path="weather-data/{name}",
    connection="AzureWebJobsStorage"
)
async def process_weather_data_file(blob: func.InputStream):
    """
    Blob trigger for processing uploaded weather data files.
    
    This demonstrates file-based agent integration.
    """
    logger.info(f"Processing weather data file: {blob.name}")
    
    try:
        # Read the blob content
        content = blob.read().decode('utf-8')
        
        # Create a request to analyze the weather data
        request_data = {
            "message": f"Analyze this weather data and provide insights: {content[:1000]}...",  # Truncate for demo
            "context": {
                "source": "blob_trigger",
                "filename": blob.name,
                "file_size": len(content),
                "trigger_type": "data_analysis"
            }
        }
        
        # Process with the agent
        response = await weather_runner.run(request_data)
        
        # Log the analysis (in a real scenario, you might save results to another blob or database)
        logger.info(f"Weather data analysis for {blob.name}: {response.get('response', 'No analysis')}")
        
        # Optional: Save analysis results
        # await save_analysis_to_blob(blob.name, response)
        
    except Exception as e:
        logger.error(f"Error processing weather data file {blob.name}: {e}")


# =============================================================================
# MANUAL RUNNER USAGE EXAMPLES
# =============================================================================

async def example_manual_usage():
    """
    Example of using the runner directly for programmatic agent execution.
    
    This is useful for testing, custom business logic, or integration scenarios.
    """
    
    # Simple string request
    response1 = await weather_runner.run("What's the weather in Tokyo?")
    print(f"Simple request response: {response1}")
    
    # Structured request with context
    structured_request = weather_runner.create_message_request(
        message="What's the weather forecast for London?",
        context={"user_id": "12345", "preference": "celsius"}
    )
    response2 = await weather_runner.run(structured_request)
    print(f"Structured request response: {response2}")
    
    # OpenAI-style messages
    openai_request = {
        "messages": [
            {"role": "user", "content": "Hi, I need weather information"},
            {"role": "assistant", "content": "I'd be happy to help with weather information!"},
            {"role": "user", "content": "What's the weather in Paris?"}
        ]
    }
    response3 = await weather_runner.run(openai_request)
    print(f"OpenAI-style request response: {response3}")
    
    # Get agent information
    agent_info = await weather_runner.get_agent_info()
    print(f"Agent info: {agent_info}")


# =============================================================================
# HELPER FUNCTIONS FOR CUSTOM LOGIC
# =============================================================================

def validate_weather_request(request_data: dict) -> Optional[str]:
    """
    Custom validation logic for weather requests.
    
    Returns:
        None if valid, error message if invalid
    """
    if not request_data.get("message") and not request_data.get("messages"):
        return "Request must contain 'message' or 'messages'"
    
    # Add more custom validation as needed
    return None


async def log_request_metrics(agent_name: str, request_data: dict, response: dict):
    """
    Custom logging/metrics for agent requests.
    """
    metrics = {
        "agent": agent_name,
        "timestamp": datetime.utcnow().isoformat(),
        "request_type": type(request_data.get("message", "")).__name__,
        "response_length": len(str(response.get("response", ""))),
        "tool_calls": len(response.get("tool_results", [])),
    }
    
    # Log to your preferred metrics system
    logger.info(f"Request metrics: {json.dumps(metrics)}")


# =============================================================================
# ERROR HANDLING EXAMPLE
# =============================================================================

@app.route(route="weather/safe-chat", auth_level=func.AuthLevel.FUNCTION, methods=["POST"])
async def safe_weather_chat(req: HttpRequest) -> HttpResponse:
    """
    Example of robust error handling with custom triggers.
    """
    try:
        request_data = req.get_json() or {}
        
        # Validate request
        validation_error = validate_weather_request(request_data)
        if validation_error:
            return weather_runner.to_http_response(
                {"error": "Validation failed", "message": validation_error},
                status_code=400
            )
        
        # Process request
        response = await weather_runner.run(request_data)
        
        # Log metrics
        await log_request_metrics(weather_runner.agent_name, request_data, response)
        
        # Return successful response
        return weather_runner.to_http_response({
            "success": True,
            "agent": weather_runner.agent_name,
            "response": response.get("response", ""),
            "metadata": response
        })
        
    except ValueError as e:
        # Handle validation errors
        return weather_runner.to_http_response(
            {"error": "Invalid request format", "message": str(e)},
            status_code=400
        )
    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error in safe weather chat: {e}")
        return weather_runner.to_http_response(
            {"error": "Internal server error", "message": "Please try again later"},
            status_code=500
        )


if __name__ == "__main__":
    # For local testing of manual runner usage
    import asyncio
    asyncio.run(example_manual_usage())
