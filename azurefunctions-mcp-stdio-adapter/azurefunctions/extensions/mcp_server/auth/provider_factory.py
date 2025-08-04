"""
Authentication provider factory for MCP servers.

This module provides a factory for creating authentication providers
based on configuration settings.
"""

import logging
from typing import Optional

from ..models.configuration import AuthConfiguration, AuthMethod
from .token_handler import (
    AuthProvider,
    AzureDefaultAuthProvider,
    AzureOBOAuthProvider,
    NoAuthProvider,
    OAuth2BearerAuthProvider,
)

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
        logger.info(f"🏭 Creating provider for method: {config.method} (type: {type(config.method)})")
        logger.info(f"🏭 Available methods: NONE={AuthMethod.NONE}, AZURE_DEFAULT={AuthMethod.AZURE_DEFAULT}")
        logger.info(f"🏭 Method comparison: {config.method} == {AuthMethod.AZURE_DEFAULT} = {config.method == AuthMethod.AZURE_DEFAULT}")
        
        if config.method == AuthMethod.NONE:
            logger.info("✅ Creating NoAuthProvider")
            return NoAuthProvider()

        elif config.method == AuthMethod.AZURE_DEFAULT:
            logger.info(f"✅ Creating AzureDefaultAuthProvider with scopes: {config.azure_scopes}")
            logger.info(f"✅ Client ID: {getattr(config, 'azure_client_id', 'Not provided')}")
            return AzureDefaultAuthProvider(
                scopes=config.azure_scopes,
                client_id=getattr(config, 'azure_client_id', None)
            )

        elif config.method == AuthMethod.AZURE_OBO:
            if not config.azure_client_id or not config.azure_client_secret:
                raise ValueError("Azure OBO requires client_id and client_secret")

            logger.info("✅ Creating AzureOBOAuthProvider")
            return AzureOBOAuthProvider(
                client_id=config.azure_client_id,
                client_secret=config.azure_client_secret,
                scopes=config.azure_scopes,
            )

        elif config.method == AuthMethod.OAUTH2_BEARER:
            logger.info("✅ Creating OAuth2BearerAuthProvider")
            return OAuth2BearerAuthProvider(
                required_scopes=config.oauth2_required_scopes
            )

        else:
            logger.error(f"❌ Unsupported authentication method: {config.method} (type: {type(config.method)})")
            raise ValueError(f"Unsupported authentication method: {config.method}")
