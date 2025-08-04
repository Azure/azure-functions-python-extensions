"""
Token handling and authentication for MCP servers.

This module provides authentication mechanisms for MCP servers,
including Azure AD token handling and OBO flows.
"""

import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class AuthMethod(Enum):
    """Supported authentication methods."""
    NONE = "none"
    AZURE_DEFAULT = "azure_default" 
    AZURE_OBO = "azure_obo"
    OAUTH2_BEARER = "oauth2_bearer"


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
    
    def __init__(self, scopes: Optional[list] = None):
        self.scopes = scopes or ["https://management.azure.com/.default"]
    
    async def authenticate(self, request_headers: Dict[str, str]) -> AuthContext:
        # For Azure Default, we don't validate incoming tokens
        # The MCP server will use DefaultAzureCredential
        return AuthContext(method=AuthMethod.AZURE_DEFAULT)
    
    def get_environment_vars(self, auth_context: AuthContext) -> Dict[str, str]:
        # Azure SDK will automatically pick up DefaultAzureCredential
        return {
            "AZURE_CLIENT_ID": "",  # Will be set by managed identity
            "AZURE_USE_MANAGED_IDENTITY": "true"
        }


class AzureOBOAuthProvider(AuthProvider):
    """Azure On-Behalf-Of authentication."""
    
    def __init__(self, client_id: str, client_secret: str, scopes: Optional[list] = None):
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
            parts = user_token.split('.')
            if len(parts) != 3:
                raise AuthenticationError("Invalid JWT format")
            
            # Decode payload (add padding if needed)
            payload = parts[1]
            payload += '=' * (4 - len(payload) % 4)
            claims = json.loads(base64.urlsafe_b64decode(payload))
            
            return AuthContext(
                method=AuthMethod.AZURE_OBO,
                access_token=user_token,
                user_id=claims.get("sub"),
                tenant_id=claims.get("tid"),
                claims=claims
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
            "AZURE_USE_OBO": "true"
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
            
            parts = token.split('.')
            if len(parts) != 3:
                raise AuthenticationError("Invalid JWT format")
            
            payload = parts[1]
            payload += '=' * (4 - len(payload) % 4)
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
                claims=claims
            )
        except Exception as e:
            raise AuthenticationError(f"Invalid token: {e}")
    
    def get_environment_vars(self, auth_context: AuthContext) -> Dict[str, str]:
        """Pass token as environment variable."""
        return {
            "OAUTH_ACCESS_TOKEN": auth_context.access_token or "",
            "OAUTH_USER_ID": auth_context.user_id or "",
            "OAUTH_SCOPES": " ".join(auth_context.scopes or [])
        }


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class AuthManager:
    """Manages authentication for MCP servers."""
    
    def __init__(self, provider: AuthProvider):
        self.provider = provider
    
    async def authenticate_request(self, request_headers: Dict[str, str]) -> AuthContext:
        """Authenticate a request and return auth context."""
        return await self.provider.authenticate(request_headers)
    
    def get_auth_env_vars(self, auth_context: AuthContext) -> Dict[str, str]:
        """Get environment variables for authenticated MCP server process."""
        return self.provider.get_environment_vars(auth_context)
