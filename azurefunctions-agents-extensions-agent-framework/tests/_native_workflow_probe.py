"""Native MAF YAML features through actual cold-rebuilt DAFX replay activities."""

from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback
from unittest.mock import patch

from agent_framework import (
    Agent, ChatResponse, ChatResponseUpdate, Content, Message, ResponseStream,
)
from agent_framework.declarative import (
    AgentFactory, HttpRequestHandler, HttpRequestResult, MCPToolHandler,
    MCPToolResult, WorkflowFactory,
)
from agent_framework.exceptions import AgentInvalidRequestException

import _yaml_workflow_probe as harness


class NativeClient(harness.LocalClient):
    """An in-memory client which does not require an async context manager."""

    instances = []
    calls = []

    def _inner_get_response(self, *, messages, stream, options, **kwargs):
        messages = list(messages)
        call = {
            "instructions": options.get("instructions"),
            "messages": [[str(message.role), message.text] for message in messages],
        }
        self.calls.append(call)
        text = f"{call['instructions']}:{messages[-1].text}"

        async def response():
            return ChatResponse(messages=[Message(role="assistant", contents=[text])])

        async def updates():
            yield ChatResponseUpdate(
                role="assistant", contents=[Content.from_text(text)],
            )

        return (ResponseStream(updates(), finalizer=ChatResponse.from_updates)
                if stream else response())


class RecordingAgentFactory(AgentFactory):
    """Observe public entry points, retaining native parsing and construction."""

    def __init__(self):
        super().__init__(client=NativeClient())
        self.definitions = []
        self.paths = []
        self.created = []

    def create_agent_from_dict(self, agent_def):
        self.definitions.append(deepcopy(agent_def))
        agent = super().create_agent_from_dict(agent_def)
        assert isinstance(agent, Agent)
        self.created.append(agent)
        return agent

    def create_agent_from_yaml_path(self, yaml_path):
        self.paths.append(Path(yaml_path))
        return super().create_agent_from_yaml_path(yaml_path)


class RecordingWorkflowFactory(WorkflowFactory):
    """Record direct path delegation, without replacing YAML parsing/building."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.paths = []

    def create_workflow_from_yaml_path(self, yaml_path):
        self.paths.append(Path(yaml_path))
        return super().create_workflow_from_yaml_path(yaml_path)


class LocalHttpHandler:
    def __init__(self, calls):
        self.calls = calls

    async def send(self, info):
        self.calls.append(asdict(info))
        return HttpRequestResult(
            status_code=201, is_success_status_code=True,
            body='{"order":"42","accepted":true,"items":[1,2]}',
            headers={"x-probe": ["one", "two"], "content-type": ["application/json"]},
        )


class LocalMcpHandler:
    def __init__(self, calls):
        self.calls = calls

    async def invoke_tool(self, invocation):
        self.calls.append(asdict(invocation))
        return MCPToolResult(outputs=[Content.from_text(
            '{"order":"42","approved":true,"tags":["local","mcp"]}',
        )])


INLINE_AGENT = {
    "kind": "Prompt", "name": "writer", "description": "Native inline probe",
    "instructions": "INLINE",
}
FILE_AGENT = {
    "kind": "Prompt", "name": "file_writer", "description": "Native file probe",
    "instructions": "FILE",
}

INLINE = """name: NativeInline
agents:
  writer:
    kind: Prompt
    name: writer
    description: Native inline probe
    instructions: INLINE
actions:
  - kind: InvokeAzureAgent
    id: invoke
    agent: writer
    input: hello
    resultProperty: Local.reply
    output:
      autoSend: false
  - kind: Question
    id: approve
    question: Approve native result?
    variable: Local.approval
  - kind: SendActivity
    id: state
    activity: '{Local}'
"""

FILE = """name: NativeFile
agents:
  writer:
    file: definitions/writer.yaml
actions:
  - kind: InvokeAzureAgent
    id: invoke
    agent: writer
    input: from-file
    resultProperty: Local.reply
    output:
      autoSend: false
  - kind: SendActivity
    id: state
    activity: '{Local}'
