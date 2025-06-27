#!/usr/bin/env python3
"""
SSE MCP Server Example

This is a sample MCP server that provides tools via Server-Sent Events (SSE).
It demonstrates how to create a simple MCP server that can be used with
Azure Functions agents.

The server provides several example tools:
- add: Add two numbers
- get_secret_word: Get a random secret word
- get_current_weather: Get weather information for a city (using wttr.in)

To run this server:
    python server.py

The server will be available at http://localhost:8000/sse
"""

import random
import sys
from typing import Any, Dict

import requests

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("Error: FastMCP not installed. Please install with: pip install mcp")
    sys.exit(1)

# Create MCP server
mcp = FastMCP("Demo SSE Server")


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers together.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        The sum of a and b
    """
    print(f"[server] add({a}, {b}) = {a + b}")
    return a + b


@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers together.
    
    Args:
        a: First number
        b: Second number
        
    Returns:
        The product of a and b
    """
    result = a * b
    print(f"[server] multiply({a}, {b}) = {result}")
    return result


@mcp.tool()
def get_secret_word() -> str:
    """Get a random secret word from a predefined list.
    
    Returns:
        A random secret word
    """
    words = ["azure", "functions", "agent", "python", "mcp", "server", "integration"]
    word = random.choice(words)
    print(f"[server] get_secret_word() = {word}")
    return word


@mcp.tool()
def get_current_weather(city: str) -> str:
    """Get current weather information for a city.
    
    Args:
        city: Name of the city to get weather for
        
    Returns:
        Weather information as text
    """
    print(f"[server] get_current_weather({city})")
    
    try:
        # Use wttr.in for weather data (free service, no API key required)
        endpoint = "https://wttr.in"
        response = requests.get(f"{endpoint}/{city}?format=3", timeout=10)
        response.raise_for_status()
        
        weather_info = response.text.strip()
        print(f"[server] Weather for {city}: {weather_info}")
        return weather_info
        
    except requests.RequestException as e:
        error_msg = f"Failed to get weather for {city}: {str(e)}"
        print(f"[server] Error: {error_msg}")
        return error_msg


@mcp.tool()
def calculate_factorial(n: int) -> int:
    """Calculate the factorial of a number.
    
    Args:
        n: The number to calculate factorial for (must be non-negative)
        
    Returns:
        The factorial of n
    """
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    
    if n == 0 or n == 1:
        result = 1
    else:
        result = 1
        for i in range(2, n + 1):
            result *= i
    
    print(f"[server] calculate_factorial({n}) = {result}")
    return result


@mcp.tool()
def generate_uuid() -> str:
    """Generate a random UUID.
    
    Returns:
        A random UUID string
    """
    import uuid
    new_uuid = str(uuid.uuid4())
    print(f"[server] generate_uuid() = {new_uuid}")
    return new_uuid


@mcp.tool()
def get_system_info() -> Dict[str, Any]:
    """Get basic system information.
    
    Returns:
        Dictionary containing system information
    """
    import platform
    import datetime
    
    info = {
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "server_time": datetime.datetime.now().isoformat(),
    }
    
    print(f"[server] get_system_info() = {info}")
    return info


if __name__ == "__main__":
    print("Starting SSE MCP Server...")
    print("Available tools:")
    print("  - add(a, b): Add two numbers")
    print("  - multiply(a, b): Multiply two numbers") 
    print("  - get_secret_word(): Get a random secret word")
    print("  - get_current_weather(city): Get weather for a city")
    print("  - calculate_factorial(n): Calculate factorial of a number")
    print("  - generate_uuid(): Generate a random UUID")
    print("  - get_system_info(): Get system information")
    print()
    print("Server will be available at: http://localhost:8000/sse")
    print("Press Ctrl+C to stop the server")
    
    try:
        mcp.run(transport="sse", port=8000)
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except Exception as e:
        print(f"Error starting server: {e}")
        print("Make sure port 8000 is available and mcp package is installed correctly.")
