"""Real YAML/DAFX probes isolated from pytest's embedded-CLR reporting hooks."""
from __future__ import annotations

import base64
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback

import azure.functions as func
from agent_framework import (
    BaseChatClient, ChatResponse, ChatResponseUpdate, Content, Message, ResponseStream,
)
from agent_framework_durabletask import deserialize_workflow_output
from durabletask.internal import orchestrator_service_pb2 as pb
from google.protobuf.timestamp_pb2 import Timestamp
from google.protobuf.wrappers_pb2 import StringValue

from azurefunctions.agents.extensions.agent_framework import AgentFunctionApp


class LocalClient(BaseChatClient):
    instances = []
    calls = []

    def __init__(self):
        super().__init__()
        self.entered = self.closed = False
        self.instances.append(self)

    async def __aenter__(self):
        self.entered = True
        return self

    async def __aexit__(self, *args):
        self.closed = True

    def _inner_get_response(self, *, messages, stream, options, **kwargs):
        self.calls.append([m.text for m in messages])

        async def updates():
            assert self.entered and not self.closed
            yield ChatResponseUpdate(
                role="assistant", contents=[Content.from_text("ok")],
            )

        async def response():
            return ChatResponse(messages=[Message(role="assistant", contents=["ok"])])

        return (ResponseStream(updates(), finalizer=ChatResponse.from_updates)
                if stream else response())


def write_workflow(root, content, filename="probe.workflow.yaml"):
    path = root / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_app(root):
    before = len(LocalClient.instances)
    app = AgentFunctionApp(
        client_factory=LocalClient, app_root=root, durable=True, workflows=True,
    )
    assert len(LocalClient.instances) == before, "Live client created during loading"
    return app


def index(root):
    app = make_app(root)
    before = len(LocalClient.instances)
    functions = {fn.get_function_name(): fn for fn in app.get_functions()}
    assert len(LocalClient.instances) == before, "Live client created during indexing"
    return app, functions


def event(event_id=-1, **kwargs):
    return pb.HistoryEvent(
        eventId=event_id, timestamp=Timestamp(seconds=1_700_000_000), **kwargs,
    )


def run_workflow(root, name, input_data=None, human_response=None):
    """Rebuild the outer app on every activation and activity, replay SDK history."""
    history = []
    new_events = [
        event(orchestratorStarted=pb.OrchestratorStartedEvent()),
        event(0, executionStarted=pb.ExecutionStartedEvent(
            name=f"dafx-{name}", input=StringValue(value=json.dumps(input_data or {})),
            orchestrationInstance=pb.OrchestrationInstance(
                instanceId="yaml-probe", executionId=StringValue(value="execution-1")),
        )),
    ]
    activity_names = []
    answered = []
    for _ in range(60):
        _, functions = index(root)
        request = pb.OrchestratorRequest(
            instanceId="yaml-probe", pastEvents=history, newEvents=new_events,
        )
        encoded = functions[f"dafx-{name}"].get_user_function()(
            func.OrchestrationContext(base64.b64encode(request.SerializeToString()))
        )
        result = pb.OrchestratorResponse.FromString(base64.b64decode(encoded))
        status = (
            json.loads(result.customStatus.value) if result.customStatus.value else {}
        )
        history.extend(new_events)
        upcoming = [event(orchestratorStarted=pb.OrchestratorStartedEvent())]
        for action in result.actions:
            if action.HasField("completeOrchestration"):
                done = action.completeOrchestration
                assert done.orchestrationStatus == pb.ORCHESTRATION_STATUS_COMPLETED, (
                    done
                )
                return (deserialize_workflow_output(json.loads(done.result.value)),
                        activity_names, answered)
            assert action.HasField("scheduleTask"), action
            scheduled = action.scheduleTask
            history.append(event(action.id, taskScheduled=pb.TaskScheduledEvent(
                name=scheduled.name, input=scheduled.input,
            )))
            _, cold_functions = index(root)
            handler = cold_functions[scheduled.name].get_user_function()
            output = handler(json.loads(scheduled.input.value))
            activity_names.append(scheduled.name)
            upcoming.append(event(1000 + len(activity_names),
                                  taskCompleted=pb.TaskCompletedEvent(
                taskScheduledId=action.id, result=StringValue(value=json.dumps(output)),
            )))
        history.append(event(orchestratorCompleted=pb.OrchestratorCompletedEvent()))
        if len(upcoming) == 1:
            pending = status.get("pending_requests", {})
            assert len(pending) == 1 and human_response is not None, status
            request_id = next(iter(pending))
            assert request_id not in answered
            answered.append(request_id)
            upcoming.append(event(2000 + len(answered), eventRaised=pb.EventRaisedEvent(
                name=request_id,
                input=StringValue(value=json.dumps({"user_input": human_response})),
            )))
        new_events = upcoming
    raise AssertionError("Workflow exceeded activation limit")


