"""Azure Functions Agents Durable Package.

This package provides a framework for calling agents from Durable Functions orchestrators
without needing explicit activity triggers. It supports multiple communication modes
including HTTP, MCP (Model Context Protocol), and Agent-to-Agent communication.

Key Features:
- Activity trigger-less notation for orchestrators
- Support for HTTP, MCP, A2A_TASK, and A2A_SYNC call modes
- Enhanced MCP support with both stdio and SSE clients
- Decorator-based framework for easy integration
- Configuration-driven agent management

Example Usage:
    from azure.functions import FunctionApp
    from azurefunctions.agents.durable import DFAgentFramework, orchestrator, AgentConfig, CallMode
    
    app = FunctionApp()
    framework = DFAgentFramework(app)
    
    # Register agents
    framework.register_agent(AgentConfig(
        name="my_mcp_agent",
        call_mode=CallMode.MCP,
        client_type="stdio",
        extra_config={
            "command": "python",
            "args": ["-m", "my_mcp_server"]
        }
    ))
    
    @orchestrator(framework)
    async def my_orchestrator(context, agents):
        tools = await agents.list_mcp_tools("my_mcp_agent")
        result = await agents.call_mcp_tool("my_mcp_agent", "my_tool", {"arg": "value"})
        return result
"""

from .types import CallMode, AgentConfig, AgentCallRequest, AgentCallResponse
from .framework import DFAgentFramework, AgentCaller
from .decorators import orchestrator, activity_with_agent_support, register_orchestrator_with_agents
from .call_modes import (
    BaseAgentCaller,
    HttpAgentCaller,
    MCPAgentCaller,
    A2ATaskAgentCaller,
    A2ASyncAgentCaller
)
from .call_modes.mcp_caller import MCPClientHelper

__version__ = "0.1.0"

__all__ = [
    # Core types
    "CallMode",
    "AgentConfig", 
    "AgentCallRequest",
    "AgentCallResponse",
    
    # Framework classes
    "DFAgentFramework",
    "AgentCaller",
    
    # Decorators
    "orchestrator",
    "activity_with_agent_support", 
    "register_orchestrator_with_agents",
    
    # MCP Helper
    "MCPClientHelper",
    "MCPAgentCaller",
    
    # Caller implementations
    "BaseAgentCaller",
    "HttpAgentCaller",
    "MCPAgentCaller", 
    "A2ATaskAgentCaller",
    "A2ASyncAgentCaller",
]