"""

DYNAMIC = """name: NativeDynamic
actions:
  - kind: SetValue
    id: select
    path: Local.selected
    value: =Workflow.Inputs.agent
  - kind: InvokeAzureAgent
    id: invoke
    agent: =Local.selected
    input: choose
    resultProperty: Local.reply
    output:
      autoSend: false
  - kind: SetValue
    id: chosen
    path: Local.actual
    value: =Agent.name
  - kind: SendActivity
    id: state
    activity: '{Local}'
"""

FUNCTION = """name: NativeFunction
actions:
  - kind: SetValue
    id: seed
    path: Local.amount
    value: =Workflow.Inputs.amount
  - kind: InvokeFunctionTool
    id: lookup
    functionName: lookup
    arguments:
      order: =Workflow.Inputs.order
      amount: =Local.amount + 1
    output:
      result: Local.result
      autoSend: false
  - kind: SendActivity
    id: state
    activity: '{Local}'
"""

HTTP = """name: NativeHttp
actions:
  - kind: HttpRequestAction
    id: request
    method: post
    url: =Env.HTTP_URL
    headers:
      X-Probe: =Env.PROBE_HEADER
      X-Empty: ''
    queryParameters:
      order: =Workflow.Inputs.order
      enabled: true
      omitted: null
    body:
      kind: json
      content: =Workflow.Inputs
    requestTimeoutInMilliseconds: 1234
    connection:
      name: local-http
    response: Local.response
    responseHeaders:
      path: Local.headers
  - kind: SendActivity
    id: state
    activity: '{Local}'
"""

MCP = """name: NativeMcp
actions:
  - kind: InvokeMcpTool
    id: tool
    serverUrl: =Env.MCP_URL
    serverLabel: local-server
    toolName: =Env.MCP_TOOL
    arguments:
      order: =Workflow.Inputs.order
      count: 2
      enabled: true
    headers:
      X-Probe: =Env.PROBE_HEADER
      X-Empty: ''
    connection:
      name: local-mcp
    output:
      result: Local.result
      autoSend: false
  - kind: SendActivity
    id: state
    activity: '{Local}'
"""

ENV = """name: NativeEnv
actions:
  - kind: SetValue
    id: configured
    path: Local.configured
    value: =Env.NATIVE_PROBE_VALUE
  - kind: SetValue
    id: fallback
    path: Local.fallback
    value: =Env.NATIVE_PROBE_FALLBACK
  - kind: SendActivity
    id: state
    activity: '{Local}'
