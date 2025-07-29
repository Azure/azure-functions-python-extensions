"""
STDIO adapter for MCP servers.

This module implements the STDIO transport for MCP servers, handling
the JSON-RPC communication over stdin/stdout with Content-Length framing
as specified in the MCP specification.
"""

import asyncio
import json
import logging
import re
from typing import Dict, Optional, Any, Callable, Awaitable

from ..core.process_manager import ProcessManager
from ..models.configuration import MCPStdioConfiguration
from ..models.enums import MCPServerStatus

logger = logging.getLogger(__name__)

# Content-Length header pattern as per MCP/LSP specification
CONTENT_LENGTH_PATTERN = re.compile(rb'Content-Length: (\d+)\r?\n\r?\n', re.IGNORECASE)


class MCPStdioAdapter:
    """
    Adapter for communicating with MCP servers over STDIO.
    
    This class implements the MCP STDIO transport, handling the Content-Length
    framing protocol and JSON-RPC message serialization/deserialization.
    """
    
    def __init__(
        self,
        config: MCPStdioConfiguration,
        message_handler: Optional[Callable[[Dict[str, Any]], Awaitable[Optional[Dict[str, Any]]]]] = None
    ):
        """
        Initialize the STDIO adapter.
        
        Args:
            config: MCP server configuration
            message_handler: Optional handler for processing messages
        """
        self.config = config
        self.message_handler = message_handler
        self.process_manager = ProcessManager(config.name, config.params)
        
        # Communication state
        self._read_buffer = b''
        self._write_lock = asyncio.Lock()
        self._read_task: Optional[asyncio.Task] = None
        self._is_connected = False
        
        # Statistics
        self._messages_sent = 0
        self._messages_received = 0
        self._bytes_sent = 0
        self._bytes_received = 0
    
    @property
    def is_connected(self) -> bool:
        """Check if the adapter is connected to the MCP server."""
        return self._is_connected and self.process_manager.is_running
    
    @property
    def status(self) -> MCPServerStatus:
        """Get the current status of the MCP server."""
        return self.process_manager.status
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get communication statistics."""
        return {
            'messages_sent': self._messages_sent,
            'messages_received': self._messages_received,
            'bytes_sent': self._bytes_sent,
            'bytes_received': self._bytes_received,
            'uptime': self.process_manager.uptime,
            'status': self.status.value,
        }
    
    async def connect(self) -> bool:
        """
        Connect to the MCP server.
        
        Returns:
            True if connected successfully, False otherwise
        """
        if self._is_connected:
            logger.warning(f"Adapter for {self.config.name} is already connected")
            return True
        
        logger.info(f"Connecting to MCP server: {self.config.name}")
        
        # Start the process
        if not await self.process_manager.start():
            logger.error(f"Failed to start MCP server process: {self.config.name}")
            return False
        
        try:
            # Start reading messages
            self._read_task = asyncio.create_task(self._read_messages())
            self._is_connected = True
            
            logger.info(f"Successfully connected to MCP server: {self.config.name}")
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
        
        logger.info(f"Disconnecting from MCP server: {self.config.name}")
        
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
            self._read_buffer = b''
            self._read_task = None
            
            logger.info(f"Successfully disconnected from MCP server: {self.config.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from MCP server {self.config.name}: {e}")
            return False
    
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
            logger.debug(f"Connection state - _is_connected: {self._is_connected}, process_running: {self.process_manager.is_running}")
            return False
        
        try:
            # Serialize the message
            message_json = json.dumps(message, separators=(',', ':'))
            message_bytes = message_json.encode('utf-8')
            
            # Create Content-Length frame
            content_length = len(message_bytes)
            frame = f"Content-Length: {content_length}\r\n\r\n".encode('utf-8')
            frame += message_bytes
            
            logger.debug(f"Sending message to {self.config.name}: {message.get('method', message.get('id', 'unknown'))}")
            
            # Send with write lock to prevent interleaving
            async with self._write_lock:
                success = await self.process_manager.send_input(frame)
                
                if success:
                    self._messages_sent += 1
                    self._bytes_sent += len(frame)
                    logger.debug(f"Successfully sent message to {self.config.name}: {message.get('method', 'response')}")
                else:
                    logger.error(f"Failed to send message to {self.config.name} - process manager returned False")
                
                return success
                
        except Exception as e:
            logger.error(f"Error sending message to {self.config.name}: {e}", exc_info=True)
            return False
    
    async def _read_messages(self) -> None:
        """
        Continuously read and process messages from the MCP server.
        """
        logger.debug(f"Started reading messages from {self.config.name}")
        
        try:
            while self._is_connected:
                # Read data from the process
                data = await self.process_manager.read_output(8192)
                
                if data is None:
                    # EOF or error
                    logger.warning(f"EOF received from {self.config.name}")
                    break
                
                if len(data) == 0:
                    # No data available, continue
                    await asyncio.sleep(0.01)
                    continue
                
                self._bytes_received += len(data)
                self._read_buffer += data
                
                # Process complete messages in the buffer
                await self._process_buffer()
                
        except asyncio.CancelledError:
            logger.debug(f"Message reading cancelled for {self.config.name}")
        except Exception as e:
            logger.error(f"Error reading messages from {self.config.name}: {e}")
        finally:
            logger.debug(f"Stopped reading messages from {self.config.name}")
    
    async def _process_buffer(self) -> None:
        """
        Process the read buffer for complete messages.
        """
        while True:
            # Look for Content-Length header
            match = CONTENT_LENGTH_PATTERN.search(self._read_buffer)
            if not match:
                # No complete header found
                break
            
            # Extract content length
            content_length = int(match.group(1))
            header_end = match.end()
            
            # Check if we have the complete message
            if len(self._read_buffer) < header_end + content_length:
                # Incomplete message, wait for more data
                break
            
            # Extract the message
            message_bytes = self._read_buffer[header_end:header_end + content_length]
            
            # Remove processed data from buffer
            self._read_buffer = self._read_buffer[header_end + content_length:]
            
            # Parse and handle the message
            try:
                message_json = message_bytes.decode('utf-8')
                message = json.loads(message_json)
                
                self._messages_received += 1
                logger.debug(f"Received message from {self.config.name}: {message.get('method', 'response')}")
                
                # Handle the message
                if self.message_handler:
                    asyncio.create_task(self._handle_message(message))
                    
            except Exception as e:
                logger.error(f"Error parsing message from {self.config.name}: {e}")
                logger.debug(f"Invalid message bytes: {message_bytes[:100]}...")
    
    async def _handle_message(self, message: Dict[str, Any]) -> None:
        """
        Handle a received message.
        
        Args:
            message: Parsed JSON-RPC message
        """
        try:
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
        request_id: Optional[str] = None
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
            'jsonrpc': '2.0',
            'method': method,
        }
        
        if params is not None:
            message['params'] = params
        
        if request_id is not None:
            message['id'] = request_id
        
        return await self.send_message(message)
    
    async def send_response(
        self, 
        request_id: str, 
        result: Optional[Any] = None,
        error: Optional[Dict[str, Any]] = None
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
            'jsonrpc': '2.0',
            'id': request_id,
        }
        
        if error is not None:
            message['error'] = error
        else:
            message['result'] = result
        
        return await self.send_message(message)
    
    async def send_notification(
        self, 
        method: str, 
        params: Optional[Dict[str, Any]] = None
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
            'jsonrpc': '2.0',
            'method': method,
        }
        
        if params is not None:
            message['params'] = params
        
        return await self.send_message(message)
