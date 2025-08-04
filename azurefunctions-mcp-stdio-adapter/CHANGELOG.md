# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0a1] - 2025-08-04

### Added

- Initial alpha release of Azure Functions MCP STDIO Adapter
- Support for STDIO-based MCP servers to HTTP endpoint conversion
- Multi-tenant session isolation with dedicated process per session
- Comprehensive authentication framework:
  - Azure On-Behalf-Of (OBO) authentication for Azure services
  - Generic OAuth2 Bearer token authentication
  - Azure Default Credentials for managed identity scenarios
  - No-auth mode for development and testing
- Configuration support for multiple MCP servers
- Process lifecycle management with automatic restart capabilities
- Streaming HTTP integration using MCP SDK
- UVX integration for running MCP servers without global installation
- Environment variable injection for secure credential passing
- Session-aware authentication with per-session isolation
- Comprehensive documentation and examples

### Features

- **Authentication Methods:**
  - `azure_obo`: On-Behalf-Of flow for user context preservation
  - `oauth2_bearer`: Generic OAuth2 token validation and forwarding
  - `azure_default`: Managed identity and default credential support
  - `none`: Development mode without authentication

- **Session Management:**
  - Dedicated MCP server process per session
  - Automatic session cleanup and resource management
  - Session state tracking and timeout handling
  - Cross-session isolation for multi-tenant scenarios

- **Configuration:**
  - JSON-based configuration with validation
  - Environment variable substitution
  - Multiple MCP server support
  - Flexible authentication settings per server

- **Process Management:**
  - Automatic MCP server startup and monitoring
  - Graceful shutdown and restart capabilities
  - Error recovery and failure handling
  - Resource cleanup and memory management

### Documentation

- Comprehensive README with usage examples
- Authentication implementation guide (AUTHENTICATION.md)
- Configuration examples for various scenarios
- Client integration examples for JavaScript, Python, and HTTP

### Examples

- Basic usage examples
- Authentication-enabled function apps
- Configuration files for different auth methods
- Client-side integration patterns

## Security Considerations

This release includes:

- JWT token parsing and validation (signature verification recommended for production)
- Secure environment variable injection for credentials
- Session isolation to prevent cross-tenant data access
- Best-effort multi-tenancy with process-level isolation

## Breaking Changes

None (initial release)

## Migration Guide

This is the initial release, no migration required.

[Unreleased]: https://github.com/Azure/azure-functions-python-extensions/compare/v0.1.0a1...HEAD
[0.1.0a1]: https://github.com/Azure/azure-functions-python-extensions/releases/tag/v0.1.0a1
