"""SDK-level workflow registration and child-orchestration probes."""
from __future__ import annotations

import base64
from itertools import product
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback

import azure.functions as func
from agent_framework.declarative import WorkflowFactory
from durabletask.internal import orchestrator_service_pb2 as pb
from google.protobuf.wrappers_pb2 import StringValue

from azurefunctions.agents.extensions.agent_framework import AgentFunctionApp
from _yaml_workflow_probe import event, run_workflow

YAML = """name: Child
actions:
  - kind: SendActivity
    id: output
    activity: Hello
"""


def prepare(root):
    (root / "Child.workflow.yaml").write_text(YAML, encoding="utf-8")
    (root / "orders.agent.md").write_text("Handle orders", encoding="utf-8")


def routes(app):
    return [b["route"] for f in app.get_functions()
            for b in f.get_bindings_dict()["bindings"] if b["type"] == "httpTrigger"]


def bind(app, exposed=False, **kwargs):
    @app.orchestration_trigger(context_name="context")
    @app.durable_workflow(
        arg_name="child", workflow_name="Child", expose_http_endpoint=exposed, **kwargs,
    )
    def parent(context, child):
        return (yield child.run({"greeting": "hello"}))
    return parent


def matrix(root):
    prepare(root)
    for discovery, bulk_exposed, binding_exposed in product((False, True), repeat=3):
        app = AgentFunctionApp(
            client_factory=lambda: None, app_root=root,
            discover_workflows=discovery, expose_workflow_endpoints=bulk_exposed,
        )
        original = app._hosted_workflows.get("Child")
        bind(app, binding_exposed)
        assert not app._durable_agents, "Workflow discovery exposed a standalone agent"
        if original:
            assert app._hosted_workflows["Child"] is original
        exposed = (discovery and bulk_exposed) or binding_exposed
        assert len(routes(app)) == (3 if exposed else 0)
        assert len([f for f in app.get_functions()
                    if f.get_function_name() == "dafx-Child"]) == 1

    for agent_outer in (False, True):
        app = AgentFunctionApp(client_factory=lambda: None, app_root=root)

        def parent(context, agent, child):
            yield child.run()
            yield agent.run("hello")

        decorators = [app.durable_workflow(arg_name="child", workflow_name="Child"),
                      app.durable_markdown_agent(arg_name="agent", agent_name="orders")]
        if agent_outer:
            decorators.reverse()
        for decorate in decorators:
            parent = decorate(parent)
        app.orchestration_trigger(context_name="context")(parent)
        assert routes(app) == []
        assert set(app._hosted_workflows) == {"Child"}
        assert set(app._durable_agents) == {"orders"}
    return {"exposure_combinations": 8, "stacked_orders": 2}


def selection(root):
    prepare(root)
    (root / "Broken.workflow.yaml").write_text("not YAML: [", encoding="utf-8")
    app = AgentFunctionApp(client_factory=lambda: None, app_root=root)
    bind(app)
    assert set(app._hosted_workflows) == {"Child"}
    assert routes(app) == []
    try:
        bind(app)
    except RuntimeError as error:
        assert "before function indexing" in str(error)
    else:
        raise AssertionError("Late binding accepted")

    calls = []

    class Factory(WorkflowFactory):
        def create_workflow_from_yaml_path(self, yaml_path):
            calls.append(Path(yaml_path))
            return super().create_workflow_from_yaml_path(yaml_path)

    app = AgentFunctionApp(client_factory=lambda: None, app_root=root,
                           workflow_factory=Factory())
    bind(app, workflow_file="Child.workflow.yaml")
    assert calls == [root / "Child.workflow.yaml"]
    (root / "sales.v2.agent.md").write_text("Non-durable only", encoding="utf-8")
    # Custom workflow loading does not consume or publish unrelated markdown.
    candidate = AgentFunctionApp(
        client_factory=lambda: None, app_root=root, workflow_factory=Factory(),
    )
    bind(candidate)
    assert routes(candidate) == []
    assert not candidate._markdown_agents
    (root / "Broken.workflow.yaml").unlink()
    candidate = AgentFunctionApp(
        client_factory=lambda: None, app_root=root, workflow_factory=Factory(),
        discover_workflows=True, expose_workflow_endpoints=False,
    )
    assert routes(candidate) == []
    assert not candidate._markdown_agents
    (root / "sales.v2.agent.md").unlink()
    for path in ("../outside.workflow.yaml", "Child.txt"):
        candidate = AgentFunctionApp(client_factory=lambda: None, app_root=root)
        try:
            bind(candidate, workflow_file=path)
        except ValueError:
            pass
        else:
            raise AssertionError(path)
    (root / "workflows").mkdir()
    (root / "workflows/Child.workflow.yml").write_text(YAML, encoding="utf-8")
    try:
        bind(AgentFunctionApp(client_factory=lambda: None, app_root=root))
    except ValueError as error:
        assert "Ambiguous" in str(error)
    else:
        raise AssertionError("Duplicate definition accepted")
    return True