CASES = {
    "simple": ("""name: Simple
actions:
  - kind: SendActivity
    id: greet
    activity: Hello
""", "Simple", {}, ["Hello"]),
    "state": ("""name: State
actions:
  - kind: SetValue
    id: set
    path: Local.count
    value: 41
  - kind: SetValue
    id: increment
    path: Local.count
    value: =Local.count + 1
  - kind: SendActivity
    id: output
    activity: =Text(Local.count)
""", "State", {}, ["42"]),
    "branch": ("""name: Branch
actions:
  - kind: ConditionGroup
    id: choose
    conditions:
      - condition: =Workflow.Inputs.color = "red"
        actions:
          - kind: SendActivity
            id: red
            activity: RED
    elseActions:
      - kind: SendActivity
        id: other
        activity: OTHER
""", "Branch", {"color": "red"}, ["RED"]),
    "loop": ("""name: Loop
actions:
  - kind: Foreach
    id: loop
    source: [apple, banana, cherry]
    itemName: fruit
    actions:
      - kind: SendActivity
        id: item
        activity: =Local.fruit
""", "Loop", {}, ["apple", "banana", "cherry"]),
    "agent": ("""name: Agent
actions:
  - kind: InvokeAzureAgent
    id: writer
    agent: writer
    input: hello
    resultProperty: Local.reply
    output:
      autoSend: false
  - kind: SendActivity
    id: output
    activity: =Local.reply
""", "Agent", {}, ["ok"]),
    "human": ("""name: Human
actions:
  - kind: Question
    id: ask
    question: Approve?
    variable: Local.answer
  - kind: SendActivity
    id: output
    activity: =Local.answer
""", "Human", {}, ["approved"]),
}
CASES["else"] = (CASES["branch"][0], "Branch", {"color": "blue"}, ["OTHER"])
CASES["if-agent"] = (json.dumps({
    "name": "IfAgent",
    "actions": [
        {
            "kind": "If", "id": "choose", "condition": True,
            "then": [{
                "kind": "InvokeAzureAgent", "id": "writer", "agent": "writer",
                "input": "hello", "resultProperty": "Local.reply",
                "output": {"autoSend": False},
            }],
            "else": [{
                "kind": "SetValue", "id": "fallback", "path": "Local.reply",
                "value": "wrong",
            }],
        },
        {"kind": "SendActivity", "id": "output", "activity": "=Local.reply"},
    ],
}), "IfAgent", {}, ["ok"])
else_definition = json.loads(CASES["if-agent"][0])
branch = else_definition["actions"][0]
branch["condition"] = False
branch["then"], branch["else"] = branch["else"], branch["then"]
CASES["if-else-agent"] = (json.dumps(else_definition), "IfAgent", {}, ["ok"])


def execution_checks():
    results = {}
    for label, (yaml, name, data, expected) in CASES.items():
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_workflow(root, yaml)
            if label in {"agent", "if-agent", "if-else-agent"}:
                (root / "writer.agent.md").write_text("Be helpful", encoding="utf-8")
            LocalClient.instances.clear()
            LocalClient.calls.clear()
            output, activities, answered = run_workflow(root, name, data, "approved")
            assert output == expected, (label, output)
            if label in {"agent", "if-agent", "if-else-agent"}:
                assert len(LocalClient.calls) == 1, LocalClient.calls
                assert len(LocalClient.instances) == 1
                assert all(c.entered and c.closed for c in LocalClient.instances)
            if label == "human":
                assert len(answered) == 1
            results[label] = {"output": output, "activities": activities}
    return results


