#!/usr/bin/env python3
"""
Example: Google AI (Gemini) Integration

This example demonstrates how to use Google's Gemini models
with the Azure Functions Agent Framework.

Installation:
pip install "azurefunctions-agents-framework[google]"

Environment Variables:
# For Google AI Studio (API Key)
GOOGLE_API_KEY=your_google_api_key

# For Vertex AI (Project-based)
GOOGLE_CLOUD_PROJECT=your_project_id
GOOGLE_CLOUD_LOCATION=us-central1
"""

from azurefunctions.agents import Agent, AgentFunctionApp, LLMConfig, LLMProvider

# Create agent with Google Gemini configuration
agent = Agent(
    name="gemini_assistant",
    instructions="You are Gemini, Google's advanced AI assistant. You are helpful, creative, and capable of understanding complex queries. Provide accurate and helpful responses.",
    description="Gemini AI assistant powered by Google",
    llm_config=LLMConfig(
        provider=LLMProvider.GOOGLE,
        model_name="gemini-1.5-pro",  # or "gemini-1.5-flash", "gemini-1.0-pro"
        temperature=0.7,
        max_tokens=2048,
    ),
)


# Add some tools
@agent.tool
def calculate_math(expression: str):
    """Calculate mathematical expressions safely."""
    try:
        # Simple safe evaluation for demo purposes
        result = eval(expression.replace("^", "**"))
        return f"Result: {expression} = {result}"
    except:
        return f"Error: Could not evaluate '{expression}'. Please use basic mathematical operations."


@agent.tool
def get_weather_info(location: str):
    """Get weather information for a location (mock implementation)."""
    return f"Weather in {location}: 72°F, Sunny with light clouds. Humidity: 45%"


@agent.tool
def translate_text(text: str, target_language: str):
    """Translate text to another language (mock implementation)."""
    return f"Translated '{text}' to {target_language}: [Mock translation - use real translation service]"


@agent.tool
def generate_image_prompt(description: str):
    """Generate a detailed prompt for image generation based on a description."""
    return f"Enhanced image prompt: A high-quality, detailed image of {description}, with professional lighting, sharp focus, and artistic composition."


# Create the function app
app = AgentFunctionApp(agents={"gemini_assistant": agent})

# Example usage in tests or local development
if __name__ == "__main__":
    print("Google Gemini agent created successfully!")
    print(f"Agent: {agent.name}")
    print(
        f"Model: {agent.llm_config.model_name if agent.llm_config else 'No LLM configured'}"
    )
    print(
        f"Provider: {agent.llm_config.provider.value if agent.llm_config else 'No provider'}"
    )
    print(f"Tools: {[tool['name'] for tool in agent.tool_registry.list_all_tools()]}")

    # Test if Google GenAI is available
    try:
        print("✓ Google GenAI package is installed")
    except ImportError:
        print("⚠️  Google GenAI package not installed. Install with:")
        print('pip install "azurefunctions-agents-framework[google]"')

    print("\nEndpoints available:")
    print("POST /api/gemini_assistant/chat - Chat with Gemini")
    print("GET /api/gemini_assistant/info - Get agent information")

    print("\nExample requests:")
    print("# Text generation")
    print("curl -X POST http://localhost:7071/api/gemini_assistant/chat \\")
    print('  -H "Content-Type: application/json" \\')
    print(
        '  -d \'{"message": "Write a creative story about a robot learning to paint."}\'\n'
    )

    print("# Math calculation")
    print("curl -X POST http://localhost:7071/api/gemini_assistant/chat \\")
    print('  -H "Content-Type: application/json" \\')
    print('  -d \'{"message": "Can you calculate 15 * 23 + 45 for me?"}\'\n')

    print("# Image prompt generation")
    print("curl -X POST http://localhost:7071/api/gemini_assistant/chat \\")
    print('  -H "Content-Type: application/json" \\')
    print(
        '  -d \'{"message": "Generate an image prompt for a sunset over mountains."}\''
    )
