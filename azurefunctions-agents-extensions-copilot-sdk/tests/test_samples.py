from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_PACKAGE_ROOT = Path(__file__).parents[1]
_SAMPLES_ROOT = _PACKAGE_ROOT / "samples"


@pytest.mark.parametrize(
    ("sample_name", "expected_names"),
    [
        (
            "agent_samples_copilot-sdk",
            {"process_order", "process_order_event"},
        ),
        (
            "agent_samples_copilot-sdk_durable",
            {
                "azurefunctions_agents_run_markdown_agent",
                "order_orchestrator",
                "start_order_orchestration",
            },
        ),
    ],
)
def test_sample_indexes_all_functions(sample_name, expected_names):
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(_PACKAGE_ROOT), environment.get("PYTHONPATH")])
    )
    environment.update(
        {
            "COPILOT_GITHUB_TOKEN": "index-only-placeholder",
            "COPILOT_MODEL": "gpt-5",
            "INVENTORY_MCP_URL": "https://inventory.example.test/mcp",
        }
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import json; import function_app; "
                "print(json.dumps([function.get_function_name() "
                "for function in function_app.app.get_functions()]))"
            ),
        ],
        cwd=_SAMPLES_ROOT / sample_name,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert set(json.loads(completed.stdout)) == expected_names


def test_direct_sample_assets_follow_discovery_conventions():
    sample_root = _SAMPLES_ROOT / "agent_samples_copilot-sdk"

    assert (sample_root / "order-fulfillment.agent.md").is_file()
    assert (sample_root / "skills" / "order-policy" / "SKILL.md").is_file()
    assert (sample_root / "mcp.json").is_file()
