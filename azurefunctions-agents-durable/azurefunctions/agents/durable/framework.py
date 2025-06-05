"""Core framework for Durable Functions Agents."""

import json
import logging
from typing import Dict, List, Any, Optional, Union
from azure.functions import FunctionApp
import azure.durable_functions as df

from .types import AgentConfig, CallMode
from .call_modes import (
    BaseAgentCaller,
    HttpAgentCaller,
    MCPAgentCaller,
    A2ATaskAgentCaller,
    A2ASyncAgentCaller
)


logger = logging.getLogger(__name__)


class DFAgentFramework:
    """Framework for managing agent calls in Durable Functions."""
    
    def __init__(self, app: Union[FunctionApp, df.DFApp]):
        self.app = app
        self.agents: Dict[str, BaseAgentCaller] = {}
        self._caller_classes = {
            CallMode.HTTP: HttpAgentCaller,
            CallMode.MCP: MCPAgentCaller,
            CallMode.A2A_TASK: A2ATaskAgentCaller,
            CallMode.A2A_SYNC: A2ASyncAgentCaller
        }
    
    def register_agent(self, config: AgentConfig) -> None:
        """Register an agent with the framework."""
        if config.name in self.agents:
            logger.warning(f"Agent '{config.name}' is already registered. Overwriting.")
        
        # Create the appropriate caller based on call mode
        caller_class = self._caller_classes.get(config.call_mode)
        if not caller_class:
            raise ValueError(f"Unsupported call mode: {config.call_mode}")
        
        # Create caller instance
        caller = caller_class(config, self.app)
        
        # Register the caller's activity functions
        caller.register_activities()
        
        # Store the caller
        self.agents[config.name] = caller
        
        logger.info(f"Registered agent '{config.name}' with call mode '{config.call_mode.value}'")
    
    def register_agents_from_config(self, config_data: List[Dict[str, Any]]) -> None:
        """Register multiple agents from configuration data."""
        for agent_data in config_data:
            config = AgentConfig.from_dict(agent_data)
            self.register_agent(config)
    
    def register_agents_from_file(self, config_file_path: str) -> None:
        """Register agents from a JSON configuration file."""
        try:
            with open(config_file_path, 'r') as f:
                config_data = json.load(f)
            
            agents_config = config_data.get("agents", [])
            self.register_agents_from_config(agents_config)
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {config_file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
    
    def get_agent(self, agent_name: str) -> Optional[BaseAgentCaller]:
        """Get a registered agent caller by name."""
        return self.agents.get(agent_name)
    
    def list_agents(self) -> List[str]:
        """List all registered agent names."""
        return list(self.agents.keys())
    
    def create_agent_caller(self) -> "AgentCaller":
        """Create an agent caller for use in orchestrators."""
        return AgentCaller(self)
    
    def create_mcp_client_helper(self, sse_url: str = "http://localhost:7071/runtime/webhooks/mcp/sse"):
        """Create an MCP client helper with the exact prototype pattern from mcp_client.py.
        
        Args:
            sse_url: MCP SSE endpoint URL
            
        Returns:
            MCPClientHelper instance with prototype pattern compatibility
        """
        # Import here to avoid circular imports
        from .call_modes.mcp_caller import MCPClientHelper
        
        # Ensure we have a DFApp for the helper
        if hasattr(self.app, '__class__') and 'DFApp' in str(self.app.__class__):
            return MCPClientHelper(self.app, sse_url)
        else:
            # If we have a FunctionApp, we need to wrap it or convert it
            # For now, assume direct compatibility
            return MCPClientHelper(self.app, sse_url)


class AgentCaller:
    """Agent caller interface for use within orchestrators."""
    def __init__(self, framework: DFAgentFramework):
        self.framework = framework
        
    def call_agent(self, context: df.DurableOrchestrationContext, agent_name: str, method: str, 
                   args: Dict[str, Any] = None, kwargs: Dict[str, Any] = None) -> Any:
        """Call an agent method using the orchestrator context.
        
        Args:
            context: Durable orchestrator context (required for this framework)
            agent_name: Name of the agent to call
            method: Method name to call on the agent
            args: Positional arguments for the method
            kwargs: Keyword arguments for the method
            
        Returns:
            The result from the agent call
            
        Raises:
            ValueError: If the agent is not found
            Exception: If the agent call fails
        """
        agent = self.framework.get_agent(agent_name)
        if not agent:
            raise ValueError(f"Agent '{agent_name}' not found. Available agents: {self.framework.list_agents()}")
        # Use the unified call_agent method with context support
        return agent.call_agent(context, method, args, kwargs)
    
    def call_service(self, context: df.DurableOrchestrationContext, agent_name: str, method: str, 
                    args: Dict[str, Any] = None, kwargs: Dict[str, Any] = None) -> Any:
        """Alias for call_agent - matches MCPClientHelper pattern."""
        return self.call_agent(context, agent_name, method, args, kwargs)
        
    # Orchestrator-compatible convenience methods
    def call_http_agent(self, context: df.DurableOrchestrationContext, agent_name: str, method: str, 
                       args: Dict[str, Any] = None, kwargs: Dict[str, Any] = None) -> Any:
        """Convenience method for calling HTTP agents."""
        return self.call_agent(context, agent_name, method, args, kwargs)
        
    def call_mcp_agent(self, context: df.DurableOrchestrationContext, agent_name: str, method: str, 
                      args: Dict[str, Any] = None, kwargs: Dict[str, Any] = None) -> Any:
        """Convenience method for calling MCP agents."""
        return self.call_agent(context, agent_name, method, args, kwargs)
    
    def call_a2a_task_agent(self, context: df.DurableOrchestrationContext, agent_name: str, method: str, 
                           args: Dict[str, Any] = None, kwargs: Dict[str, Any] = None) -> Any:
        """Convenience method for calling A2A task agents."""
        return self.call_agent(context, agent_name, method, args, kwargs)
    
    def call_a2a_sync_agent(self, context: df.DurableOrchestrationContext, agent_name: str, method: str, 
                           args: Dict[str, Any] = None, kwargs: Dict[str, Any] = None) -> Any:
        """Convenience method for calling A2A sync agents."""
        return self.call_agent(context, agent_name, method, args, kwargs)
        
    # MCP-specific convenience methods
    def list_mcp_tools(self, context: df.DurableOrchestrationContext, agent_name: str) -> Any:
        """List tools available on an MCP agent."""
        return self.call_agent(context, agent_name, "list_tools")
    
    def call_mcp_tool(self, context: df.DurableOrchestrationContext, agent_name: str, tool_name: str, 
                     arguments: Dict[str, Any] = None) -> Any:
        """Call a specific tool on an MCP agent."""
        return self.call_agent(context, agent_name, "call_tool", {"name": tool_name, "arguments": arguments or {}})
    
    def list_mcp_resources(self, context: df.DurableOrchestrationContext, agent_name: str) -> Any:
        """List resources available on an MCP agent."""
        return self.call_agent(context, agent_name, "list_resources")
        
    def read_mcp_resource(self, context: df.DurableOrchestrationContext, agent_name: str, uri: str) -> Any:
        """Read a specific resource from an MCP agent."""
        return self.call_agent(context, agent_name, "read_resource", {"uri": uri})