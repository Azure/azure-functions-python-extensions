"""
Configuration models for the MCP STDIO adapter.

This module defines the data models used to configure MCP servers
and their execution parameters.
"""

import os
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class MCPServerStdioParams(BaseModel):
    """
    Parameters for executing a STDIO-based MCP server.
    
    This class defines the execution parameters needed to start and
    communicate with an MCP server process via STDIO.
    """
    
    command: str = Field(
        ..., 
        description="Command to execute (e.g., 'uvx', 'python')"
    )
    args: List[str] = Field(
        default_factory=list,
        description="Command line arguments for the MCP server"
    )
    env: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to pass to the MCP server"
    )
    working_dir: Optional[str] = Field(
        default=None,
        description="Working directory for the MCP server process"
    )
    timeout_seconds: int = Field(
        default=30,
        description="Timeout in seconds for process startup",
        ge=1
    )
    restart_on_failure: bool = Field(
        default=True,
        description="Whether to restart the server on failure"
    )
    max_restarts: int = Field(
        default=3,
        description="Maximum number of restart attempts",
        ge=0
    )
    
    @field_validator('working_dir')
    @classmethod
    def validate_working_dir(cls, v: Optional[str]) -> Optional[str]:
        """Validate that working directory exists if specified."""
        if v is not None and not os.path.isdir(v):
            raise ValueError(f"Working directory does not exist: {v}")
        return v
    
    @field_validator('command')
    @classmethod
    def validate_command(cls, v: str) -> str:
        """Validate that command is not empty."""
        if not v.strip():
            raise ValueError("Command cannot be empty")
        return v.strip()


class MCPStdioConfiguration(BaseModel):
    """
    Main configuration container for an MCP STDIO server.
    
    This class encapsulates all the information needed to configure
    and manage an MCP server instance.
    """
    
    name: str = Field(
        ...,
        description="Unique name for the MCP server instance"
    )
    params: MCPServerStdioParams = Field(
        ...,
        description="Server execution parameters"
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional description of the MCP server"
    )
    enabled: bool = Field(
        default=True,
        description="Whether this server configuration is enabled"
    )
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate that name is not empty and contains valid characters."""
        if not v.strip():
            raise ValueError("Server name cannot be empty")
        
        # Allow alphanumeric, hyphens, underscores
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v.strip()):
            raise ValueError(
                "Server name can only contain letters, numbers, hyphens, and underscores"
            )
        
        return v.strip()


class MCPMultiServerConfiguration(BaseModel):
    """
    Configuration for multiple MCP servers.
    
    This class can hold multiple MCP server configurations
    for scenarios where multiple servers need to be managed.
    """
    
    servers: Dict[str, MCPStdioConfiguration] = Field(
        default_factory=dict,
        description="Dictionary of MCP server configurations"
    )
    default_server: Optional[str] = Field(
        default=None,
        description="Name of the default server to use"
    )
    
    @model_validator(mode='after')
    def validate_default_server(self) -> 'MCPMultiServerConfiguration':
        """Validate that default server exists in servers dict."""
        if self.default_server is not None:
            if self.default_server not in self.servers:
                raise ValueError(f"Default server '{self.default_server}' not found in servers")
        return self
    
    def get_server(self, name: Optional[str] = None) -> Optional[MCPStdioConfiguration]:
        """
        Get a server configuration by name.
        
        Args:
            name: Server name, or None to get the default server
            
        Returns:
            MCPStdioConfiguration if found, None otherwise
        """
        if name is None:
            name = self.default_server
            
        if name is None and len(self.servers) == 1:
            # If no default specified and only one server, use that one
            return next(iter(self.servers.values()))
            
        return self.servers.get(name) if name else None
    
    def list_servers(self) -> List[str]:
        """Get list of all server names."""
        return list(self.servers.keys())
    
    def add_server(self, config: MCPStdioConfiguration) -> None:
        """Add a server configuration."""
        self.servers[config.name] = config
        
        # Set as default if it's the first server
        if self.default_server is None and len(self.servers) == 1:
            self.default_server = config.name
