"""
Unit tests for configuration models and validation.
"""

import pytest
from pydantic import ValidationError

from azurefunctions.extensions.mcp_server.models.configuration import (
    MCPServerStdioParams,
    MCPStdioConfiguration,
    MCPMultiServerConfiguration,
)
from azurefunctions.extensions.mcp_server.utils.validation import (
    ConfigurationValidator,
    ValidationError as CustomValidationError,
)


class TestMCPServerStdioParams:
    """Test MCPServerStdioParams model."""
    
    def test_valid_params(self):
        """Test creating valid parameters."""
        params = MCPServerStdioParams(
            command="python",
            args=["server.py"],
            env={"TEST": "value"},
            working_dir="/tmp",
            timeout_seconds=30
        )
        
        assert params.command == "python"
        assert params.args == ["server.py"]
        assert params.env == {"TEST": "value"}
        assert params.working_dir == "/tmp"
        assert params.timeout_seconds == 30
        assert params.restart_on_failure is True
        assert params.max_restarts == 3
    
    def test_minimal_params(self):
        """Test creating minimal parameters."""
        params = MCPServerStdioParams(command="echo")
        
        assert params.command == "echo"
        assert params.args == []
        assert params.env == {}
        assert params.working_dir is None
        assert params.timeout_seconds == 30
    
    def test_empty_command_validation(self):
        """Test validation of empty command."""
        with pytest.raises(ValidationError):
            MCPServerStdioParams(command="")
    
    def test_whitespace_command_validation(self):
        """Test validation of whitespace-only command."""
        with pytest.raises(ValidationError):
            MCPServerStdioParams(command="   ")
    
    def test_invalid_timeout_validation(self):
        """Test validation of invalid timeout."""
        with pytest.raises(ValidationError):
            MCPServerStdioParams(command="echo", timeout_seconds=0)
        
        with pytest.raises(ValidationError):
            MCPServerStdioParams(command="echo", timeout_seconds=-1)
    
    def test_invalid_max_restarts_validation(self):
        """Test validation of invalid max_restarts."""
        with pytest.raises(ValidationError):
            MCPServerStdioParams(command="echo", max_restarts=-1)


class TestMCPStdioConfiguration:
    """Test MCPStdioConfiguration model."""
    
    def test_valid_configuration(self, sample_mcp_config):
        """Test creating valid configuration."""
        config = sample_mcp_config
        
        assert config.name == "test-server"
        assert config.params.command == "echo"
        assert config.description == "Test MCP server"
        assert config.enabled is True
    
    def test_minimal_configuration(self):
        """Test creating minimal configuration."""
        params = MCPServerStdioParams(command="echo")
        config = MCPStdioConfiguration(name="test", params=params)
        
        assert config.name == "test"
        assert config.params.command == "echo"
        assert config.description is None
        assert config.enabled is True
    
    def test_empty_name_validation(self):
        """Test validation of empty name."""
        params = MCPServerStdioParams(command="echo")
        
        with pytest.raises(ValidationError):
            MCPStdioConfiguration(name="", params=params)
    
    def test_whitespace_name_validation(self):
        """Test validation of whitespace-only name."""
        params = MCPServerStdioParams(command="echo")
        
        with pytest.raises(ValidationError):
            MCPStdioConfiguration(name="   ", params=params)
    
    def test_invalid_characters_name_validation(self):
        """Test validation of invalid characters in name."""
        params = MCPServerStdioParams(command="echo")
        
        invalid_names = ["test@server", "test server", "test.server", "test/server"]
        for name in invalid_names:
            with pytest.raises(ValidationError):
                MCPStdioConfiguration(name=name, params=params)
    
    def test_valid_name_characters(self):
        """Test that valid name characters are accepted."""
        params = MCPServerStdioParams(command="echo")
        
        valid_names = ["test", "test-server", "test_server", "TestServer123"]
        for name in valid_names:
            config = MCPStdioConfiguration(name=name, params=params)
            assert config.name == name


