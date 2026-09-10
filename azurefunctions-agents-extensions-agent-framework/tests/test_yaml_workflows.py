from __future__ import annotations

import builtins
from importlib.util import find_spec
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest

from azurefunctions.agents.extensions.agent_framework import AgentFunctionApp
from azurefunctions.agents.extensions.agent_framework import _workflows


@pytest.mark.parametrize("value", [None, 0, 1, "true", [], {}])
def test_workflows_flag_requires_bool(tmp_path, value):
    with pytest.raises(TypeError, match="workflows must be a bool"):
        AgentFunctionApp(
            client_factory=lambda: None, app_root=tmp_path, workflows=value,
        )


def test_workflows_requires_explicit_durable_opt_in(tmp_path):
    with pytest.raises(ValueError, match="requires durable=True"):
        AgentFunctionApp(client_factory=lambda: None, app_root=tmp_path, workflows=True)


def test_workflow_files_are_ignored_without_workflow_opt_in(tmp_path):
    (tmp_path / "bad.workflow.yaml").write_text("not valid: [", encoding="utf-8")
    plain = AgentFunctionApp(client_factory=lambda: None, app_root=tmp_path)
    assert plain.get_functions() == []
    durable = AgentFunctionApp(
        client_factory=lambda: None, app_root=tmp_path, durable=True,
    )
    assert durable._durable_app.workflows == {}


def test_unsupported_python_does_not_silently_ignore_expressions(tmp_path, monkeypatch):
    monkeypatch.setattr(_workflows.sys, "version_info", (3, 14))
    with pytest.raises(RuntimeError, match="Python 3.13"):
        _workflows.load_workflows(tmp_path, Mock())


@pytest.mark.parametrize("missing", ["yaml", "agent_framework_declarative", "clr"])
def test_missing_workflow_dependencies(tmp_path, monkeypatch, missing):
    monkeypatch.setattr(_workflows.sys, "version_info", (3, 13))
    original = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "yaml":
            raise ModuleNotFoundError(name=missing)
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    with pytest.raises(ImportError) as error:
        _workflows.load_workflows(tmp_path, Mock())
    if missing == "clr":
        assert error.value.name == "clr"
    else:
        assert "[durable,workflows]" in str(error.value)


def test_workflow_symlink_escape_is_rejected(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside.yaml"
    outside.write_text("name: Outside", encoding="utf-8")
    try:
        (tmp_path / "escape.workflow.yaml").symlink_to(outside)
    except OSError as error:
        pytest.skip(f"Symlinks unavailable: {error}")
    with pytest.raises(ValueError, match="escapes app root"):
        _workflows._definition_paths(tmp_path)


@pytest.mark.parametrize("mode", ["validation", "execution", "sample"])
def test_real_yaml_workflow_probes(mode):
    if sys.version_info >= (3, 14) or find_spec("agent_framework_declarative") is None:
        pytest.skip("Requires Python 3.13 and workflows extra")
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(Path(__file__).with_name(
            "_yaml_workflow_probe.py")), mode],
        capture_output=True, text=True, encoding="utf-8", timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(result.stdout.strip().splitlines()[-1])["result"]
    if mode == "execution":
        assert set(data) == {
            "simple", "state", "branch", "else", "loop", "agent", "human",
            "if-agent", "if-else-agent",
        }
    elif mode == "sample":
        assert data == {
            "OrderReview": ["User turn 1: Review order 42."],
            "Approval": ["approved"],
        }
    else:
        assert len(data) == 21
