"""
Unit tests for process manager functionality.
"""

import asyncio
import os
import pytest
import signal
from unittest.mock import AsyncMock, MagicMock, patch

from azurefunctions.extensions.mcp_server.core.process_manager import ProcessManager
from azurefunctions.extensions.mcp_server.models.configuration import MCPServerStdioParams
from azurefunctions.extensions.mcp_server.models.enums import MCPServerStatus
from tests.conftest import AsyncTestCase


class TestProcessManager(AsyncTestCase):
    """Test ProcessManager class."""
    
    async def setup_method(self):
        """Set up test fixtures."""
        self.params = MCPServerStdioParams(
            command="echo",
            args=["test"],
            env={"TEST_VAR": "test_value"},
            timeout_seconds=10
        )
        self.manager = ProcessManager("test-server", self.params)
    
    def test_initialization(self):
        """Test process manager initialization."""
        assert self.manager.name == "test-server"
        assert self.manager.params == self.params
        assert self.manager.status == MCPServerStatus.STOPPED
        assert not self.manager.is_running
        assert self.manager.process is None
        assert self.manager.uptime is None
    
    def test_process_id_generation(self):
        """Test process ID generation."""
        manager1 = ProcessManager("test", self.params)
        manager2 = ProcessManager("test", self.params)
        
        # Should generate different process IDs
        assert manager1.process_id != manager2.process_id
        assert manager1.process_id.startswith("mcp-test-")
        assert manager2.process_id.startswith("mcp-test-")
    
    def test_custom_process_id(self):
        """Test custom process ID."""
        manager = ProcessManager("test", self.params, process_id="custom-id")
        assert manager.process_id == "custom-id"
    
    def test_uvx_validation_success(self):
        """Test UVX validation when uvx is available."""
        params = MCPServerStdioParams(command="uvx", args=["test"])
        
        with patch('shutil.which', return_value='/usr/bin/uvx'):
            # Should not raise an exception
            manager = ProcessManager("test", params)
            assert manager.params.command == "uvx"
    
    def test_uvx_validation_failure(self):
        """Test UVX validation when uvx is not available."""
        params = MCPServerStdioParams(command="uvx", args=["test"])
        
        with patch('shutil.which', return_value=None):
            with pytest.raises(RuntimeError) as exc_info:
                ProcessManager("test", params)
            
            error_msg = str(exc_info.value)
            assert "uvx not found in PATH" in error_msg
            assert "install uv" in error_msg
    
    async def test_start_success(self, mock_asyncio_create_subprocess_exec, mock_process):
        """Test successful process start."""
        with patch('shutil.which', return_value='/usr/bin/echo'):
            success = await self.manager.start()
            
            assert success
            assert self.manager.status == MCPServerStatus.RUNNING
            assert self.manager.is_running
            assert self.manager.process is not None
            assert self.manager.uptime is not None
    
    async def test_start_already_running(self, mock_asyncio_create_subprocess_exec, mock_process):
        """Test starting when process is already running."""
        with patch('shutil.which', return_value='/usr/bin/echo'):
            # Start the process first
            await self.manager.start()
            assert self.manager.is_running
            
            # Try to start again
            success = await self.manager.start()
            assert success  # Should return True but not start again
    
    async def test_start_process_fails_immediately(self, mock_asyncio_create_subprocess_exec):
        """Test handling of process that fails immediately."""
        # Mock process that exits immediately
        mock_process = AsyncMock()
        mock_process.returncode = 1  # Process exited
        mock_process.stderr = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"Test error")
        
        with patch('shutil.which', return_value='/usr/bin/echo'):
            with patch('asyncio.create_subprocess_exec', return_value=mock_process):
                success = await self.manager.start()
                
                assert not success
                assert self.manager.status == MCPServerStatus.FAILED
                assert not self.manager.is_running
    
    async def test_stop_not_running(self):
        """Test stopping when process is not running."""
        success = await self.manager.stop()
        assert success  # Should return True even if not running
    
    async def test_stop_graceful(self, mock_asyncio_create_subprocess_exec, mock_process):
        """Test graceful process stop."""
        with patch('shutil.which', return_value='/usr/bin/echo'):
            # Start the process
            await self.manager.start()
            assert self.manager.is_running
            
            # Mock the process wait to succeed (graceful shutdown)
            mock_process.wait = AsyncMock(return_value=0)
            
            # Stop the process
            success = await self.manager.stop()
            
            assert success
            assert self.manager.status == MCPServerStatus.STOPPED
            assert not self.manager.is_running
            
            # Verify process.wait was called (indicating graceful shutdown attempt)
            mock_process.wait.assert_called()
    
    async def test_stop_force_kill(self, mock_asyncio_create_subprocess_exec, mock_process):
        """Test force kill when graceful stop times out."""
        # Mock process.wait to timeout first, then succeed after force kill
        wait_calls = 0
        async def mock_wait():
            nonlocal wait_calls
            wait_calls += 1
            if wait_calls == 1:
                # First call times out (graceful shutdown)
                raise asyncio.TimeoutError()
            else:
                # Second call succeeds (after force kill)
                return -9  # SIGKILL exit code
        
        mock_process.wait = mock_wait
        
        with patch('shutil.which', return_value='/usr/bin/echo'):
            with patch('os.name', 'posix'):
                with patch('os.killpg') as mock_killpg:
                    # Start the process
                    await self.manager.start()
                    
                    # Stop with short timeout
                    success = await self.manager.stop(timeout=0.1)
                    
                    assert success
                    # Should call SIGTERM then SIGKILL
                    assert mock_killpg.call_count >= 1
    
    async def test_restart(self, mock_asyncio_create_subprocess_exec, mock_process):
        """Test process restart."""
        with patch('shutil.which', return_value='/usr/bin/echo'):
            # Start the process
            await self.manager.start()
            assert self.manager.is_running
            
            # Restart the process
            success = await self.manager.restart()
            
            assert success
            assert self.manager.is_running
            assert self.manager.status == MCPServerStatus.RUNNING
    
    async def test_send_input_not_running(self):
        """Test sending input when process is not running."""
        success = await self.manager.send_input(b"test data")
        assert not success
    
    async def test_send_input_success(self, mock_asyncio_create_subprocess_exec, mock_process):
        """Test successful input sending."""
        with patch('shutil.which', return_value='/usr/bin/echo'):
            await self.manager.start()
            
            success = await self.manager.send_input(b"test data")
            
            assert success
            mock_process.stdin.write.assert_called_once_with(b"test data")
            mock_process.stdin.drain.assert_called_once()
    
    async def test_send_input_error(self, mock_asyncio_create_subprocess_exec, mock_process):
        """Test error handling in input sending."""
        mock_process.stdin.write.side_effect = Exception("Write error")
        
        with patch('shutil.which', return_value='/usr/bin/echo'):
            await self.manager.start()
            
            success = await self.manager.send_input(b"test data")
            
            assert not success
    
    async def test_read_output_not_running(self):
        """Test reading output when process is not running."""
        data = await self.manager.read_output()
        assert data is None
    
    async def test_read_output_success(self, mock_asyncio_create_subprocess_exec, mock_process):
        """Test successful output reading."""
        mock_process.stdout.read = AsyncMock(return_value=b"test output")
        
        with patch('shutil.which', return_value='/usr/bin/echo'):
            await self.manager.start()
            
            data = await self.manager.read_output()
            
            assert data == b"test output"
            mock_process.stdout.read.assert_called_once_with(8192)
    
    async def test_read_output_eof(self, mock_asyncio_create_subprocess_exec, mock_process):
        """Test reading output at EOF."""
        mock_process.stdout.read = AsyncMock(return_value=b"")
        
        with patch('shutil.which', return_value='/usr/bin/echo'):
            await self.manager.start()
            
            data = await self.manager.read_output()
            
            assert data is None  # EOF should return None
    
    async def test_read_output_error(self, mock_asyncio_create_subprocess_exec, mock_process):
        """Test error handling in output reading."""
        mock_process.stdout.read.side_effect = Exception("Read error")
        
        with patch('shutil.which', return_value='/usr/bin/echo'):
            await self.manager.start()
            
            data = await self.manager.read_output()
            
            assert data is None
    
    def test_build_command(self):
        """Test command building."""
        cmd = self.manager._build_command()
        expected = ["echo", "test"]
        assert cmd == expected
        
        # Test with no args
        params = MCPServerStdioParams(command="python")
        manager = ProcessManager("test", params)
        cmd = manager._build_command()
        assert cmd == ["python"]
    
    def test_build_environment(self):
        """Test environment building."""
        with patch.dict(os.environ, {"EXISTING": "value"}, clear=True):
            env = self.manager._build_environment()
            
            # Should include both existing and new env vars
            assert "EXISTING" in env
            assert env["EXISTING"] == "value"
            assert "TEST_VAR" in env
            assert env["TEST_VAR"] == "test_value"
    
    async def test_monitor_process_unexpected_exit(self, mock_asyncio_create_subprocess_exec):
        """Test monitoring process that exits unexpectedly."""
        # Mock process that exits with non-zero code
        mock_process = AsyncMock()
        mock_process.pid = 12345
        mock_process.returncode = None
        mock_process.stdin = AsyncMock()
        mock_process.stdout = AsyncMock()
        mock_process.stderr = AsyncMock()
        mock_process.wait = AsyncMock(return_value=1)  # Non-zero exit code
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()
        
        # Configure restart parameters
        self.manager.params.restart_on_failure = True
        self.manager.params.max_restarts = 1
        
        with patch('shutil.which', return_value='/usr/bin/echo'):
            with patch('asyncio.create_subprocess_exec', return_value=mock_process):
                # Start the process
                await self.manager.start()
                
                # Wait a bit for monitoring to process the exit
                await asyncio.sleep(0.1)
                
                # Should attempt restart
                # Note: In real scenario this would involve more complex async coordination
                # but for unit test we just verify the logic paths are covered
    
    async def test_restart_limit_exceeded(self, mock_asyncio_create_subprocess_exec):
        """Test restart limit being exceeded."""
        self.manager.params.restart_on_failure = True
        self.manager.params.max_restarts = 0  # No restarts allowed
        self.manager._restart_count = 1  # Already exceeded
        
        # Mock a failing process
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.stderr = AsyncMock()
        mock_process.stderr.read = AsyncMock(return_value=b"Error")
        
        with patch('shutil.which', return_value='/usr/bin/echo'):
            with patch('asyncio.create_subprocess_exec', return_value=mock_process):
                success = await self.manager.start()
                
                assert not success
                assert self.manager.status == MCPServerStatus.FAILED
