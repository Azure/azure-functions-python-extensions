"""
MCP Server with StreamableHTTP Transport Sample

This sample demonstrates how to create an Azure Function MCP server using the new
StreamableHTTP transport, which provides better performance and standards compliance
compared to the previous SSE implementation.

Key Features:
- Single endpoint (/mcp) for all MCP communication
- Built-in session management and connection pooling
- Support for tools, resources, and prompts
- Automatic error handling and recovery
- Standards-compliant HTTP streaming
"""

import logging
from typing import List, Optional

import azure.functions as func
from azurefunctions.extensions.mcp_server import MCPFunctionApp

logging.info("MCP Server with StreamableHTTP Transport Sample")

# Create the MCP Function App with StreamableHTTP transport
# The StreamableHTTP transport is automatically configured for optimal performance
app = MCPFunctionApp(
    auth_level=func.AuthLevel.ANONYMOUS,  # For demo purposes - use FUNCTION in production
    name="streamable-http-mcp-server",
    instructions="A comprehensive MCP server demonstrating StreamableHTTP transport capabilities"
)

logging.info(f"MCP Function App initialized with StreamableHTTP transport - {app._session_manager}")

# =============================================================================
# MCP TOOLS - Functions that can be called by the MCP client
# =============================================================================

@app.tool()
def get_weather(location: str, units: str = "celsius") -> str:
    """
    Get current weather information for a location.
    
    Args:
        location: The city or location to get weather for
        units: Temperature units (celsius or fahrenheit)
    
    Returns:
        Weather information as a string
    """
    logging.info(f"Getting weather for {location} in {units}")
    
    # Simulate weather data (in real app, you'd call a weather API)
    weather_data = {
        "new york": {"temp": 22, "condition": "sunny", "humidity": 65},
        "london": {"temp": 15, "condition": "cloudy", "humidity": 80},
        "tokyo": {"temp": 28, "condition": "rainy", "humidity": 85},
        "sydney": {"temp": 18, "condition": "windy", "humidity": 60}
    }
    
    location_lower = location.lower()
    if location_lower in weather_data:
        data = weather_data[location_lower]
        temp = data["temp"]
        if units.lower() == "fahrenheit":
            temp = (temp * 9/5) + 32
        
        return f"Weather in {location}: {temp}°{units[0].upper()}, {data['condition']}, {data['humidity']}% humidity"
    else:
        return f"Weather data not available for {location}. Try: New York, London, Tokyo, or Sydney"


@app.tool()
def calculate_math(expression: str) -> str:
    """
    Calculate a mathematical expression safely.
    
    Args:
        expression: Mathematical expression to evaluate (e.g., "2 + 3 * 4")
    
    Returns:
        The result of the calculation or an error message
    """
    logging.info(f"Calculating: {expression}")
    
    try:
        # Simple whitelist of allowed characters for security
        allowed_chars = set('0123456789+-*/()%. ')
        if not all(c in allowed_chars for c in expression):
            return "Error: Expression contains invalid characters. Only numbers, +, -, *, /, (), and spaces are allowed."
        
        # Evaluate the expression
        result = eval(expression)
        return f"Result: {expression} = {result}"
    except ZeroDivisionError:
        return "Error: Division by zero"
    except Exception as e:
        return f"Error calculating '{expression}': {str(e)}"


@app.tool()
def generate_password(length: int = 12, include_symbols: bool = True) -> str:
    """
    Generate a secure random password.
    
    Args:
        length: Length of the password (default: 12)
        include_symbols: Whether to include special symbols (default: True)
    
    Returns:
        A randomly generated password
    """
    import random
    import string
    
    logging.info(f"Generating password of length {length}, symbols: {include_symbols}")
    
    if length < 4:
        return "Error: Password length must be at least 4 characters"
    if length > 100:
        return "Error: Password length cannot exceed 100 characters"
    
    # Character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    symbols = "!@#$%^&*()_+-=[]{}|;:,.<>?" if include_symbols else ""
    
    # Ensure at least one character from each required set
    password = [
        random.choice(lowercase),
        random.choice(uppercase),
        random.choice(digits)
    ]
    
    if include_symbols:
        password.append(random.choice(symbols))
    
    # Fill remaining length with random characters from all sets
    all_chars = lowercase + uppercase + digits + symbols
    for _ in range(length - len(password)):
        password.append(random.choice(all_chars))
    
    # Shuffle the password to avoid predictable patterns
    random.shuffle(password)
    
    return "".join(password)


