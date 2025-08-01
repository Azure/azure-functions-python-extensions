import contextlib
from typing import Any, Union

import logging

from azure.functions import (
    AuthLevel,
    BindingApi,
    ExternalHttpFunctionApp,
    FunctionRegister,
    HttpMethod,
    HttpResponse,
    TriggerApi,
)
from azure.functions.decorators.function_app import HttpFunctionsAuthLevelMixin
from mcp.server.fastmcp.server import FastMCP
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager

from azurefunctions.extensions.mcp_server.starlette import Request, Response

try:
    from azure.functions import SettingsApi
except ImportError:  # backwards compatibility path

    class SettingsApi:
        """Backwards compatibility mock of SettingsApi."""

        pass


class MCPFunctionApp(
    FastMCP, TriggerApi, FunctionRegister, HttpFunctionsAuthLevelMixin
):
    """MCP Functions (DF) Blueprint container.

    It allows functions to be declared via trigger and binding decorators,
    but does not automatically index/register these functions.
    """

    _session_manager = None

    def __init__(
        self,
        auth_level: Union[AuthLevel, str] = AuthLevel.FUNCTION,
        name: str | None = None,
        instructions: str | None = None,
        *args,
        **settings: Any,
    ):
        """Instantiate a Durable Functions app with which to register Functions.

        Parameters
        ----------
        http_auth_level: Union[AuthLevel, str]
            Authorization level required for Function invocation.
            Defaults to AuthLevel.Function.

        Returns
        -------
        DFApp
            New instance of a Durable Functions app
        """
        FunctionRegister.__init__(self, auth_level=auth_level, *args, **settings)
        FastMCP.__init__(self, name, instructions, **settings)
        self._add_http_app(auth_level)



    def _add_http_app(self, auth_level) -> None:
        """Add a StreamableHTTP integrated MCP server function.

        :param auth_level: Authorization level for the HTTP endpoints.

        :return: None
        """

        @self.function_name(name="mcp")
        @self.route(
            trigger_arg_name="req",
            methods=(method for method in HttpMethod),
            auth_level=auth_level,
            route="mcp",
        )
        async def http_mcp_func(req: Request) -> Response:
            """Handle all MCP requests through StreamableHTTP transport."""
            try:
                # Create a NEW session manager instance for each request
                session_manager = StreamableHTTPSessionManager(
                    app=self._mcp_server,
                    json_response=False,  # Use streaming HTTP instead of JSON responses
                    stateless=True,  # Use stateless mode for Azure Functions
                )
                
                # Create a response capturer
                captured_response = {
                    "status": 200,
                    "headers": {},
                    "body": b""
                }
                
                # Create a custom send function to capture the response (DON'T call original send)
                async def send_wrapper(message):
                    if message["type"] == "http.response.start":
                        captured_response["status"] = message["status"]
                        # Convert headers from bytes tuples to string dict
                        headers = {}
                        for header_name, header_value in message.get("headers", []):
                            if isinstance(header_name, bytes):
                                header_name = header_name.decode('latin-1')
                            if isinstance(header_value, bytes):
                                header_value = header_value.decode('latin-1')
                            headers[header_name] = header_value
                        captured_response["headers"] = headers
                    elif message["type"] == "http.response.body":
                        captured_response["body"] += message.get("body", b"")
                    # Don't call req._send here to avoid double response

                # Use the session manager within its proper context
                async with session_manager.run():
                    await session_manager.handle_request(
                        req.scope, req.receive, send_wrapper
                    )
                
                # Return the captured response
                return Response(
                    captured_response["body"].decode('utf-8'),
                    status_code=captured_response["status"],
                    headers=captured_response["headers"]
                )
                
            except Exception as e:
                logging.error(f"MCP request error: {e}", exc_info=True)
                
                # Send a proper error response
                return Response(
                    f"MCP Error: {str(e)}",
                    status_code=500
                )
