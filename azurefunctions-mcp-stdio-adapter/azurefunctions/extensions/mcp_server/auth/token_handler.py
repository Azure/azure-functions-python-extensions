"""
Token handling and authentication for MCP servers.

This module provides authentication mechanisms for MCP servers,
including Azure AD token handling and OBO flows.
"""

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional
import os

from ..models.configuration import AuthMethod

logger = logging.getLogger(__name__)


@dataclass
class AuthContext:
    """Authentication context for a request."""

    method: AuthMethod
    access_token: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    scopes: Optional[list] = None
    claims: Optional[Dict[str, Any]] = None


class AuthProvider(ABC):
    """Abstract base class for authentication providers."""

    @abstractmethod
    async def authenticate(self, request_headers: Dict[str, str]) -> AuthContext:
        """
        Authenticate a request based on headers.

        Args:
            request_headers: HTTP headers from the request

        Returns:
            AuthContext with authentication details

        Raises:
            AuthenticationError: If authentication fails
        """
        pass

    @abstractmethod
    def get_environment_vars(self, auth_context: AuthContext) -> Dict[str, str]:
        """
        Get environment variables to pass to the MCP server process.

        Args:
            auth_context: Authentication context

        Returns:
            Dictionary of environment variables
        """
        pass


class NoAuthProvider(AuthProvider):
    """No authentication - for development/testing."""

    async def authenticate(self, request_headers: Dict[str, str]) -> AuthContext:
        return AuthContext(method=AuthMethod.NONE)

    def get_environment_vars(self, auth_context: AuthContext) -> Dict[str, str]:
        return {}


