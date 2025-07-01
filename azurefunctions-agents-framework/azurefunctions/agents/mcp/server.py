# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""MCP Server implementations for Azure Functions Agent Framework.

Based on the OpenAI agents SDK MCP implementation but adapted for Azure Functions.
Provides a unified MCPServer class with configurable communication modes.
"""

from __future__ import annotations

import abc
import asyncio
import logging
from contextlib import AbstractAsyncContextManager, AsyncExitStack
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream
from mcp import ClientSession, StdioServerParameters
from mcp import Tool as MCPTool
from mcp import stdio_client
from mcp.client.sse import sse_client
from mcp.client.streamable_http import GetSessionIdCallback, streamablehttp_client
from mcp.shared.message import SessionMessage
from mcp.types import CallToolResult, InitializeResult
from typing_extensions import NotRequired, TypedDict

from ..types import MCPServerMode

# Setup logger
logger = logging.getLogger(__name__)


class AgentError(Exception):
    """Base exception for agent-related errors."""

    pass


class UserError(AgentError):
    """Error raised due to user configuration or input issues."""

    pass


# Parameter types for different MCP server modes
class MCPServerStdioParams(TypedDict):
    """Parameters for STDIO mode MCP server."""

    command: str
    """The executable to run to start the server. For example, `python` or `node`."""

    args: NotRequired[List[str]]
    """Command line args to pass to the `command` executable."""

    env: NotRequired[Optional[Dict[str, str]]]
    """The environment variables to set for the server."""

    cwd: NotRequired[Optional[str | Path]]
    """The working directory to use when spawning the process."""

    encoding: NotRequired[str]
    """The text encoding used when sending/receiving messages. Defaults to `utf-8`."""

    encoding_error_handler: NotRequired[Literal["strict", "ignore", "replace"]]
    """The text encoding error handler. Defaults to `strict`."""


class MCPServerSseParams(TypedDict):
    """Parameters for SSE mode MCP server."""

    url: str
    """The URL for the SSE endpoint."""

    headers: NotRequired[Optional[Dict[str, str]]]
    """Headers to include in the request."""

    timeout: NotRequired[float]
    """Connection timeout in seconds."""

    sse_read_timeout: NotRequired[float]
    """SSE read timeout in seconds."""


class MCPServerStreamableHttpParams(TypedDict):
    """Parameters for Streamable HTTP mode MCP server."""

    session_url: str
    """The base URL for the MCP server's session endpoint."""

    get_session_id: NotRequired[Optional[GetSessionIdCallback]]
    """Function to retrieve the session ID."""

    headers: NotRequired[Optional[Dict[str, str]]]
    """Headers to include in requests."""

    timeout: NotRequired[float]
    """Connection timeout in seconds."""


