"""
STDIO adapter for MCP servers.

This module implements the STDIO transport for MCP servers, handling
the line-delimited JSON communication as specified in the MCP specification.
"""

import asyncio
import json
import logging
from typing import Any, Awaitable, Callable, Dict, Optional

from ..auth.token_handler import AuthContext
from ..core.process_manager import ProcessManager
from ..core.session_manager import get_session_manager
from ..models.configuration import MCPStdioConfiguration
from ..models.enums import MCPServerStatus

logger = logging.getLogger(__name__)


class MCPStdioAdapter:
    """
    Adapter for communicating with MCP servers over STDIO.

    This class implements the MCP STDIO transport, handling line-delimited
    JSON communication as specified in the MCP specification.
    """

    def __init__(
        self,
        config: MCPStdioConfiguration,
        message_handler: Optional[
            Callable[[Dict[str, Any]], Awaitable[Optional[Dict[str, Any]]]]
        ] = None,
        auth_context: Optional[AuthContext] = None,
    ):
        """
        Initialize the STDIO adapter.

        Args:
            config: MCP server configuration
            message_handler: Optional handler for processing messages
            auth_context: Authentication context for this session
        """
        self.config = config
        self.message_handler = message_handler
        self.auth_context = auth_context

        # Create process manager with authentication environment variables
        auth_env = self._get_auth_environment_vars()
        self.process_manager = ProcessManager(
            config.name, config.params, auth_env=auth_env
        )

        # Communication state
        self._read_buffer = b""
        self._write_lock = asyncio.Lock()
        self._read_task: Optional[asyncio.Task] = None
        self._is_connected = False

        # Session management for automatic initialization
        self._session_manager: Optional[Any] = None
        self._current_session_id: Optional[str] = None

        # Statistics
        self._messages_sent = 0
        self._messages_received = 0
        self._bytes_sent = 0
        self._bytes_received = 0

    def _get_auth_environment_vars(self) -> Dict[str, str]:
        """
        Get environment variables for authentication.

        Returns:
            Dictionary of environment variables to pass to the MCP server process
        """
        if not self.auth_context:
            return {}

        # Import here to avoid circular imports
        from ..auth.provider_factory import AuthProviderFactory

        try:
            provider = AuthProviderFactory.create_provider(self.config.auth)
            return provider.get_environment_vars(self.auth_context)
        except Exception as e:
            logger.warning(f"Failed to get auth environment vars: {e}")
            return {}

    @property
    def is_connected(self) -> bool:
        """Check if the adapter is connected to the MCP server."""
        # Check both internal state and process state
        process_running = self.process_manager.is_running

        # If process is not running but we think we're connected, update state
        if self._is_connected and not process_running:
            logger.warning(
                f"Process for {self.config.name} is not running, updating connection state"
            )
            self._is_connected = False
            # Cancel read task if it's still running
            if self._read_task and not self._read_task.done():
                self._read_task.cancel()
                self._read_task = None

        return self._is_connected and process_running

    @property
    def status(self) -> MCPServerStatus:
        """Get the current status of the MCP server."""
        return self.process_manager.status

    @property
    def stats(self) -> Dict[str, Any]:
        """Get communication statistics."""
        return {
            "messages_sent": self._messages_sent,
            "messages_received": self._messages_received,
            "bytes_sent": self._bytes_sent,
            "bytes_received": self._bytes_received,
            "uptime": self.process_manager.uptime,
            "status": self.status.value,
        }

    async def connect(self) -> bool:
        """
        Connect to the MCP server.

        Returns:
            True if connected successfully, False otherwise
        """
        # Check current connection state first
        if self.is_connected:
            logger.debug(
                f"Adapter for {self.config.name} is already connected and process is running"
            )
            return True

        # If we think we're connected but process is dead, clean up first
        if self._is_connected and not self.process_manager.is_running:
            logger.debug(f"Cleaning up stale connection for {self.config.name}")
            await self.disconnect()

        logger.debug(f"Connecting to MCP server: {self.config.name}")

        # Start the process
        if not await self.process_manager.start():
            logger.error(f"Failed to start MCP server process: {self.config.name}")
            return False

        try:
            # Only use persistent connections if needed for session state
            if self._use_persistent_connection():
                # Start reading messages for persistent connections
                self._read_task = asyncio.create_task(self._read_messages())
                logger.debug(
                    f"Started persistent connection for MCP server: {self.config.name}"
                )
            else:
                logger.debug(
                    f"Using request-response mode for MCP server: {self.config.name}"
                )

            self._is_connected = True

            logger.debug(f"Successfully connected to MCP server: {self.config.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to MCP server {self.config.name}: {e}")
            await self.disconnect()
            return False

    async def disconnect(self) -> bool:
        """
        Disconnect from the MCP server.

        Returns:
            True if disconnected successfully, False otherwise
        """
        if not self._is_connected:
            return True

        logger.debug(f"Disconnecting from MCP server: {self.config.name}")

        try:
            # Stop reading messages
            if self._read_task and not self._read_task.done():
                self._read_task.cancel()
                try:
                    await self._read_task
                except asyncio.CancelledError:
                    pass

            # Stop the process
            await self.process_manager.stop()

            # Reset state
            self._is_connected = False
            self._read_buffer = b""
            self._read_task = None

            logger.debug(
                f"Successfully disconnected from MCP server: {self.config.name}"
            )
            return True

        except Exception as e:
            logger.error(f"Error disconnecting from MCP server {self.config.name}: {e}")
            return False

    async def send_message_stateless(
        self, message: Dict[str, Any], session_id: Optional[str] = None
    ) -> bool:
        """
        Send a JSON-RPC message using stateless approach with session management.

        Args:
            message: JSON-RPC message dictionary
            session_id: Optional session ID for state tracking

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if session_id:
                # Use session manager for stateless operation
                session_manager = get_session_manager()

                # Create the appropriate request (with auto-init if needed)
                frame_data = await session_manager.create_stateless_request(
                    session_id, message
                )

                logger.debug(
                    f"Sending stateless request for session {session_id}: {message.get('method')} (ID: {message.get('id')})"
                )

                # Send using request-response method
                response_data = (
                    await self.process_manager.send_request_to_persistent_process(
                        frame_data
                    )
                )

                if response_data:
                    self._messages_sent += 1
                    self._bytes_sent += len(frame_data)
                    self._bytes_received += len(response_data)

                    logger.debug(f"Got stateless response: {len(response_data)} bytes")

                    # Handle initialization tracking
                    if message.get("method") == "initialize":
                        await self._handle_initialize_response(
                            session_id, response_data, session_manager
                        )

                    # Process the response
                    await self._process_response_data(response_data)
                    return True
                else:
                    logger.error(f"No response received for stateless request")
                    return False
            else:
                # Fall back to regular send_message for non-session requests
                return await self.send_message(message)

        except Exception as e:
            logger.error(f"Error in stateless message sending: {e}", exc_info=True)
            return False

    async def _handle_initialize_response(
        self, session_id: str, response_data: bytes, session_manager
    ):
        """Handle initialization response to update session state."""
        try:
            # Parse the response to extract the initialize result
            response_str = response_data.decode("utf-8").strip()

            # Look for initialize response in the data
            if response_str.startswith("{") and response_str.endswith("}"):
                response_obj = json.loads(response_str)
                if response_obj.get("id") and "result" in response_obj:
                    await session_manager.mark_session_initialized(
                        session_id, response_obj
                    )
                    logger.debug(f"Session {session_id} marked as initialized")
        except Exception as e:
            logger.error(f"Error handling initialize response: {e}")

    async def send_message(self, message: Dict[str, Any]) -> bool:
        """
        Send a JSON-RPC message to the MCP server.

        Args:
            message: JSON-RPC message dictionary

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_connected:
            logger.error(f"Cannot send message: not connected to {self.config.name}")
            logger.debug(
                f"Connection state - _is_connected: {self._is_connected}, process_running: {self.process_manager.is_running}"
            )
            return False

        try:
            # Serialize the message
            message_json = json.dumps(message, separators=(",", ":"))

            # CRITICAL FIX: MCP servers expect line-delimited JSON, NOT Content-Length framing!
            # Use newline-terminated JSON like the official MCP STDIO implementation
            frame = message_json.encode("utf-8") + b"\n"

            logger.debug(
                f"Sending message to {self.config.name}: {message.get('method', message.get('id', 'unknown'))}"
            )

            # Choose communication mode based on server requirements
            if self._use_persistent_connection():
                return await self._send_persistent(message, frame)
            else:
                return await self._send_request_response(message, frame)

        except Exception as e:
            logger.error(
                f"Error sending message to {self.config.name}: {e}", exc_info=True
            )
            return False

    def _use_persistent_connection(self) -> bool:
        """Check if this MCP server should use persistent connections to maintain protocol state."""
        # For stateless requests, we DO want persistent connections to maintain state
        # across the initialization sequence within a single session

        # Check if this is a session adapter that needs stateless sequence support
        if hasattr(self, "_session_context") or getattr(
            self, "_is_session_adapter", False
        ):
            logger.debug(
                f"Session adapter {self.config.name} - using persistent connection for stateless sequences"
            )
            return True

        # For regular adapters, use persistent connections to properly handle the MCP protocol
        return True  # Use persistent connections to maintain protocol state

    async def _send_persistent(self, message: Dict[str, Any], frame: bytes) -> bool:
        """
        Send data to a persistent process using session-aware request-response.
        For session-based adapters, we use request-response to avoid blocking issues
        but maintain the same process instance across the session.

        Args:
            message: The JSON-RPC message dictionary
            frame: The framed message bytes to send

        Returns:
            True if successful, False otherwise
        """
        if not self.process_manager:
            logger.error("No process manager available for persistent send")
            return False

        try:
            is_notification = "method" in message and message.get("id") is None

            if is_notification:
                logger.debug(
                    f"Sending notification to session process {self.config.name}: {message.get('method')} (no response expected)"
                )
                # For notifications, just send without expecting a response
                success = await self.process_manager.send_input(frame)
                if success:
                    self._messages_sent += 1
                    self._bytes_sent += len(frame)
                return success
            else:
                logger.debug(
                    f"Sending request to session process {self.config.name}: {message.get('method')} (ID: {message.get('id')}) - expecting response"
                )

                # For session adapters, use persistent process method to avoid creating new processes
                # Don't stop the background reader - instead use the regular send and let background reader handle response
                success = await self.process_manager.send_input(frame)
                if success:
                    self._messages_sent += 1
                    self._bytes_sent += len(frame)
                    logger.debug(
                        f"Successfully sent request to persistent process, relying on background reader for response"
                    )
                    return True
                else:
                    logger.error("Failed to send request to persistent process")
                    return False
        except Exception as e:
            logger.error(
                f"Error in session process communication with {self.config.name}: {e}"
            )
            return False

    async def _send_request_response(
        self, message: Dict[str, Any], frame: bytes
    ) -> bool:
        """Send message using request-response mode with optional auto-initialization."""
        try:
            is_notification = "method" in message and message.get("id") is None

            if is_notification:
                logger.debug(
                    f"Sending notification to {self.config.name}: {message.get('method')} (no response expected)"
                )
                # For notifications, just send without expecting a response
                success = await self.process_manager.send_input(frame)
                if success:
                    self._messages_sent += 1
                    self._bytes_sent += len(frame)
                return success
            else:
                logger.debug(
                    f"Sending request to {self.config.name}: {message.get('method')} (ID: {message.get('id')}) - expecting response"
                )

                # For non-initialize requests in session adapters, we might need to include initialization
                if (
                    getattr(self, "_is_session_adapter", False)
                    and message.get("method") != "initialize"
                ):

                    logger.info(
                        f"🔄 Session adapter request for {message.get('method')} - using persistent process"
                    )

                    # CRITICAL FIX: Stop background reader to avoid read conflicts
                    if (
                        hasattr(self, "_read_task")
                        and self._read_task
                        and not self._read_task.done()
                    ):
                        logger.info(
                            f"🛑 Stopping background reader to avoid read conflicts"
                        )
                        self._read_task.cancel()
                        try:
                            await self._read_task
                        except asyncio.CancelledError:
                            pass

                    # For session adapters making non-initialize requests, use persistent process
                    response_data = (
                        await self.process_manager.send_request_to_persistent_process(
                            frame
                        )
                    )

                    # Restart background reader after getting response
                    if (
                        self._use_persistent_connection()
                        and self.process_manager.is_running
                    ):
                        logger.info(f"🔄 Restarting background reader")
                        self._read_task = asyncio.create_task(self._read_messages())
                else:
                    # CRITICAL FIX: Stop background reader to avoid read conflicts
                    if (
                        hasattr(self, "_read_task")
                        and self._read_task
                        and not self._read_task.done()
                    ):
                        logger.info(
                            f"🛑 Stopping background reader to avoid read conflicts"
                        )
                        self._read_task.cancel()
                        try:
                            await self._read_task
                        except asyncio.CancelledError:
                            pass

                    # Regular request-response using persistent process
                    response_data = (
                        await self.process_manager.send_request_to_persistent_process(
                            frame
                        )
                    )

                    # Restart background reader after getting response
                    if (
                        self._use_persistent_connection()
                        and self.process_manager.is_running
                    ):
                        logger.info(f"🔄 Restarting background reader")
                        self._read_task = asyncio.create_task(self._read_messages())

                if response_data:
                    self._messages_sent += 1
                    self._bytes_sent += len(frame)
                    self._bytes_received += len(response_data)

                    logger.debug(
                        f"Got response from {self.config.name}: {len(response_data)} bytes"
                    )

                    # Process the response immediately - this will handle request matching
                    await self._process_response_data(response_data)
                    return True
                else:
                    logger.error(f"No response received from {self.config.name}")
                    return False

        except Exception as e:
            logger.error(
                f"Error in request-response communication with {self.config.name}: {e}"
            )
            return False

    async def _send_streaming(self, frame: bytes) -> bool:
        """Send message using traditional streaming mode."""
        async with self._write_lock:
            success = await self.process_manager.send_input(frame)

            if success:
                self._messages_sent += 1
                self._bytes_sent += len(frame)
                logger.debug(
                    f"Successfully sent message to {self.config.name}: streaming mode"
                )
            else:
                logger.error(
                    f"Failed to send message to {self.config.name} - process manager returned False"
                )

            return success

    async def _process_response_data(self, data: bytes) -> None:
        """Process response data from request-response mode."""
        try:
            logger.info(f"Processing response data: {len(data)} bytes: {data}")

            # Check if this looks like raw JSON (from git servers) or Content-Length framed data
            if self._is_raw_json_response(data):
                logger.info("Detected raw JSON response, processing directly")
                await self._process_raw_json_response(data)
            else:
                logger.info(
                    "Detected Content-Length framed response, using buffer processing"
                )
                # Add to buffer and process normally
                self._read_buffer += data
                logger.info(
                    f"Buffer now contains: {len(self._read_buffer)} bytes: {self._read_buffer}"
                )
                await self._process_buffer()
        except Exception as e:
            logger.error(f"Error processing response data from {self.config.name}: {e}")
            import traceback

            traceback.print_exc()

    def _is_raw_json_response(self, data: bytes) -> bool:
        """Check if response data is line-delimited JSON (which is what MCP servers use)."""
        try:
            # MCP servers send line-delimited JSON, so check if it looks like JSON lines
            data_str = data.decode("utf-8").strip()
            # Handle both single JSON lines and multiple JSON lines
            lines = data_str.split("\n")
            for line in lines:
                line = line.strip()
                if line and (line.startswith("{") and line.endswith("}")):
                    return True
            return False
        except:
            return False

    async def _process_raw_json_response(self, data: bytes) -> None:
        """Process line-delimited JSON response data from MCP servers."""
        try:
            # Decode and process each JSON line
            data_str = data.decode("utf-8").strip()
            lines = data_str.split("\n")

            for line in lines:
                line = line.strip()
                if not line:
                    continue

                try:
                    message = json.loads(line)
                    self._messages_received += 1
                    logger.info(
                        f"Received JSON line from {self.config.name}: {json.dumps(message, indent=2)}"
                    )

                    # Handle the message directly
                    if self.message_handler:
                        try:
                            await self.message_handler(message)
                            logger.debug(
                                f"Message handler processed message for {self.config.name}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Error in message handler for {self.config.name}: {e}"
                            )
                    else:
                        logger.warning(
                            f"No message handler registered for {self.config.name}"
                        )

                except json.JSONDecodeError as e:
                    logger.error(
                        f"Failed to parse JSON line from {self.config.name}: {e} - Line: {line}"
                    )
                    continue

        except Exception as e:
            logger.error(
                f"Error processing line-delimited JSON from {self.config.name}: {e}"
            )

    async def send_stateless_request(
        self, message: Dict[str, Any], session_id: str, session_manager
    ) -> Optional[Dict[str, Any]]:
        """
        Send a JSON-RPC message using stateless approach with persistent process.

        SIMPLIFIED VERSION: Focus on initialization flow first.
        1. Start and keep one MCP server process running
        2. Handle initialization sequence if needed
        3. Send the actual request

        Args:
            message: JSON-RPC message dictionary
            session_id: Session ID for state tracking
            session_manager: Session manager instance

        Returns:
            Response data dictionary, or None if failed
        """
        try:
            # Set session tracking for background reader
            self._session_manager = session_manager
            self._current_session_id = session_id
            # Step 1: Ensure we have a persistent connection
            if not self.is_connected:
                logger.debug(
                    f"Starting persistent MCP server process for session {session_id}"
                )
                if not await self.connect():
                    logger.error(f"Failed to start MCP server process")
                    return None
                logger.debug(f"MCP server process started and connected")

            # Step 2: Check if session needs initialization
            session = await session_manager.get_session(session_id)

            logger.debug(
                f"Session {session_id}: is_initialized={session.is_initialized}, method={message.get('method')}"
            )

            if not session.is_initialized and message.get("method") != "initialize":
                logger.debug(
                    f"Session {session_id} needs initialization - starting init sequence"
                )

                # Send initialize request
                init_result = await self._send_initialize_sequence(
                    session_id, session_manager
                )
                if not init_result:
                    logger.error(f"Initialization failed for session {session_id}")
                    return None

                logger.debug(f"Session {session_id} initialization complete")

            # Step 3: Send the actual request and capture response
            logger.debug(
                f"Sending request: {message.get('method')} (ID: {message.get('id')})"
            )

            # Set up response capture for this specific request
            request_id = message.get("id")
            response_received = asyncio.Event()
            captured_response = None

            # Temporarily override the message handler to capture our response
            original_handler = self.message_handler

            async def response_capture_handler(
                incoming_message: Dict[str, Any]
            ) -> Optional[Dict[str, Any]]:
                nonlocal captured_response, response_received

                logger.info(
                    f"📨 Response handler got message: ID={incoming_message.get('id')}, method={incoming_message.get('method')}"
                )

                # Check if this is the response to our request
                if incoming_message.get("id") == request_id and (
                    "result" in incoming_message or "error" in incoming_message
                ):
                    captured_response = incoming_message
                    response_received.set()
                    logger.debug(f"Captured response for request {request_id}")

                # Still call the original handler if it exists
                if original_handler:
                    return await original_handler(incoming_message)
                return None

            # Temporarily set our capture handler
            self.message_handler = response_capture_handler

            try:
                # Send the request using the PERSISTENT process, NOT request-response mode
                # Serialize the message
                message_json = json.dumps(message, separators=(",", ":"))

                # Use line-delimited JSON for MCP servers
                frame = message_json.encode("utf-8") + b"\n"

                logger.debug(
                    f"Sending to PERSISTENT process: {message.get('method')} (ID: {message.get('id')})"
                )

                # Send directly to the persistent process stdin
                success = await self.process_manager.send_input(frame)
                if not success:
                    logger.error(
                        f"Failed to send message {message.get('method')} to persistent process"
                    )
                    return None

                # For requests (not notifications), rely on background reader to capture response
                if message.get("id") is not None:
                    logger.debug(
                        f"Waiting for background reader to capture response for request {message.get('id')}"
                    )
                    # The background reader (_read_messages) will process the response
                    # and call our response_capture_handler when it arrives

                # Wait for the response with a shorter timeout for testing
                try:
                    await asyncio.wait_for(response_received.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    logger.error(
                        f"⏰ Timeout waiting for response to {message.get('method')}"
                    )
                    # Let's return what we have for debugging
                    return {
                        "jsonrpc": "2.0",
                        "id": message.get("id"),
                        "error": {
                            "code": -32603,
                            "message": "Timeout waiting for response",
                            "data": "",
                        },
                    }

                if captured_response:
                    logger.debug(
                        f"Got real response for {message.get('method')}: {captured_response}"
                    )
                    return captured_response
                else:
                    logger.error(f"No response captured for {message.get('method')}")
                    return {
                        "jsonrpc": "2.0",
                        "id": message.get("id"),
                        "error": {
                            "code": -32603,
                            "message": "No response received",
                            "data": "",
                        },
                    }

            finally:
                # Restore the original handler
                self.message_handler = original_handler

        except Exception as e:
            logger.error(f"Error in stateless request: {e}", exc_info=True)
            return None

    async def _send_initialize_sequence(self, session_id: str, session_manager) -> bool:
        """
        Send the MCP initialization sequence to the persistent process.

        Args:
            session_id: Session identifier
            session_manager: Session manager instance

        Returns:
            True if initialization succeeded, False otherwise
        """
        try:
            # Step 1: Send initialize request
            init_message = {
                "jsonrpc": "2.0",
                "id": f"init-{session_id[:8]}",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                    "clientInfo": {
                        "name": "azurefunctions-mcp-adapter",
                        "version": "1.0.0",
                    },
                },
            }

            logger.debug(f"Sending initialize request to persistent process")

            # Serialize the message
            message_json = json.dumps(init_message, separators=(",", ":"))

            # Use line-delimited JSON for MCP servers
            frame = message_json.encode("utf-8") + b"\n"

            # Send directly to the persistent process stdin
            success = await self.process_manager.send_input(frame)
            if not success:
                logger.error(f"Failed to send initialize message to persistent process")
                return False

            # The initialize response will be captured by the background reader
            logger.debug(
                f"Initialize request sent, background reader will capture response"
            )
            # No direct reading needed - the background reader (_read_messages) will process it

            # Wait for initialize to be processed
            await asyncio.sleep(0.3)

            # Step 2: Send notifications/initialized
            initialized_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
            }

            logger.debug(f"Sending notifications/initialized to persistent process")

            # Serialize the notification
            message_json = json.dumps(initialized_notification, separators=(",", ":"))

            # Use line-delimited JSON for MCP servers
            frame = message_json.encode("utf-8") + b"\n"

            # Send directly to the persistent process stdin
            await self.process_manager.send_input(frame)

            # Wait for notification to be processed
            await asyncio.sleep(0.3)

            logger.debug(f"Initialization sequence complete for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error in initialization sequence: {e}", exc_info=True)
            return False

    async def _parse_single_response(
        self, response_data: bytes, expected_id
    ) -> Optional[Dict[str, Any]]:
        """Parse line-delimited JSON response data and return the response for the expected ID."""
        try:
            response_str = response_data.decode("utf-8").strip()

            # Parse line-delimited JSON responses
            lines = response_str.split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                try:
                    response_obj = json.loads(line)
                    if response_obj.get("id") == expected_id or expected_id is None:
                        return response_obj
                except json.JSONDecodeError:
                    continue

            logger.warning(f"No matching response found for ID: {expected_id}")
            return None

        except Exception as e:
            logger.error(f"Error parsing response: {e}", exc_info=True)
            return None

    async def _parse_final_response(
        self, response_data: bytes, request_id
    ) -> Optional[Dict[str, Any]]:
        """Parse line-delimited JSON response data and return the matching response for the request ID."""
        try:
            response_str = response_data.decode("utf-8").strip()
            logger.debug(
                f"Parsing response data for request ID {request_id}: {response_str}"
            )

            # Parse line-delimited JSON responses
            responses = []
            for line in response_str.split("\n"):
                line = line.strip()
                if line and line.startswith("{"):
                    try:
                        response_obj = json.loads(line)
                        responses.append(response_obj)
                        logger.info(
                            f"📄 Parsed response: ID={response_obj.get('id')}, method={response_obj.get('method')}"
                        )
                    except json.JSONDecodeError:
                        continue

            logger.info(f"📊 Found {len(responses)} total responses")

            # Look for the response that matches our original request ID
            for response_obj in responses:
                response_id = response_obj.get("id")
                logger.debug(
                    f"Checking response ID {response_id} against request ID {request_id}"
                )

                if response_id == request_id:
                    logger.debug(f"Found matching response for request ID {request_id}")
                    return response_obj

            # If no exact match, look for error responses or the last response with result/error
            for response_obj in responses:
                if (
                    "result" in response_obj or "error" in response_obj
                ) and response_obj.get("id") is not None:
                    logger.info(
                        f"🎯 Using response with result/error: ID={response_obj.get('id')}"
                    )
                    return response_obj

            logger.warning(
                f"❌ No matching response found for request ID: {request_id}"
            )
            logger.info(f"Available responses: {[r.get('id') for r in responses]}")
            return None

        except Exception as e:
            logger.error(f"Error parsing final response: {e}", exc_info=True)
            return None

    async def send_message_old(self, message: Dict[str, Any]) -> bool:
        """
        Send a JSON-RPC message to the MCP server.

        Args:
            message: JSON-RPC message dictionary

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_connected:
            logger.error(f"Cannot send message: not connected to {self.config.name}")
            logger.debug(
                f"Connection state - _is_connected: {self._is_connected}, process_running: {self.process_manager.is_running}"
            )
            return False

        try:
            # Serialize the message
            message_json = json.dumps(message, separators=(",", ":"))

            # Use line-delimited JSON for MCP servers
            frame = message_json.encode("utf-8") + b"\n"

            logger.debug(
                f"Sending message to {self.config.name}: {message.get('method', message.get('id', 'unknown'))}"
            )

            # Send with write lock to prevent interleaving
            async with self._write_lock:
                success = await self.process_manager.send_input(frame)

                if success:
                    self._messages_sent += 1
                    self._bytes_sent += len(frame)
                    logger.debug(
                        f"Successfully sent message to {self.config.name}: {message.get('method', 'response')}"
                    )
                else:
                    logger.error(
                        f"Failed to send message to {self.config.name} - process manager returned False"
                    )

                return success

        except Exception as e:
            logger.error(
                f"Error sending message to {self.config.name}: {e}", exc_info=True
            )
            return False

    async def _read_messages(self) -> None:
        """
        Continuously read and process messages from the MCP server.
        """
        logger.debug(f"Started reading messages from {self.config.name}")

        try:
            while self._is_connected:
                # Check if process is still running before attempting to read
                if not self.process_manager.is_running:
                    logger.warning(
                        f"Process for {self.config.name} is no longer running, stopping message reading"
                    )
                    self._is_connected = False
                    break

                logger.debug(f"Attempting to read from {self.config.name} process...")
                # Read data from the process
                data = await self.process_manager.read_output(8192)
                logger.debug(
                    f"Read attempt result for {self.config.name}: data={data}, length={len(data) if data else 'None'}"
                )

                if data is None:
                    # EOF or error - process might have died
                    logger.warning(
                        f"EOF received from {self.config.name}, checking process status"
                    )
                    if not self.process_manager.is_running:
                        logger.error(f"Process for {self.config.name} has died")
                        self._is_connected = False
                    break

                if len(data) == 0:
                    # No data available right now, continue polling
                    logger.debug(
                        f"No data available from {self.config.name}, sleeping..."
                    )
                    await asyncio.sleep(0.01)
                    continue

                logger.debug(
                    f"Read {len(data)} bytes from {self.config.name}: {data[:200]}..."
                )
                self._bytes_received += len(data)
                self._read_buffer += data

                # Process complete messages in the buffer
                await self._process_buffer()

        except asyncio.CancelledError:
            logger.debug(f"Message reading cancelled for {self.config.name}")
        except Exception as e:
            logger.error(f"Error reading messages from {self.config.name}: {e}")
            # Mark as disconnected on error
            self._is_connected = False
        finally:
            logger.debug(f"Stopped reading messages from {self.config.name}")
            # Ensure we're marked as disconnected when read task ends
            if self._is_connected:
                logger.info(
                    f"Marking {self.config.name} as disconnected after read task ended"
                )
                self._is_connected = False

    async def _process_buffer(self) -> None:
        """
        Process the read buffer for complete messages.
        Now handles line-delimited JSON from MCP servers.
        """
        logger.debug(
            f"Processing buffer for {self.config.name}, buffer size: {len(self._read_buffer)}"
        )
        logger.debug(f"Buffer content: {self._read_buffer[:200]}...")

        # Convert buffer to string and process line by line
        try:
            buffer_str = self._read_buffer.decode("utf-8")
            lines = buffer_str.split("\n")

            # Process complete lines (all but the last, which might be incomplete)
            complete_lines = lines[:-1]
            remaining_line = lines[-1]

            for line in complete_lines:
                line = line.strip()
                if not line:
                    continue

                try:
                    # Parse JSON line
                    message = json.loads(line)
                    self._messages_received += 1
                    logger.debug(
                        f"Received complete message from {self.config.name}: {json.dumps(message, indent=2)}"
                    )

                    # Handle the message
                    if self.message_handler:
                        await self._handle_message(message)
                    else:
                        logger.warning(f"No message handler for {self.config.name}")

                except json.JSONDecodeError as e:
                    logger.error(
                        f"Error parsing JSON line from {self.config.name}: {e}"
                    )
                    logger.debug(f"Invalid line: {line}")
                    continue

            # Update buffer with remaining incomplete line
            self._read_buffer = remaining_line.encode("utf-8")

        except UnicodeDecodeError as e:
            logger.error(f"Error decoding buffer for {self.config.name}: {e}")
            # Reset buffer on decode error
            self._read_buffer = b""

    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """
        Handle a received message.

        Args:
            message: Parsed JSON-RPC message
        """
        try:
            # Check if this is an initialize response that we need to handle for session management
            if (
                message.get("id")
                and "result" in message
                and self._session_manager
                and self._current_session_id
            ):

                # Check if this looks like an initialize response
                result = message.get("result", {})
                if (
                    isinstance(result, dict)
                    and "protocolVersion" in result
                    and "capabilities" in result
                ):
                    logger.debug(
                        f"🔧 Auto-handling initialize response for session {self._current_session_id}"
                    )
                    await self._session_manager.mark_session_initialized(
                        self._current_session_id, message
                    )

            # Call the regular message handler
            if self.message_handler:
                response = await self.message_handler(message)
                if response:
                    await self.send_message(response)
        except Exception as e:
            logger.error(f"Error handling message from {self.config.name}: {e}")

    async def send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> bool:
        """
        Send a JSON-RPC request message.

        Args:
            method: RPC method name
            params: Optional parameters
            request_id: Optional request ID

        Returns:
            True if sent successfully, False otherwise
        """
        message = {
            "jsonrpc": "2.0",
            "method": method,
        }

        if params is not None:
            message["params"] = params

        if request_id is not None:
            message["id"] = request_id

        return await self.send_message(message)

    async def send_response(
        self,
        request_id: str,
        result: Optional[Any] = None,
        error: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Send a JSON-RPC response message.

        Args:
            request_id: ID of the request being responded to
            result: Response result (if successful)
            error: Error information (if failed)

        Returns:
            True if sent successfully, False otherwise
        """
        message = {
            "jsonrpc": "2.0",
            "id": request_id,
        }

        if error is not None:
            message["error"] = error
        else:
            message["result"] = result

        return await self.send_message(message)

    async def send_notification(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send a JSON-RPC notification message.

        Args:
            method: RPC method name
            params: Optional parameters

        Returns:
            True if sent successfully, False otherwise
        """
        message = {
            "jsonrpc": "2.0",
            "method": method,
        }

        if params is not None:
            message["params"] = params

        return await self.send_message(message)
