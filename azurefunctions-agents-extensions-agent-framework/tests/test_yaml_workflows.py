from __future__ import annotations

import builtins
from importlib.util import find_spec
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock, call

import pytest

from azurefunctions.agents.extensions.agent_framework import AgentFunctionApp
from azurefunctions.agents.extensions.agent_framework import _workflows


@pytest.mark.parametrize("value", [None, 0, 1, "true", [], {}])
def test_discover_workflows_flag_requires_bool(tmp_path, value):
    with pytest.raises(TypeError, match="discover_workflows must be a bool"):
        AgentFunctionApp(
            client_factory=lambda: None, app_root=tmp_path, discover_workflows=value,
        )


def test_workflow_discovery_does_not_register_standalone_agents(tmp_path, monkeypatch):
    (tmp_path / "orders.agent.md").write_text("Handle orders.", encoding="utf-8")
    load = Mock(return_value=[])
    monkeypatch.setattr(_workflows, "load_workflows", load)
    app = AgentFunctionApp(
        client_factory=lambda: None, app_root=tmp_path, discover_workflows=True,
    )
    assert set(app._markdown_agents) == {"orders"}
    load.assert_called_once_with(tmp_path, app._markdown_agents, factory=None)
    assert app._durable_agents == {}
    assert app._hosted_workflows == {}
    assert app.get_functions() == []
    assert app._durable_app is None


def test_workflow_files_are_ignored_without_workflow_opt_in(tmp_path):
    (tmp_path / "bad.workflow.yaml").write_text("not valid: [", encoding="utf-8")
    plain = AgentFunctionApp(client_factory=lambda: None, app_root=tmp_path)
    assert plain.get_functions() == []
    durable = AgentFunctionApp(
        client_factory=lambda: None, app_root=tmp_path, discover_agents=True,
    )
    assert durable._hosted_workflows == {}
    assert durable.get_functions() == []
    assert durable._durable_app is None


def test_factory_can_be_configured_without_workflow_discovery(tmp_path):
    (tmp_path / "bad.workflow.yaml").write_text("not valid: [", encoding="utf-8")
    factory = Mock()
    app = AgentFunctionApp(client_factory=lambda: None, app_root=tmp_path,
                           workflow_factory=factory)
    assert app._workflow_factory is factory
    assert factory.mock_calls == []
    assert app._hosted_workflows == {}
    assert app.get_functions() == []
    assert app._durable_app is None


@pytest.mark.parametrize("missing", ["agent_framework_declarative", "yaml", "clr"])
def test_missing_workflow_dependencies(tmp_path, monkeypatch, missing):
    (tmp_path / "orders.workflow.yaml").write_text("name: Orders", encoding="utf-8")
    original = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "agent_framework.declarative":
            raise ModuleNotFoundError(name=missing)
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    with pytest.raises(ImportError) as error:
        _workflows.load_workflows(tmp_path, {})
    if missing == "agent_framework_declarative":
        assert "[durable,workflows]" in str(error.value)
    else:
        assert error.value.name == missing


def test_custom_factory_is_used_unchanged_without_declarative_import(
    tmp_path, monkeypatch,
):
    from agent_framework import Workflow
    original = builtins.__import__

    def no_declarative(name, *args, **kwargs):
        if "declarative" in name or name in {"yaml", "powerfx"}:
            raise AssertionError("Custom factory must not import the default loader")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_declarative)
    paths = [tmp_path / "one.workflow.yaml", tmp_path / "workflows/two.workflow.yml"]
    for path in paths:
        path.parent.mkdir(exist_ok=True)
        path.write_text("caller-defined format", encoding="utf-8")
    outputs = [Mock(spec=Workflow, name="One"), Mock(spec=Workflow, name="Two")]
    for output, name in zip(outputs, ["One", "Two"]):
        output.name = name
    factory = Mock()
    factory.create_workflow_from_yaml_path.side_effect = outputs
    assert _workflows.load_workflows(tmp_path, {"ignored": object()}, factory) == (
        outputs
    )
    assert factory.method_calls == [
        call.create_workflow_from_yaml_path(path) for path in paths
    ]


def test_custom_factory_errors_propagate(tmp_path):
    (tmp_path / "bad.workflow.yaml").touch()
    error = RuntimeError("custom factory rejected definition")
    factory = Mock()
    factory.create_workflow_from_yaml_path.side_effect = error
    with pytest.raises(RuntimeError) as caught:
        _workflows.load_workflows(tmp_path, {}, factory)
    assert caught.value is error


def test_factory_must_return_a_workflow(tmp_path):
    (tmp_path / "bad.workflow.yaml").touch()
    factory = Mock()
    factory.create_workflow_from_yaml_path.return_value = object()
    with pytest.raises(TypeError, match="MAF Workflow"):
        _workflows.load_workflows(tmp_path, {}, factory)


def test_workflow_symlink_escape_is_rejected(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside.yaml"
    outside.write_text("name: Outside", encoding="utf-8")
    try:
        (tmp_path / "escape.workflow.yaml").symlink_to(outside)
    except OSError as error:
        pytest.skip(f"Symlinks unavailable: {error}")
    with pytest.raises(ValueError, match="escapes app root"):
        _workflows._definition_paths(tmp_path)


@pytest.mark.parametrize("mode", [
    "validation", "execution", "sample", "native", "configured-sample",
])
def test_real_yaml_workflow_probes(mode):
    if sys.version_info >= (3, 14) or find_spec("agent_framework_declarative") is None:
        pytest.skip("Requires Python 3.13 and workflows extra")
    filename = (
        "_native_workflow_probe.py" if mode == "native" else "_yaml_workflow_probe.py"
    )
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(Path(__file__).with_name(
            filename)), mode],
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
    elif mode == "validation":
        assert len(data) == 13
    elif mode == "configured-sample":
        assert data == ["Local order 42."]
    else:
        assert len(data) == 13
