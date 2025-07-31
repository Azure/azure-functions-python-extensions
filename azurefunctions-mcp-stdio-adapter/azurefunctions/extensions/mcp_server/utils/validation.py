"""
Configuration validation utilities.

This module provides validation functions for MCP server configurations
to ensure they are valid and can be used to start MCP server processes.
"""

import os
import shutil
from typing import List, Optional

from ..models.configuration import MCPServerStdioParams, MCPStdioConfiguration


class ValidationError(Exception):
    """Exception raised when configuration validation fails."""

    pass


class ConfigurationValidator:
    """
    Validates MCP server configurations.

    This class provides methods to validate various aspects of MCP server
    configurations including command availability, environment variables,
    and parameter consistency.
    """

    def __init__(self):
        """Initialize the configuration validator."""
        pass

    def validate_configuration(self, config: MCPStdioConfiguration) -> None:
        """
        Validate a complete MCP server configuration.

        Args:
            config: Configuration to validate

        Raises:
            ValidationError: If validation fails
        """
        self.validate_server_params(config.params)
        self._validate_server_name(config.name)

    def validate_server_params(self, params: MCPServerStdioParams) -> None:
        """
        Validate MCP server execution parameters.

        Args:
            params: Parameters to validate

        Raises:
            ValidationError: If validation fails
        """
        self._validate_command(params.command, params.args)
        self._validate_environment(params.env)
        self._validate_working_directory(params.working_dir)
        self._validate_timeout_settings(params)

    def _validate_server_name(self, name: str) -> None:
        """
        Validate server name.

        Args:
            name: Server name to validate

        Raises:
            ValidationError: If name is invalid
        """
        if not name or not name.strip():
            raise ValidationError("Server name cannot be empty")

        # Check for valid characters
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", name):
            raise ValidationError(
                f"Server name '{name}' contains invalid characters. "
                f"Only letters, numbers, hyphens, and underscores are allowed."
            )

    def _validate_command(self, command: str, args: List[str]) -> None:
        """
        Validate command and arguments.

        Args:
            command: Command to validate
            args: Command arguments

        Raises:
            ValidationError: If command is invalid
        """
        if not command or not command.strip():
            raise ValidationError("Command cannot be empty")

        # Check if command is available
        if not shutil.which(command):
            if command == "uvx":
                raise ValidationError(
                    f"Command '{command}' not found in PATH. "
                    f"Please install uv and ensure 'uvx' is available. "
                    f"See https://docs.astral.sh/uv/guides/tools/ for installation instructions."
                )
            else:
                raise ValidationError(
                    f"Command '{command}' not found in PATH. "
                    f"Please ensure the command is installed and available."
                )

        # Validate arguments
        if args is None:
            return

        if not isinstance(args, list):
            raise ValidationError("Command arguments must be a list")

        for arg in args:
            if not isinstance(arg, str):
                raise ValidationError("All command arguments must be strings")

    def _validate_environment(self, env: dict) -> None:
        """
        Validate environment variables.

        Args:
            env: Environment variables dictionary

        Raises:
            ValidationError: If environment variables are invalid
        """
        if env is None:
            return

        if not isinstance(env, dict):
            raise ValidationError("Environment variables must be a dictionary")

        for key, value in env.items():
            if not isinstance(key, str):
                raise ValidationError("Environment variable names must be strings")

            if not isinstance(value, str):
                raise ValidationError("Environment variable values must be strings")

            if not key:
                raise ValidationError("Environment variable names cannot be empty")

    def _validate_working_directory(self, working_dir: Optional[str]) -> None:
        """
        Validate working directory.

        Args:
            working_dir: Working directory path

        Raises:
            ValidationError: If working directory is invalid
        """
        if working_dir is None:
            return

        if not isinstance(working_dir, str):
            raise ValidationError("Working directory must be a string")

        if not working_dir.strip():
            raise ValidationError("Working directory cannot be empty")

        # Check if directory exists
        if not os.path.isdir(working_dir):
            raise ValidationError(f"Working directory does not exist: {working_dir}")

        # Check if directory is accessible
        if not os.access(working_dir, os.R_OK | os.X_OK):
            raise ValidationError(f"Working directory is not accessible: {working_dir}")

    def _validate_timeout_settings(self, params: MCPServerStdioParams) -> None:
        """
        Validate timeout and restart settings.

        Args:
            params: Server parameters to validate

        Raises:
            ValidationError: If timeout settings are invalid
        """
        if params.timeout_seconds <= 0:
            raise ValidationError("Timeout must be greater than 0 seconds")

        if params.timeout_seconds > 300:  # 5 minutes
            raise ValidationError("Timeout cannot exceed 300 seconds")

        if params.max_restarts < 0:
            raise ValidationError("Maximum restarts cannot be negative")

        if params.max_restarts > 10:
            raise ValidationError("Maximum restarts cannot exceed 10")


def validate_uvx_availability() -> bool:
    """
    Check if uvx is available in the system PATH.

    Returns:
        True if uvx is available, False otherwise
    """
    return shutil.which("uvx") is not None


def get_command_path(command: str) -> Optional[str]:
    """
    Get the full path to a command.

    Args:
        command: Command name to look up

    Returns:
        Full path to command if found, None otherwise
    """
    return shutil.which(command)


def validate_json_structure(data: dict, required_keys: List[str]) -> List[str]:
    """
    Validate that a dictionary contains required keys.

    Args:
        data: Dictionary to validate
        required_keys: List of required keys

    Returns:
        List of missing keys
    """
    if not isinstance(data, dict):
        return required_keys

    missing_keys = []
    for key in required_keys:
        if key not in data:
            missing_keys.append(key)

    return missing_keys
