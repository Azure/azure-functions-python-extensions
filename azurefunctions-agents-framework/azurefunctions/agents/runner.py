import asyncio
import json
from typing import Any, Dict, List, Optional, Union

from .types import ChatRequest, ChatResponse, MessageRequest, Request, Response

# Type alias for request data - supporting both old and new abstractions
RequestInput = Union[str, Dict[str, Any], MessageRequest, Request]


class Runner:
    """
    Complete agent execution abstraction for running agents programmatically.

    This is the primary interface for executing agents. It provides a clean
    abstraction layer between user code and agent implementation, supporting
    both async and sync execution with flexible input/output types.

    The Runner is framework-agnostic and does not contain any HTTP or Azure
    Functions specific logic. For Azure Functions integration, use AgentFunctionApp.
    """

    def __init__(self, agent):
        """
        Initialize the runner with an agent.

        Args:
            agent: The Agent instance to run
        """
        self.agent = agent

    async def run(self, request: RequestInput) -> Response:
        """
        Run the agent with the provided request asynchronously.

        Args:
            request: Can be:
                - str: Simple message string
                - dict: Full request dictionary with message, context, etc.
                - MessageRequest: Legacy structured request object
                - Request: Abstract request object (e.g., ChatRequest)

        Returns:
            Response object (e.g., ChatResponse) containing agent response

        Raises:
            ValueError: If request format is invalid
        """
        request_data = self._normalize_request(request)
        response_data = await self.agent.process_request(request_data)
        return self._create_response(response_data)

    def run_sync(self, request: RequestInput) -> Response:
        """
        Run the agent with the provided request synchronously.

        Args:
            request: Can be:
                - str: Simple message string
                - dict: Full request dictionary with message, context, etc.
                - MessageRequest: Legacy structured request object
                - Request: Abstract request object (e.g., ChatRequest)

        Returns:
            Response object (e.g., ChatResponse) containing agent response

        Raises:
            ValueError: If request format is invalid
        """
        try:
            # Try to get the existing event loop
            loop = asyncio.get_running_loop()
            # If there's already a running loop, we need to use a different approach
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.run(request))
                return future.result()
        except RuntimeError:
            # No running event loop, we can create a new one
            return asyncio.run(self.run(request))

    def _normalize_request(self, request: RequestInput) -> Dict[str, Any]:
        """
        Normalize different request formats into a standard dictionary.

        Args:
            request: Request in various formats

        Returns:
            Normalized request dictionary

        Raises:
            ValueError: If request format is invalid
        """
        if isinstance(request, str):
            return {"message": request}
        elif isinstance(request, (MessageRequest, Request)):
            return request.to_dict()
        elif isinstance(request, dict):
            return request
        else:
            raise ValueError(
                f"Request must be a string, dict, MessageRequest, or Request object, got {type(request)}"
            )

    def _create_response(self, response_data: Dict[str, Any]) -> Response:
        """
        Create a Response object from agent response data.

        Args:
            response_data: Raw response data from agent

        Returns:
            Structured Response object
        """
        # For now, we default to ChatResponse, but this could be made configurable
        # based on agent type or request type in the future
        return ChatResponse(
            response=response_data.get("response"),
            messages=response_data.get("messages"),
            context=response_data.get("context"),
            tool_calls=response_data.get("tool_calls"),
            metadata=response_data.get("metadata"),
            status=response_data.get("status", "success"),
            error=response_data.get("error"),
        )

    async def get_agent_info(self) -> Dict[str, Any]:
        """
        Get information about the agent this runner manages.

        Returns:
            Agent information dictionary
        """
        return await self.agent.get_agent_info()

    def get_agent_info_sync(self) -> Dict[str, Any]:
        """
        Get information about the agent this runner manages (synchronous).

        Returns:
            Agent information dictionary
        """
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.get_agent_info())
                return future.result()
        except RuntimeError:
            return asyncio.run(self.get_agent_info())

    def create_chat_request(
        self,
        message: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        context: Optional[Dict[str, Any]] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> ChatRequest:
        """
        Create a structured ChatRequest object.

        This is a convenience method for building structured requests.

        Args:
            message: Simple message string
            messages: OpenAI-style messages array
            context: Additional context data
            tool_calls: Explicit tool calls (legacy mode)
            user_id: User identifier
            session_id: Session identifier

        Returns:
            ChatRequest object that can be passed to run()
        """
        return ChatRequest(
            message=message,
            messages=messages,
            context=context,
            tool_calls=tool_calls,
            user_id=user_id,
            session_id=session_id,
        )

    def create_message_request(
        self,
        message: Optional[str] = None,
        messages: Optional[List[Dict[str, str]]] = None,
        context: Optional[Dict[str, Any]] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> MessageRequest:
        """
        Create a structured MessageRequest object.

        DEPRECATED: Use create_chat_request() instead.
        This is a convenience method for building structured requests.

        Args:
            message: Simple message string
            messages: OpenAI-style messages array
            context: Additional context data
            tool_calls: Explicit tool calls (legacy mode)

        Returns:
            MessageRequest object that can be passed to run()
        """
        return MessageRequest(
            message=message, messages=messages, context=context, tool_calls=tool_calls
        )

    @property
    def agent_name(self) -> str:
        """Get the name of the agent this runner manages."""
        return self.agent.name

    def __repr__(self) -> str:
        """String representation of the runner."""
        return f"Runner(agent='{self.agent.name}')"