def validation_checks():
    checks = []

    def invalid(label, files, expected):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for filename, content in files.items():
                write_workflow(root, content, filename)
            try:
                make_app(root)
            except Exception as error:
                assert expected.lower() in str(error).lower(), (label, str(error))
            else:
                raise AssertionError(f"Accepted invalid definition: {label}")
            checks.append(label)

    for label, content, error in [
        ("scalar", "hello", "mapping"),
        ("malformed", "[", "parsing"),
        ("unnamed", "actions: []", "explicit name"),
        ("bad-name", "name: ../bad\nactions: []", "explicit name"),
        ("duplicate-key", "name: First\nname: Second", "Duplicate YAML key"),
        ("cyclic-alias", "name: Cycle\nactions: &a [*a]", "Cyclic"),
        ("inline-agent", "name: Inline\nagents: {writer: {kind: Prompt}}",
         "inline/file"),
        ("file-agent", "name: File\nagents: {writer: {file: ../escape.yaml}}",
         "inline/file"),
        ("unknown-action", "name: Unknown\nactions: [{kind: Imaginary}]", "Unknown"),
        ("missing-agent", CASES["agent"][0], "was not found"),
        ("dynamic-agent", CASES["agent"][0].replace(
            "agent: writer", "agent: =Local.name"),
         "static markdown"),
    ]:
        invalid(label, {"probe.workflow.yaml": content}, error)
    invalid("duplicate-name", {
        "one.workflow.yaml": CASES["simple"][0],
        "workflows/two.workflow.yml": CASES["simple"][0].replace("Simple", "simple"),
    }, "Duplicate workflow name")
    invalid("shadowed-root-actions", {
        "probe.workflow.yaml": CASES["simple"][0] + "trigger: {actions: []}",
    }, "both")
    invalid("ignored-if-elseActions", {
        "probe.workflow.yaml": CASES["if-agent"][0].replace(
            '"else":', '"elseActions":'),
    }, "elseActions")
    invalid("unregistered-function-tool", {
        "probe.workflow.yaml": "name: Tool\nactions:\n"
        "  - {kind: InvokeFunctionTool, id: tool, functionName: lookup}\n"
        "  - {kind: SendActivity, id: done, activity: DONE}\n",
    }, "handler")

    invalid("unknown-nested-action", {
        "probe.workflow.yaml": CASES["if-agent"][0].replace(
            '"kind": "InvokeAzureAgent"', '"kind": "Imaginary"'),
    }, "Unknown workflow action")
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        definition = json.loads(CASES["if-agent"][0])
        definition["trigger"] = {"actions": definition.pop("actions")}
        write_workflow(root, json.dumps(definition))
        (root / "writer.agent.md").write_text("Be helpful", encoding="utf-8")
        assert run_workflow(root, "IfAgent")[0] == ["ok"]
        checks.append("trigger-nested-agent")
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        write_workflow(root, json.dumps({"name": "Literal", "actions": [
            {"kind": "SetValue", "id": "set", "path": "Local.data",
             "value": {"actions": [{"kind": "NotAnAction"}]}},
            {"kind": "SendActivity", "id": "out", "activity": "done"},
        ]}))
        make_app(root)
        checks.append("literal-data-not-actions")

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        write_workflow(root, CASES["simple"][0], "first.workflow.yml")
        write_workflow(root, CASES["state"][0], "workflows/second.workflow.yaml")
        write_workflow(root, "not YAML", "ignored.yaml")
        write_workflow(root, "not YAML", "nested/ignored.workflow.yaml")
        app, functions = index(root)
        assert set(app._durable_app.workflows) == {"Simple", "State"}
        assert len(app._durable_app.agents) == 0
        assert [f.get_function_name() for f in app.get_functions()] == list(functions)
        checks.append("both-suffixes-and-directories-only")
        for workflow_name in ["Simple", "State"]:
            assert f"dafx-{workflow_name}" in functions
            routes = [
                b["route"] for f in functions.values()
                for b in f.get_bindings_dict()["bindings"] if b["type"] == "httpTrigger"
            ]
            assert f"workflow/{workflow_name}/run" in routes
            assert f"workflow/{workflow_name}/status/{{instanceId}}" in routes
            respond_route = (
                f"workflow/{workflow_name}/respond/{{instanceId}}/{{requestId}}"
            )
            assert respond_route in routes
        checks.append("workflow-routes")

    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / "invalid.workflow.yaml").mkdir()
        try:
            make_app(root)
        except ValueError as error:
            assert "not a file" in str(error)
        else:
            raise AssertionError("Accepted directory")
        checks.append("directory-rejected")

    return checks


def main():
    global LocalClient
    mode = sys.argv[1]
    if mode == "execution":
        return execution_checks()
    if mode == "validation":
        return validation_checks()
    if mode == "sample":
        root = Path(__file__).parents[1] / "samples" / "durable-yaml-workflow"
        spec = importlib.util.spec_from_file_location(
            "yaml_sample_client", root / "local_chat_client.py",
        )
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        class SampleClient(module.LocalChatClient):
            instances = []

            def __init__(self):
                super().__init__()
                self.instances.append(self)

        LocalClient = SampleClient
        return {
            name: run_workflow(root, name, {"order": "42"}, "approved")[0]
            for name in ["OrderReview", "Approval"]
        }
    if mode == "review":
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_workflow(root, CASES["if-agent"][0])
            (root / "writer.agent.md").write_text("Be helpful", encoding="utf-8")
            output = run_workflow(root, "IfAgent")[0]
            assert output == ["ok"], output
            return output
    if mode == "mutation":
        from azurefunctions.agents.extensions.agent_framework import _workflows
        _workflows.load_workflows = lambda *args: []
        return execution_checks()
    raise ValueError(mode)


if __name__ == "__main__":
    try:
        print(json.dumps({"result": main()}), flush=True)
        exit_code = 0
    except Exception:
        traceback.print_exc()
        exit_code = 1
    sys.stdout.flush()
    sys.stderr.flush()
    # The tests are complete; isolate PowerFx/CLR shutdown from the pytest host.
    os._exit(exit_code)
