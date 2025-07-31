"""
Pytest configuration and fixtures for MCP STDIO adapter tests.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Dict, Any
import pytest
from unittest.mock import AsyncMock, MagicMock

from azurefunctions.extensions.mcp_server.models.configuration import (
    MCPStdioConfiguration,
    MCPServerStdioParams,
)
from azurefunctions.extensions.mcp_server.models.enums import MCPMode


# Remove deprecated event_loop fixture - pytest-asyncio handles this automatically


@pytest.fixture
def sample_mcp_config() -> MCPStdioConfiguration:
    """Create a sample MCP configuration for testing."""
    params = MCPServerStdioParams(
        command="echo",
        args=["test"],
        env={"TEST_VAR": "test_value"},
        timeout_seconds=10,
    )
    return MCPStdioConfiguration(
        name="test-server",
        params=params,
        description="Test MCP server"
    )


@pytest.fixture
def sample_config_data_format1() -> Dict[str, Any]:
    """Sample configuration in format 1 (mcpServers)."""
    return {
        "mcpServers": {
            "test-server": {
                "command": "python",
                "args": ["test_server.py"],
                "env": {
                    "TEST_ENV": "test_value"
                }
            }
        }
    }


@pytest.fixture
def sample_config_data_format2() -> Dict[str, Any]:
    """Sample configuration in format 2 (servers)."""
    return {
        "servers": {
            "mysql": {
                "type": "stdio",
                "command": "uvx",
                "args": ["--from", "mysql-mcp-server", "mysql_mcp_server"],
                "env": {
                    "MYSQL_HOST": "localhost",
                    "MYSQL_PORT": "3306"
                }
            }
        }
    }


@pytest.fixture
def sample_config_data_format3() -> Dict[str, Any]:
    """Sample configuration in format 3 (mcp.server)."""
    return {
        "mcp": {
            "server": {
                "fabric-rti-mcp": {
                    "command": "uvx",
                    "args": ["microsoft-fabric-rti-mcp"],
                    "env": {
                        "KUSTO_SERVICE_URI": "https://help.kusto.windows.net/"
                    }
                }
            }
        }
    }


@pytest.fixture
def temp_config_file(sample_config_data_format1) -> Path:
    """Create a temporary configuration file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(sample_config_data_format1, f)
        return Path(f.name)


@pytest.fixture
def mock_process():
    """Create a mock asyncio subprocess for testing."""
    process = AsyncMock()
    process.pid = 12345
    process.returncode = None
    
    # Create regular mocks for synchronous methods
    process.stdin = MagicMock()
    process.stdin.write = MagicMock()
    process.stdin.drain = AsyncMock()
    process.stdin.close = MagicMock()
    process.stdin.is_closing = MagicMock(return_value=False)
    
    process.stdout = MagicMock()
    process.stdout.read = AsyncMock(return_value=b"test output")
    process.stdout.close = MagicMock()
    process.stdout.is_closing = MagicMock(return_value=False)
    
    process.stderr = MagicMock()
    process.stderr.read = AsyncMock(return_value=b"")
    process.stderr.close = MagicMock()
    process.stderr.is_closing = MagicMock(return_value=False)
    
    process.wait = AsyncMock(return_value=0)
    process.terminate = MagicMock()
    process.kill = MagicMock()
    
    return process


@pytest.fixture
def mock_asyncio_create_subprocess_exec(monkeypatch, mock_process):
    """Mock asyncio.create_subprocess_exec."""
    async def mock_create_subprocess_exec(*args, **kwargs):
        return mock_process
    
    monkeypatch.setattr(
        "asyncio.create_subprocess_exec", 
        mock_create_subprocess_exec
    )
    return mock_create_subprocess_exec


@pytest.fixture
def mock_shutil_which(monkeypatch):
    """Mock shutil.which to simulate command availability."""
    def mock_which(command):
        # Simulate that common commands are available
        available_commands = ["python", "echo", "uvx", "node"]
        return f"/usr/bin/{command}" if command in available_commands else None
    
    monkeypatch.setattr("shutil.which", mock_which)
    return mock_which


@pytest.fixture
def sample_json_rpc_message() -> Dict[str, Any]:
    """Sample JSON-RPC message for testing."""
    return {
        "jsonrpc": "2.0",
        "method": "test_method",
        "params": {"test_param": "test_value"},
        "id": "test-123"
    }


@pytest.fixture
def sample_content_length_frame() -> bytes:
    """Sample Content-Length framed message for testing."""
    message = '{"jsonrpc":"2.0","method":"test","id":"1"}'
    message_bytes = message.encode('utf-8')
    content_length = len(message_bytes)
    frame = f"Content-Length: {content_length}\r\n\r\n".encode('utf-8')
    return frame + message_bytes


# AsyncTestCase is no longer needed - pytest-asyncio handles async tests automatically
# Tests should inherit from regular classes and use @pytest.mark.asyncio on async methods
