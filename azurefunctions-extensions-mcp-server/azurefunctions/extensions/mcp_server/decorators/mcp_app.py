from typing import Union, Any
from azure.functions import (FunctionRegister, TriggerApi, BindingApi, 
AuthLevel, HttpMethod, ExternalHttpFunctionApp)
from azure.functions.decorators.function_app import HttpFunctionsAuthLevelMixin
from azurefunctions.extensions.mcp_server.starlette import Request, Response

from mcp.server.fastmcp.server import FastMCP
from mcp.server.sse import SseServerTransport

try:
    from azure.functions import SettingsApi
except ImportError:  # backwards compatibility path
    class SettingsApi:
        """Backwards compatibility mock of SettingsApi."""

        pass


class MCPFunctionApp(FastMCP, TriggerApi, FunctionRegister, HttpFunctionsAuthLevelMixin):
    """MCP Functions (DF) Blueprint container.

    It allows functions to be declared via trigger and binding decorators,
    but does not automatically index/register these functions.
    """

    def __init__(self,
                 auth_level: Union[AuthLevel, str] = AuthLevel.FUNCTION,
                 name: str | None = None, instructions: str | None = None, *args, **settings: Any):
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
        """Add an Asgi app integrated mcp_server function.

        :param http_middleware: :class:`WsgiMiddleware`
                                or class:`AsgiMiddleware` instance.

        :return: None
        """

        sse = SseServerTransport("/messages/")

        @self.function_name(name="sse")
        @self.route(trigger_arg_name="request" , methods=(method for method in HttpMethod),
                    auth_level=auth_level,
                    route="sse")
        async def http_app_func(request: Request):
           async with sse.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await self._mcp_server.run(
                    streams[0],
                    streams[1],
                    self._mcp_server.create_initialization_options(),
                )

        @self.function_name(name="messages")
        @self.route(trigger_arg_name="request", methods=(method for method in HttpMethod),
                            auth_level=auth_level,
                    route="messages")
        async def http_messages_func(request: Request):
           return await sse.handle_post_message(request.scope, request.receive, request._send)

