"""
Configuration loader for MCP STDIO adapter.

This module handles loading and parsing configuration files in various formats,
supporting the different JSON schemas that customers might use.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional, Union

from ..models.configuration import (
    MCPMultiServerConfiguration,
    MCPServerStdioParams,
    MCPStdioConfiguration,
)
from ..models.enums import ConfigurationFormat
from ..utils.validation import ConfigurationValidator

logger = logging.getLogger(__name__)


class ConfigurationLoader:
    """
    Loads and parses MCP server configurations from various file formats.

    Supports multiple JSON configuration formats as used by different
    MCP client implementations.
    """

    # Well-known configuration file names
    WELL_KNOWN_FILES = [
        "mcp_config.json",
        "mcp.json",
        ".mcp.json",
        "mcp_servers.json",
        "servers.json",
    ]

    def __init__(self, validator: Optional[ConfigurationValidator] = None):
        """
        Initialize the configuration loader.

        Args:
            validator: Optional configuration validator instance
        """
        self.validator = validator or ConfigurationValidator()

    def load_from_file(
        self, file_path: Union[str, Path]
    ) -> MCPMultiServerConfiguration:
        """
        Load configuration from a JSON file.

        Args:
            file_path: Path to the configuration file

        Returns:
            MCPMultiServerConfiguration instance

        Raises:
            FileNotFoundError: If the configuration file doesn't exist
            ValueError: If the configuration format is invalid
            json.JSONDecodeError: If the file contains invalid JSON
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        logger.info(f"Loading MCP configuration from: {path}")

        try:
            with path.open("r", encoding="utf-8") as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in configuration file {path}: {e.msg}", e.doc, e.pos
            )

        return self._parse_configuration(config_data, str(path))

    def load_from_well_known_locations(
        self, search_paths: Optional[list] = None
    ) -> Optional[MCPMultiServerConfiguration]:
        """
        Load configuration from well-known file locations.

        Args:
            search_paths: Optional list of directories to search

        Returns:
            MCPMultiServerConfiguration if found, None otherwise
        """
        if search_paths is None:
            search_paths = [
                os.getcwd(),
                os.path.expanduser("~"),
                os.path.expanduser("~/.config/mcp"),
            ]

        for search_path in search_paths:
            path_obj = Path(search_path)
            if not path_obj.exists():
                continue

            for filename in self.WELL_KNOWN_FILES:
                config_file = path_obj / filename
                if config_file.exists():
                    logger.info(f"Found configuration file: {config_file}")
                    try:
                        return self.load_from_file(config_file)
                    except Exception as e:
                        logger.warning(f"Failed to load {config_file}: {e}")
                        continue

        logger.debug("No well-known configuration files found")
        return None

    def _parse_configuration(
        self, config_data: Dict, source: str = "<unknown>"
    ) -> MCPMultiServerConfiguration:
        """
        Parse configuration data into MCPMultiServerConfiguration.

        Args:
            config_data: Raw configuration dictionary
            source: Source description for error messages

        Returns:
            MCPMultiServerConfiguration instance

        Raises:
            ValueError: If configuration format is not recognized or invalid
        """
        # Detect configuration format
        config_format = self._detect_format(config_data)
        logger.debug(f"Detected configuration format: {config_format} in {source}")

        # Parse based on format
        if config_format == ConfigurationFormat.MCP_SERVERS:
            return self._parse_mcp_servers_format(config_data, source)
        elif config_format == ConfigurationFormat.SERVERS:
            return self._parse_servers_format(config_data, source)
        elif config_format == ConfigurationFormat.MCP_SERVER:
            return self._parse_mcp_server_format(config_data, source)
        else:
            raise ValueError(f"Unrecognized configuration format in {source}")

    def _detect_format(self, config_data: Dict) -> ConfigurationFormat:
        """
        Detect the configuration format from the data structure.

        Args:
            config_data: Configuration dictionary

        Returns:
            ConfigurationFormat enum value
        """
        if "mcpServers" in config_data:
            return ConfigurationFormat.MCP_SERVERS
        elif "servers" in config_data:
            return ConfigurationFormat.SERVERS
        elif "mcp" in config_data and isinstance(config_data["mcp"], dict):
            if "server" in config_data["mcp"]:
                return ConfigurationFormat.MCP_SERVER

        # Default to MCP_SERVERS if we can't detect
        return ConfigurationFormat.MCP_SERVERS

    def _parse_mcp_servers_format(
        self, config_data: Dict, source: str
    ) -> MCPMultiServerConfiguration:
        """
        Parse Format 1: {"mcpServers": {...}}
        """
        servers_data = config_data.get("mcpServers", {})
        return self._parse_servers_dict(servers_data, source)

    def _parse_servers_format(
        self, config_data: Dict, source: str
    ) -> MCPMultiServerConfiguration:
        """
        Parse Format 2: {"servers": {...}}
        """
        servers_data = config_data.get("servers", {})
        return self._parse_servers_dict(servers_data, source)

    def _parse_mcp_server_format(
        self, config_data: Dict, source: str
    ) -> MCPMultiServerConfiguration:
        """
        Parse Format 3: {"mcp": {"server": {...}}}
        """
        mcp_data = config_data.get("mcp", {})
        servers_data = mcp_data.get("server", {})
        return self._parse_servers_dict(servers_data, source)

    def _parse_servers_dict(
        self, servers_data: Dict, source: str
    ) -> MCPMultiServerConfiguration:
        """
        Parse a dictionary of server configurations.

        Args:
            servers_data: Dictionary with server name -> config mappings
            source: Source description for error messages

        Returns:
            MCPMultiServerConfiguration instance
        """
        config = MCPMultiServerConfiguration()

        for server_name, server_config in servers_data.items():
            try:
                # Extract server parameters
                command = server_config.get("command", "")
                args = server_config.get("args", [])
                env = server_config.get("env", {})
                working_dir = server_config.get("working_dir")

                # Handle 'type' field (ignore for now, assume stdio)
                server_type = server_config.get("type", "stdio")
                if server_type != "stdio":
                    logger.warning(
                        f"Server {server_name} has type '{server_type}', "
                        f"treating as stdio"
                    )

                # Create parameter object
                params = MCPServerStdioParams(
                    command=command, args=args, env=env, working_dir=working_dir
                )

                # Create server configuration
                mcp_config = MCPStdioConfiguration(name=server_name, params=params)

                # Validate if validator is available
                if self.validator:
                    self.validator.validate_configuration(mcp_config)

                config.add_server(mcp_config)
                logger.debug(f"Added server configuration: {server_name}")

            except Exception as e:
                logger.error(f"Failed to parse server '{server_name}' in {source}: {e}")
                raise ValueError(f"Invalid server configuration '{server_name}': {e}")

        if not config.servers:
            raise ValueError(f"No valid server configurations found in {source}")

        logger.info(f"Loaded {len(config.servers)} server configurations from {source}")
        return config
