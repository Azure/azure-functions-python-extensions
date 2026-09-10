from __future__ import annotations

from itertools import product
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock

import pytest
from agent_framework import AgentResponse, Message
from azure.durable_functions import DurableOrchestrationContext
from durabletask.task import CompletableTask, OrchestrationContext

from azurefunctions.agents.extensions.agent_framework import AgentFunctionApp
from azurefunctions.agents.extensions.agent_framework._workflow_client import (
    DurableWorkflow,
)


def define_agent(root):
    (root / "orders.agent.md").write_text("Handle orders", encoding="utf-8")


def agent_binding(app, exposed=False):
    @app.orchestration_trigger(context_name="context")
    @app.durable_markdown_agent(
        arg_name="agent", agent_name="orders", expose_http_endpoint=exposed,
    )
    def orchestrator(context, agent):
        yield agent.run("hello")
    return orchestrator


def http_routes(app):
    return [binding["route"] for fn in app.get_functions()
            for binding in fn.get_bindings_dict()["bindings"]
            if binding["type"] == "httpTrigger"]


@pytest.mark.parametrize("discover,bulk_exposed,binding_exposed", list(product(
    (False, True), repeat=3,
)))
def test_agent_discovery_and_binding_exposure_matrix(
    tmp_path, discover, bulk_exposed, binding_exposed,
):
    define_agent(tmp_path)
    app = AgentFunctionApp(
        client_factory=lambda: None, app_root=tmp_path,
        discover_agents=discover, expose_agent_endpoints=bulk_exposed,
    )
    before = app._durable_agents.get("orders")
    agent_binding(app, binding_exposed)
    if before:
        assert app._durable_agents["orders"] is before
    assert app._durable_app is None
    exposed = (discover and bulk_exposed) or binding_exposed
    expected = ["agents/orders/run"] if exposed else []
    assert http_routes(app) == expected
    functions = app.get_functions()
    assert sum(fn.get_function_name() == "dafx-orders" for fn in functions) == 1


@pytest.mark.parametrize("flags", [
    {}, {"expose_agent_endpoints": True}, {"expose_workflow_endpoints": True},
    {"discover_agents": True},
])
def test_empty_configuration_does_not_load_dafx(tmp_path, flags):
    app = AgentFunctionApp(client_factory=lambda: None, app_root=tmp_path, **flags)
    assert app.get_functions() == []
    assert app._durable_app is None


@pytest.mark.parametrize("first,second", [(False, True), (True, False)])
def test_repeated_agent_exposure_is_order_independent(tmp_path, first, second):
    define_agent(tmp_path)
    app = AgentFunctionApp(client_factory=lambda: None, app_root=tmp_path)

    def flow(context, agent):
        yield agent

    for expose in [first, second]:
        app.durable_markdown_agent(
            arg_name="agent", agent_name="orders", expose_http_endpoint=expose,
        )(flow)
    assert len(app._durable_agents) == 1
    assert http_routes(app) == ["agents/orders/run"]


@pytest.mark.parametrize("legacy", ["durable", "workflows"])
def test_ambiguous_legacy_flags_are_not_silently_accepted(tmp_path, legacy):
    with pytest.raises(TypeError, match=legacy):
        AgentFunctionApp(
            client_factory=lambda: None, app_root=tmp_path, **{legacy: True},
        )


@pytest.mark.parametrize("compatibility_context", [False, True])
def test_workflow_proxy_schedules_child_and_decodes_output(compatibility_context):
    from agent_framework_durabletask._workflows.serialization import serialize_value

    context = Mock(spec=OrchestrationContext)
    pending = CompletableTask()
    context.call_sub_orchestrator.return_value = pending
    wrapped = DurableOrchestrationContext(context) if compatibility_context else context
    proxy = DurableWorkflow(wrapped, "Child")
    task = proxy.run({"message": "hello"}, instance_id="child-1")
    context.call_sub_orchestrator.assert_called_once_with(
        "dafx-Child", input={"message": "hello"}, instance_id="child-1",
    )
    assert not task.is_complete
    response = AgentResponse(messages=[Message(role="assistant", contents=["done"])])
    pending.complete([serialize_value(response)])
    output = task.get_result()
    assert isinstance(output[0], AgentResponse)
    assert output[0].text == "done"


def test_child_failure_propagates():
    context = Mock(spec=OrchestrationContext)
    pending = CompletableTask()
    context.call_sub_orchestrator.return_value = pending
    task = DurableWorkflow(context, "Child").run()
    pending.fail("child failed", ValueError("bad input"))
    assert task.is_failed
    with pytest.raises(Exception, match="bad input|failed"):
        task.get_result()


def test_child_input_cannot_impersonate_internal_checkpoint_envelope():
    context = Mock(spec=OrchestrationContext)
    context.call_sub_orchestrator.return_value = CompletableTask()
    payload = {
        "__subworkflow_input__": {"__pickled__": "not-a-pickle"},
        "__subworkflow_address__": {"root_instance_id": "wrong"},
        "message": "hello", "nested": {"__type__": "untrusted"},
    }
    DurableWorkflow(context, "Child").run(payload)
    assert context.call_sub_orchestrator.call_args.kwargs["input"] == {
        "message": "hello", "nested": None,
    }
    assert "__subworkflow_input__" in payload  # Sanitization must not mutate input.


def test_internal_workflow_agent_cannot_shadow_standalone_agent(tmp_path):
    from agent_framework import Agent, AgentExecutor, WorkflowBuilder

    internal = Agent(client=Mock(), name="inner")
    node = AgentExecutor(internal, id="reviewer")
    workflow = WorkflowBuilder(start_executor=node, name="Review").build()
    app = AgentFunctionApp(client_factory=lambda: None, app_root=tmp_path)
    app._register_workflow(workflow, expose_http_endpoint=False)
    app.add_durable_agent(Agent(client=Mock(), name="Review-reviewer"))
    with pytest.raises(ValueError, match="collides"):
        app.get_functions()


@pytest.mark.parametrize("mode", ["matrix", "selection", "transport"])
def test_workflow_registration_probes(mode):
    from importlib.util import find_spec
    if sys.version_info >= (3, 14) or find_spec("agent_framework_declarative") is None:
        pytest.skip("YAML execution probes need the workflows extra and Python 3.13")
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(Path(__file__).with_name(
            "_registration_probe.py")), mode],
        capture_output=True, text=True, encoding="utf-8", timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout.strip().splitlines()[-1])["result"]