@app.tool()
def list_todos(filter_status: Optional[str] = None) -> str:
    """
    List todo items with optional status filtering.
    
    Args:
        filter_status: Filter by status ("pending", "completed", or None for all)
    
    Returns:
        List of todo items
    """
    logging.info(f"Listing todos with filter: {filter_status}")
    
    # Sample todo data (in real app, this would come from a database)
    todos = [
        {"id": 1, "task": "Complete MCP server implementation", "status": "completed"},
        {"id": 2, "task": "Write comprehensive documentation", "status": "pending"},
        {"id": 3, "task": "Add unit tests", "status": "pending"},
        {"id": 4, "task": "Deploy to Azure", "status": "completed"},
        {"id": 5, "task": "Monitor performance", "status": "pending"}
    ]
    
    # Filter by status if specified
    if filter_status:
        todos = [todo for todo in todos if todo["status"] == filter_status.lower()]
    
    if not todos:
        return f"No todos found{' with status: ' + filter_status if filter_status else ''}"
    
    result = f"Todo Items{' (' + filter_status + ')' if filter_status else ''}:\n"
    for todo in todos:
        status_emoji = "✅" if todo["status"] == "completed" else "⏳"
        result += f"{status_emoji} [{todo['id']}] {todo['task']} ({todo['status']})\n"
    
    return result.strip()


# =============================================================================
# MCP RESOURCES - Static or dynamic content that can be retrieved
# =============================================================================

@app.resource("config://app/{section}")
def get_app_config(section: str) -> str:
    """
    Get application configuration for a specific section.
    
    Args:
        section: Configuration section name
    
    Returns:
        Configuration data as JSON string
    """
    logging.info(f"Getting config for section: {section}")
    
    configs = {
        "database": {
            "host": "localhost",
            "port": "5432",
            "name": "mcp_demo",
            "ssl": True
        },
        "api": {
            "base_url": "https://api.example.com",
            "timeout": 30,
            "retries": 3
        },
        "features": {
            "streamable_http": True,
            "session_management": True,
            "error_recovery": True
        }
    }
    
    if section in configs:
        import json
        return json.dumps(configs[section], indent=2)
    else:
        available = ", ".join(configs.keys())
        return f"Configuration section '{section}' not found. Available sections: {available}"


@app.resource("docs://api/{endpoint}")
def get_api_documentation(endpoint: str) -> str:
    """
    Get API documentation for a specific endpoint.
    
    Args:
        endpoint: API endpoint name
    
    Returns:
        API documentation in markdown format
    """
    logging.info(f"Getting documentation for endpoint: {endpoint}")
    
    docs = {
        "weather": """
# Weather API Endpoint

## GET /api/weather

Get current weather information for a location.

### Parameters
- `location` (string, required): City or location name
- `units` (string, optional): Temperature units ("celsius" or "fahrenheit")

### Response
```json
{
    "location": "New York",
    "temperature": 22,
    "condition": "sunny",
    "humidity": 65,
    "units": "celsius"
}
```
        """,
        "todos": """
# Todo API Endpoint

## GET /api/todos

List todo items with optional filtering.

### Parameters
- `status` (string, optional): Filter by status ("pending" or "completed")

### Response
```json
{
    "todos": [
        {
            "id": 1,
            "task": "Complete project",
            "status": "pending"
        }
    ]
}
```
        """,
        "calculate": """
# Calculate API Endpoint

## POST /api/calculate

Perform mathematical calculations.

### Request Body
```json
{
    "expression": "2 + 3 * 4"
}
```

### Response
```json
{
    "expression": "2 + 3 * 4",
    "result": 14
}
```
        """
    }
    
    if endpoint in docs:
        return docs[endpoint].strip()
    else:
        available = ", ".join(docs.keys())
        return f"Documentation for '{endpoint}' not found. Available endpoints: {available}"


