"""
Session state manager for MCP servers in Azure Functions.

This module provides in-memory session state management to track
MCP protocol initialization across HTTP requests in a stateless environment.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass
class MCPSessionState:
    """Track MCP session initialization state."""

    session_id: str
    is_initialized: bool = False
    initialization_response: Optional[Dict[str, Any]] = None
    last_activity: float = 0.0

    def __post_init__(self):
        self.last_activity = time.time()

    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = time.time()

    def mark_initialized(self, init_response: Dict[str, Any]):
        """Mark session as initialized with the init response."""
        self.is_initialized = True
        self.initialization_response = init_response
        self.update_activity()


class MCPSessionManager:
    """
    In-memory session state manager for MCP servers.

    Tracks initialization state across HTTP requests in Azure Functions
    to provide stateless MCP operation with proper protocol handling.
    """

    def __init__(self, session_timeout_seconds: float = 3600):  # 1 hour default
        self._sessions: Dict[str, MCPSessionState] = {}
        self._session_timeout = session_timeout_seconds
        self._lock = asyncio.Lock()

    async def get_session(self, session_id: str) -> MCPSessionState:
        """
        Get or create a session state.

        Args:
            session_id: Session identifier

        Returns:
            Session state object
        """
        async with self._lock:
            # Clean up expired sessions first
            await self._cleanup_expired_sessions()

            if session_id not in self._sessions:
                logger.debug(f"🆕 Creating new MCP session: {session_id}")
                self._sessions[session_id] = MCPSessionState(session_id)
            else:
                logger.debug(f"📋 Using existing MCP session: {session_id}")
                self._sessions[session_id].update_activity()

            return self._sessions[session_id]

    async def mark_session_initialized(
        self, session_id: str, init_response: Dict[str, Any]
    ):
        """
        Mark a session as initialized.

        Args:
            session_id: Session identifier
            init_response: The initialize method response
        """
        async with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].mark_initialized(init_response)
                logger.debug(f"✅ Marked session {session_id} as initialized")
            else:
                logger.warning(
                    f"⚠️ Attempted to mark unknown session {session_id} as initialized"
                )

    async def is_session_initialized(self, session_id: str) -> bool:
        """
        Check if a session is initialized.

        Args:
            session_id: Session identifier

        Returns:
            True if session is initialized, False otherwise
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            return session.is_initialized if session else False

    async def get_initialization_response(
        self, session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the cached initialization response for a session.

        Args:
            session_id: Session identifier

        Returns:
            Cached initialization response or None
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            return session.initialization_response if session else None

    async def create_stateless_request(
        self, session_id: str, original_message: Dict[str, Any]
    ) -> bytes:
        """
        Create a stateless request that includes initialization if needed.

        For non-initialize requests in uninitialized sessions, this will
        create a combined request with init + initialized + original request.

        Args:
            session_id: Session identifier
            original_message: The original JSON-RPC message

        Returns:
            Framed request bytes ready to send to MCP server
        """
        session = await self.get_session(session_id)

        # If it's an initialize request, just return it as-is
        if original_message.get("method") == "initialize":
            logger.debug(f"🔄 Initialize request for session {session_id}")
            return self._create_frame(original_message)

        # If it's a notification, just return it as-is
        if "id" not in original_message:
            logger.debug(
                f"🔔 Notification for session {session_id}: {original_message.get('method')}"
            )
            return self._create_frame(original_message)

        # For requests in uninitialized sessions, create a stateless sequence
        if not session.is_initialized:
            logger.info(
                f"🔧 Creating stateless request sequence for session {session_id}"
            )
            return await self._create_stateless_sequence(original_message)
        else:
            logger.debug(f"📤 Regular request for initialized session {session_id}")
            return self._create_frame(original_message)

    async def _create_stateless_sequence(
        self, original_message: Dict[str, Any]
    ) -> bytes:
        """
        Create a stateless sequence: init + initialized + original request.

        Args:
            original_message: The original request message

        Returns:
            Combined framed request bytes
        """
        # Create initialize message
        init_message = {
            "jsonrpc": "2.0",
            "id": f"auto-init-{original_message.get('id', 'unknown')}",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {
                    "name": "azure-functions-mcp-adapter",
                    "version": "1.0.0",
                },
            },
        }

        # Create initialized notification
        initialized_message = {"jsonrpc": "2.0", "method": "notifications/initialized"}

        # Combine all frames
        frames = [
            self._create_frame(init_message),
            self._create_frame(initialized_message),
            self._create_frame(original_message),
        ]

        combined = b"".join(frames)
        logger.debug(
            f"📦 Created stateless sequence: {len(combined)} bytes (init + initialized + {original_message.get('method')})"
        )
        return combined

    def _create_frame(self, message: Dict[str, Any]) -> bytes:
        """
        Create a Content-Length framed message.

        Args:
            message: JSON-RPC message

        Returns:
            Framed message bytes
        """
        content = json.dumps(message, separators=(",", ":"))
        content_bytes = content.encode("utf-8")
        frame = f"Content-Length: {len(content_bytes)}\r\n\r\n".encode("utf-8")
        return frame + content_bytes

    async def _cleanup_expired_sessions(self):
        """Clean up expired sessions."""
        current_time = time.time()
        expired_sessions = [
            session_id
            for session_id, session in self._sessions.items()
            if current_time - session.last_activity > self._session_timeout
        ]

        for session_id in expired_sessions:
            logger.debug(f"🧹 Cleaning up expired session: {session_id}")
            del self._sessions[session_id]

    async def get_stats(self) -> Dict[str, Any]:
        """Get session manager statistics."""
        async with self._lock:
            return {
                "total_sessions": len(self._sessions),
                "initialized_sessions": sum(
                    1 for s in self._sessions.values() if s.is_initialized
                ),
                "session_timeout": self._session_timeout,
            }


# Global session manager instance
_session_manager: Optional[MCPSessionManager] = None


def get_session_manager() -> MCPSessionManager:
    """Get the global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = MCPSessionManager()
    return _session_manager