"""


def run_case(label, definition, name, expected, *, input_data=None,
             agent_definitions=(), agent_paths=(), agents=(), files=None,
             filename="probe.workflow.yaml", configure=None,
             expected_client_calls=(), human_response=None, default_factory=False):
    """Require native construction at app init and one call per replayed effect."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp).resolve()
        harness.write_workflow(root, definition, filename)
        for relative, content in (files or {}).items():
            harness.write_workflow(root, content, relative)
        NativeClient.instances.clear()
        NativeClient.calls.clear()
        harness.LocalClient.instances.clear()
        harness.LocalClient.calls.clear()
        factories = []
        agent_factories = []

        def build(app_root):
            assert Path(app_root) == root
            agent_factory = RecordingAgentFactory()
            agent_factories.append(agent_factory)
            supplied_agents = {
                key: Agent(client=NativeClient(), name=key, instructions=key.upper())
                for key in agents
            }
            factory = RecordingWorkflowFactory(
                agent_factory=agent_factory, agents=supplied_agents,
                **(configure() if configure else {}),
            )
            factories.append(factory)
            if label in {"function-sync", "function-async"}:
                assert factory.register_tool("lookup", lookup) is factory
            return factory

        tool_calls = []

        def sync_lookup(order, amount):
            tool_calls.append({"order": order, "amount": amount})
            return {"order": order, "amount": amount, "source": "registered"}

        async def async_lookup(order, amount):
            return sync_lookup(order, amount)

        lookup = async_lookup if label == "function-async" else sync_lookup

        def check_construction():
            if default_factory:
                assert not factories
                return
            assert factories, "Harness did not call WORKFLOW_FACTORY_BUILDER"
            for factory, agent_factory in zip(factories, agent_factories, strict=True):
                assert factory.paths == [root / filename], factory.paths
                assert agent_factory.definitions == list(agent_definitions), (
                    agent_factory.definitions
                )
                assert agent_factory.paths == [root / p for p in agent_paths], (
                    agent_factory.paths
                )
                assert len(agent_factory.created) == len(agent_definitions)

        with patch.object(harness, "WORKFLOW_FACTORY_BUILDER",
                          None if default_factory else build):
            app = harness.make_app(root)
            check_construction()
            assert app._durable_app is None
            assert set(app._hosted_workflows) == {name}
            app.get_functions()
            check_construction()
            assert not NativeClient.calls and not harness.LocalClient.calls
            output, activities, answered = harness.run_workflow(
                root, name, input_data, human_response,
            )
            check_construction()

        assert len(output) == 1 and isinstance(output[0], str), (label, output)
        state = ast.literal_eval(output[0])
        assert state == expected, (label, state, expected)
        assert len(activities) >= 2, (label, activities)
        assert len(answered) == (1 if human_response is not None else 0), answered
        if not default_factory:
            assert len(factories) > len(activities) + 1, (factories, activities)
            assert NativeClient.calls == list(expected_client_calls), NativeClient.calls
            assert not harness.LocalClient.calls, harness.LocalClient.calls
            assert all(not c.entered and not c.closed for c in NativeClient.instances)
        else:
            assert not NativeClient.calls
            assert harness.LocalClient.calls == [["choose"]], harness.LocalClient.calls
            assert len(harness.LocalClient.instances) == 1
            assert all(c.entered and c.closed for c in harness.LocalClient.instances)
        if label in {"function-sync", "function-async"}:
            assert tool_calls == [{"order": "42", "amount": 42}], tool_calls
        return {
            "output": output, "state": state, "activities": activities,
            "factory_builds": len(factories), "responses": len(answered),
            "agent_calls": deepcopy(NativeClient.calls or harness.LocalClient.calls),
            "function_calls": tool_calls,
        }