class AzureDefaultAuthProvider(AuthProvider):
    """Azure Default Credential authentication."""

    def __init__(self, scopes: Optional[list] = None, client_id: Optional[str] = None):
        self.scopes = scopes or ["https://management.azure.com/.default"]
        self.client_id = client_id
        logger.info(f"🔑 AzureDefaultAuthProvider initialized with client_id: {client_id}")

    async def authenticate(self, request_headers: Dict[str, str]) -> AuthContext:
        # For Azure Default, we don't validate incoming tokens
        # The MCP server will use DefaultAzureCredential
        return AuthContext(method=AuthMethod.AZURE_DEFAULT)

    def get_environment_vars(self, auth_context: AuthContext) -> Dict[str, str]:
        """Pass through Azure managed identity environment variables to subprocess."""
        import os
        
        # Debug: Log all available environment variables starting with specific prefixes
        logger.info("=== DEBUGGING AZURE ENVIRONMENT VARIABLES ===")
        azure_related_vars = {}
        for key, value in os.environ.items():
            if any(prefix in key.upper() for prefix in ["AZURE", "IDENTITY", "MSI", "WEBSITE", "FUNCTIONS"]):
                # Mask sensitive values for logging
                masked_value = value[:10] + "..." if len(value) > 10 else value
                azure_related_vars[key] = masked_value
                logger.info(f"Available: {key} = {masked_value}")
        
        logger.info(f"Found {len(azure_related_vars)} Azure-related environment variables")
        
        env_vars = {}
        
        # Pass through all Azure-related environment variables from the parent process
        azure_env_vars = [
            # Managed Identity specific
            "IDENTITY_ENDPOINT",
            "IDENTITY_HEADER", 
            "MSI_ENDPOINT",
            "MSI_SECRET",
            
            # App Service / Functions specific
            "WEBSITE_SITE_NAME",
            "WEBSITE_RESOURCE_GROUP", 
            "WEBSITE_OWNER_NAME",
            "FUNCTIONS_EXTENSION_VERSION",
            
            # Azure credentials
            "AZURE_CLIENT_ID",
            "AZURE_TENANT_ID",
            "AZURE_SUBSCRIPTION_ID",
            
            # Additional Azure environment variables
            "AZURE_CLOUD_NAME",
            "AZURE_AUTHORITY_HOST",
            "AZURE_RESOURCE_MANAGER_URL",
        ]
        
        # Copy Azure environment variables from parent process
        passed_vars = 0
        for var in azure_env_vars:
            value = os.environ.get(var)
            if value:
                env_vars[var] = value
                passed_vars += 1
                logger.info(f"Passing to MCP server: {var} = {value[:10]}...")
            else:
                logger.debug(f"Missing environment variable: {var}")
                
        # If we have managed identity variables, set up AZURE_CLIENT_ID
        if "MSI_ENDPOINT" in env_vars or "IDENTITY_ENDPOINT" in env_vars:
            # First priority: explicitly provided client_id from configuration
            if self.client_id:
                env_vars["AZURE_CLIENT_ID"] = self.client_id
                passed_vars += 1
                logger.info(f"🎯 Using configured client_id: {self.client_id}")
            elif "AZURE_CLIENT_ID" not in env_vars:
                # Second priority: try to get it from function app environment
                client_id_candidates = [
                    os.environ.get("AZURE_CLIENT_ID"),
                    os.environ.get("WEBSITE_AZURE_CLIENT_ID"), 
                    os.environ.get("APPSETTING_AZURE_CLIENT_ID"),
                    os.environ.get("MSI_CLIENT_ID")
                ]
                
                function_client_id = next((cid for cid in client_id_candidates if cid), None)
                if function_client_id:
                    env_vars["AZURE_CLIENT_ID"] = function_client_id
                    passed_vars += 1
                    logger.info(f"Setting AZURE_CLIENT_ID for user-assigned MI: {function_client_id[:10]}...")
                else:
                    logger.warning("No AZURE_CLIENT_ID found - using system-assigned managed identity")
                
        # Ensure we indicate managed identity should be used
        env_vars["AZURE_USE_MANAGED_IDENTITY"] = "true"
        
        # Additional environment variables to help Azure SDK detect managed identity
        # These are sometimes needed depending on the Azure SDK version
        if "MSI_ENDPOINT" in env_vars:
            # For older Azure SDK versions, set explicit managed identity URL
            env_vars["AZURE_MSI_ENDPOINT"] = env_vars["MSI_ENDPOINT"]
            
        if "IDENTITY_ENDPOINT" in env_vars:
            # For newer Azure SDK versions
            env_vars["AZURE_IDENTITY_ENDPOINT"] = env_vars["IDENTITY_ENDPOINT"]
            
        if "IDENTITY_HEADER" in env_vars:
            env_vars["AZURE_IDENTITY_HEADER"] = env_vars["IDENTITY_HEADER"]
            
        # Force exclude certain credential types that might interfere
        env_vars["AZURE_EXCLUDE_CLI_CREDENTIAL"] = "true"
        env_vars["AZURE_EXCLUDE_BROWSER_CREDENTIAL"] = "true"
        env_vars["AZURE_EXCLUDE_SHARED_TOKEN_CACHE_CREDENTIAL"] = "true"
        env_vars["AZURE_EXCLUDE_VISUAL_STUDIO_CREDENTIAL"] = "true"
        env_vars["AZURE_EXCLUDE_VISUAL_STUDIO_CODE_CREDENTIAL"] = "true"
        env_vars["AZURE_EXCLUDE_AZURE_POWERSHELL_CREDENTIAL"] = "true"
        env_vars["AZURE_EXCLUDE_AZURE_DEVELOPER_CLI_CREDENTIAL"] = "true"
        
        # Force managed identity to be prioritized
        env_vars["AZURE_EXCLUDE_ENVIRONMENT_CREDENTIAL"] = "false"
        env_vars["AZURE_EXCLUDE_MANAGED_IDENTITY_CREDENTIAL"] = "false"
        
        logger.info(f"=== PASSING {passed_vars + 9} ENVIRONMENT VARIABLES TO MCP SERVER ===")
        
        # Log all environment variables being passed (masked for security)
        logger.info("📋 Environment variables being passed to MCP server:")
        for key, value in sorted(env_vars.items()):
            if key in ["MSI_SECRET", "IDENTITY_HEADER", "AZURE_CLIENT_SECRET"]:
                masked_value = "***MASKED***"
            elif len(str(value)) > 20:
                masked_value = str(value)[:10] + "..." + str(value)[-5:]
            else:
                masked_value = str(value)
            logger.info(f"  {key} = {masked_value}")
        
        # Also log the current working directory and other debug info
        logger.info(f"🗂️ Current working directory: {os.getcwd()}")
        import sys
        logger.info(f"🐍 Python executable: {sys.executable}")
        
        return env_vars


