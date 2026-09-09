from __future__ import annotations

from pathlib import Path

from ..capabilities import AgentCapabilities
from .mcp import discover_mcp_servers
from .skills import discover_skills


def discover_capabilities(app_root: Path) -> AgentCapabilities:
    return AgentCapabilities(
        skills=discover_skills(app_root),
        mcp_servers=discover_mcp_servers(app_root),
    )


__all__ = [
    "discover_capabilities",
    "discover_mcp_servers",
    "discover_skills",
]
