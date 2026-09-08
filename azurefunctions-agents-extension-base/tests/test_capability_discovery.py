from __future__ import annotations

import json

import pytest

from azurefunctions.extensions.agents.base.discovery import (
    discover_mcp_servers,
    discover_skills,
)


def test_discover_skills_returns_paths_in_stable_order_without_parsing(tmp_path):
    for directory, contents in (
        ("z-last", "not frontmatter"),
        ("a-first", "---\nmalformed: [\n---\n"),
    ):
        skill_directory = tmp_path / "skills" / directory
        skill_directory.mkdir(parents=True)
        (skill_directory / "SKILL.md").write_text(
            contents,
            encoding="utf-8",
        )

    skills = discover_skills(tmp_path)

    assert tuple(skill.path for skill in skills) == (
        (tmp_path / "skills" / "a-first").resolve(),
        (tmp_path / "skills" / "z-last").resolve(),
    )


def test_discover_mcp_servers_keeps_environment_references_immutable(tmp_path):
    config = {
        "servers": {
            "inventory": {
                "type": "streamable-http",
                "url": "$INVENTORY_MCP_URL",
                "tools": ["lookup", "reserve"],
                "headers": {"X-Tenant": "%TENANT_ID%"},
                "auth": {
                    "scope": "$INVENTORY_SCOPE",
                    "client_id": "%CLIENT_ID%",
                },
            }
        }
    }
    (tmp_path / "mcp.json").write_text(json.dumps(config), encoding="utf-8")

    servers = discover_mcp_servers(tmp_path)

    assert len(servers) == 1
    server = servers[0]
    assert server.name == "inventory"
    assert server.config.url == "$INVENTORY_MCP_URL"
    assert server.config.allowed_tools == ("lookup", "reserve")
    assert server.config.headers == (("X-Tenant", "%TENANT_ID%"),)
    assert server.config.auth is not None
    assert server.config.auth.scope == "$INVENTORY_SCOPE"
    assert server.config.auth.client_id == "%CLIENT_ID%"


def test_discover_mcp_servers_rejects_stdio(tmp_path):
    config = {
        "servers": {
            "local": {
                "type": "stdio",
                "command": "python",
                "args": ["server.py"],
            }
        }
    }
    (tmp_path / "mcp.json").write_text(json.dumps(config), encoding="utf-8")

    with pytest.raises(ValueError, match="stdio"):
        discover_mcp_servers(tmp_path)