def transport(root):
    prepare(root)
    app = AgentFunctionApp(client_factory=lambda: None, app_root=root)
    bind(app)
    handler = next(f.get_user_function() for f in app.get_functions()
                   if f.get_function_name() == "parent")
    start = [
        event(orchestratorStarted=pb.OrchestratorStartedEvent()),
        event(0, executionStarted=pb.ExecutionStartedEvent(
            name="parent", input=StringValue(value="{}"),
            orchestrationInstance=pb.OrchestrationInstance(instanceId="parent-1"),
        )),
    ]
    request = pb.OrchestratorRequest(instanceId="parent-1", newEvents=start)
    encoded = handler(func.OrchestrationContext(
        base64.b64encode(request.SerializeToString()),
    ))
    result = pb.OrchestratorResponse.FromString(base64.b64decode(encoded))
    assert len(result.actions) == 1, result
    action = result.actions[0]
    assert action.HasField("createSubOrchestration"), result
    child = action.createSubOrchestration
    assert child.name == "dafx-Child"
    assert json.loads(child.input.value) == {"greeting": "hello"}
    child_output = run_workflow(root, "Child")[0]
    assert child_output == ["Hello"]
    past = start + [event(action.id, subOrchestrationInstanceCreated=(
        pb.SubOrchestrationInstanceCreatedEvent(
            name=child.name, instanceId=child.instanceId, input=child.input,
        )
    )), event(orchestratorCompleted=pb.OrchestratorCompletedEvent())]
    new = [event(orchestratorStarted=pb.OrchestratorStartedEvent()), event(
        100, subOrchestrationInstanceCompleted=(
            pb.SubOrchestrationInstanceCompletedEvent(
                taskScheduledId=action.id,
                result=StringValue(value=json.dumps(child_output)),
            )
        ),
    )]
    request = pb.OrchestratorRequest(
        instanceId="parent-1", pastEvents=past, newEvents=new,
    )
    encoded = handler(func.OrchestrationContext(
        base64.b64encode(request.SerializeToString()),
    ))
    result = pb.OrchestratorResponse.FromString(base64.b64decode(encoded))
    assert len(result.actions) == 1, result
    done = result.actions[0].completeOrchestration
    assert done.orchestrationStatus == pb.ORCHESTRATION_STATUS_COMPLETED, result
    assert json.loads(done.result.value) == ["Hello"]
    return ["Hello"]


if __name__ == "__main__":
    try:
        with tempfile.TemporaryDirectory() as temp:
            output = {"matrix": matrix, "selection": selection, "transport": transport}[
                sys.argv[1]
            ](Path(temp).resolve())
        print(json.dumps({"result": output}), flush=True)
        code = 0
    except Exception:
        traceback.print_exc()
        code = 1
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(code)
