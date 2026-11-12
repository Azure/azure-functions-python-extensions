from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from copilot import CopilotClient, ToolSet
from copilot.session import (
    MCPHTTPServerConfig,
    MCPStdioServerConfig,
    PermissionHandler,
    SystemMessageReplaceConfig,
)
from copilot.session_events import AssistantMessageData

SAMPLE_ROOT = Path(__file__).resolve().parent


def required_setting(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"{name} must be set")
    return value


async def assess_order(order_id: str, order: dict[str, object]) -> str:
    instructions = (SAMPLE_ROOT / "order-fulfillment.agent.md").read_text(
        encoding="utf-8"
    )
    skill_directories = [str(SAMPLE_ROOT / "skills")]
    mcp_servers: dict[str, MCPStdioServerConfig | MCPHTTPServerConfig] = {
        "inventory": {
            "type": "http",
            "url": required_setting("INVENTORY_MCP_URL"),
            "tools": ["lookup_stock"],
        }
    }
    available_tools = ToolSet()
    available_tools.add_builtin("skill")
    available_tools.add_mcp("*")

    async with CopilotClient(
        mode="empty",
        github_token=required_setting("COPILOT_GITHUB_TOKEN"),
        base_directory=required_setting("COPILOT_BASE_DIRECTORY"),
        use_logged_in_user=False,
        log_level="none",
        telemetry=None,
    ) as client:
        session = await client.create_session(
            model=required_setting("COPILOT_MODEL"),
            available_tools=available_tools,
            system_message=SystemMessageReplaceConfig(
                mode="replace",
                content=instructions,
            ),
            on_permission_request=PermissionHandler.approve_all,
            streaming=False,
            enable_config_discovery=False,
            enable_session_telemetry=False,
            request_extensions=False,
            enable_session_store=False,
            included_builtin_skills=[],
            enable_skills=True,
            skill_directories=skill_directories,
            mcp_servers=mcp_servers,
            mcp_oauth_token_storage="in-memory",
            skip_custom_instructions=True,
            tool_search={"enabled": False},
            infinite_sessions={"enabled": False},
            memory={"enabled": False},
        )
        async with session:
            response = await session.send_and_wait(
                json.dumps(
                    {
                        "order_id": order_id,
                        "order": order,
                        "task": "assess fulfillment readiness",
                    }
                )
            )

    if response is None or not isinstance(response.data, AssistantMessageData):
        raise RuntimeError("Copilot did not return a final assistant message")
    if not isinstance(response.data.content, str):
        raise RuntimeError("Copilot returned non-text assistant content")
    return response.data.content


async def main() -> None:
    assessment = await assess_order(
        "sample-order-001",
        {
            "sku": "SKU-LOCAL-001",
            "quantity": 2,
            "destination": "Seattle",
            "priority": "standard",
        },
    )
    print(json.dumps({"assessment": assessment}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
