"""Core AgentFunctionApp class - the main entry point for the agent framework."""

import asyncio
import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Union

from azure.functions import (
    AuthLevel,
    BindingApi,
    FunctionRegister,
    HttpRequest,
    HttpResponse,
    SettingsApi,
    TriggerApi,
)

from .a2a.manager import A2AManager
from .model_providers.client import LLMClient
from .tools.tool_registry import ToolRegistry
from .types import (
    AgentMode,
    ChatMessage,
    LLMConfig,
    LLMProvider,
    MaybeAwaitable,
    MCPConfig,
    MCPServer,
    ToolDefinition,
    ToolFunction,
)


class AgentFunctionApp(FunctionRegister, TriggerApi, BindingApi, SettingsApi):
    """
    Main AgentFunctionApp class for building AI agents as Azure Functions.

    Features:
    - Multiple LLM provider support
    - A2A protocol compliance
    - MCP tool integration
    - Conversational AI capabilities
    - Function calling and tool execution
    """

    def __init__(
        self,
        name: str,
        instructions: Union[str, Callable[[], MaybeAwaitable[str]], None] = None,
        tools: Optional[List[Union[ToolFunction, ToolDefinition]]] = None,
        mcp_servers: Optional[List[Any]] = None,  # Will be properly typed when importing from mcp
        http_auth_level: Union[AuthLevel, str] = AuthLevel.FUNCTION,
        llm_config: Optional[LLMConfig] = None,
        enable_conversational_agent: bool = True,
        mode: AgentMode = AgentMode.AZURE_FUNCTION_AGENT,
        version: str = "1.0.0",
        description: Optional[str] = None,
    ):
        """
        Initialize the AgentFunctionApp.

        Args:
            name: Name of the agent
            instructions: System prompt/instructions for the agent
            tools: List of tools (functions) the agent can use
            mcp_servers: List of MCP servers to integrate with the agent
            http_auth_level: HTTP authentication level for endpoints
            llm_config: Configuration for the LLM provider
            enable_conversational_agent: Enable conversational AI capabilities
            mode: Operating mode (standard or A2A)
            version: Version of the agent
            description: Description of the agent for A2A protocol
        """
        super().__init__(auth_level=http_auth_level)

        # Core properties
        self.name: str = name
        self.instructions: Union[str, Callable[[], MaybeAwaitable[str]], None] = (
            instructions
        )
        self.mode: AgentMode = mode
        self.version: str = version
        self.description: str = description or f"Azure Function Agent: {name}"

        # Tool management
        self.tool_registry = ToolRegistry(MCPConfig())

        # LLM Configuration
        self.llm_config = llm_config
        self.llm_client: Optional[LLMClient] = None
        self.enable_conversational_agent = enable_conversational_agent

        # Only set default LLM config if explicitly requested and environment has API key
        if enable_conversational_agent and not llm_config:
            import os

            if os.getenv("OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_API_KEY"):
                self.llm_config = LLMConfig(
                    provider=LLMProvider.OPENAI,
                    model_name="gpt-4o-mini",
                    temperature=0.7,
                )
            else:
                # Disable conversational agent if no config and no API key
                self.enable_conversational_agent = False

        # MCP Configuration
        self.mcp_servers: List[MCPServer] = mcp_servers or []
        self.mcp_config: MCPConfig = MCPConfig()

        # A2A Protocol support
        self.a2a_manager: Optional[A2AManager] = None
        if self.mode == AgentMode.A2A:
            self.a2a_manager = A2AManager(self)

        # Logger
        self.logger = logging.getLogger(f"AgentFunctionApp.{self.name}")

        # Initialize LLM client if enabled
        if self.enable_conversational_agent and self.llm_config:
            self.llm_client = LLMClient(self.llm_config)

        # Register tools if provided
        self._register_tools(tools or [])

        # Register MCP tools if servers are provided
        if self.mcp_servers:
            self._register_mcp_tools()

        # Auto-register endpoints
        self._register_agent_endpoint()

    def _register_tools(self, tools: List[Union[ToolFunction, ToolDefinition]]):
        """Register tools with the agent."""
        for tool in tools:
            if isinstance(tool, ToolDefinition):
                self.tool_registry.register_function_tool(
                    tool.name,
                    tool.function,
                    tool.description,
                    tool.parameters,
                    tool.required_params,
                )
            elif callable(tool):
                # Convert function to ToolDefinition
                self.tool_registry.register_function_tool(
                    tool.__name__, tool, tool.__doc__ or f"Tool: {tool.__name__}"
                )
            else:
                raise ValueError(f"Invalid tool type: {type(tool)}")

    def _register_mcp_tools(self):
        """Register MCP tools from configured servers."""
        if not self.mcp_servers:
            return
            
        # Start a background task to connect and register MCP tools
        # This allows the agent to start up without waiting for MCP servers
        asyncio.create_task(self._async_register_mcp_tools())
    
    async def _async_register_mcp_tools(self):
        """Asynchronously connect to MCP servers and register their tools."""
        try:
            self.logger.info(f"Connecting to {len(self.mcp_servers)} MCP servers...")
            
            # Register each MCP server with the tool registry
            # The tool registry handles connection and tool discovery
            for server in self.mcp_servers:
                success = await self.tool_registry.add_mcp_server(server)
                if success:
                    self.logger.info(f"Successfully registered MCP server: {server.name}")
                else:
                    self.logger.warning(f"Failed to register MCP server: {server.name}")
            
            self.logger.info("MCP tools registration completed")
            
        except Exception as e:
            self.logger.error(f"Failed to register MCP tools: {e}")

    def tool(
        self,
        func: Optional[ToolFunction] = None,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        required_params: Optional[List[str]] = None,
    ):
        """
        Decorator to register a tool with the agent.

        Can be used as @app.tool or @app.tool(name="custom_name", description="...")

        Args:
            func: The function to decorate (when used without parentheses)
            name: Name of the tool (defaults to function name)
            description: Description of the tool (defaults to function docstring)
            parameters: Parameter schema for the tool
            required_params: List of required parameter names
        """

        def decorator(f: ToolFunction) -> ToolFunction:
            tool_name = name or f.__name__
            tool_description = description or f.__doc__ or f"Tool: {tool_name}"

            # Register the tool
            success = self.tool_registry.register_function_tool(
                tool_name, f, tool_description, parameters, required_params
            )

            if not success:
                self.logger.warning(f"Failed to register tool: {tool_name}")

            return f

        # If func is provided, this was called as @app.tool (without parentheses)
        if func is not None:
            return decorator(func)

        # Otherwise, this was called as @app.tool(...) (with parentheses)
        return decorator

    def _register_agent_endpoint(self):
        """Register the main agent endpoint automatically."""

        @self.route(
            route=f"{self.name.lower()}/{{action?}}",
            auth_level=self._auth_level,
            methods=["GET", "POST"],
        )
        async def agent_endpoint(req: HttpRequest) -> HttpResponse:
            return await self._handle_agent_request(req)

    async def _handle_agent_request(self, req: HttpRequest) -> HttpResponse:
        """Handle requests to the agent endpoint."""
        try:
            action = req.route_params.get("action")

            if req.method == "GET":
                return await self._handle_get_request(action)
            elif req.method == "POST":
                return await self._handle_post_request(req, action)

        except Exception as e:
            self.logger.error(f"Error handling agent request: {str(e)}")
            return HttpResponse(
                json.dumps({"error": f"Internal server error: {str(e)}"}),
                status_code=500,
                headers={"Content-Type": "application/json"},
            )

    async def _handle_get_request(self, action: Optional[str]) -> HttpResponse:
        """Handle GET requests - return agent info."""
        agent_info = {
            "agent": self.name,
            "instructions": await self._get_instructions(),
            "tools": self.tool_registry.list_all_tools(),
            "endpoints": {
                "info": f"GET /api/{self.name.lower()}",
                "invoke": f"POST /api/{self.name.lower()}",
                "tool": f"POST /api/{self.name.lower()}/tool",
            },
        }

        if action:
            agent_info["action"] = action

        return HttpResponse(
            json.dumps(agent_info, indent=2),
            status_code=200,
            headers={"Content-Type": "application/json"},
        )

    async def _handle_post_request(
        self, req: HttpRequest, action: Optional[str]
    ) -> HttpResponse:
        """Handle POST requests - process agent requests."""
        try:
            request_data = req.get_json() or {}
        except ValueError:
            return HttpResponse(
                json.dumps({"error": "Invalid JSON in request body"}),
                status_code=400,
                headers={"Content-Type": "application/json"},
            )

        if action == "tool":
            # Direct tool execution
            return await self._handle_tool_execution(request_data)
        else:
            # General agent processing
            response = await self._process_agent_request(request_data)
            return HttpResponse(
                json.dumps(response, indent=2),
                status_code=200,
                headers={"Content-Type": "application/json"},
            )

    async def _handle_tool_execution(
        self, request_data: Dict[str, Any]
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

        result = await self._execute_tool(tool_name, arguments)
        return HttpResponse(
            json.dumps(result, indent=2),
            status_code=200,
            headers={"Content-Type": "application/json"},
        )

    async def _get_instructions(self) -> str:
        """Get the agent instructions (system prompt)."""
        if self.instructions is None:
            return f"You are {self.name}, an AI agent."

        if isinstance(self.instructions, str):
            return self.instructions

        if callable(self.instructions):
            result = self.instructions()
            if asyncio.iscoroutine(result):
                return await result
            return result

        return str(self.instructions)

    async def _process_agent_request(
        self, request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process an agent request and return response."""

        # Handle different input formats
        messages = request_data.get("messages", [])
        message = request_data.get("message", "")
        tool_calls = request_data.get("tool_calls", [])
        context = request_data.get("context", {})

        # If we have a simple message, convert to messages format
        if message and not messages:
            messages = [{"role": "user", "content": message}]

        # If we have explicit tool calls, process them (legacy mode)
        if tool_calls:
            return await self._process_legacy_tool_calls(message, tool_calls, context)

        # If conversational agent is enabled, use LLM processing
        if self.enable_conversational_agent and self.llm_client and messages:
            return await self._process_conversational_request(messages, context)

        # Fallback to basic response
        return {
            "agent": self.name,
            "message": message,
            "instructions": await self._get_instructions(),
            "tool_results": [],
            "context": context,
            "response": "Hello! I'm an agent but I need conversational AI capabilities to be enabled to process your request properly.",
        }

    async def _process_legacy_tool_calls(
        self, message: str, tool_calls: List[Dict], context: Dict
    ) -> Dict[str, Any]:
        """Process explicit tool calls (legacy mode)."""
        response = {
            "agent": self.name,
            "message": message,
            "instructions": await self._get_instructions(),
            "tool_results": [],
            "context": context,
        }

        # Process tool calls if any
        for tool_call in tool_calls:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("arguments", {})

            if tool_name:
                result = await self._execute_tool(tool_name, tool_args)
                response["tool_results"].append({"tool": tool_name, **result})

        return response

    async def _process_conversational_request(
        self, messages: List[Dict], context: Dict
    ) -> Dict[str, Any]:
        """Process a conversational request using LLM."""
        try:
            # Convert messages to ChatMessage format
            chat_messages = []

            # Add system message with instructions
            instructions = await self._get_instructions()
            chat_messages.append(ChatMessage(role="system", content=instructions))

            # Add conversation messages
            for msg in messages:
                chat_messages.append(
                    ChatMessage(
                        role=msg.get("role", "user"),
                        content=msg.get("content", ""),
                        tool_calls=msg.get("tool_calls"),
                        tool_call_id=msg.get("tool_call_id"),
                    )
                )

            # Prepare tools for LLM
            tools_schema = self.tool_registry.get_tools_for_llm()

            # Get LLM response
            llm_response = await self.llm_client.chat_completion(
                messages=chat_messages,
                tools=tools_schema if tools_schema else None,
                tool_choice="auto" if tools_schema else None,
            )

            response_message = llm_response["message"]
            tool_results = []

            # If LLM wants to call tools, execute them and get final response
            if hasattr(response_message, "tool_calls") and response_message.tool_calls:
                # Add the assistant's message with tool calls to conversation
                chat_messages.append(
                    ChatMessage(
                        role="assistant",
                        content=response_message.content,
                        tool_calls=[
                            {
                                "id": tc.id,
                                "type": tc.type,
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in response_message.tool_calls
                        ],
                    )
                )

                # Process tool calls
                for tool_call in response_message.tool_calls:
                    if tool_call.type == "function":
                        function_call = tool_call.function
                        tool_name = function_call.name

                        try:
                            # Parse arguments
                            arguments = (
                                json.loads(function_call.arguments)
                                if function_call.arguments
                                else {}
                            )

                            # Execute tool
                            self.logger.info(f"Executing function tool: {tool_name}")
                            tool_result = await self.tool_registry.execute_tool(
                                tool_name, arguments
                            )

                            # Add tool result to conversation
                            chat_messages.append(
                                ChatMessage(
                                    role="tool",
                                    content=json.dumps(
                                        tool_result.get("result", tool_result)
                                    ),
                                    tool_call_id=tool_call.id,
                                    name=tool_name,
                                )
                            )

                            tool_results.append(
                                {
                                    "tool_call_id": tool_call.id,
                                    "tool": tool_name,
                                    "arguments": arguments,
                                    **tool_result,
                                }
                            )

                        except Exception as e:
                            self.logger.error(f"Tool execution failed: {e}")
                            # Add error result to conversation
                            chat_messages.append(
                                ChatMessage(
                                    role="tool",
                                    content=f"Error: {str(e)}",
                                    tool_call_id=tool_call.id,
                                    name=tool_name,
                                )
                            )

                            tool_results.append(
                                {
                                    "tool_call_id": tool_call.id,
                                    "tool": tool_name,
                                    "error": str(e),
                                    "status": "error",
                                }
                            )

                # Get final response from LLM after tool execution
                final_response = await self.llm_client.chat_completion(
                    messages=chat_messages,
                    tools=tools_schema if tools_schema else None,
                    tool_choice="auto" if tools_schema else None,
                )

                response_message = final_response["message"]

            # Safely serialize usage information
            usage = llm_response.get("usage")
            usage_dict = None
            if usage:
                try:
                    # Convert usage object to dict, handling nested objects
                    usage_dict = {
                        "prompt_tokens": getattr(usage, "prompt_tokens", None),
                        "completion_tokens": getattr(usage, "completion_tokens", None),
                        "total_tokens": getattr(usage, "total_tokens", None),
                    }
                except Exception:
                    # If serialization fails, just omit usage info
                    usage_dict = None

            return {
                "agent": self.name,
                "response": (
                    response_message.content
                    if hasattr(response_message, "content")
                    else str(response_message)
                ),
                "tool_results": tool_results,
                "context": context,
                "usage": usage_dict,
                "finish_reason": llm_response.get("finish_reason"),
            }

        except Exception as e:
            self.logger.error(f"Conversational processing failed: {e}")
            return {
                "agent": self.name,
                "error": f"Failed to process conversational request: {str(e)}",
                "context": context,
                "status": "error",
            }

    async def _execute_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool with the given arguments."""
        try:
            result = await self.tool_registry.execute_tool(tool_name, arguments)
            return {"result": result, "status": "success"}
        except KeyError:
            return {"error": f"Tool '{tool_name}' not found", "status": "error"}
        except Exception as e:
            self.logger.error(f"Tool execution failed for {tool_name}: {str(e)}")
            return {"error": str(e), "status": "error"}

    def _prepare_tools_schema(self) -> Optional[List[Dict[str, Any]]]:
        """Prepare tools schema for LLM function calling."""
        return self.tool_registry.get_tools_for_llm()

    # Tool and MCP management methods
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        tools = self.tool_registry.list_all_tools()
        return [tool.get("name", "") for tool in tools if tool.get("name")]

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Get tool information by name."""
        return self.tool_registry.get_tool_info(name)

    def add_mcp_server(self, server: MCPServer):
        """Add an MCP server to the agent."""
        self.mcp_servers.append(server)

    def remove_mcp_server(self, server: MCPServer):
        """Remove an MCP server from the agent."""
        if server in self.mcp_servers:
            self.mcp_servers.remove(server)

    # LLM configuration methods
    def set_llm_config(self, config: LLMConfig):
        """Update the LLM configuration and reinitialize the client."""
        self.llm_config = config
        if self.enable_conversational_agent:
            self.llm_client = LLMClient(config)

    async def initialize_llm(self):
        """Manually initialize the LLM client."""
        if self.llm_client:
            await self.llm_client.initialize()

    @property
    def model(self) -> Optional[LLMClient]:
        """Expose the LLM model for advanced use cases."""
        return self.llm_client
