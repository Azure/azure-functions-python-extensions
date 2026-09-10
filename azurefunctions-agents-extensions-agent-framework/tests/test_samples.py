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
            "agent_samples_agent-framework",
            {"process_order", "process_order_event"},
        ),
        (
            "agent_samples_agent-framework_durable",
            {
                "azurefunctions_agents_run_markdown_agent",
                "order_orchestrator",
                "prepare_order_activity",
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


def test_agent_framework_sample_rejects_malformed_json():
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(_PACKAGE_ROOT), environment.get("PYTHONPATH")])
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import asyncio, json; import azure.functions as func; "
                "import function_app; "
                "request = func.HttpRequest(method='POST', url='https://example.test', "
                "body=b'{not json', route_params={'orderId': '42'}); "
                "handler = function_app.process_order._function.get_user_function()"
                ".__wrapped__; "
                "response = asyncio.run(handler(request, object())); "
                "print(json.dumps({'status_code': response.status_code, "
                "'body': response.get_body().decode()}))"
            ),
        ],
        cwd=_SAMPLES_ROOT / "agent_samples_agent-framework",
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(completed.stdout)
    assert result["status_code"] == 400
    assert json.loads(result["body"]) == {"error": "Order failed validation."}


def test_agent_framework_durable_sample_starts_orchestration():
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(_PACKAGE_ROOT), environment.get("PYTHONPATH")])
    )
    script = (
        "import asyncio, json\n"
        "import azure.functions as func\n"
        "import function_app\n"
        "class FakeClient:\n"
        "    async def start_new(self, name, *, client_input):\n"
        "        return 'instance-42'\n"
        "    def create_http_management_payload(self, request, instance_id):\n"
        "        assert request is not None\n"
        "        return {'statusQueryGetUri': 'https://example.test/status/42'}\n"
        "request = func.HttpRequest(method='POST', url='https://example.test', "
        "body=b'{}')\n"
        "handler = function_app.start_order_orchestration._function"
        ".get_user_function().__wrapped__\n"
        "response = asyncio.run(handler(request, FakeClient()))\n"
        "print(json.dumps({'status_code': response.status_code, "
        "'mimetype': response.mimetype, "
        "'location': response.headers['Location']}))\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=_SAMPLES_ROOT / "agent_samples_agent-framework_durable",
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == {
        "status_code": 202,
        "mimetype": "application/json",
        "location": "https://example.test/status/42",
    }


def test_agent_framework_durable_sample_rejects_malformed_json():
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(_PACKAGE_ROOT), environment.get("PYTHONPATH")])
    )
    script = (
        "import asyncio, json\n"
        "import azure.functions as func\n"
        "import function_app\n"
        "class FakeClient:\n"
        "    async def start_new(self, name, *, client_input):\n"
        "        raise AssertionError('orchestration must not start')\n"
        "request = func.HttpRequest(method='POST', url='https://example.test', "
        "body=b'{not json')\n"
        "handler = function_app.start_order_orchestration._function"
        ".get_user_function().__wrapped__\n"
        "response = asyncio.run(handler(request, FakeClient()))\n"
        "print(json.dumps({'status_code': response.status_code, "
        "'body': response.get_body().decode()}))\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=_SAMPLES_ROOT / "agent_samples_agent-framework_durable",
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    result = json.loads(completed.stdout)
    assert result["status_code"] == 400
    assert json.loads(result["body"]) == {"error": "Order failed validation."}


def test_agent_framework_sample_assets_follow_discovery_conventions():
    sample_root = _SAMPLES_ROOT / "agent_samples_agent-framework"

    assert (sample_root / "order-fulfillment.agent.md").is_file()
    assert (sample_root / "skills" / "order-policy" / "SKILL.md").is_file()
    assert (sample_root / "mcp.json").is_file()
