"""
Process manager for MCP STDIO servers.

This module handles the lifecycle management of MCP server processes,
including starting, monitoring, and stopping processes with proper
error handling and recovery.
"""

import asyncio
import logging
import os
import shutil
import signal
import subprocess
import time
import uuid
from typing import Dict, List, Optional, Union

from ..models.configuration import MCPServerStdioParams
from ..models.enums import MCPServerStatus

logger = logging.getLogger(__name__)


class ProcessManager:
    """
    Manages the lifecycle of MCP server processes.

    This class handles starting, monitoring, and stopping MCP server processes
    with proper error handling, timeout management, and restart capabilities.
    """

    def __init__(
        self,
        name: str,
        params: MCPServerStdioParams,
        process_id: Optional[str] = None,
        auth_env: Optional[Dict[str, str]] = None,
    ):
        """
        Initialize the process manager.

        Args:
            name: Unique name for the MCP server
            params: Server execution parameters
            process_id: Optional process ID for tracking
            auth_env: Optional authentication environment variables
        """
        self.name = name
        self.params = params
        self.process_id = process_id or f"mcp-{name}-{uuid.uuid4().hex[:8]}"
        self.auth_env = auth_env or {}

        self._process: Optional[asyncio.subprocess.Process] = None
        self._status = MCPServerStatus.STOPPED
        self._restart_count = 0
        self._start_time: Optional[float] = None
        self._stop_event = asyncio.Event()

        # Validate uvx availability if needed
        if params.command == "uvx":
            self._validate_uvx()

    @property
    def status(self) -> MCPServerStatus:
        """Get the current status of the MCP server process."""
        return self._status

    @property
    def process(self) -> Optional[asyncio.subprocess.Process]:
        """Get the underlying process object."""
        return self._process

    @property
    def is_running(self) -> bool:
        """Check if the process is currently running."""
        return (
            self._process is not None
            and self._process.returncode is None
            and self._status == MCPServerStatus.RUNNING
        )

    @property
    def uptime(self) -> Optional[float]:
        """Get the uptime in seconds, or None if not running."""
        if self._start_time is None or not self.is_running:
            return None
        return time.time() - self._start_time

    async def start(self) -> bool:
        """
        Start the MCP server process.

        Returns:
            True if started successfully, False otherwise
        """
        if self.is_running:
            logger.warning(f"Process {self.name} is already running")
            return True

        logger.debug(f"🔧 Starting MCP server process: {self.name}")
        logger.debug(f"🆔 Process Manager ID: {self.process_id}")
        self._status = MCPServerStatus.STARTING

        try:
            # Build the command
            cmd = self._build_command()
            env = self._build_environment()
            cwd = self.params.working_dir

            logger.debug(f"📋 Executing command: {' '.join(cmd)}")
            logger.debug(f"Working directory: {cwd}")
            logger.debug(f"Environment variables: {list(env.keys())}")

            # Start the process
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=cwd,
                preexec_fn=None if os.name == "nt" else os.setsid,
            )

            # Wait a bit to ensure the process started successfully
            await asyncio.sleep(0.5)

            if self._process.returncode is not None:
                # Process exited immediately
                if self._process.stderr:
                    stderr = await self._process.stderr.read()
                    error_msg = stderr.decode("utf-8", errors="ignore")
                else:
                    error_msg = "Unknown error - no stderr available"
                raise RuntimeError(f"Process exited immediately: {error_msg}")

            self._status = MCPServerStatus.RUNNING
            self._start_time = time.time()
            logger.debug(f"Successfully started MCP server: {self.name}")
            logger.debug(
                f"Process Manager ID: {self.process_id}, System PID: {self._process.pid}"
            )

            # Start monitoring the process
            asyncio.create_task(self._monitor_process())

            return True

        except Exception as e:
            logger.error(f"Failed to start MCP server {self.name}: {e}")
            self._status = MCPServerStatus.FAILED
            await self._cleanup_process()
            return False

    async def stop(self, timeout: float = 10.0) -> bool:
        """
        Stop the MCP server process gracefully.

        Args:
            timeout: Maximum time to wait for graceful shutdown

        Returns:
            True if stopped successfully, False otherwise
        """
        if not self.is_running:
            logger.debug(f"Process {self.name} is not running")
            return True

        logger.debug(f"Stopping MCP server process: {self.name}")
        self._status = MCPServerStatus.STOPPING
        self._stop_event.set()

        try:
            # First, try graceful shutdown
            if self._process and self._process.returncode is None:
                logger.debug(f"Sending SIGTERM to process {self._process.pid}")

                if os.name == "nt":
                    # Windows
                    self._process.terminate()
                else:
                    # Unix-like systems
                    try:
                        os.killpg(self._process.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        # Process might have already exited
                        pass

                # Wait for graceful shutdown
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=timeout)
                    logger.debug(f"Process {self.name} stopped gracefully")
                except asyncio.TimeoutError:
                    logger.warning(
                        f"Process {self.name} did not stop gracefully, forcing..."
                    )

                    # Force kill
                    if self._process.returncode is None:
                        if os.name == "nt":
                            self._process.kill()
                        else:
                            try:
                                os.killpg(self._process.pid, signal.SIGKILL)
                            except ProcessLookupError:
                                pass

                        # Wait a bit more
                        try:
                            await asyncio.wait_for(self._process.wait(), timeout=5.0)
                        except asyncio.TimeoutError:
                            logger.error(f"Failed to kill process {self.name}")
                            return False

            await self._cleanup_process()
            self._status = MCPServerStatus.STOPPED
            logger.debug(f"Successfully stopped MCP server: {self.name}")
            return True

        except Exception as e:
            logger.error(f"Error stopping MCP server {self.name}: {e}")
            return False

    async def restart(self) -> bool:
        """
        Restart the MCP server process.

        Returns:
            True if restarted successfully, False otherwise
        """
        logger.debug(f"Restarting MCP server: {self.name}")

        # Stop the current process
        if not await self.stop():
            logger.error(f"Failed to stop process {self.name} for restart")
            return False

        # Wait a bit before restarting
        await asyncio.sleep(1.0)

        # Start the process again
        return await self.start()

    async def send_input(self, data: bytes) -> bool:
        """
        Send data to the process stdin.

        Args:
            data: Data to send

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_running or not self._process or not self._process.stdin:
            logger.error(f"Cannot send input to {self.name}: process not running")
            logger.debug(
                f"Process state - is_running: {self.is_running}, process: {self._process is not None}, stdin: {self._process.stdin is not None if self._process else 'N/A'}"
            )
            return False

        try:
            # Check if process is still alive
            if self._process.returncode is not None:
                logger.error(
                    f"Process {self.name} has terminated with return code: {self._process.returncode}"
                )
                self._status = MCPServerStatus.FAILED
                return False

            # Log what we're sending for debugging
            logger.debug(f"Sending {len(data)} bytes to {self.name} stdin: {data}")

            self._process.stdin.write(data)
            await self._process.stdin.drain()

            logger.debug(f"Successfully sent {len(data)} bytes to {self.name}")

            # Also check stderr immediately after sending to see if there are any errors
            try:
                # Non-blocking read of stderr to see if there are any immediate errors
                if self._process.stderr:
                    stderr_data = await asyncio.wait_for(
                        self._process.stderr.read(1024), timeout=0.1
                    )
                    if stderr_data:
                        logger.warning(
                            f"stderr from {self.name}: {stderr_data.decode('utf-8', errors='ignore')}"
                        )
            except asyncio.TimeoutError:
                # No stderr data, which is normal
                pass

            return True
        except Exception as e:
            logger.error(f"Error sending input to {self.name}: {e}", exc_info=True)
            # Process might have died, update status
            if self._process and self._process.returncode is not None:
                self._status = MCPServerStatus.FAILED
            return False

    async def read_output(self, max_bytes: int = 8192) -> Optional[bytes]:
        """
        Read data from process stdout.

        Args:
            max_bytes: Maximum bytes to read

        Returns:
            Data read, or None if error/EOF
        """
        if not self.is_running or not self._process or not self._process.stdout:
            logger.debug(
                f"Cannot read from {self.name}: is_running={self.is_running}, process={self._process is not None}, stdout={self._process.stdout is not None if self._process else 'N/A'}"
            )
            return None

        try:
            logger.debug(f"Attempting to read from {self.name} stdout...")

            # For MCP servers, we need to be more patient as they may take time to respond
            # Use a longer timeout but not blocking indefinitely
            try:
                # Use 5 second timeout for MCP responses - they can take time to initialize
                data = await asyncio.wait_for(
                    self._process.stdout.read(max_bytes), timeout=5.0
                )
                if data:
                    logger.debug(
                        f"Read {len(data)} bytes from {self.name}: {data[:100]}..."
                    )
                    return data
                else:
                    logger.debug(f"EOF received from {self.name}")
                    return None
            except asyncio.TimeoutError:
                # No data available within timeout - return empty to continue polling
                logger.debug(
                    f"No data received from {self.name} within 5 second timeout"
                )
                return b""  # Return empty bytes instead of None to indicate no data but no error

        except Exception as e:
            logger.error(f"Error reading output from {self.name}: {e}")
            return None

    def _validate_uvx(self) -> None:
        """
        Validate that uvx is available when needed.

        Raises:
            RuntimeError: If uvx is not found
        """
        if not shutil.which("uvx"):
            raise RuntimeError(
                "uvx not found in PATH. Please install uv and ensure 'uvx' is available. "
                "See https://docs.astral.sh/uv/guides/tools/ for installation instructions."
            )

    def _build_command(self) -> List[str]:
        """
        Build the command line for the process.

        Returns:
            List of command line arguments
        """
        cmd = [self.params.command]
        cmd.extend(self.params.args)
        return cmd

    def _build_environment(self) -> Dict[str, str]:
        """
        Build the environment variables for the process.

        Returns:
            Dictionary of environment variables
        """
        env = os.environ.copy()
        env.update(self.params.env)

        # Add authentication environment variables
        logger.info(f"=== PROCESS MANAGER: Adding {len(self.auth_env)} auth environment variables ===")
        for key, value in self.auth_env.items():
            masked_value = value[:10] + "..." if len(value) > 10 else value
            logger.info(f"Auth env: {key} = {masked_value}")
        
        env.update(self.auth_env)

        # Add some environment variables that might help with subprocess interaction
        # Force line buffering which might help with uvx subprocess behavior
        env["PYTHONUNBUFFERED"] = "1"
        # Ensure we have a proper TERM setting
        if "TERM" not in env:
            env["TERM"] = "xterm-256color"
            
        # Debug: Log Azure-specific environment variables that will be passed to subprocess
        azure_vars_in_env = {k: v for k, v in env.items() if any(prefix in k.upper() for prefix in ["AZURE", "IDENTITY", "MSI"])}
        logger.info(f"=== SUBPROCESS WILL RECEIVE {len(azure_vars_in_env)} AZURE ENVIRONMENT VARIABLES ===")
        for key in sorted(azure_vars_in_env.keys()):
            masked_value = azure_vars_in_env[key][:10] + "..." if len(azure_vars_in_env[key]) > 10 else azure_vars_in_env[key]
            logger.info(f"Subprocess env: {key} = {masked_value}")

        return env

    async def _monitor_process(self) -> None:
        """
        Monitor the process and handle restarts if needed.
        """
        if not self._process:
            return

        try:
            # Wait for the process to exit
            returncode = await self._process.wait()

            if not self._stop_event.is_set():
                # Process exited unexpectedly
                logger.warning(
                    f"MCP server {self.name} exited unexpectedly with code {returncode}"
                )
                self._status = MCPServerStatus.FAILED

                # Try to restart if configured
                if (
                    self.params.restart_on_failure
                    and self._restart_count < self.params.max_restarts
                ):

                    self._restart_count += 1
                    logger.info(
                        f"Attempting restart {self._restart_count}/{self.params.max_restarts} "
                        f"for {self.name}"
                    )

                    await asyncio.sleep(2.0)  # Wait before restart
                    await self.start()
                else:
                    logger.error(f"Max restarts exceeded for {self.name}, giving up")

        except Exception as e:
            logger.error(f"Error monitoring process {self.name}: {e}")
            self._status = MCPServerStatus.FAILED

    async def _cleanup_process(self) -> None:
        """Clean up process resources."""
        if self._process:
            # Close pipes safely
            for pipe in [
                self._process.stdin,
                self._process.stdout,
                self._process.stderr,
            ]:
                if pipe:
                    try:
                        # For StreamWriter (stdin), check is_closing()
                        if hasattr(pipe, "is_closing") and not pipe.is_closing():
                            pipe.close()
                        # For StreamReader (stdout/stderr), just close
                        elif hasattr(pipe, "close"):
                            pipe.close()
                    except Exception as e:
                        logger.debug(f"Error closing pipe for {self.name}: {e}")

            self._process = None

        self._start_time = None

    async def send_notification(self, data: bytes) -> bool:
        """
        Send a notification to the process without waiting for response.
        This maintains a persistent process for session state.

        Args:
            data: Notification data to send

        Returns:
            True if sent successfully, False otherwise
        """
        if not self.is_running:
            # Start the process if not running (for session-persistent mode)
            if not await self.start():
                logger.error(f"Failed to start process {self.name} for notification")
                return False

        # Send to the persistent process stdin
        return await self.send_input(data)

    async def send_request_to_persistent_process(
        self, data: bytes, timeout: float = 30.0
    ) -> Optional[bytes]:
        """
        Send a request to the persistent process and wait for a response.
        This reuses the existing process instead of creating a new one each time.

        Args:
            data: Data to send
            timeout: Timeout in seconds to wait for response

        Returns:
            Response data, or None if error
        """
        # Start the process if not already running
        if not self.is_running:
            logger.debug(
                f"Starting persistent process {self.name} for request-response communication"
            )
            if not await self.start():
                logger.error(f"Failed to start persistent process {self.name}")
                return None

        try:
            # Send the request to the persistent process
            success = await self.send_input(data)
            if not success:
                logger.error(
                    f"Failed to send request to persistent process {self.name}"
                )
                return None

            logger.debug(
                f"Sent {len(data)} bytes to persistent process {self.name}, waiting for response..."
            )

            # Read the response with timeout
            response_data = await asyncio.wait_for(
                self.read_output(max_bytes=1024 * 1024), timeout=timeout  # 1MB max
            )

            if response_data:
                logger.debug(
                    f"Received {len(response_data)} bytes from persistent process {self.name}"
                )
                return response_data
            else:
                logger.warning(
                    f"No response data received from persistent process {self.name}"
                )
                return None

        except asyncio.TimeoutError:
            logger.error(
                f"Timeout waiting for response from persistent process {self.name}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Error in persistent process communication with {self.name}: {e}"
            )
            return None