class MCPServer:
    """Unified MCP server that supports multiple communication modes.

    This replaces the previous MCPServerStdio, MCPServerSse, and MCPServerStreamableHttp
    classes with a single, configurable server class.
    """

    def __init__(
        self,
        name: str,
        mode: MCPServerMode,
        params: Union[
            MCPServerStdioParams, MCPServerSseParams, MCPServerStreamableHttpParams
        ],
        cache_tools_list: bool = False,
        client_session_timeout_seconds: Optional[float] = 5.0,
    ):
        """Create a new MCP server.

        Args:
            name: A readable name for the server.
            mode: The communication mode to use (STDIO, SSE, or STREAMABLE_HTTP).
            params: Mode-specific parameters. Use:
                - MCPServerStdioParams for STDIO mode
                - MCPServerSseParams for SSE mode
                - MCPServerStreamableHttpParams for STREAMABLE_HTTP mode
            cache_tools_list: Whether to cache the tools list for performance.
            client_session_timeout_seconds: The read timeout for the MCP ClientSession.
        """
        self._name = name
        self.mode = mode
        self.params = params
        self.cache_tools_list = cache_tools_list
        self.client_session_timeout_seconds = client_session_timeout_seconds

        # Validate that params match the mode
        self._validate_params_for_mode(mode, params)

        self.session: Optional[ClientSession] = None
        self._cleanup_context: Optional[AbstractAsyncContextManager] = None
        self._tools_cache: Optional[List[MCPTool]] = None

    @property
    def name(self) -> str:
        """A readable name for the server."""
        return self._name

    def _validate_params_for_mode(
        self,
        mode: MCPServerMode,
        params: Union[
            MCPServerStdioParams, MCPServerSseParams, MCPServerStreamableHttpParams
        ],
    ) -> None:
        """Validate that the params are appropriate for the given mode."""
        if mode == MCPServerMode.STDIO:
            # Check that required STDIO parameters are present
            if not isinstance(params, dict) or "command" not in params:
                raise ValueError(
                    "STDIO mode requires MCPServerStdioParams with 'command' parameter"
                )

        elif mode == MCPServerMode.SSE:
            # Check that required SSE parameters are present
            if not isinstance(params, dict) or "url" not in params:
                raise ValueError(
                    "SSE mode requires MCPServerSseParams with 'url' parameter"
                )

        elif mode == MCPServerMode.STREAMABLE_HTTP:
            # Check that required HTTP parameters are present
            if not isinstance(params, dict) or "session_url" not in params:
                raise ValueError(
                    "STREAMABLE_HTTP mode requires MCPServerStreamableHttpParams with 'session_url' parameter"
                )

        else:
            raise ValueError(f"Unsupported MCP server mode: {mode}")

    async def connect(self):
        """Connect to the MCP server using the configured mode."""
        if self.session is not None:
            return  # Already connected

        try:
            if self.mode == MCPServerMode.STDIO:
                await self._connect_stdio()
            elif self.mode == MCPServerMode.SSE:
                await self._connect_sse()
            elif self.mode == MCPServerMode.STREAMABLE_HTTP:
                await self._connect_streamable_http()
            else:
                raise ValueError(f"Unsupported MCP server mode: {self.mode}")

            logger.info(
                f"Successfully connected to MCP server '{self.name}' using {self.mode.value} mode"
            )

        except Exception as e:
            logger.error(f"Failed to connect to MCP server '{self.name}': {e}")
            raise

    async def _connect_stdio(self):
        """Connect using STDIO transport."""
        params = self.params
        if not isinstance(params, dict) or "command" not in params:
            raise ValueError("STDIO mode requires MCPServerStdioParams with 'command'")

        # Convert to StdioServerParameters
        stdio_params = StdioServerParameters(
            command=params["command"],
            args=params.get("args", []),
            env=params.get("env"),
            cwd=Path(params["cwd"]) if params.get("cwd") else None,
            encoding=params.get("encoding", "utf-8"),
            encoding_error_handler=params.get("encoding_error_handler", "strict"),
        )

        # Create stdio client and session
        stdio_read_stream, stdio_write_stream = await stdio_client(stdio_params)
        self._cleanup_context = AsyncExitStack()
        self.session = await self._cleanup_context.aenter(
            ClientSession(
                stdio_read_stream,
                stdio_write_stream,
                timeout_seconds=self.client_session_timeout_seconds,
            )
        )
        await self.session.initialize()

    async def _connect_sse(self):
        """Connect using SSE transport."""
        params = self.params
        if not isinstance(params, dict) or "url" not in params:
            raise ValueError("SSE mode requires MCPServerSseParams with 'url'")

        # Create SSE client and session
        sse_read_stream, sse_write_stream = await sse_client(
            url=params["url"],
            headers=params.get("headers"),
            timeout=params.get("timeout", 5.0),
            sse_read_timeout=params.get("sse_read_timeout", 300.0),
        )
        self._cleanup_context = AsyncExitStack()
        self.session = await self._cleanup_context.aenter(
            ClientSession(
                sse_read_stream,
                sse_write_stream,
                timeout_seconds=self.client_session_timeout_seconds,
            )
        )
        await self.session.initialize()

    async def _connect_streamable_http(self):
        """Connect using Streamable HTTP transport."""
        params = self.params
        if not isinstance(params, dict) or "session_url" not in params:
            raise ValueError(
                "STREAMABLE_HTTP mode requires MCPServerStreamableHttpParams with 'session_url'"
            )

        # Create streamable HTTP client and session
        http_read_stream, http_write_stream = await streamablehttp_client(
            session_url=params["session_url"],
            get_session_id=params.get("get_session_id"),
            headers=params.get("headers"),
            timeout=params.get("timeout", 5.0),
        )
        self._cleanup_context = AsyncExitStack()
        self.session = await self._cleanup_context.aenter(
            ClientSession(
                http_read_stream,
                http_write_stream,
                timeout_seconds=self.client_session_timeout_seconds,
            )
        )
        await self.session.initialize()

    async def cleanup(self):
        """Cleanup the server connection."""
        if self._cleanup_context is not None:
            await self._cleanup_context.aclose()
            self._cleanup_context = None
        self.session = None
        self._tools_cache = None

    async def list_tools(self) -> List[MCPTool]:
        """List the tools available on the server."""
        if self.session is None:
            await self.connect()

        if self.cache_tools_list and self._tools_cache is not None:
            return self._tools_cache

        assert self.session is not None
        list_tools_result = await self.session.list_tools()
        tools = list_tools_result.tools

        if self.cache_tools_list:
            self._tools_cache = tools

        return tools

    async def call_tool(
        self, tool_name: str, arguments: Optional[Dict[str, Any]] = None
    ) -> CallToolResult:
        """Invoke a tool on the server."""
        if self.session is None:
            await self.connect()

        assert self.session is not None
        return await self.session.call_tool(tool_name, arguments or {})

    def invalidate_tools_cache(self):
        """Invalidate the cached tools list."""
        self._tools_cache = None


