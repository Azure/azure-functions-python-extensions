"""

This module provides the MCPFunctionApp class that extends FastMCP and Azure Functions
to create a streamable HTTP endpoint for STDIO-based MCP servers.
"""

import asyncio
import json
import logging
import uuid
from collections import defaultdict
from typing import Any, Dict, Optional, Union

import azure.functions as func
from azure.functions import AuthLevel, FunctionRegister, HttpMethod, TriggerApi
from azurefunctions.extensions.http.fastapi import Request, Response, StreamingResponse

from ..core.config_loader import ConfigurationLoader
from ..core.session_manager import MCPSessionManager
from ..core.stdio_adapter import MCPStdioAdapter
from ..models.configuration import MCPMultiServerConfiguration, MCPStdioConfiguration
from ..models.enums import MCPMode
from ..utils.validation import ConfigurationValidator

logger = logging.getLogger(__name__)

# Version marker for debugging
PACKAGE_VERSION = "0.1.0a14-managed-identity-fix"
logger.info(f"🔍 MCPFunctionApp module loaded - Package version: {PACKAGE_VERSION}")


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
        **kwargs,
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
        logger.info("🚀 === STARTING MCPFunctionApp INITIALIZATION ===")
        logger.info(f"📦 Package version: {PACKAGE_VERSION}")
        logger.info(f"🔧 Args: mode={mode}, auth_level={auth_level}, mcp_server provided: {mcp_server is not None}")
        print(f"🚀 MCPFunctionApp.__init__ called - Version: {PACKAGE_VERSION}")
        print(f"📊 Args received: mode={mode}, mcp_server={mcp_server is not None}")
        
        try:
            # Initialize parent classes
            print("🔧 Initializing parent classes...")
            logger.info("Initializing parent classes...")
            FunctionRegister.__init__(self, auth_level=auth_level, *args, **kwargs)
            print("✅ FunctionRegister initialized")
            logger.info("✅ FunctionRegister initialized")
            # FastMCP.__init__(self, name or "MCP STDIO Adapter", **kwargs)

            # Store configuration
            print("⚙️ Setting up basic configuration...")
            logger.info("Setting up basic configuration...")
            self.mode = mode
            self._auth_level = auth_level  # Use private attribute to avoid conflicts

            # Configuration loading
            self.config_loader = ConfigurationLoader()
            self.validator = ConfigurationValidator()
            self.multi_config: Optional[MCPMultiServerConfiguration] = None
            self.current_server_config: Optional[MCPStdioConfiguration] = None

            # STDIO adapters per session for streamable HTTP
            self._session_adapters: Dict[str, MCPStdioAdapter] = {}

            # Session manager for stateless operation
            self._session_manager = MCPSessionManager()

            # Legacy single adapter for backward compatibility
            self.stdio_adapter: Optional[MCPStdioAdapter] = None

            # Session management for streamable HTTP
            self._active_sessions: Dict[str, bool] = {}
            self._response_timeout = 30.0  # 30 seconds timeout for responses

            # Authentication manager
            self._auth_manager: Optional[Any] = None
            print("✅ Basic configuration complete")
            logger.info("✅ Basic configuration complete")

            # Load configuration
            try:
                print("=== LOADING CONFIGURATION ===")
                logger.info("=== LOADING CONFIGURATION ===")
                self._load_configuration(mcp_server, config_file)
                print("✅ Configuration loaded successfully")
                logger.info("✅ Configuration loaded successfully")
            except Exception as e:
                print(f"❌ Failed to load configuration: {e}")
                logger.error(f"❌ Failed to load configuration: {e}", exc_info=True)
                raise

            # Initialize authentication
            try:
                print("=== STARTING AUTHENTICATION INITIALIZATION ===")
                logger.info("=== STARTING AUTHENTICATION INITIALIZATION ===")
                self._initialize_authentication()
                print("✅ Authentication initialization completed")
                logger.info("✅ Authentication initialization completed")
            except Exception as e:
                print(f"❌ CRITICAL: Failed to initialize authentication: {e}")
                print(f"❌ CRITICAL: Exception type: {type(e)}")
                print(f"❌ CRITICAL: Exception args: {e.args}")
                logger.error(f"❌ Failed to initialize authentication: {e}", exc_info=True)
                # Don't fail completely - continue without auth
                self._auth_manager = None
                print(f"⚠️ CRITICAL: Auth manager set to None due to initialization failure")

            # Add HTTP endpoint
            try:
                print("📡 Adding HTTP endpoint...")
                logger.info("Adding HTTP endpoint...")
                self._add_http_app(auth_level)
                print("✅ HTTP endpoint added successfully")
                logger.info("✅ HTTP endpoint added successfully")
            except Exception as e:
                print(f"❌ Failed to add HTTP endpoint: {e}")
                logger.error(f"❌ Failed to add HTTP endpoint: {e}", exc_info=True)
                raise
                
            print("🎉 === MCPFunctionApp INITIALIZATION COMPLETE ===")
            logger.info("🎉 === MCPFunctionApp INITIALIZATION COMPLETE ===")
            
        except Exception as e:
            print(f"💥 === MCPFunctionApp INITIALIZATION FAILED ===: {e}")
            logger.error(f"💥 === MCPFunctionApp INITIALIZATION FAILED ===: {e}", exc_info=True)
            raise

    def _load_configuration(
        self, mcp_server: Optional[MCPStdioConfiguration], config_file: Optional[str]
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
                logger.info(
                    f"Using programmatic configuration for server: {mcp_server.name}"
                )
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

            logger.info(
                f"Successfully loaded configuration for: {self.current_server_config.name}"
            )

        except Exception as e:
            logger.error(f"Failed to load MCP configuration: {e}")
            raise

    def _initialize_authentication(self) -> None:
        """Initialize authentication manager based on server configuration."""
        print("🔐 === INITIALIZING AUTHENTICATION ===")
        logger.info("=== INITIALIZING AUTHENTICATION ===")
        
        print(f"📋 Server config available: {self.current_server_config is not None}")
        if not self.current_server_config:
            print("❌ No server configuration available for authentication")
            logger.error("❌ No server configuration available for authentication")
            raise ValueError("No server configuration available")

        print(f"🔍 Server name: {self.current_server_config.name}")
        print(f"🔍 Auth config available: {hasattr(self.current_server_config, 'auth')}")
        logger.info(f"Server name: {self.current_server_config.name}")
        logger.info(f"Auth config available: {hasattr(self.current_server_config, 'auth')}")
        
        if hasattr(self.current_server_config, 'auth') and self.current_server_config.auth:
            print(f"🔑 Auth method: {self.current_server_config.auth.method}")
            print(f"🔑 Auth scopes: {getattr(self.current_server_config.auth, 'azure_scopes', [])}")
            print(f"🔑 Auth client_id: {getattr(self.current_server_config.auth, 'azure_client_id', 'Not configured')}")
            logger.info(f"Auth method: {self.current_server_config.auth.method}")
            logger.info(f"Auth scopes: {getattr(self.current_server_config.auth, 'azure_scopes', [])}")
            logger.info(f"Auth client_id: {getattr(self.current_server_config.auth, 'azure_client_id', 'Not configured')}")
        else:
            print("❌ No auth configuration found on server config")
            logger.error("❌ No auth configuration found on server config")
            return

        # Import here to avoid circular imports
        try:
            print("📦 Importing authentication modules...")
            logger.info("Importing authentication modules...")
            from ..auth.provider_factory import AuthProviderFactory
            from ..auth.token_handler import AuthManager
            print("✅ Authentication modules imported successfully")
            logger.info("✅ Authentication modules imported successfully")
        except Exception as e:
            print(f"❌ Failed to import authentication modules: {e}")
            logger.error(f"❌ Failed to import authentication modules: {e}", exc_info=True)
            raise

        try:
            print("🏭 Creating authentication provider...")
            logger.info("Creating authentication provider...")
            provider = AuthProviderFactory.create_provider(
                self.current_server_config.auth
            )
            print(f"✅ Provider created: {type(provider)}")
            logger.info(f"✅ Provider created: {type(provider)}")
            
            print("🎛️ Creating authentication manager...")
            logger.info("Creating authentication manager...")
            self._auth_manager = AuthManager(provider)
            print(f"✅ Auth manager created: {self._auth_manager}")
            logger.info(f"✅ Auth manager created: {self._auth_manager}")
            
            print(f"🎉 Successfully initialized authentication with method: {self.current_server_config.auth.method}")
            logger.info(
                f"🎉 Successfully initialized authentication with method: {self.current_server_config.auth.method}"
            )
        except Exception as e:
            print(f"❌ Failed to create authentication provider/manager: {e}")
            logger.error(f"❌ Failed to create authentication provider/manager: {e}", exc_info=True)
            raise

    async def _authenticate_request(self, headers: Dict[str, str]) -> Optional[Any]:
        """
        Authenticate incoming request.

        Args:
            headers: HTTP request headers

        Returns:
            AuthContext if authentication succeeds, None if no auth configured

        Raises:
            Exception: If authentication fails
        """
        logger.info("=== AUTHENTICATING REQUEST ===")
        logger.info(f"Auth manager available: {self._auth_manager is not None}")
        
        if not self._auth_manager:
            logger.info("❌ No auth manager - skipping authentication")
            return None

        try:
            logger.info("🔐 Calling auth manager to authenticate request")
            logger.info(f"Request headers: {list(headers.keys())}")
            
            auth_context = await self._auth_manager.authenticate_request(headers)
            
            logger.info(f"✅ Authentication result: {auth_context}")
            if auth_context:
                logger.info(f"Auth method: {auth_context.method}")
                logger.info(f"User ID: {auth_context.user_id}")
            
            return auth_context
        except Exception as e:
            logger.error(f"❌ Authentication failed: {e}", exc_info=True)
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
            methods=[HttpMethod.GET, HttpMethod.POST],
            auth_level=auth_level,
            route="mcp",
        )
        async def http_mcp_func(req: Request) -> Response:
            """Handle MCP JSON-RPC requests by forwarding to STDIO MCP server."""
            try:
                # Extract key headers for debugging
                content_type = req.headers.get("content-type", "Not set")
                accept = req.headers.get("accept", "Not set")
                session_id_header = req.headers.get("mcp-session-id", "Not set")
                user_agent = req.headers.get("user-agent", "Not set")
                auth_header = req.headers.get("authorization", "Not set")
                logger.debug(
                    f"=== NEW REQUEST === {req.method} {req.url} | Headers: {dict(req.headers)} | Query: {dict(req.query_params)} | Content-Type: {content_type}, Accept: {accept}, User-Agent: {user_agent}, MCP-Session-ID: {session_id_header}, Auth: {auth_header[:20] + '...' if auth_header != 'Not set' else 'Not set'}"
                )

                # Handle CORS preflight requests
                if req.method.upper() == "OPTIONS":
                    logger.debug("Handling OPTIONS request - CORS preflight")
                    response = Response(
                        "",
                        status_code=200,
                        headers={
                            "Access-Control-Allow-Origin": "*",
                            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                            "Access-Control-Allow-Headers": "Content-Type, Authorization, mcp-session-id",
                            "Access-Control-Expose-Headers": "mcp-session-id",
                            "Access-Control-Max-Age": "86400",
                        },
                    )
                    logger.debug(f"OPTIONS Response Headers: {dict(response.headers)}")
                    return response

                # Authenticate the request
                auth_context = await self._authenticate_request(req.headers)

                # Check if this is a streamable HTTP connection request from MCP Inspector
                if req.method.upper() == "GET":
                    # Check if this is an MCP Inspector streamable HTTP request
                    transport_type = req.query_params.get("transportType")

                    if transport_type == "streamable-http":
                        logger.debug(f"Establishing MCP Streamable HTTP connection")
                        response = await self._handle_streamable_http_connection(
                            req, auth_context
                        )
                        logger.debug(
                            f"Streamable HTTP connection established - Status: {response.status_code}"
                        )
                        return response

                    logger.debug(
                        f"Regular GET request - transport_type: {transport_type}, returning info message"
                    )
                    return Response(
                        "MCP endpoint active. Use POST for JSON-RPC requests.",
                        status_code=200,
                        headers={"Content-Type": "text/plain, text/event-stream"},
                    )

                # Only accept POST requests with JSON-RPC (GET and OPTIONS already handled above)
                if req.method.upper() != "POST":
                    logger.warning(
                        f"Method {req.method} not allowed - MCP requires POST for messages"
                    )
                    return Response(
                        json.dumps(
                            {
                                "jsonrpc": "2.0",
                                "id": None,
                                "error": {
                                    "code": -32600,
                                    "message": f"Method {req.method} not allowed - MCP requires POST for messages",
                                },
                            }
                        ),
                        status_code=405,
                        headers={"Content-Type": "application/json"},
                    )

                # Simple MCP JSON-RPC handling following the official SDK pattern
                return await self._handle_mcp_post_request(req)

            except Exception as e:
                logger.error(
                    f"MCP request error: {e} | Method: {req.method} | URL: {req.url} | Headers: {dict(req.headers)}",
                    exc_info=True,
                )

                error_id = None
                try:
                    # Try to get the request ID if we parsed the message
                    body = await req.body()
                    if isinstance(body, bytes):
                        body_str = body.decode("utf-8")
                    else:
                        body_str = str(body)
                    if body_str.strip():
                        rpc_data = json.loads(body_str)
                        error_id = rpc_data.get("id")
                        logger.debug(f"Extracted error ID from request: {error_id}")
                except Exception as parse_error:
                    logger.debug(f"Could not extract request ID: {parse_error}")

                error_response = Response(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": error_id,
                            "error": {
                                "code": -32603,
                                "message": "Internal error",
                                "data": str(e),
                            },
                        }
                    ),
                    status_code=500,
                    headers={"Content-Type": "application/json"},
                )

                logger.debug(f"Returning error response: {error_response.body}")
                return error_response

    async def _handle_mcp_post_request(self, req: Request) -> Response:
        """
        Handle MCP JSON-RPC POST requests following the official SDK pattern.

        This simplified implementation follows the MCP StreamableHTTPServerTransport pattern:
        1. Validate headers and content type
        2. Parse JSON-RPC message
        3. For notifications/responses: return 202 Accepted
        4. For requests: send to STDIO, wait for response, return JSON
        """
        logger.debug("Processing MCP POST request")
        try:
            # Authenticate the request first
            auth_context = await self._authenticate_request(req.headers)
            
            accept_header = req.headers.get("accept", "")
            has_json = "application/json" in accept_header
            has_sse = "text/event-stream" in accept_header
            is_streamable_http = has_json and has_sse
            logger.debug(
                f"Accept validation - JSON: {has_json}, SSE: {has_sse}, Streamable: {is_streamable_http}"
            )
            content_type = req.headers.get("content-type", "")
            if not content_type.startswith("application/json"):
                return self._create_error_response(
                    "Unsupported Media Type: Content-Type must be application/json",
                    415,
                    -32600,
                )
            session_id = req.headers.get("mcp-session-id")
            if is_streamable_http:
                if not session_id:
                    # CRITICAL FIX: Use a consistent default session ID instead of random UUIDs
                    # This prevents creating new processes for each request
                    session_id = "default-session"
                    if session_id not in self._active_sessions:
                        self._active_sessions[session_id] = True
                        session_status = "auto-created"
                    else:
                        session_status = "reusing"
                elif session_id not in self._active_sessions:
                    # Register the session if it's not already active
                    self._active_sessions[session_id] = True
                    session_status = "registered existing"
                else:
                    session_status = "using existing"

                logger.debug(
                    f"Session management - {session_status} session: {session_id}"
                )
            if not await self._ensure_connection(session_id, auth_context):
                return self._create_error_response(
                    "Internal error: MCP server connection failed", 503, -32603
                )
            body = await req.body()
            if isinstance(body, bytes):
                body_str = body.decode("utf-8")
            else:
                body_str = str(body)
            if not body_str.strip():
                return self._create_error_response(
                    "Parse error: Empty request body", 400, -32700
                )
            try:
                rpc_message = json.loads(body_str)
                logger.debug(
                    f"Parsed JSON-RPC - Method: {rpc_message.get('method', 'response')}, ID: {rpc_message.get('id', 'none')} | Full message: {json.dumps(rpc_message, indent=2)}"
                )
            except json.JSONDecodeError as e:
                return self._create_error_response(
                    f"Parse error: {str(e)}", 400, -32700
                )
            if "method" not in rpc_message or rpc_message.get("id") is None:
                logger.debug(
                    f"Handling notification/response - Method: {rpc_message.get('method', 'N/A')}, Has ID: {rpc_message.get('id') is not None}, returning 202 Accepted"
                )

                # Get the appropriate adapter for this session
                adapter = self._get_adapter(session_id)
                if not adapter:
                    return self._create_error_response(
                        "Internal error: No adapter available for session", 500, -32603
                    )

                await adapter.send_message(rpc_message)

                return self._create_json_response(None, 202, session_id)

            # Get the appropriate adapter for this session
            adapter = self._get_adapter(session_id)
            if not adapter:
                return self._create_error_response(
                    "Internal error: No adapter available for session", 500, -32603
                )

            request_id = rpc_message["id"]  # Keep original type (int, string, etc.)
            method = rpc_message.get("method", "")
            logger.debug(f"Processing request with ID: {request_id}, method: {method}")

            # Check if this is a session-based request that needs initialization
            session_based_methods = [
                "tools/list",
                "tools/call",
                "resources/list",
                "resources/read",
                "resources/subscribe",
                "resources/unsubscribe",
                "prompts/list",
                "prompts/get",
                "completion/complete",
            ]

            if method in session_based_methods:
                logger.debug(
                    f"Using stateless approach for session-based method: {method}"
                )

                # Use stateless request handling with automatic initialization
                response_data = await adapter.send_stateless_request(
                    rpc_message, session_id, self._session_manager
                )

                if response_data is None:
                    return self._create_error_response(
                        "Internal error: No response received from stateless request",
                        500,
                        -32603,
                        request_id,
                    )

                logger.debug(f"Returning stateless response for {request_id}")
                return self._create_json_response(response_data, 200, session_id)

            # For non-session-based methods, use the original approach
            logger.debug(f"Using original approach for method: {method}")
            response_received = asyncio.Event()
            response_data = None

            async def response_handler(
                message: Dict[str, Any]
            ) -> Optional[Dict[str, Any]]:
                nonlocal response_data, response_received
                message_id = message.get("id")
                if message_id == request_id and (
                    "result" in message or "error" in message
                ):
                    response_data = message
                    response_received.set()
                    logger.debug(
                        f"Response handler - captured matching response for request {request_id} (checked ID {message_id})"
                    )
                return None

            original_handler = getattr(adapter, "message_handler", None)

            async def combined_handler(
                message: Dict[str, Any]
            ) -> Optional[Dict[str, Any]]:
                if original_handler:
                    result = await original_handler(message)
                else:
                    result = None
                await response_handler(message)
                logger.debug(
                    f"Combined handler processed message ID: {message.get('id')}"
                )
                return result

            logger.debug(
                f"Handler setup - temp handler for request {request_id}, original: {original_handler}"
            )
            adapter.message_handler = combined_handler
            try:
                success = await adapter.send_message(rpc_message)
                if not success:
                    return self._create_error_response(
                        "Internal error: Failed to send message to MCP server",
                        500,
                        -32603,
                        request_id,
                    )
                logger.debug(f"Message sent - awaiting response for {request_id}")
                await asyncio.wait_for(
                    response_received.wait(), timeout=self._response_timeout
                )
                if response_data is None:
                    return self._create_error_response(
                        "Internal error: No response received", 500, -32603, request_id
                    )
                logger.debug(f"Returning response for {request_id}")
                return self._create_json_response(response_data, 200, session_id)
            except asyncio.TimeoutError:
                logger.error(f"Timeout waiting for response to {request_id}")
                return self._create_error_response(
                    f"Internal error: Timeout waiting for MCP server response",
                    500,
                    -32603,
                    request_id,
                )
            finally:
                logger.debug(f"Restoring original handler for request {request_id}")
                adapter.message_handler = original_handler
        except Exception as e:
            logger.error(f"Error handling MCP POST request: {e}", exc_info=True)
            return self._create_error_response(f"Internal error: {str(e)}", 500, -32603)

    def _create_error_response(
        self,
        message: str,
        status_code: int,
        error_code: int,
        request_id: Optional[Union[str, int]] = None,
    ) -> Response:
        """Create a JSON-RPC error response following MCP SDK pattern."""
        error_response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": error_code, "message": message},
        }

        return Response(
            json.dumps(error_response),
            status_code=status_code,
            headers={"Content-Type": "application/json"},
        )

    def _create_json_response(
        self,
        response_message: Optional[Dict[str, Any]],
        status_code: int,
        session_id: Optional[str] = None,
    ) -> Response:
        """Create a JSON response following MCP SDK pattern."""
        headers = {"Content-Type": "application/json"}

        # Add session ID header for streamable HTTP
        if session_id:
            headers["mcp-session-id"] = session_id
            headers["Access-Control-Allow-Origin"] = "*"
            headers["Access-Control-Expose-Headers"] = "mcp-session-id"

        body = json.dumps(response_message) if response_message else ""

        return Response(body, status_code=status_code, headers=headers)

    async def _ensure_connection(
        self, session_id: Optional[str] = None, auth_context: Optional[Any] = None
    ) -> bool:
        """
        Ensure the STDIO adapter is connected to the MCP server.

        Args:
            session_id: Session ID for streamable HTTP (None for legacy mode)

        Returns:
            True if connected, False otherwise
        """
        logger.info(f"=== ENSURING CONNECTION FOR SESSION: {session_id} ===")
        logger.info(f"Auth context provided: {auth_context is not None}")
        if auth_context:
            logger.info(f"Auth method: {auth_context.method}")
            
        if not self.current_server_config:
            logger.error("❌ No MCP server configuration available")
            return False

        # Determine which adapter to use
        if session_id:
            # Session-specific adapter for streamable HTTP
            if session_id not in self._session_adapters:
                logger.info(f"🆕 Creating new session adapter for {session_id}")
                
                # Get auth environment variables
                auth_env = {}
                if auth_context and self._auth_manager:
                    logger.info("🔐 Getting auth environment variables from auth manager")
                    auth_env = self._auth_manager.get_auth_env_vars(auth_context)
                    logger.info(f"Auth env vars count: {len(auth_env)}")
                else:
                    logger.warning("⚠️ No auth context or auth manager - no auth env vars will be set")
                
                adapter = MCPStdioAdapter(
                    self.current_server_config,
                    message_handler=self._handle_stdio_message,
                    auth_context=auth_context,
                )
                self._session_adapters[session_id] = adapter
                logger.info(
                    f"📡 Session adapter - created new for {session_id}: {self.current_server_config.name} with auth: {auth_context.method if auth_context else 'none'}"
                )
            else:
                logger.info(f"♻️ Session adapter - using existing for {session_id}")

            adapter = self._session_adapters[session_id]
        else:
            # Legacy single adapter
            if not self.stdio_adapter:
                logger.info(
                    f"Creating STDIO adapter for: {self.current_server_config.name}"
                )
                self.stdio_adapter = MCPStdioAdapter(
                    self.current_server_config,
                    message_handler=self._handle_stdio_message,
                    auth_context=auth_context,
                )

            adapter = self.stdio_adapter
            logger.debug(f"Using legacy single adapter")

        # Check connection state - the is_connected property will auto-update if process died
        if not adapter.is_connected:
            # If we had a previous failed connection, clean it up first
            if getattr(adapter, "_is_connected", False) or getattr(
                adapter, "_read_task", None
            ):
                logger.info(
                    f"Cleaning up previous connection for: {self.current_server_config.name}"
                )
                await adapter.disconnect()

                # Brief pause to ensure cleanup is complete
                await asyncio.sleep(0.1)

            success = await adapter.connect()
            logger.debug(
                f"Connection attempt to MCP server {self.current_server_config.name}: {'successful' if success else 'failed'}"
            )

            if not success:
                logger.error(
                    f"Failed to connect to MCP server: {self.current_server_config.name}"
                )
                return False
        else:
            logger.debug(
                f"Already connected to MCP server: {self.current_server_config.name}"
            )

        return True

    async def _handle_stdio_message(
        self, message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Handle messages received from the STDIO MCP server.

        Args:
            message: JSON-RPC message from MCP server

        Returns:
            Optional response message
        """
        logger.debug(f"Received STDIO message: {json.dumps(message, indent=2)}")

        # This is used by the temporary response handler in _handle_mcp_post_request
        # No need for complex pending request tracking here since we use event-based handling

        return None

    async def _handle_streamable_http_connection(
        self, req: Request, auth_context: Optional[Any] = None
    ) -> Response:
        """
        Handle MCP Streamable HTTP connection establishment using proper MCP protocol.

        This implements the MCP Streamable HTTP protocol as defined in the MCP SDK.
        For GET requests without session ID, create a new session and return a
        connection response with the session ID header.

        Args:
            req: HTTP request for connection establishment

        Returns:
            Response with session ID header for streamable HTTP protocol
        """
        # Generate session ID for this connection if not provided
        session_id = req.headers.get("mcp-session-id")
        if not session_id:
            session_id = str(uuid.uuid4()).replace("-", "")
            session_status = "Generated new"
        else:
            session_status = "Using existing"

        logger.debug(f"{session_status} MCP session: {session_id}")

        # Ensure STDIO adapter is connected for this session
        if not await self._ensure_connection(session_id, auth_context):
            logger.error("STDIO adapter connection failed during streamable HTTP setup")
            return Response(
                json.dumps({"error": "MCP server connection failed"}),
                status_code=503,
                headers={"Content-Type": "application/json"},
            )

        # Register the session as active
        self._active_sessions[session_id] = True
        logger.debug(
            f"Streamable HTTP setup - adapter connected and session {session_id} registered"
        )

        # For MCP Streamable HTTP, return empty body with session ID in headers only
        # This follows the official MCP Streamable HTTP specification
        response_headers = {
            "mcp-session-id": session_id,  # Essential for MCP protocol
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, mcp-session-id",
            "Access-Control-Expose-Headers": "mcp-session-id",  # Allow client to read this header
        }

        logger.debug(
            f"Streamable HTTP connection established - session: {session_id}, headers: {response_headers}"
        )

        return Response(
            "",  # Empty body for connection establishment (following MCP SDK)
            status_code=200,
            headers=response_headers,
        )

    def _convert_request_to_scope(self, req: Request) -> Dict[str, Any]:
        """
        Convert Azure Functions HttpRequest to ASGI scope.

        Args:
            req: Azure Functions HTTP request

        Returns:
            ASGI scope dictionary
        """
        # Parse URL components
        url = req.url
        path = req.path_params.get("path", "/")
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
            "query_string": (
                req.url.split("?", 1)[1].encode("utf-8") if "?" in req.url else b""
            ),
            "headers": headers,
            "server": ("localhost", 80),
            "client": ("127.0.0.1", 0),
        }

        return scope

    async def cleanup(self) -> None:
        """Clean up resources when the function app is shutting down."""
        logger.info("Cleaning up MCP Function App resources")

        # Clean up session-specific adapters
        for session_id, adapter in self._session_adapters.items():
            logger.info(f"Disconnecting session adapter: {session_id}")
            await adapter.disconnect()
        self._session_adapters.clear()

        # Clean up legacy adapter
        if self.stdio_adapter:
            await self.stdio_adapter.disconnect()
            self.stdio_adapter = None

        # Clear active sessions
        self._active_sessions.clear()

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
        stats["server_name"] = (
            self.current_server_config.name if self.current_server_config else "unknown"
        )
        stats["mode"] = self.mode.value

        return stats

    def _get_adapter(
        self, session_id: Optional[str] = None
    ) -> Optional[MCPStdioAdapter]:
        """
        Get the appropriate STDIO adapter for the session.

        Args:
            session_id: Session ID for streamable HTTP (None for legacy mode)

        Returns:
            The appropriate STDIO adapter or None
        """
        if session_id:
            return self._session_adapters.get(session_id)
        else:
            return self.stdio_adapter