class AzureOBOAuthProvider(AuthProvider):
    """Azure On-Behalf-Of authentication."""

    def __init__(
        self, client_id: str, client_secret: str, scopes: Optional[list] = None
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.scopes = scopes or ["https://management.azure.com/.default"]

    async def authenticate(self, request_headers: Dict[str, str]) -> AuthContext:
        """Extract and validate Bearer token from Authorization header."""
        auth_header = request_headers.get("authorization", "")

        if not auth_header.startswith("Bearer "):
            raise AuthenticationError("Missing or invalid Authorization header")

        user_token = auth_header[7:]  # Remove "Bearer " prefix

        try:
            # Simple JWT parsing without verification for now
            # In production, you should verify the token signature
            import base64

            # Split the JWT and decode the payload
            parts = user_token.split(".")
            if len(parts) != 3:
                raise AuthenticationError("Invalid JWT format")

            # Decode payload (add padding if needed)
            payload = parts[1]
            payload += "=" * (4 - len(payload) % 4)
            claims = json.loads(base64.urlsafe_b64decode(payload))

            return AuthContext(
                method=AuthMethod.AZURE_OBO,
                access_token=user_token,
                user_id=claims.get("sub"),
                tenant_id=claims.get("tid"),
                claims=claims,
            )
        except Exception as e:
            raise AuthenticationError(f"Invalid token: {e}")

    def get_environment_vars(self, auth_context: AuthContext) -> Dict[str, str]:
        """Set environment variables for OBO flow."""
        if not auth_context.access_token:
            raise AuthenticationError("No access token available for OBO")

        return {
            "AZURE_CLIENT_ID": self.client_id,
            "AZURE_CLIENT_SECRET": self.client_secret,
            "AZURE_TENANT_ID": auth_context.tenant_id or "",
            "AZURE_USER_ASSERTION": auth_context.access_token,
            "AZURE_USE_OBO": "true",
        }


class OAuth2BearerAuthProvider(AuthProvider):
    """Generic OAuth2 Bearer token authentication."""

    def __init__(self, required_scopes: Optional[list] = None):
        self.required_scopes = required_scopes or []

    async def authenticate(self, request_headers: Dict[str, str]) -> AuthContext:
        """Extract Bearer token and validate scopes."""
        auth_header = request_headers.get("authorization", "")

        if not auth_header.startswith("Bearer "):
            raise AuthenticationError("Missing or invalid Authorization header")

        token = auth_header[7:]

        try:
            # Simple JWT parsing without verification
            import base64

            parts = token.split(".")
            if len(parts) != 3:
                raise AuthenticationError("Invalid JWT format")

            payload = parts[1]
            payload += "=" * (4 - len(payload) % 4)
            claims = json.loads(base64.urlsafe_b64decode(payload))

            token_scopes = claims.get("scope", "").split()

            # Check required scopes
            if self.required_scopes:
                if not all(scope in token_scopes for scope in self.required_scopes):
                    raise AuthenticationError("Insufficient scopes")

            return AuthContext(
                method=AuthMethod.OAUTH2_BEARER,
                access_token=token,
                user_id=claims.get("sub"),
                scopes=token_scopes,
                claims=claims,
            )
        except Exception as e:
            raise AuthenticationError(f"Invalid token: {e}")

    def get_environment_vars(self, auth_context: AuthContext) -> Dict[str, str]:
        """Pass token as environment variable."""
        return {
            "OAUTH_ACCESS_TOKEN": auth_context.access_token or "",
            "OAUTH_USER_ID": auth_context.user_id or "",
            "OAUTH_SCOPES": " ".join(auth_context.scopes or []),
        }


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


class AuthManager:
    """Manages authentication for MCP servers."""

    def __init__(self, provider: AuthProvider):
        self.provider = provider

    async def authenticate_request(
        self, request_headers: Dict[str, str]
    ) -> AuthContext:
        """Authenticate a request and return auth context."""
        return await self.provider.authenticate(request_headers)

    def get_auth_env_vars(self, auth_context: AuthContext) -> Dict[str, str]:
        """Get environment variables for authenticated MCP server process."""
        return self.provider.get_environment_vars(auth_context)