# Backward compatibility aliases (deprecated)
class MCPServerStdio(MCPServer):
    """Deprecated: Use MCPServer with mode=MCPServerMode.STDIO instead."""

    def __init__(
        self,
        params: MCPServerStdioParams,
        cache_tools_list: bool = False,
        name: Optional[str] = None,
        client_session_timeout_seconds: Optional[float] = 5,
    ):
        import warnings

        warnings.warn(
            "MCPServerStdio is deprecated. Use MCPServer with mode=MCPServerMode.STDIO instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(
            name=name or "MCPServerStdio",
            mode=MCPServerMode.STDIO,
            params=params,
            cache_tools_list=cache_tools_list,
            client_session_timeout_seconds=client_session_timeout_seconds,
        )


class MCPServerSse(MCPServer):
    """Deprecated: Use MCPServer with mode=MCPServerMode.SSE instead."""

    def __init__(
        self,
        params: MCPServerSseParams,
        cache_tools_list: bool = False,
        name: Optional[str] = None,
        client_session_timeout_seconds: Optional[float] = 5,
    ):
        import warnings

        warnings.warn(
            "MCPServerSse is deprecated. Use MCPServer with mode=MCPServerMode.SSE instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(
            name=name or "MCPServerSse",
            mode=MCPServerMode.SSE,
            params=params,
            cache_tools_list=cache_tools_list,
            client_session_timeout_seconds=client_session_timeout_seconds,
        )


class MCPServerStreamableHttp(MCPServer):
    """Deprecated: Use MCPServer with mode=MCPServerMode.STREAMABLE_HTTP instead."""

    def __init__(
        self,
        params: MCPServerStreamableHttpParams,
        cache_tools_list: bool = False,
        name: Optional[str] = None,
        client_session_timeout_seconds: Optional[float] = 5,
    ):
        import warnings

        warnings.warn(
            "MCPServerStreamableHttp is deprecated. Use MCPServer with mode=MCPServerMode.STREAMABLE_HTTP instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(
            name=name or "MCPServerStreamableHttp",
            mode=MCPServerMode.STREAMABLE_HTTP,
            params=params,
            cache_tools_list=cache_tools_list,
            client_session_timeout_seconds=client_session_timeout_seconds,
        )