def main():
    results = {}
    results["inline-agent"] = run_case(
        "inline-agent", INLINE, "NativeInline",
        {"reply": "INLINE:hello", "approval": "approved"},
        agent_definitions=[INLINE_AGENT], human_response="approved",
        files={"writer.agent.md": "A markdown name must not replace YAML agents."},
        expected_client_calls=[{
            "instructions": "INLINE", "messages": [["user", "hello"]],
        }],
    )
    results["relative-file-agent"] = run_case(
        "relative-file-agent", FILE, "NativeFile", {"reply": "FILE:from-file"},
        filename="workflows/probe.workflow.yaml",
        files={
            "workflows/definitions/writer.yaml": (
                "kind: Prompt\nname: file_writer\ndescription: Native file probe\n"
                "instructions: FILE\n"
            ),
            "definitions/writer.yaml": "not the workflow-relative agent",
        },
        agent_definitions=[FILE_AGENT],
        agent_paths=["workflows/definitions/writer.yaml"],
        expected_client_calls=[{
            "instructions": "FILE", "messages": [["user", "from-file"]],
        }],
    )
    for selected in ("first", "second"):
        for default_factory in (False, True):
            label = f"dynamic-{'default' if default_factory else 'custom'}-{selected}"
            results[label] = run_case(
                label, DYNAMIC, "NativeDynamic",
                {"selected": selected, "actual": selected,
                 "reply": "ok" if default_factory else f"{selected.upper()}:choose"},
                input_data={"agent": selected}, agents=("first", "second"),
                files={"first.agent.md": "First adapter",
                       "agents/second.agent.md": "Second adapter"},
                default_factory=default_factory,
                expected_client_calls=[{
                    "instructions": selected.upper(), "messages": [["user", "choose"]],
                }],
            )
    try:
        run_case(
            "custom-factory-no-markdown-merge", DYNAMIC, "NativeDynamic", {},
            input_data={"agent": "second"}, agents=("first",),
            files={"agents/second.agent.md": "Not supplied to the custom factory"},
        )
    except AgentInvalidRequestException as error:
        missing_agent = "Agent 'second' invocation failed: not found in registry"
        assert missing_agent in str(error), str(error)
        assert not NativeClient.calls and not harness.LocalClient.calls
        results["custom-factory-no-markdown-merge"] = {
            "rejected": "Agent 'second' invocation failed: not found in registry",
        }
    else:
        raise AssertionError("Custom factory unexpectedly received a markdown agent")
    for kind in ("sync", "async"):
        label = f"function-{kind}"
        results[label] = run_case(
            label, FUNCTION, "NativeFunction",
            {"amount": 41, "result": {
                "order": "42", "amount": 42, "source": "registered",
            }},
            input_data={"order": "42", "amount": 41},
        )
    http_calls = []

    def http_config():
        handler = LocalHttpHandler(http_calls)
        assert isinstance(handler, HttpRequestHandler)
        return {"http_request_handler": handler, "configuration": {
            "HTTP_URL": "https://native-probe.invalid/orders", "PROBE_HEADER": "local",
        }}

    results["http-handler"] = run_case(
        "http-handler", HTTP, "NativeHttp",
        {"response": {"order": "42", "accepted": True, "items": [1, 2]},
         "headers": {"x-probe": "one,two", "content-type": "application/json"}},
        input_data={"order": "42"}, configure=http_config,
    )
    assert len(http_calls) == 1, http_calls
    http_call = dict(http_calls[0])
    http_call["body"] = json.loads(http_call["body"])
    assert http_call == {
        "method": "POST", "url": "https://native-probe.invalid/orders",
        "headers": {"X-Probe": "local"},
        "query_parameters": {"order": "42", "enabled": "true"},
        "body": {"order": "42"}, "body_content_type": "application/json",
        "timeout_ms": 1234, "connection_name": "local-http",
    }, http_call
    results["http-handler"]["handler_calls"] = http_calls
    mcp_calls = []

    def mcp_config():
        handler = LocalMcpHandler(mcp_calls)
        assert isinstance(handler, MCPToolHandler)
        return {"mcp_tool_handler": handler, "configuration": {
            "MCP_URL": "https://native-probe.invalid/mcp", "MCP_TOOL": "lookup",
            "PROBE_HEADER": "local",
        }}

    results["mcp-handler"] = run_case(
        "mcp-handler", MCP, "NativeMcp",
        {"result": [{"order": "42", "approved": True, "tags": ["local", "mcp"]}]},
        input_data={"order": "42"}, configure=mcp_config,
    )
    assert mcp_calls == [{
        "server_url": "https://native-probe.invalid/mcp", "tool_name": "lookup",
        "server_label": "local-server",
        "arguments": {"order": "42", "count": 2, "enabled": True},
        "headers": {"X-Probe": "local"}, "connection_name": "local-mcp",
    }], mcp_calls
    results["mcp-handler"]["handler_calls"] = mcp_calls
    with patch.dict(os.environ, {
        "NATIVE_PROBE_VALUE": "ambient-wrong",
        "NATIVE_PROBE_FALLBACK": "ambient-fallback",
    }):
        for restricted in (True, False):
            label = f"env-{'restricted' if restricted else 'fallback'}"
            results[label] = run_case(
                label, ENV, "NativeEnv",
                {"configured": "configured",
                 "fallback": None if restricted else "ambient-fallback"},
                configure=lambda: {
                    "configuration": {"NATIVE_PROBE_VALUE": "configured"},
                    "restrict_env_to_configuration": restricted,
                },
            )
    return results


if __name__ == "__main__":
    try:
        print(json.dumps({"result": main()}), flush=True)
        exit_code = 0
    except Exception:
        traceback.print_exc()
        exit_code = 1
    sys.stdout.flush()
    sys.stderr.flush()
    # Do not let PowerFx/CLR teardown enter the parent pytest reporting process.
    os._exit(exit_code)
