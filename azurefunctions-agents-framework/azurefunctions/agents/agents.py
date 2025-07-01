# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Agent classes for the Azure Functions Agent Framework."""

import asyncio
import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Union

from .model_providers.client import LLMClient
from .tools.tool_registry import ToolRegistry
from .types import (
    ChatMessage,
    LLMConfig,
    LLMProvider,
    MaybeAwaitable,
    MCPConfig,
    MCPServer,
    ToolDefinition,
    ToolFunction,
)


class Agent:
    """
    Core Agent class - represents a single AI agent with its configuration and capabilities.

    This class handles:
    - Agent configuration and metadata
    - Tool management and execution
    - LLM integration
    - MCP server integration

    This separation allows for specialized agent types like Reflection Agents,
    Multi-step reasoning agents, etc.
    """

    def __init__(
        self,
        name: str,
        instructions: Union[str, Callable[[], MaybeAwaitable[str]], None] = None,
        tools: Optional[List[Union[ToolFunction, ToolDefinition]]] = None,
        mcp_servers: Optional[List[Any]] = None,
        llm_config: Optional[LLMConfig] = None,
        enable_conversational_agent: bool = True,
        version: str = "1.0.0",
        description: Optional[str] = None,
        expose_agent_info: bool = True,
        expose_instructions: bool = True,
        expose_tools: bool = True,
    ):
        """
        Initialize an Agent.

        Args:
            name: Name of the agent
            instructions: System prompt/instructions for the agent
            tools: List of tools (functions) the agent can use
            mcp_servers: List of MCP servers to integrate with the agent
            llm_config: Configuration for the LLM provider
            enable_conversational_agent: Enable conversational AI capabilities
            version: Version of the agent
            description: Description of the agent
            expose_agent_info: Whether to expose agent information via GET endpoints
            expose_instructions: Whether to expose agent instructions via GET endpoints
            expose_tools: Whether to expose tool information via GET endpoints
        """
        # Basic agent configuration
        self.name = name
        self.instructions = instructions
        self.version = version
        self.description = description or f"AI Agent: {name}"
        self.enable_conversational_agent = enable_conversational_agent

        # Privacy/Security settings
        self.expose_agent_info = expose_agent_info
        self.expose_instructions = expose_instructions
        self.expose_tools = expose_tools

        # Logger
        self.logger = logging.getLogger(f"Agent.{name}")

        # LLM Configuration
        self.llm_config = llm_config
        if not llm_config and enable_conversational_agent:
            # Try to auto-detect LLM configuration
            auto_config = self._auto_detect_llm_config()
            if auto_config:
                self.llm_config = auto_config
            else:
                self.logger.warning(
                    f"Agent '{name}' has conversational capabilities enabled but no LLM configuration provided. "
                    "The agent will not be able to process conversational requests."
                )

        if enable_conversational_agent and not llm_config:
            raise ValueError(
                f"Agent '{name}' requires LLM configuration when enable_conversational_agent=True. "
                "Please provide llm_config or set enable_conversational_agent=False."
            )

        # Tool Registry - handles both function tools and MCP tools
        self.tool_registry = ToolRegistry()

        # MCP Configuration
        self.mcp_servers: List[MCPServer] = mcp_servers or []
        self.mcp_config: MCPConfig = MCPConfig()

        # Initialize LLM client if enabled
        if self.enable_conversational_agent and self.llm_config:
            self.llm_client = LLMClient(self.llm_config)
        else:
            self.llm_client = None

        # Register tools if provided
        self._register_tools(tools or [])

        # Mark MCP tools for registration if servers are provided
        self._mcp_tools_registered = False
        self._mcp_registration_needed = bool(self.mcp_servers)
        if self.mcp_servers:
            self.logger.info(
                f"Agent '{name}' will register {len(self.mcp_servers)} MCP servers"
            )

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
        if not self.mcp_servers or self._mcp_tools_registered:
            return

        # Check if we have a running event loop
        try:
            loop = asyncio.get_running_loop()
            # Schedule MCP registration as a task
            loop.create_task(self._async_register_mcp_tools())
        except RuntimeError:
            self.logger.info(
                "No event loop running, MCP tools will be registered when needed"
            )

    async def _async_register_mcp_tools(self):
        """Asynchronously connect to MCP servers and register their tools."""
        try:
            for server in self.mcp_servers:
                self.logger.info(f"Connecting to MCP server: {server.name}")
                await server.connect()
                tools = await server.list_tools()
                for tool in tools:
                    self.tool_registry.register_mcp_tool(server, tool)
                self.logger.info(
                    f"Registered {len(tools)} tools from MCP server: {server.name}"
                )

            self._mcp_tools_registered = True
            self._mcp_registration_needed = False
            self.logger.info(
                f"Successfully registered MCP tools for agent '{self.name}'"
            )

        except Exception as e:
            self.logger.error(
                f"Failed to register MCP tools for agent '{self.name}': {e}"
            )
            # Don't raise here - agent should still function without MCP tools

    async def _ensure_mcp_tools_registered(self):
        """Ensure MCP tools are registered if we have an event loop and they're not already registered."""
        if not self.mcp_servers or self._mcp_tools_registered:
            return

        # If registration is needed, do it now
        if self._mcp_registration_needed:
            await self._async_register_mcp_tools()

    def _try_sync_mcp_registration(self):
        """Try to register MCP tools synchronously if possible."""
        if (
            not self.mcp_servers
            or self._mcp_tools_registered
            or not self._mcp_registration_needed
        ):
            return

        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, schedule registration
            loop.create_task(self._async_register_mcp_tools())
        except RuntimeError:
            # No event loop, can't register synchronously
            pass

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

        Can be used as @agent.tool or @agent.tool(name="custom_name", description="...")

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
                self.logger.warning(
                    f"Failed to register tool '{tool_name}' for agent '{self.name}'"
                )

            return f

        # If func is provided, this was called as @agent.tool (without parentheses)
        if func is not None:
            return decorator(func)

        # Otherwise, this was called as @agent.tool(...) (with parentheses)
        return decorator

    async def get_agent_info(self) -> Dict[str, Any]:
        """Get agent information respecting privacy settings."""
        # Check if agent info exposure is disabled
        if not self.expose_agent_info:
            return {
                "error": "Agent information is not available",
                "message": "This agent has disabled information exposure for security reasons",
            }

        # Build response based on what's allowed to be exposed
        agent_info = {
            "agent": self.name,
            "version": self.version,
            "description": self.description,
        }

        # Only include instructions if allowed
        if self.expose_instructions:
            agent_info["instructions"] = await self._get_instructions()

        # Only include tools if allowed
        if self.expose_tools:
            agent_info["tools"] = self.tool_registry.list_all_tools()

        # Always include endpoints info (this is generally safe)
        agent_info["endpoints"] = {
            "info": f"GET /api/agents/{self.name}/actions",
            "invoke": f"POST /api/agents/{self.name}/actions",
        }

        return agent_info

    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
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

    async def _get_instructions(self) -> str:
        """Get the agent instructions (system prompt)."""
        if self.instructions is None:
            return f"You are {self.name}, an AI agent."

        if isinstance(self.instructions, str):
            return self.instructions

        if callable(self.instructions):
            result = self.instructions()
            if asyncio.iscoroutine(result):
                result = await result
            return result

        return str(self.instructions)

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
                tool_result = await self._execute_tool(tool_name, tool_args)
                response["tool_results"].append(
                    {"tool": tool_name, "arguments": tool_args, "result": tool_result}
                )

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
                        role=msg.get("role", "user"), content=msg.get("content", "")
                    )
                )

            # Ensure MCP tools are registered before preparing tools
            await self._ensure_mcp_tools_registered()

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
                # Add the assistant's message with tool calls (convert to ChatMessage format)
                chat_messages.append(
                    ChatMessage(
                        role="assistant",
                        content=response_message.content or "",
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
                    tool_result = await self.tool_registry.execute_tool(
                        tool_call.function.name,
                        (
                            json.loads(tool_call.function.arguments)
                            if tool_call.function.arguments
                            else {}
                        ),
                    )
                    tool_results.append(
                        {"tool": tool_call.function.name, "result": tool_result}
                    )

                    # Add tool result message
                    chat_messages.append(
                        ChatMessage(
                            role="tool",
                            content=json.dumps(tool_result),
                            tool_call_id=tool_call.id,
                        )
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
                    usage_dict = (
                        usage.model_dump()
                        if hasattr(usage, "model_dump")
                        else dict(usage)
                    )
                except Exception:
                    usage_dict = {"total_tokens": getattr(usage, "total_tokens", 0)}

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
            # Ensure MCP tools are registered before executing
            await self._ensure_mcp_tools_registered()

            result = await self.tool_registry.execute_tool(tool_name, arguments)
            return {"result": result, "status": "success"}
        except KeyError:
            return {"error": f"Tool '{tool_name}' not found", "status": "error"}
        except Exception as e:
            self.logger.error(f"Tool execution failed for {tool_name}: {str(e)}")
            return {"error": str(e), "status": "error"}

    # Tool and MCP management methods
    def list_tools(self) -> List[str]:
        """List all registered tool names."""
        # Try to register MCP tools synchronously if we have an event loop
        self._try_sync_mcp_registration()

        tools = self.tool_registry.list_all_tools()
        return [tool.get("name", "") for tool in tools if tool.get("name")]

    def list_tools_details(self) -> Dict[str, Any]:
        """List all registered tool details."""
        # Try to register MCP tools synchronously if we have an event loop
        self._try_sync_mcp_registration()

        return self.tool_registry.list_all_tools()

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

    def _auto_detect_llm_config(self) -> Optional[LLMConfig]:
        """
        Auto-detect LLM configuration based on available environment variables.

        Priority order:
        1. Azure OpenAI (if both endpoint and API key are available)
        2. OpenAI (if API key is available)

        Returns:
            LLMConfig if a provider can be configured, None otherwise
        """
        # Check for Azure OpenAI first (more specific)
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")

        if azure_endpoint and azure_api_key:
            self.logger.info("Auto-detected Azure OpenAI configuration")
            return LLMConfig(
                provider=LLMProvider.AZURE_OPENAI,
                model_name="gpt-4o-mini",  # Default model
                azure_endpoint=azure_endpoint,
                api_key=azure_api_key,
                api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
                azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                temperature=0.7,
            )

        # Check for standard OpenAI
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if openai_api_key:
            self.logger.info("Auto-detected OpenAI configuration")
            return LLMConfig(
                provider=LLMProvider.OPENAI,
                model_name="gpt-4o-mini",  # Default model
                api_key=openai_api_key,
                organization=os.getenv("OPENAI_ORG_ID"),
                temperature=0.7,
            )

        # No suitable provider found
        self.logger.warning(
            "No LLM provider configuration could be auto-detected. Set OPENAI_API_KEY or AZURE_OPENAI_ENDPOINT+AZURE_OPENAI_API_KEY environment variables."
        )
        return None

    # Privacy/Security configuration methods
    def configure_privacy(
        self,
        expose_agent_info: Optional[bool] = None,
        expose_instructions: Optional[bool] = None,
        expose_tools: Optional[bool] = None,
    ):
        """
        Configure what information is exposed via GET endpoints.

        Args:
            expose_agent_info: Whether to expose any agent information (overrides other settings)
            expose_instructions: Whether to expose agent instructions
            expose_tools: Whether to expose tool information
        """
        if expose_agent_info is not None:
            self.expose_agent_info = expose_agent_info
        if expose_instructions is not None:
            self.expose_instructions = expose_instructions
        if expose_tools is not None:
            self.expose_tools = expose_tools

    def disable_info_exposure(self):
        """Disable all information exposure via GET endpoints for maximum security."""
        self.expose_agent_info = False
        self.expose_instructions = False
        self.expose_tools = False

    def enable_info_exposure(self):
        """Enable all information exposure via GET endpoints (default behavior)."""
        self.expose_agent_info = True
        self.expose_instructions = True
        self.expose_tools = True

    def expose_only_endpoints(self):
        """Expose only endpoint information, hiding instructions and tools."""
        self.expose_agent_info = True
        self.expose_instructions = False
        self.expose_tools = False

    @property
    def model(self) -> Optional[LLMClient]:
        """Expose the LLM model for advanced use cases."""
        return self.llm_client


class ReflectionAgent(Agent):
    """
    Specialized agent that implements reflection and self-correction patterns.

    This agent type demonstrates how the new architecture enables advanced agent patterns:
    - Evaluator-optimizer pattern
    - Self-correction loops
    - Multi-step reasoning with reflection
    - Quality assessment and improvement iterations

    The ReflectionAgent enhances responses through iterative reflection and improvement.
    """

    def __init__(
        self,
        name: str,
        instructions: Union[str, Callable[[], MaybeAwaitable[str]], None] = None,
        tools: Optional[List[Union[ToolFunction, ToolDefinition]]] = None,
        mcp_servers: Optional[List[Any]] = None,
        llm_config: Optional[LLMConfig] = None,
        enable_conversational_agent: bool = True,
        version: str = "1.0.0",
        description: Optional[str] = None,
        expose_agent_info: bool = True,
        expose_instructions: bool = True,
        expose_tools: bool = True,
        # Reflection-specific parameters
        max_reflection_iterations: int = 3,
        reflection_threshold: float = 0.8,
        enable_self_evaluation: bool = True,
        evaluation_prompt: Optional[str] = None,
        evaluation_function: Optional[Callable] = None,
    ):
        """
        Initialize a ReflectionAgent.

        Args:
            max_reflection_iterations: Maximum number of reflection iterations
            reflection_threshold: Quality threshold to stop reflection (0.0-1.0)
            enable_self_evaluation: Whether to perform self-evaluation of responses
            evaluation_prompt: Custom evaluation prompt template for quality assessment
            evaluation_function: Custom function for evaluating response quality
            ... (other args inherited from Agent)
        """
        super().__init__(
            name=name,
            instructions=instructions,
            tools=tools,
            mcp_servers=mcp_servers,
            llm_config=llm_config,
            enable_conversational_agent=enable_conversational_agent,
            version=version,
            description=description or f"Reflection Agent: {name}",
            expose_agent_info=expose_agent_info,
            expose_instructions=expose_instructions,
            expose_tools=expose_tools,
        )

        # Reflection configuration
        self.max_reflection_iterations = max_reflection_iterations
        self.reflection_threshold = reflection_threshold
        self.enable_self_evaluation = enable_self_evaluation
        self.evaluation_prompt = evaluation_prompt
        self.evaluation_function = evaluation_function

        # Reflection tracking
        self.reflection_history: List[Dict[str, Any]] = []

        self.logger.info(
            f"Initialized ReflectionAgent with max_iterations={max_reflection_iterations}, threshold={reflection_threshold}"
        )

    async def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process request with reflection and self-correction.

        This method enhances the base agent processing with:
        1. Initial response generation
        2. Self-evaluation of response quality
        3. Iterative reflection and improvement
        4. Final quality assessment
        """
        # Get initial response from base agent
        initial_response = await super().process_request(request_data)

        if not self.enable_self_evaluation or not self.enable_conversational_agent:
            # Return basic response if reflection is disabled
            return initial_response

        try:
            # Perform reflection and improvement
            improved_response = await self._reflect_and_improve(
                request_data, initial_response
            )

            # Add reflection metadata
            improved_response["reflection"] = {
                "iterations_performed": len(self.reflection_history),
                "final_quality_score": improved_response.get("quality_score"),
                "improvement_applied": len(self.reflection_history) > 0,
                "reflection_history": self.reflection_history.copy(),
            }

            # Clear history for next request
            self.reflection_history.clear()

            return improved_response

        except Exception as e:
            self.logger.error(f"Reflection process failed: {e}")
            # Return original response if reflection fails
            initial_response["reflection_error"] = str(e)
            return initial_response

    async def _reflect_and_improve(
        self, original_request: Dict[str, Any], current_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform iterative reflection and improvement on the response.
        """
        best_response = current_response.copy()
        best_quality = 0.0

        for iteration in range(self.max_reflection_iterations):
            self.logger.info(f"Starting reflection iteration {iteration + 1}")

            # Evaluate current response quality
            quality_score = await self._evaluate_response_quality(
                original_request, best_response
            )

            # Record this iteration
            iteration_record = {
                "iteration": iteration + 1,
                "quality_score": quality_score,
                "response_preview": (
                    best_response.get("response", "")[:100] + "..."
                    if len(best_response.get("response", "")) > 100
                    else best_response.get("response", "")
                ),
            }

            # Check if we've reached the quality threshold
            if quality_score >= self.reflection_threshold:
                iteration_record["stopped_reason"] = "quality_threshold_reached"
                self.reflection_history.append(iteration_record)
                self.logger.info(
                    f"Quality threshold reached: {quality_score:.2f} >= {self.reflection_threshold}"
                )
                break

            # Generate reflection and improvements
            reflection_result = await self._generate_reflection(
                original_request, best_response, quality_score
            )

            if reflection_result.get("improvements"):
                # Apply improvements to generate better response
                improved_response = await self._apply_improvements(
                    original_request, best_response, reflection_result["improvements"]
                )

                # Check if the improved response is actually better
                improved_quality = await self._evaluate_response_quality(
                    original_request, improved_response
                )

                if improved_quality > best_quality:
                    best_response = improved_response
                    best_quality = improved_quality
                    iteration_record["improvement_applied"] = True
                    iteration_record["improved_quality"] = improved_quality
                else:
                    iteration_record["improvement_applied"] = False
                    iteration_record["reason"] = "improvement_did_not_increase_quality"
            else:
                iteration_record["improvement_applied"] = False
                iteration_record["reason"] = "no_improvements_suggested"

            self.reflection_history.append(iteration_record)

            # Stop if no meaningful improvement is possible
            if not reflection_result.get("improvements"):
                break

        # Add final quality score to response
        best_response["quality_score"] = best_quality
        return best_response

    async def _evaluate_response_quality(
        self, original_request: Dict[str, Any], response: Dict[str, Any]
    ) -> float:
        """
        Evaluate the quality of a response using custom evaluation logic.

        Returns a quality score between 0.0 and 1.0.
        """
        # If custom evaluation function is provided, use it
        if self.evaluation_function:
            try:
                user_message = original_request.get("message", "")
                if not user_message and original_request.get("messages"):
                    for msg in reversed(original_request["messages"]):
                        if msg.get("role") == "user":
                            user_message = msg.get("content", "")
                            break

                agent_response = response.get("response", "")

                # Call custom evaluation function
                result = self.evaluation_function(
                    user_message, agent_response, original_request, response
                )

                # Handle both sync and async evaluation functions
                if hasattr(result, "__await__"):
                    result = await result

                # Convert result to float if needed
                if isinstance(result, (int, float)):
                    return max(0.0, min(1.0, float(result)))
                elif isinstance(result, dict) and "score" in result:
                    return max(0.0, min(1.0, float(result["score"])))
                else:
                    self.logger.warning(
                        f"Custom evaluation function returned unexpected type: {type(result)}"
                    )
                    return 0.5

            except Exception as e:
                self.logger.error(f"Custom evaluation function failed: {e}")
                return 0.5

        # If no LLM client available, return default
        if not self.llm_client:
            return 0.5  # Default neutral score if no LLM available

        try:
            user_message = original_request.get("message", "")
            if not user_message and original_request.get("messages"):
                # Extract last user message
                for msg in reversed(original_request["messages"]):
                    if msg.get("role") == "user":
                        user_message = msg.get("content", "")
                        break

            agent_response = response.get("response", "")

            # Use custom evaluation prompt if provided, otherwise use default
            if self.evaluation_prompt:
                evaluation_prompt = self.evaluation_prompt.format(
                    user_request=user_message,
                    agent_response=agent_response,
                    user_message=user_message,  # Alternative variable name
                    response=agent_response,  # Alternative variable name
                )
            else:
                # Default evaluation prompt template following the PASS/FAIL pattern
                evaluation_prompt = f"""
You are an expert evaluator assessing whether an AI agent's response meets the user's requirements.

The user requested: {user_message}

The generated output is: {agent_response}

Evaluation Question: Does the generated output really do what the user needed?

Assess the response based on:
1. Does it directly address the user's request?
2. Is the information accurate and reliable?
3. Is the response complete and sufficient?
4. Is it clear and well-structured?
5. Does it provide practical value to the user?

Respond with either:
- PASS (if the response adequately meets the user's needs)
- FAIL (if the response is inadequate or doesn't address the request)

Then provide specific feedback explaining your decision.

Format your response as:
STATUS: [PASS/FAIL]
FEEDBACK: [Your detailed explanation]

For scoring purposes:
- PASS responses should score 1.0
- FAIL responses should score 0.6 or lower
- Respond with the numeric score on the last line: SCORE: [0.0-1.0]
"""

            evaluation_response = await self.llm_client.chat_completion(
                messages=[ChatMessage(role="user", content=evaluation_prompt)],
                tools=None,
                tool_choice=None,
            )

            # Extract quality score from response
            response_text = evaluation_response["message"].content.strip()

            # Try to parse the new PASS/FAIL format first
            try:
                if "STATUS:" in response_text and "SCORE:" in response_text:
                    # New structured format
                    score_line = [
                        line
                        for line in response_text.split("\n")
                        if line.strip().startswith("SCORE:")
                    ]
                    if score_line:
                        score_text = score_line[0].split("SCORE:")[1].strip()
                        quality_score = float(score_text)
                        return max(0.0, min(1.0, quality_score))

                # Check for PASS/FAIL keywords if SCORE not found
                if "PASS" in response_text.upper():
                    return 1.0  # PASS = high quality
                elif "FAIL" in response_text.upper():
                    return 0.6  # FAIL = needs improvement

                # Fallback: try to parse as a plain number
                quality_score = float(response_text)
                return max(0.0, min(1.0, quality_score))

            except ValueError:
                self.logger.warning(
                    f"Could not parse quality score from: {response_text}"
                )
                return 0.5

        except Exception as e:
            self.logger.error(f"Quality evaluation failed: {e}")
            return 0.5

    async def _generate_reflection(
        self,
        original_request: Dict[str, Any],
        current_response: Dict[str, Any],
        quality_score: float,
    ) -> Dict[str, Any]:
        """
        Generate reflection and improvement suggestions for the current response.
        """
        if not self.llm_client:
            return {"improvements": []}

        try:
            user_message = original_request.get("message", "")
            if not user_message and original_request.get("messages"):
                for msg in reversed(original_request["messages"]):
                    if msg.get("role") == "user":
                        user_message = msg.get("content", "")
                        break

            agent_response = current_response.get("response", "")

            reflection_prompt = f"""
You are a reflection expert helping to improve AI agent responses.

User Request: {user_message}

Current Agent Response: {agent_response}

Current Quality Score: {quality_score:.2f}/1.0

Analyze this response and provide specific, actionable improvements. Consider:
1. What aspects could be enhanced or clarified?
2. What information might be missing?
3. How could the structure or presentation be improved?
4. Are there any errors or inaccuracies to correct?

Respond in JSON format:
{{
    "analysis": "Your detailed analysis of the current response",
    "improvements": [
        "Specific improvement 1",
        "Specific improvement 2",
        "..."
    ],
    "priority": "high|medium|low"
}}
"""

            reflection_response = await self.llm_client.chat_completion(
                messages=[ChatMessage(role="user", content=reflection_prompt)],
                tools=None,
                tool_choice=None,
            )

            # Parse reflection result
            reflection_text = reflection_response["message"].content.strip()
            try:
                reflection_data = json.loads(reflection_text)
                return reflection_data
            except json.JSONDecodeError:
                self.logger.warning("Could not parse reflection response as JSON")
                return {"improvements": []}

        except Exception as e:
            self.logger.error(f"Reflection generation failed: {e}")
            return {"improvements": []}

    async def _apply_improvements(
        self,
        original_request: Dict[str, Any],
        current_response: Dict[str, Any],
        improvements: List[str],
    ) -> Dict[str, Any]:
        """
        Apply improvement suggestions to generate a better response.
        """
        if not self.llm_client or not improvements:
            return current_response

        try:
            user_message = original_request.get("message", "")
            if not user_message and original_request.get("messages"):
                for msg in reversed(original_request["messages"]):
                    if msg.get("role") == "user":
                        user_message = msg.get("content", "")
                        break

            current_response_text = current_response.get("response", "")
            improvements_text = "\n".join(f"- {imp}" for imp in improvements)

            improvement_prompt = f"""
You are tasked with improving an AI agent response based on specific feedback.

Original User Request: {user_message}

Current Response: {current_response_text}

Improvement Suggestions:
{improvements_text}

Please provide an improved version of the response that addresses these suggestions while maintaining the core helpfulness and accuracy. Make the response better, more complete, and more valuable to the user.

Respond with only the improved response text.
"""

            improved_response = await self.llm_client.chat_completion(
                messages=[ChatMessage(role="user", content=improvement_prompt)],
                tools=None,
                tool_choice=None,
            )

            # Create improved response object
            new_response = current_response.copy()
            new_response["response"] = improved_response["message"].content.strip()
            new_response["improved"] = True
            new_response["applied_improvements"] = improvements

            return new_response

        except Exception as e:
            self.logger.error(f"Improvement application failed: {e}")
            return current_response

    # Override tool decorator to add reflection capabilities
    def tool(
        self,
        func: Optional[ToolFunction] = None,
        *,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        required_params: Optional[List[str]] = None,
        enable_reflection: bool = True,
    ):
        """
        Enhanced tool decorator that can apply reflection to tool results.

        Args:
            enable_reflection: Whether to apply reflection to this tool's results
            ... (other args inherited from Agent.tool)
        """
        return super().tool(
            func,
            name=name,
            description=description,
            parameters=parameters,
            required_params=required_params,
        )

    def configure_reflection(
        self,
        max_iterations: Optional[int] = None,
        quality_threshold: Optional[float] = None,
        enable_evaluation: Optional[bool] = None,
        evaluation_prompt: Optional[str] = None,
        evaluation_function: Optional[Callable] = None,
    ):
        """
        Configure reflection parameters.

        Args:
            max_iterations: Maximum number of reflection iterations
            quality_threshold: Quality threshold to stop reflection (0.0-1.0)
            enable_evaluation: Whether to perform self-evaluation
            evaluation_prompt: Custom evaluation prompt template
            evaluation_function: Custom function for evaluating response quality
        """
        if max_iterations is not None:
            self.max_reflection_iterations = max_iterations
        if quality_threshold is not None:
            self.reflection_threshold = max(0.0, min(1.0, quality_threshold))
        if enable_evaluation is not None:
            self.enable_self_evaluation = enable_evaluation
        if evaluation_prompt is not None:
            self.evaluation_prompt = evaluation_prompt
        if evaluation_function is not None:
            self.evaluation_function = evaluation_function

        self.logger.info(
            f"Updated reflection config: max_iterations={self.max_reflection_iterations}, "
            f"threshold={self.reflection_threshold}, evaluation={self.enable_self_evaluation}"
        )

    def get_reflection_stats(self) -> Dict[str, Any]:
        """Get statistics about recent reflection operations."""
        if not self.reflection_history:
            return {"message": "No recent reflection data available"}

        return {
            "last_reflection": {
                "iterations": len(self.reflection_history),
                "final_quality": (
                    self.reflection_history[-1].get("quality_score")
                    if self.reflection_history
                    else None
                ),
                "improvements_applied": sum(
                    1
                    for r in self.reflection_history
                    if r.get("improvement_applied", False)
                ),
            },
            "configuration": {
                "max_iterations": self.max_reflection_iterations,
                "quality_threshold": self.reflection_threshold,
                "evaluation_enabled": self.enable_self_evaluation,
            },
        }