@app.resource("logs://recent/{hours}")
def get_recent_logs(hours: str) -> str:
    """
    Get recent application logs.
    
    Args:
        hours: Number of hours to look back
    
    Returns:
        Recent log entries
    """
    logging.info(f"Getting logs for last {hours} hours")
    
    try:
        hours_int = int(hours)
        if hours_int < 1 or hours_int > 168:  # Max 1 week
            return "Error: Hours must be between 1 and 168 (1 week)"
    except ValueError:
        return "Error: Hours must be a valid number"
    
    # Sample log data (in real app, this would come from actual logs)
    import datetime
    
    logs = []
    for i in range(min(hours_int * 2, 20)):  # Simulate ~2 entries per hour, max 20
        timestamp = datetime.datetime.now() - datetime.timedelta(minutes=i*30)
        level = ["INFO", "DEBUG", "WARNING"][i % 3]
        message = [
            "MCP request processed successfully",
            "Session manager initialized",
            "Client connected via StreamableHTTP",
            "Tool execution completed",
            "Resource request handled"
        ][i % 5]
        
        logs.append(f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {level}: {message}")
    
    logs.reverse()  # Most recent first
    result = f"Recent logs (last {hours} hours):\n\n"
    result += "\n".join(logs)
    
    return result


# =============================================================================
# MCP PROMPTS - Reusable prompt templates
# =============================================================================

@app.prompt("code-review")
def code_review_prompt(language: str = "python", style: str = "comprehensive") -> str:
    """
    Generate a code review prompt template.
    
    Args:
        language: Programming language for the review
        style: Review style ("comprehensive", "security", "performance")
    
    Returns:
        Code review prompt template
    """
    logging.info(f"Generating code review prompt for {language} ({style} style)")
    
    base_prompt = f"""
Please review the following {language} code with a focus on {style} aspects.

Consider the following areas:
"""
    
    if style == "comprehensive":
        base_prompt += """
- Code quality and readability
- Best practices adherence
- Potential bugs and edge cases
- Performance considerations
- Security vulnerabilities
- Documentation completeness
- Test coverage
"""
    elif style == "security":
        base_prompt += """
- Input validation and sanitization
- Authentication and authorization
- Data encryption and secure storage
- SQL injection and XSS vulnerabilities
- Secure communication protocols
- Error handling that doesn't leak information
"""
    elif style == "performance":
        base_prompt += """
- Algorithm efficiency and Big O complexity
- Memory usage and potential leaks
- Database query optimization
- Caching strategies
- Network request optimization
- Resource utilization
"""
    else:
        base_prompt += """
- General code quality
- Basic functionality
- Error handling
"""
    
    base_prompt += """

Code to review:
[INSERT CODE HERE]

Please provide:
1. Overall assessment
2. Specific issues found
3. Recommended improvements
4. Priority level for each issue
"""
    
    return base_prompt.strip()


@app.prompt("api-documentation")
def api_documentation_prompt(service_name: str, include_examples: bool = True) -> str:
    """
    Generate an API documentation prompt template.
    
    Args:
        service_name: Name of the service/API
        include_examples: Whether to include example requests/responses
    
    Returns:
        API documentation prompt template
    """
    logging.info(f"Generating API documentation prompt for {service_name}")
    
    prompt = f"""
Please create comprehensive API documentation for the {service_name} service.

Include the following sections:

## Overview
- Brief description of the service
- Base URL and versioning
- Authentication methods

## Endpoints
For each endpoint, provide:
- HTTP method and path
- Description
- Parameters (query, path, body)
- Response format
- HTTP status codes
- Error responses
"""
    
    if include_examples:
        prompt += """

## Examples
- Sample requests with curl commands
- Sample responses (success and error cases)
- Code snippets in popular languages (Python, JavaScript, etc.)
"""
    
    prompt += """

## Rate Limiting
- Request limits and windows
- Rate limit headers
- Handling rate limit exceeded

## Best Practices
- Recommended usage patterns
- Performance optimization tips
- Common pitfalls to avoid

Please ensure the documentation is clear, complete, and follows REST API best practices.
"""
    
    return prompt.strip()


# Log startup information
logging.info("StreamableHTTP MCP Server initialized")
logging.info("Available tools: get_weather, calculate_math, generate_password, list_todos")
logging.info("Available resources: config://, docs://, logs://")
logging.info("Available prompts: code-review, api-documentation")
logging.info("Main endpoint: POST /api/mcp")
logging.info("Health check: GET /api/health")
