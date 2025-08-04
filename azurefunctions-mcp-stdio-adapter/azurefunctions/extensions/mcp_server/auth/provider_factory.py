"""
Authentication provider factory for MCP servers.

This module provides a factory for creating authentication providers
based on configuration settings.
"""

import logging
from typing import Optional

from .token_handler import (
    AuthProvider, 
    NoAuthProvider, 
    AzureDefaultAuthProvider, 
    AzureOBOAuthProvider, 
    OAuth2BearerAuthProvider,
    AuthMethod
)
from ..models.configuration import AuthConfiguration

logger = logging.getLogger(__name__)


class AuthProviderFactory:
    """Factory for creating authentication providers."""
    
    @staticmethod
    def create_provider(config: AuthConfiguration) -> AuthProvider:
        """
        Create an authentication provider based on configuration.
        
        Args:
            config: Authentication configuration
            
        Returns:
            Configured authentication provider
            
        Raises:
            ValueError: If configuration is invalid
        """
        if config.method == AuthMethod.NONE:
            return NoAuthProvider()
        
        elif config.method == AuthMethod.AZURE_DEFAULT:
            return AzureDefaultAuthProvider(scopes=config.azure_scopes)
        
        elif config.method == AuthMethod.AZURE_OBO:
            if not config.azure_client_id or not config.azure_client_secret:
                raise ValueError("Azure OBO requires client_id and client_secret")
            
            return AzureOBOAuthProvider(
                client_id=config.azure_client_id,
                client_secret=config.azure_client_secret,
                scopes=config.azure_scopes
            )
        
        elif config.method == AuthMethod.OAUTH2_BEARER:
            return OAuth2BearerAuthProvider(
                required_scopes=config.oauth2_required_scopes
            )
        
        else:
            raise ValueError(f"Unsupported authentication method: {config.method}")
