from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlsplit

from ..capabilities import (
    MCPAuthConfig,
    MCPHTTPConfig,
    MCPServerDefinition,
)

_ENV_REFERENCE = re.compile(
    r"(?:\$[A-Za-z_][A-Za-z0-9_]*|%[A-Za-z_][A-Za-z0-9_]*%)"
)
_VALID_SERVER_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate key {key!r} in mcp.json")
        result[key] = value
    return result


def _string(value: Any, *, field: str, required: bool = True) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"MCP {field} must be a non-empty string")
    return value.strip()


def _allowed_tools(value: Any) -> tuple[str, ...] | None:
    if value is None:
        return None
    if not isinstance(value, list) or any(
        not isinstance(tool, str) or not tool.strip() for tool in value
    ):
        raise ValueError("MCP tools must be a list of non-empty strings")
    tools = tuple(tool.strip() for tool in value)
    if len(tools) != len(set(tools)):
        raise ValueError("MCP tools must not contain duplicates")
    if "*" in tools:
        if len(tools) != 1:
            raise ValueError("MCP '*' tool selection cannot be combined")
        return None
    return tools


def _headers(value: Any) -> tuple[tuple[str, str], ...]:
    if value is None:
        return ()
    if not isinstance(value, dict):
        raise ValueError("MCP headers must be an object")
    headers: list[tuple[str, str]] = []
    for key, header_value in value.items():
        header_name = _string(key, field="header name")
        header_text = _string(header_value, field=f"header {key!r}")
        assert header_name is not None and header_text is not None
        headers.append((header_name, header_text))
    return tuple(sorted(headers))


def _auth(value: Any) -> MCPAuthConfig | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("MCP auth must be an object")
    unknown = sorted(set(value) - {"scope", "client_id"})
    if unknown:
        raise ValueError(f"Unknown MCP auth field(s): {', '.join(unknown)}")
    scope = _string(value.get("scope"), field="auth scope")
    client_id = _string(
        value.get("client_id"),
        field="auth client_id",
        required=False,
    )
    assert scope is not None
    return MCPAuthConfig(scope=scope, client_id=client_id)


def _server_definition(name: str, value: Any) -> MCPServerDefinition:
    if _VALID_SERVER_NAME.fullmatch(name) is None:
        raise ValueError(f"Invalid MCP server name {name!r}")
    if not isinstance(value, dict):
        raise ValueError(f"MCP server {name!r} must be an object")
    server = cast(dict[str, Any], value)
    server_type = str(server.get("type", "")).strip().lower()
    if "command" in server or server_type in {"stdio", "local"}:
        raise ValueError(f"MCP server {name!r} uses unsupported stdio transport")
    if server_type and server_type not in {"http", "streamable-http"}:
        raise ValueError(f"MCP server {name!r} has unsupported type {server_type!r}")

    url = _string(server.get("url"), field=f"server {name!r} url")
    assert url is not None
    if _ENV_REFERENCE.search(url) is None:
        parsed_url = urlsplit(url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError(f"MCP server {name!r} requires an HTTP URL")
    unknown = sorted(
        set(server) - {"type", "url", "tools", "headers", "auth"}
    )
    if unknown:
        raise ValueError(
            f"Unknown MCP server {name!r} field(s): {', '.join(unknown)}"
        )
    return MCPServerDefinition(
        name=name,
        config=MCPHTTPConfig(
            url=url,
            allowed_tools=_allowed_tools(server.get("tools")),
            headers=_headers(server.get("headers")),
            auth=_auth(server.get("auth")),
        ),
    )


def discover_mcp_servers(app_root: Path) -> tuple[MCPServerDefinition, ...]:
    resolved_root = Path(app_root).resolve(strict=True)
    candidate = resolved_root / "mcp.json"
    if not candidate.exists():
        return ()
    config_path = candidate.resolve(strict=True)
    if not config_path.is_relative_to(resolved_root):
        raise ValueError("mcp.json resolves outside the app root")
    try:
        data = json.loads(
            config_path.read_text(encoding="utf-8"),
            object_pairs_hook=_object_without_duplicates,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"Failed to read {str(config_path)!r}") from error
    if not isinstance(data, dict):
        raise ValueError("mcp.json must contain an object")
    servers = data.get("servers")
    if not isinstance(servers, dict):
        raise ValueError("mcp.json 'servers' must be an object")
    unknown = sorted(set(data) - {"servers"})
    if unknown:
        raise ValueError(f"Unknown mcp.json field(s): {', '.join(unknown)}")
    return tuple(
        _server_definition(name, servers[name])
        for name in sorted(servers)
    )
