#!/usr/bin/env python3
"""
Example: Anthropic Claude Integration

This example demonstrates how to use Anthropic's Claude models
with the Azure Functions Agent Framework.

Installation:
pip install "azurefunctions-agents-framework[anthropic]"

Environment Variables:
ANTHROPIC_API_KEY=your_anthropic_api_key
"""

from azurefunctions.agents import Agent, AgentFunctionApp, LLMConfig, LLMProvider

# Create agent with Anthropic Claude configuration
agent = Agent(
    name="claude_assistant",
    instructions="You are Claude, a helpful AI assistant created by Anthropic. You are knowledgeable, thoughtful, and aim to be helpful while being honest about your limitations.",
    description="Claude AI assistant powered by Anthropic",
    llm_config=LLMConfig(
        provider=LLMProvider.ANTHROPIC,
        model_name="claude-3-sonnet-20240229",  # or "claude-3-haiku-20240307", "claude-3-opus-20240229"
        temperature=0.7,
        max_tokens=4096,
    ),
)


# Add some tools
@agent.tool
def search_web(query: str):
    """Search the web for information (mock implementation)."""
    return f"Search results for '{query}': Mock search results..."


@agent.tool
def analyze_text(text: str):
    """Analyze text for sentiment, key topics, or other insights."""
    return f"Analysis of text: '{text[:50]}...' - This is a mock analysis."


@agent.tool
def write_code(language: str, description: str):
    """Write code in a specified programming language."""
    return f"Generated {language} code for: {description}\n# Mock code implementation\nprint('Hello, World!')"


# Create the function app
app = AgentFunctionApp(agents={"claude_assistant": agent})

# Example usage in tests or local development
if __name__ == "__main__":
    print("Anthropic Claude agent created successfully!")
    print(f"Agent: {agent.name}")
    print(
        f"Model: {agent.llm_config.model_name if agent.llm_config else 'No LLM configured'}"
    )
    print(
        f"Provider: {agent.llm_config.provider.value if agent.llm_config else 'No provider'}"
    )
    print(f"Tools: {[tool['name'] for tool in agent.tool_registry.list_all_tools()]}")

    # Test if Anthropic is available
    try:
        print("✓ Anthropic package is installed")
    except ImportError:
        print("⚠️  Anthropic package not installed. Install with:")
        print('pip install "azurefunctions-agents-framework[anthropic]"')

    print("\nEndpoints available:")
    print("POST /api/claude_assistant/chat - Chat with Claude")
    print("GET /api/claude_assistant/info - Get agent information")

    print("\nExample request:")
    print("curl -X POST http://localhost:7071/api/claude_assistant/chat \\")
    print('  -H "Content-Type: application/json" \\')
    print(
        '  -d \'{"message": "Hello Claude! Can you help me write a Python function to calculate fibonacci numbers?"}\''
    )