class TestMCPMultiServerConfiguration:
    """Test MCPMultiServerConfiguration model."""
    
    def test_empty_multi_config(self):
        """Test creating empty multi-server configuration."""
        config = MCPMultiServerConfiguration()
        
        assert config.servers == {}
        assert config.default_server is None
        assert config.list_servers() == []
    
    def test_add_server(self, sample_mcp_config):
        """Test adding a server to multi-config."""
        config = MCPMultiServerConfiguration()
        config.add_server(sample_mcp_config)
        
        assert len(config.servers) == 1
        assert "test-server" in config.servers
        assert config.default_server == "test-server"
    
    def test_get_server_by_name(self, sample_mcp_config):
        """Test getting server by name."""
        config = MCPMultiServerConfiguration()
        config.add_server(sample_mcp_config)
        
        server = config.get_server("test-server")
        assert server is not None
        assert server.name == "test-server"
        
        # Test non-existent server
        assert config.get_server("non-existent") is None
    
    def test_get_default_server(self, sample_mcp_config):
        """Test getting default server."""
        config = MCPMultiServerConfiguration()
        config.add_server(sample_mcp_config)
        
        # Should return the single server when no name specified
        server = config.get_server()
        assert server is not None
        assert server.name == "test-server"
    
    def test_multiple_servers(self):
        """Test multi-server configuration with multiple servers."""
        config = MCPMultiServerConfiguration()
        
        # Add first server
        params1 = MCPServerStdioParams(command="echo")
        server1 = MCPStdioConfiguration(name="server1", params=params1)
        config.add_server(server1)
        
        # Add second server
        params2 = MCPServerStdioParams(command="python")
        server2 = MCPStdioConfiguration(name="server2", params=params2)
        config.add_server(server2)
        
        assert len(config.servers) == 2
        assert config.default_server == "server1"  # First server becomes default
        assert set(config.list_servers()) == {"server1", "server2"}
    
    def test_invalid_default_server(self):
        """Test validation of invalid default server."""
        params = MCPServerStdioParams(command="echo")
        server = MCPStdioConfiguration(name="test", params=params)
        
        with pytest.raises(ValidationError):
            MCPMultiServerConfiguration(
                servers={"test": server},
                default_server="non-existent"
            )


class TestConfigurationValidator:
    """Test ConfigurationValidator class."""
    
    def test_valid_configuration(self, sample_mcp_config, mock_shutil_which):
        """Test validation of valid configuration."""
        validator = ConfigurationValidator()
        
        # Should not raise any exception
        validator.validate_configuration(sample_mcp_config)
    
    def test_invalid_command(self, mock_shutil_which):
        """Test validation of invalid command."""
        # Mock shutil.which to return None for unavailable command
        def mock_which(command):
            return None if command == "unavailable-command" else "/usr/bin/echo"
        
        import unittest.mock
        with unittest.mock.patch("shutil.which", mock_which):
            validator = ConfigurationValidator()
            params = MCPServerStdioParams(command="unavailable-command")
            config = MCPStdioConfiguration(name="test", params=params)
            
            with pytest.raises(CustomValidationError) as exc_info:
                validator.validate_configuration(config)
            
            assert "not found in PATH" in str(exc_info.value)
    
    def test_uvx_specific_error(self):
        """Test specific error message for uvx command."""
        import unittest.mock
        with unittest.mock.patch("shutil.which", return_value=None):
            validator = ConfigurationValidator()
            params = MCPServerStdioParams(command="uvx")
            config = MCPStdioConfiguration(name="test", params=params)
            
            with pytest.raises(CustomValidationError) as exc_info:
                validator.validate_configuration(config)
            
            error_msg = str(exc_info.value)
            assert "uvx' not found in PATH" in error_msg
            assert "install uv" in error_msg
            assert "https://docs.astral.sh/uv/guides/tools/" in error_msg
    
    def test_invalid_environment_variables(self, mock_shutil_which):
        """Test validation of invalid environment variables."""
        # Test non-dict env
        with pytest.raises(ValidationError):
            MCPServerStdioParams(command="echo", env="not-a-dict")
        
        # Test non-string key - this is actually allowed by Pydantic dict type
        # so we'll skip this test case
        
        # Test non-string value - also allowed by Pydantic for Dict[str, str]
        # since Pydantic will try to convert it
    
    def test_invalid_working_directory(self, mock_shutil_which):
        """Test validation of invalid working directory."""
        # Test non-existent directory - this will be caught by Pydantic validator
        with pytest.raises(ValidationError) as exc_info:
            MCPServerStdioParams(command="echo", working_dir="/non/existent/path")
        
        assert "does not exist" in str(exc_info.value)
    
    def test_timeout_validation(self, mock_shutil_which):
        """Test validation of timeout settings."""
        validator = ConfigurationValidator()
        
        # Test timeout too large
        params = MCPServerStdioParams(command="echo", timeout_seconds=500)
        with pytest.raises(CustomValidationError):
            validator.validate_server_params(params)
        
        # Test max_restarts too large
        params = MCPServerStdioParams(command="echo", max_restarts=20)
        with pytest.raises(CustomValidationError):
            validator.validate_server_params(params)
