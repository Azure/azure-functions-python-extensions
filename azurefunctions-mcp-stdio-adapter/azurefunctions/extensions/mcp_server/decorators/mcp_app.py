"""
MCP Function App decorator and main class.

This module provides the MCPFunctionApp class that extends FastMCP and Azure Functions
to create a streamable HTTP endpoint for STDIO-based MCP servers.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional, Union

import azure.functions as func
from azure.functions import (
    AuthLevel,
    FunctionRegister,
    TriggerApi,
    HttpMethod,
    HttpRequest,
    HttpResponse
)

from ..core.config_loader import ConfigurationLoader
from ..core.stdio_adapter import MCPStdioAdapter
from ..models.configuration import (
    MCPMultiServerConfiguration,
    MCPStdioConfiguration,
)
from ..models.enums import MCPMode
from ..utils.validation import ConfigurationValidator

logger = logging.getLogger(__name__)


class MCPFunctionApp(TriggerApi, FunctionRegister):
    """
    MCP Functions app that adapts STDIO MCP servers to streamable HTTP.
    
    This class extends FastMCP and Azure Functions decorators to create
    an HTTP endpoint that proxies requests to STDIO-based MCP servers.
    """

    def __init__(
        self,
        mode: MCPMode = MCPMode.STDIO,
        mcp_server: Optional[MCPStdioConfiguration] = None,
        config_file: Optional[str] = None,
        auth_level: Union[AuthLevel, str] = AuthLevel.FUNCTION,
        name: Optional[str] = None,
        instructions: Optional[str] = None,
        *args,
        **kwargs
    ):
        """
        Initialize the MCP Function App.
        
        Args:
            mode: Operating mode (currently only STDIO supported)
            mcp_server: Programmatic MCP server configuration
            config_file: Path to JSON configuration file
            auth_level: Azure Functions authorization level
            name: Optional name for the MCP server
            instructions: Optional instructions for the MCP server
        """
        # Initialize parent classes
        FunctionRegister.__init__(self, auth_level=auth_level, *args, **kwargs)
        # FastMCP.__init__(self, name or "MCP STDIO Adapter", **kwargs)
        
        # Store configuration
        self.mode = mode
        self._auth_level = auth_level  # Use private attribute to avoid conflicts
        
        # Configuration loading
        self.config_loader = ConfigurationLoader()
        self.validator = ConfigurationValidator()
        self.multi_config: Optional[MCPMultiServerConfiguration] = None
        self.current_server_config: Optional[MCPStdioConfiguration] = None
        
        # STDIO adapter
        self.stdio_adapter: Optional[MCPStdioAdapter] = None
        
        # Load configuration
        self._load_configuration(mcp_server, config_file)
        
        # Add HTTP endpoint
        self._add_http_app(auth_level)
    
    def _load_configuration(
        self, 
        mcp_server: Optional[MCPStdioConfiguration],
        config_file: Optional[str]
    ) -> None:
        """
        Load MCP server configuration from various sources.
        
        Args:
            mcp_server: Programmatic configuration
            config_file: Configuration file path
        """
        try:
            if mcp_server:
                # Use programmatic configuration
                logger.info(f"Using programmatic configuration for server: {mcp_server.name}")
                self.validator.validate_configuration(mcp_server)
                self.current_server_config = mcp_server
                
                # Create multi-config wrapper
                self.multi_config = MCPMultiServerConfiguration()
                self.multi_config.add_server(mcp_server)
                
            elif config_file:
                # Load from specified file
                logger.info(f"Loading configuration from file: {config_file}")
                self.multi_config = self.config_loader.load_from_file(config_file)
                self.current_server_config = self.multi_config.get_server()
                
            else:
                # Try to load from well-known locations
                logger.info("Searching for configuration in well-known locations")
                self.multi_config = self.config_loader.load_from_well_known_locations()
                
                if self.multi_config:
                    self.current_server_config = self.multi_config.get_server()
                else:
                    raise ValueError("No MCP server configuration found")
            
            if not self.current_server_config:
                raise ValueError("No valid MCP server configuration available")
            
            logger.info(f"Successfully loaded configuration for: {self.current_server_config.name}")
            
        except Exception as e:
            logger.error(f"Failed to load MCP configuration: {e}")
            raise
    
    def _add_http_app(self, auth_level: Union[AuthLevel, str]) -> None:
        """
        Add the HTTP endpoint for MCP communication.
        
        Args:
            auth_level: Authorization level for the HTTP endpoint
        """
        @self.function_name(name="mcp")
        @self.route(
            trigger_arg_name="req",
            methods=[method for method in HttpMethod],
            auth_level=auth_level,
            route="mcp",
        )
        async def http_mcp_func(req: HttpRequest) -> HttpResponse:
            """Handle MCP JSON-RPC requests by forwarding to STDIO MCP server."""
            try:
                logger.debug(f"Received MCP request: {req.method} {req.url}")
                
                # Only accept POST requests with JSON-RPC
                if req.method.upper() != "POST":
                    return HttpResponse(
                        "Method not allowed - MCP requires POST",
                        status_code=405,
                        headers={"Content-Type": "text/plain"}
                    )
                
                # Ensure STDIO adapter is connected
                if not await self._ensure_connection():
                    return HttpResponse(
                        "MCP server connection failed",
                        status_code=503,
                        headers={"Content-Type": "text/plain"}
                    )
                
                # Get request body and parse JSON-RPC message
                try:
                    body = req.get_body()
                    if isinstance(body, bytes):
                        body_str = body.decode('utf-8')
                    else:
                        body_str = str(body)
                    
                    # Parse JSON-RPC message
                    if not body_str.strip():
                        return HttpResponse(
                            "Empty request body",
                            status_code=400,
                            headers={"Content-Type": "text/plain"}
                        )
                    
                    rpc_message = json.loads(body_str)
                    logger.debug(f"Parsed JSON-RPC message: {rpc_message.get('method', 'response')}")
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in request body: {e}")
                    return HttpResponse(
                        json.dumps({
                            "jsonrpc": "2.0",
                            "id": None,
                            "error": {
                                "code": -32700,
                                "message": "Parse error",
                                "data": str(e)
                            }
                        }),
                        status_code=400,
                        headers={"Content-Type": "application/json"}
                    )
                
                # Forward the JSON-RPC message to STDIO MCP server
                if not self.stdio_adapter:
                    error_msg = "STDIO adapter not initialized"
                    logger.error(error_msg)
                    return HttpResponse(
                        json.dumps({
                            "jsonrpc": "2.0",
                            "id": rpc_message.get("id"),
                            "error": {
                                "code": -32603,
                                "message": "Internal error: STDIO adapter not initialized",
                                "data": error_msg
                            }
                        }),
                        status_code=500,
                        headers={"Content-Type": "application/json"}
                    )
                
                success = await self.stdio_adapter.send_message(rpc_message)
                if not success:
                    server_name = self.current_server_config.name if self.current_server_config else "unknown"
                    error_msg = f"Failed to send message to MCP server: {server_name}"
                    logger.error(error_msg)
                    return HttpResponse(
                        json.dumps({
                            "jsonrpc": "2.0",
                            "id": rpc_message.get("id"),
                            "error": {
                                "code": -32603,
                                "message": "Internal error: Failed to send message to MCP server",
                                "data": error_msg
                            }
                        }),
                        status_code=500,
                        headers={"Content-Type": "application/json"}
                    )
                
                # Wait for a response from the MCP server
                # TODO: Implement proper response handling with a response queue
                # For now, we'll wait a short time and then return a basic response
                await asyncio.sleep(0.5)  # Give the STDIO server time to respond
                
                # For initialize messages, return a basic successful response
                if rpc_message.get("method") == "initialize":
                    server_name = self.current_server_config.name if self.current_server_config else "unknown"
                    response_message = {
                        "jsonrpc": "2.0",
                        "id": rpc_message.get("id"),
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {
                                "tools": {},
                                "resources": {},
                                "prompts": {}
                            },
                            "serverInfo": {
                                "name": f"MCP Server Proxy ({server_name})",
                                "version": "1.0.0"
                            }
                        }
                    }
                else:
                    # For other messages, return a basic acknowledgment
                    # In a real implementation, this would return the actual STDIO response
                    response_message = {
                        "jsonrpc": "2.0",
                        "id": rpc_message.get("id"),
                        "result": {
                            "status": "forwarded_to_stdio",
                            "server": self.current_server_config.name if self.current_server_config else "unknown",
                            "note": "This is a simplified response. Real implementation would return STDIO server response."
                        }
                    }
                
                return HttpResponse(
                    json.dumps(response_message),
                    status_code=200,
                    headers={"Content-Type": "application/json"}
                )
                
            except Exception as e:
                logger.error(f"MCP request error: {e}", exc_info=True)
                error_id = None
                try:
                    # Try to get the request ID if we parsed the message
                    body = req.get_body()
                    if isinstance(body, bytes):
                        body_str = body.decode('utf-8')
                    else:
                        body_str = str(body)
                    if body_str.strip():
                        rpc_data = json.loads(body_str)
                        error_id = rpc_data.get("id")
                except:
                    pass
                    
                return HttpResponse(
                    json.dumps({
                        "jsonrpc": "2.0",
                        "id": error_id,
                        "error": {
                            "code": -32603,
                            "message": "Internal error",
                            "data": str(e)
                        }
                    }),
                    status_code=500,
                    headers={"Content-Type": "application/json"}
                )
    
    async def _ensure_connection(self) -> bool:
        """
        Ensure the STDIO adapter is connected to the MCP server.
        
        Returns:
            True if connected, False otherwise
        """
        if not self.current_server_config:
            logger.error("No MCP server configuration available")
            return False
        
        # Create adapter if needed
        if not self.stdio_adapter:
            logger.info(f"Creating STDIO adapter for: {self.current_server_config.name}")
            self.stdio_adapter = MCPStdioAdapter(
                self.current_server_config,
                message_handler=self._handle_stdio_message
            )
        
        # Connect if not already connected
        if not self.stdio_adapter.is_connected:
            logger.info(f"Connecting to MCP server: {self.current_server_config.name}")
            success = await self.stdio_adapter.connect()
            
            if not success:
                logger.error(f"Failed to connect to MCP server: {self.current_server_config.name}")
                return False
        
        return True
    
    async def _handle_stdio_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Handle messages received from the STDIO MCP server.
        
        Args:
            message: JSON-RPC message from MCP server
            
        Returns:
            Optional response message
        """
        logger.debug(f"Handling STDIO message: {message.get('method', message.get('id', 'unknown'))}")
        
        # For now, we mainly forward messages between HTTP and STDIO
        # The actual message handling is done by the StreamableHTTPSessionManager
        return None
    
    def _convert_request_to_scope(self, req: HttpRequest) -> Dict[str, Any]:
        """
        Convert Azure Functions HttpRequest to ASGI scope.
        
        Args:
            req: Azure Functions HTTP request
            
        Returns:
            ASGI scope dictionary
        """
        # Parse URL components
        url = req.url
        path = req.route_params.get("path", "/")
        if not path.startswith("/"):
            path = "/" + path
        
        # Convert headers
        headers = []
        for name, value in req.headers.items():
            headers.append([name.lower().encode("latin-1"), value.encode("latin-1")])
        
        # Create ASGI scope
        scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.1"},
            "http_version": "1.1",
            "method": req.method.upper(),
            "scheme": "https",  # Azure Functions typically use HTTPS
            "path": path,
            "raw_path": path.encode("utf-8"),
            "query_string": req.url.split("?", 1)[1].encode("utf-8") if "?" in req.url else b"",
            "headers": headers,
            "server": ("localhost", 80),
            "client": ("127.0.0.1", 0),
        }
        
        return scope
    
    async def cleanup(self) -> None:
        """Clean up resources when the function app is shutting down."""
        logger.info("Cleaning up MCP Function App resources")
        
        if self.stdio_adapter:
            await self.stdio_adapter.disconnect()
            self.stdio_adapter = None
        
        if self._session_manager:
            # Clean up session manager if needed
            self._session_manager = None
        
        logger.info("MCP Function App cleanup completed")
    
    def get_server_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the MCP server connection.
        
        Returns:
            Dictionary with server statistics
        """
        if not self.stdio_adapter:
            return {"status": "not_initialized"}
        
        stats = self.stdio_adapter.stats.copy()
        stats["server_name"] = self.current_server_config.name if self.current_server_config else "unknown"
        stats["mode"] = self.mode.value
        
        return stats
