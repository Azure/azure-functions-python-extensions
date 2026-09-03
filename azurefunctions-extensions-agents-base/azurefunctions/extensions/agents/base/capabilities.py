from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillDefinition:
    path: Path


@dataclass(frozen=True)
class MCPAuthConfig:
    scope: str
    client_id: str | None = None


@dataclass(frozen=True)
class MCPHTTPConfig:
    url: str
    allowed_tools: tuple[str, ...] | None = None
    headers: tuple[tuple[str, str], ...] = ()
    auth: MCPAuthConfig | None = None


@dataclass(frozen=True)
class MCPServerDefinition:
    name: str
    config: MCPHTTPConfig


@dataclass(frozen=True)
class AgentCapabilities:
    skills: tuple[SkillDefinition, ...] = ()
    mcp_servers: tuple[MCPServerDefinition, ...] = ()
