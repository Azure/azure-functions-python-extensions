# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Core Azure Functions integration for the Agent Framework."""

import asyncio
import json
import logging
import os
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

if TYPE_CHECKING:
    from .a2a.manager import A2AManager

from azure.functions import (
    AuthLevel,
    BindingApi,
    FunctionRegister,
    HttpRequest,
    HttpResponse,
    SettingsApi,
    TriggerApi,
)

from .agents import Agent, ReflectionAgent
from .handoff import ControlFlowManager, HandoffEngine
from .model_providers.client import LLMClient
from .runner import Runner
from .tools.tool_registry import ToolRegistry
from .types import (
    AgentMode,
    ChatMessage,
    ChatResponse,
    LLMConfig,
    LLMProvider,
    MaybeAwaitable,
    MCPConfig,
    MCPServer,
    Response,
    ToolDefinition,
    ToolFunction,
)


class AgentFunctionApp(FunctionRegister, TriggerApi, BindingApi, SettingsApi):
    """
    Azure Function App that hosts AI agents with clean HTTP endpoints.

    This class manages the Azure Functions infrastructure and routes requests
    to appropriate agents. It supports both single-agent and multi-agent architectures,
    as well as A2A (Agent-to-Agent) protocol compliance.

    Features:
    - Unified routing pattern for single and multi-agent deployments
    - Clean, predictable API endpoints
    - HTTP authentication and routing
    - A2A protocol support with specification compliance
    - Custom triggers mode (create_triggers=False) for manual integration

    API Endpoints:

    Standard Mode (AZURE_FUNCTION_AGENT):
    - POST /api/agents/{agent_name}/chat - Chat with any agent
    - GET /api/agents/{agent_name}/info - Get agent information
    - GET /api/agents - List all available agents
    - GET /api/health - System health check

    A2A Mode (A2A):
    - POST {agent_url} - JSON-RPC 2.0 endpoint (A2A spec compliance)
    - GET /.well-known/agent.json - Agent Card discovery (A2A spec compliance) 
    - GET /api/agents - List all available agents
    - GET /api/health - System health check
    """

    def __init__(
        self,
        agents: Union[Dict[str, Agent], List[Agent]],
        mode: AgentMode = AgentMode.AZURE_FUNCTION_AGENT,
        http_auth_level: Union[AuthLevel, str] = AuthLevel.FUNCTION,
        create_triggers: bool = True,
    ):
        """
        Initialize the AgentFunctionApp.

        Args:
            agents: Either a dictionary of agent_name -> Agent instances, or a list of Agent instances
                   If a list is provided, agent names will be taken from Agent.name property
            mode: Operating mode (AZURE_FUNCTION_AGENT or A2A)
            http_auth_level: HTTP authentication level for endpoints
            create_triggers: Whether to automatically create HTTP trigger endpoints.
                           Set to False when using custom triggers or manual integration.
        """
        super().__init__(auth_level=http_auth_level)

        # Convert list to dict if needed, using agent.name as keys
        if isinstance(agents, list):
            if not agents:
                raise ValueError("Must provide at least one agent")

            # Check for duplicate names
            agent_names = [agent.name for agent in agents]
            if len(agent_names) != len(set(agent_names)):
                duplicates = [
                    name for name in agent_names if agent_names.count(name) > 1
                ]
                raise ValueError(f"Duplicate agent names found: {duplicates}")

            # Convert to dict using agent.name as key
            agents_dict = {agent.name: agent for agent in agents}
        elif isinstance(agents, dict):
            if not agents:
                raise ValueError(
                    "Must provide 'agents' dictionary with at least one agent"
                )
            agents_dict = agents.copy()
        else:
            raise ValueError("agents must be either a Dict[str, Agent] or List[Agent]")

        # Validate A2A mode constraints
        if mode == AgentMode.A2A and len(agents_dict) > 1:
            raise ValueError(
                "A2A mode is only supported for single-agent apps. Use AZURE_FUNCTION_AGENT mode for multi-agent apps."
            )

        self.agents: Dict[str, Agent] = agents_dict
        self.mode: AgentMode = mode
        self.create_triggers: bool = create_triggers
        self.logger = logging.getLogger("AgentFunctionApp")

        # Initialize handoff system for multi-agent support
        self.control_flow_manager = ControlFlowManager()
        self.handoff_engine = HandoffEngine(self.control_flow_manager)
        self.handoff_engine.register_agents(self.agents)
        
        # Set agent registry on all agents for handoff tools
        for agent in self.agents.values():
            agent.set_agent_registry(self.agents)
        
        # Create runners for each agent with handoff engine
        self.runners: Dict[str, Runner] = {
            agent.name: Runner(agent, self.handoff_engine) for agent in self.agents.values()
        }
        
        # Register all runners with each other for handoff operations
        for runner_name, runner in self.runners.items():
            for other_name, other_runner in self.runners.items():
                if runner_name != other_name:
                    runner.register_runner(other_name, other_runner)

        # Initialize A2A manager if in A2A mode
        self.a2a_manager: Optional["A2AManager"] = None
        if self.mode == AgentMode.A2A:
            from .a2a.manager import A2AManager

            self.a2a_manager = A2AManager(self)
        
        # Start control flow cleanup task
        self.control_flow_manager.start_cleanup_task()

        self.logger.info(
            f"Initialized AgentFunctionApp in {mode.value} mode with {len(self.agents)} agent(s): {list(self.agents.keys())}"
        )

        # Register endpoints only if create_triggers is True
        if self.create_triggers:
            self._register_endpoints()
        else:
            self.logger.info(
                "Skipping HTTP trigger creation (create_triggers=False). Use manual integration or custom triggers."
            )

    def _register_endpoints(self):
        """Register HTTP endpoints with unified routing for all modes."""
        if self.mode == AgentMode.A2A:
            self._register_a2a_endpoints()
        else:
            # Use unified routing for both single and multi-agent modes
            self._register_unified_endpoints()

    def _register_a2a_endpoints(self):
        """Register A2A protocol endpoints for single-agent A2A mode.
        
        Note: Current implementation provides HTTP endpoints for compatibility.
        True A2A compliance requires JSON-RPC 2.0 methods like message/send, 
        tasks/get, etc. posted to a single endpoint. This is handled by A2AManager.
        """
        # A2A endpoints are registered by the A2AManager
        # Standard agent endpoints are still available for compatibility
        agent_name = next(iter(self.agents.keys()))

        @self.route(
            route=f"{agent_name}/chat",
            auth_level=self._auth_level,
            methods=["POST"],
        )
        async def agent_chat(req: HttpRequest) -> HttpResponse:
            """Chat with the agent."""
            agent = next(iter(self.agents.values()))
            return await self._handle_chat_request(agent, req)

        @self.route(
            route=f"{agent_name}/info",
            auth_level=self._auth_level,
            methods=["GET"],
        )
        async def agent_info(req: HttpRequest) -> HttpResponse:
            """Get agent information."""
            agent = next(iter(self.agents.values()))
            return await self._handle_info_request(agent)

        @self.route(
            route="agents",
            auth_level=self._auth_level,
            methods=["GET"],
        )
        async def list_agents_endpoint(req: HttpRequest) -> HttpResponse:
            """List all available agents."""
            return await self._handle_list_agents()

        @self.route(
            route="health",
            auth_level=self._auth_level,
            methods=["GET"],
        )
        async def health_check(req: HttpRequest) -> HttpResponse:
            """Health check endpoint."""
            return await self._handle_health_check()

        self.logger.info(
            f"Registered A2A endpoints with unified routing for agent: {agent_name}"
        )

    def _register_unified_endpoints(self):
        """Register unified endpoints that work for both single and multi-agent modes."""

        @self.route(
            route="agents/{agent_name}/chat",
            auth_level=self._auth_level,
            methods=["POST"],
        )
        async def agent_chat(req: HttpRequest) -> HttpResponse:
            """Chat with a specific agent."""
            agent_name = req.route_params.get("agent_name")

            if not agent_name or agent_name not in self.agents:
                return self._dict_to_http(
                    {
                        "error": f"Agent '{agent_name}' not found",
                        "available_agents": list(self.agents.keys()),
                    },
                    status_code=404,
                )

            agent = self.agents[agent_name]
            return await self._handle_chat_request(agent, req)

        @self.route(
            route="agents/{agent_name}/info",
            auth_level=self._auth_level,
            methods=["GET"],
        )
        async def agent_info(req: HttpRequest) -> HttpResponse:
            """Get information about a specific agent."""
            agent_name = req.route_params.get("agent_name")

            if not agent_name or agent_name not in self.agents:
                return self._dict_to_http(
                    {
                        "error": f"Agent '{agent_name}' not found",
                        "available_agents": list(self.agents.keys()),
                    },
                    status_code=404,
                )

            agent = self.agents[agent_name]
            return await self._handle_info_request(agent)

        @self.route(
            route="agents",
            auth_level=self._auth_level,
            methods=["GET"],
        )
        async def list_agents_endpoint(req: HttpRequest) -> HttpResponse:
            """List all available agents."""
            return await self._handle_list_agents()

        @self.route(
            route="health",
            auth_level=self._auth_level,
            methods=["GET"],
        )
        async def health_check(req: HttpRequest) -> HttpResponse:
            """Health check endpoint."""
            return await self._handle_health_check()

        mode_description = "single-agent" if len(self.agents) == 1 else "multi-agent"
        self.logger.info(
            f"Registered unified endpoints for {mode_description} mode with {len(self.agents)} agent(s): {list(self.agents.keys())}"
        )

    # Legacy handler methods removed - only clean endpoints are supported now

    async def _handle_tool_execution(
        self, agent: Agent, request_data: Dict[str, Any]
    ) -> HttpResponse:
        """Handle direct tool execution."""
        tool_name = request_data.get("tool")
        arguments = request_data.get("arguments", {})

        if not tool_name:
            return HttpResponse(
                json.dumps({"error": "Tool name is required"}),
                status_code=400,
                headers={"Content-Type": "application/json"},
            )

        result = await agent._execute_tool(tool_name, arguments)
        return HttpResponse(
            json.dumps(result, indent=2),
            status_code=200,
            headers={"Content-Type": "application/json"},
        )

    async def _handle_chat_request(
        self, agent: Agent, req: HttpRequest
    ) -> HttpResponse:
        """Handle chat requests for both single and multi-agent modes."""
        try:
            request_data = req.get_json() or {}
        except ValueError:
            return self._dict_to_http(
                {"error": "Invalid JSON in request body"}, status_code=400
            )

        # Handle both simple message format and OpenAI messages format
        if "messages" not in request_data and "message" not in request_data:
            return self._dict_to_http(
                {
                    "error": "Either 'message' or 'messages' is required",
                    "examples": {
                        "simple": {"message": "Hello, how are you?"},
                        "openai": {
                            "messages": [
                                {"role": "user", "content": "Hello, how are you?"}
                            ]
                        },
                    },
                },
                status_code=400,
            )

        try:
            # Use the Runner to process the request
            # Since we now key runners by agent.name, we can access directly
            runner = self.runners[agent.name]
            response = await runner.run(request_data)

            # Convert Response object to HttpResponse
            return self._response_to_http(response, agent_name=agent.name)

        except Exception as e:
            self.logger.error(f"Error processing chat request: {e}")
            error_response = ChatResponse(
                status="error", error=f"Failed to process chat request: {str(e)}"
            )
            return self._response_to_http(error_response, status_code=500)

    async def _handle_info_request(self, agent: Agent) -> HttpResponse:
        """Handle info requests for single agent mode."""
        try:
            agent_info = await agent.get_agent_info()
            return self._dict_to_http(agent_info)
        except Exception as e:
            self.logger.error(f"Error getting agent info: {str(e)}")
            return self._dict_to_http(
                {"error": "Failed to get agent info", "message": str(e)},
                status_code=500,
            )

    async def _handle_health_check(self) -> HttpResponse:
        """Handle health check requests."""
        try:
            health_info = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "mode": self.mode.value,
                "agents": {
                    "total": len(self.agents),
                    "names": list(self.agents.keys()),
                },
                "endpoints": {
                    "chat": "/api/agents/{agent_name}/chat",
                    "info": "/api/agents/{agent_name}/info",
                    "list": "/api/agents",
                    "health": "/api/health",
                },
            }
            return self._dict_to_http(health_info)
        except Exception as e:
            self.logger.error(f"Error in health check: {str(e)}")
            return self._dict_to_http(
                {
                    "status": "unhealthy",
                    "timestamp": datetime.utcnow().isoformat(),
                    "error": str(e),
                },
                status_code=500,
            )

    async def _handle_list_agents(self) -> HttpResponse:
        """Handle listing all agents in multi-agent mode."""
        try:
            agents_info = []
            for agent_name, agent in self.agents.items():
                try:
                    info = await agent.get_agent_info()
                    agents_info.append(
                        {
                            "name": agent_name,
                            "description": info.get("description", ""),
                            "version": info.get("version", "1.0.0"),
                            "tools_count": len(info.get("tools", [])),
                            "endpoints": {"chat": f"/api/agents/{agent_name}/chat"},
                        }
                    )
                except Exception as e:
                    self.logger.warning(
                        f"Error getting info for agent {agent_name}: {e}"
                    )
                    agents_info.append(
                        {
                            "name": agent_name,
                            "description": "Error retrieving info",
                            "error": str(e),
                        }
                    )

            return HttpResponse(
                json.dumps({"agents": agents_info, "total": len(agents_info)}),
                status_code=200,
                headers={"Content-Type": "application/json"},
            )
        except Exception as e:
            self.logger.error(f"Error listing agents: {str(e)}")
            return HttpResponse(
                json.dumps({"error": "Failed to list agents", "message": str(e)}),
                status_code=500,
                headers={"Content-Type": "application/json"},
            )

    # Agent management methods
    def add_agent(self, agent: Agent) -> bool:
        """Add an agent to the function app."""
        if agent.name in self.agents:
            self.logger.warning(f"Agent '{agent.name}' already exists, overriding")

        self.agents[agent.name] = agent
        self.logger.info(f"Added agent: {agent.name}")
        return True

    def remove_agent(self, agent_name: str) -> bool:
        """Remove an agent from the function app."""
        if agent_name in self.agents:
            del self.agents[agent_name]
            self.logger.info(f"Removed agent: {agent_name}")
            return True
        return False

    def get_agent(self, agent_name: str) -> Optional[Agent]:
        """Get an agent by name."""
        return self.agents.get(agent_name)

    def list_agents(self) -> List[str]:
        """List all agent names."""
        return list(self.agents.keys())

    # Manual integration helpers for custom triggers
    def get_runner(self, agent_name: str) -> Runner:
        """
        Get a runner for a specific agent.

        This method is useful when create_triggers=False and you want to
        integrate agent processing into your own custom triggers.

        Args:
            agent_name: Name of the agent

        Returns:
            Runner instance for the agent

        Raises:
            KeyError: If agent_name is not found
        """
        if agent_name not in self.runners:
            available_agents = list(self.runners.keys())
            raise KeyError(
                f"Agent '{agent_name}' not found. Available agents: {available_agents}"
            )

        return self.runners[agent_name]

    def get_single_runner(self) -> Runner:
        """
        Get the runner for the single agent (only works in single-agent mode).

        This is a convenience method for single-agent setups where you don't
        need to specify the agent name.

        Returns:
            Runner instance for the single agent

        Raises:
            ValueError: If not in single-agent mode
        """
        if len(self.runners) != 1:
            raise ValueError("get_single_runner only works in single-agent mode")

        return next(iter(self.runners.values()))

    def _response_to_http(
        self,
        response: Response,
        agent_name: Optional[str] = None,
        status_code: int = 200,
    ) -> HttpResponse:
        """
        Convert agent Response to Azure Functions HttpResponse.

        This is the only place in the framework that handles HTTP/Azure Functions logic.

        Args:
            response: Response object from agent processing
            agent_name: Name of the agent that generated the response
            status_code: HTTP status code

        Returns:
            Azure Functions HttpResponse
        """
        response_dict = response.to_dict()

        # Add agent metadata if provided
        if agent_name:
            response_dict["agent"] = agent_name

        # Add timestamp
        response_dict["timestamp"] = datetime.utcnow().isoformat()

        # For error responses, use appropriate status code
        if response_dict.get("status") == "error" or response_dict.get("error"):
            status_code = 500 if status_code == 200 else status_code

        return HttpResponse(
            json.dumps(response_dict),
            status_code=status_code,
            headers={"Content-Type": "application/json"},
        )

    def _dict_to_http(
        self, data: Dict[str, Any], status_code: int = 200
    ) -> HttpResponse:
        """
        Convert dictionary to Azure Functions HttpResponse.

        Utility method for non-agent responses like errors and info.

        Args:
            data: Dictionary to convert
            status_code: HTTP status code

        Returns:
            Azure Functions HttpResponse
        """
        return HttpResponse(
            json.dumps(data),
            status_code=status_code,
            headers={"Content-Type": "application/json"},
        )
