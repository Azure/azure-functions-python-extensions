from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

_PACKAGE_ROOT = Path(__file__).parents[1]
_SAMPLES_ROOT = _PACKAGE_ROOT / "samples"
_SAMPLE_INDEXES = {
    "agent_samples_agent-framework": {"process_order", "process_order_event"},
    "agent_samples_agent-framework_durable": {
        "order_orchestrator", "prepare_order_activity", "start_order_orchestration",
        "dafx-order-fulfillment", "http-order_fulfillment",
        "BuiltIn__HttpActivity", "BuiltIn__HttpPollOrchestrator",
    },
    "lazy-owned-dafx": {
        "dafx-orders", "http-orders",
        "BuiltIn__HttpActivity", "BuiltIn__HttpPollOrchestrator",
    },
    "durable-markdown-binding": {
        "orders", "start_orders", "dafx-orders", "http-orders",
        "BuiltIn__HttpActivity", "BuiltIn__HttpPollOrchestrator",
    },
    "durable-yaml-workflow": {
        "BuiltIn__HttpActivity", "BuiltIn__HttpPollOrchestrator",
        "dafx-writer", "http-writer",
        "dafx-OrderReview", "dafx-OrderReview-start", "dafx-OrderReview-status",
        "dafx-OrderReview-respond", "dafx-OrderReview-_workflow_entry",
        "dafx-OrderReview-capture_order", "dafx-OrderReview-prepare_prompt",
        "dafx-OrderReview-review_order", "dafx-OrderReview-send_review",
        "dafx-Approval", "dafx-Approval-start", "dafx-Approval-status",
        "dafx-Approval-respond", "dafx-Approval-_workflow_entry",
        "dafx-Approval-request_approval", "dafx-Approval-send_answer",
    },
}
_LOCAL_SAMPLES = ("lazy-owned-dafx", "durable-markdown-binding")


def _run_sample(sample_path, script):
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, [
            str(_PACKAGE_ROOT),
            str(_PACKAGE_ROOT.parent / "azurefunctions-agents-extensions-base"),
            environment.get("PYTHONPATH"),
        ])
    )
    completed = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", textwrap.dedent(script)],
        cwd=_SAMPLES_ROOT / sample_path,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    # PowerFx's loader may print initialization notices before the JSON result.
    return json.loads(completed.stdout.strip().splitlines()[-1])


def test_index_cases_cover_every_sample_app():
    assert set(_SAMPLE_INDEXES) == {
        path.parent.relative_to(_SAMPLES_ROOT).as_posix()
        for path in _SAMPLES_ROOT.rglob("function_app.py")
    }


@pytest.mark.parametrize("sample_path", _SAMPLE_INDEXES)
def test_sample_indexes_all_functions(sample_path):
    if sample_path == "durable-yaml-workflow":
        from importlib.util import find_spec
        if (
            sys.version_info >= (3, 14)
            or find_spec("agent_framework_declarative") is None
        ):
            pytest.skip("YAML sample requires Python 3.13 and the workflows extra")
    # Exact names were recorded from the SDK 2/DAFX PR #72 index. DAFX sanitizes
    # HTTP names (_build_function_name), but preserves hyphens in entity names.
    result = _run_sample(sample_path, """
        import json
        from unittest.mock import patch
        from azurefunctions.agents.extensions.agent_framework.provider import (
            AgentFrameworkBinding,
        )
        with patch.object(AgentFrameworkBinding, '_create_agent',
                          side_effect=AssertionError('live agent during indexing')):
            import function_app
            first = function_app.app.get_functions()
            second = function_app.app.get_functions()
        names = [fn.get_function_name() for fn in first]
        assert names == [fn.get_function_name() for fn in second]
        assert len(names) == len(set(names))
        for fn in first:
            if fn.get_function_name().startswith('http-'):
                trigger = next(b for b in fn.get_bindings_dict()['bindings']
                               if b['type'] == 'httpTrigger')
                agent = next(iter(function_app.app._durable_app.agents))
                assert trigger['route'] == f'agents/{agent}/run'
                assert [method.value for method in trigger['methods']] == ['POST']
                assert trigger['authLevel'].value == 'function'
        print(json.dumps(names))
    """)
    assert set(result) == _SAMPLE_INDEXES[sample_path]


def test_agent_framework_sample_rejects_malformed_json():
    result = _run_sample("agent_samples_agent-framework", """
        import asyncio, json
        import azure.functions as func
        import function_app
        request = func.HttpRequest(method='POST', url='https://example.test',
                                  body=b'{not json', route_params={'orderId': '42'})
        handler = function_app.process_order._function.get_user_function().__wrapped__
        response = asyncio.run(handler(request, object()))
        print(json.dumps({'status_code': response.status_code,
                          'body': response.get_body().decode()}))
    """)
    assert result["status_code"] == 400
    assert json.loads(result["body"]) == {"error": "Order failed validation."}


def test_agent_framework_durable_sample_starts_orchestration():
    script = (
        "import asyncio, json\n"
        "import azure.functions as func\n"
        "import function_app\n"
        "class FakeClient:\n"
        "    async def start_new(self, name, *, client_input):\n"
        "        assert name == 'order_orchestrator' and client_input == {}\n"
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
    assert _run_sample("agent_samples_agent-framework_durable", script) == {
        "status_code": 202,
        "mimetype": "application/json",
        "location": "https://example.test/status/42",
    }


def test_agent_framework_durable_sample_rejects_malformed_json():
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
    result = _run_sample("agent_samples_agent-framework_durable", script)
    assert result["status_code"] == 400
    assert json.loads(result["body"]) == {"error": "Order failed validation."}


def test_agent_framework_sample_assets_follow_discovery_conventions():
    sample_root = _SAMPLES_ROOT / "agent_samples_agent-framework"

    assert (sample_root / "order-fulfillment.agent.md").is_file()
    assert (sample_root / "skills" / "order-policy" / "SKILL.md").is_file()
    assert (sample_root / "mcp.json").is_file()


def test_binding_sample_starts_orchestration():
    result = _run_sample("durable-markdown-binding", """
        import asyncio, json
        import azure.functions as func
        import function_app
        class FakeClient:
            async def start_new(self, name, *, client_input):
                assert name == 'orders' and client_input == {}
                return 'instance-42'
            def create_check_status_response(self, request, instance_id):
                assert request is not None and instance_id == 'instance-42'
                return func.HttpResponse(status_code=202)
        request = func.HttpRequest(method='POST', url='https://example.test', body=b'')
        handler = function_app.start_orders._function.get_user_function().__wrapped__
        response = asyncio.run(handler(request, FakeClient()))
        print(json.dumps(response.status_code))
    """)
    assert result == 202


@pytest.mark.parametrize("sample_path", _LOCAL_SAMPLES)
def test_local_sample_preserves_history_with_fresh_execution_clients(sample_path):
    result = _run_sample(sample_path, """
        import asyncio, base64, json, uuid
        from unittest.mock import Mock
        import azure.functions as func
        from azure.durable_functions import DurableOrchestrationContext
        from durabletask.internal import orchestrator_service_pb2 as pb
        from durabletask.task import CompletableTask
        from google.protobuf.wrappers_pb2 import StringValue
        import local_chat_client

        clients = []
        class TrackingClient(local_chat_client.LocalChatClient):
            def __init__(self):
                super().__init__()
                self.entered = self.closed = False
                clients.append(self)
            async def __aenter__(self):
                self.entered = True
                return self
            async def __aexit__(self, *args):
                self.closed = True
        local_chat_client.LocalChatClient = TrackingClient
        import function_app
        assert clients == [], 'client constructed during app import'
        functions = function_app.app.get_functions()
        assert clients == [], 'client constructed during indexing'
        entity = next(fn.get_user_function() for fn in functions
                      if fn.get_function_name() == 'dafx-orders')
        scheduled = []
        def call_entity(entity_id, operation, input_=None):
            assert operation == 'run'
            task = CompletableTask()
            scheduled.append((entity_id, input_, task))
            return task
        scheduler = Mock(instance_id='workflow-1')
        scheduler.new_uuid.side_effect = [str(uuid.UUID(int=n)) for n in range(1, 5)]
        scheduler.call_entity.side_effect = call_entity
        context = DurableOrchestrationContext(scheduler)

        generator = None
        if hasattr(function_app, 'orders'):
            # Keep the actual binding injection; bypass only the SDK host transport.
            handler = function_app.orders._function.get_user_function()
            generator = handler.orchestrator_function(context)
            task = next(generator)
        else:
            http = next(fn.get_user_function().__wrapped__ for fn in functions
                        if fn.get_function_name() == 'http-orders')
            class Client:
                async def signal_entity(self, entity_id, operation, input_):
                    call_entity(entity_id, operation, input_)
            def submit(prompt):
                request = func.HttpRequest(
                    method='POST', url='https://example.test/api/agents/orders/run',
                    headers={'Content-Type': 'application/json'},
                    body=json.dumps({'message': prompt, 'session_id': 'orders-demo',
                                     'wait_for_response': False}).encode())
                response = asyncio.run(http(request, Client()))
                assert response.status_code == 202, response.get_body()
                return scheduled[-1][2]
            task = submit('Assess the order.')

        state = None
        replies = []
        for turn in (1, 2):
            assert not task.is_complete
            entity_id, request, pending = scheduled[-1]
            batch = pb.EntityBatchRequest(
                instanceId=str(entity_id), operations=[pb.OperationRequest(
                    operation='run', input=StringValue(value=json.dumps(request)))])
            if state is not None:
                batch.entityState.CopyFrom(StringValue(value=state))
            transport = func.EntityContext(base64.b64encode(batch.SerializeToString()))
            result = pb.EntityBatchResult.FromString(
                base64.b64decode(entity(transport)))
            assert not result.HasField('failureDetails'), result
            assert len(result.results) == 1
            assert result.results[0].HasField('success'), result
            payload = json.loads(result.results[0].success.result.value)
            state = result.entityState.value
            pending.complete(payload)
            assert len(clients) == turn
            assert all(client.entered and client.closed for client in clients)
            if generator is not None:
                response = task.get_result()
                replies.append(response.text)
                if turn == 1:
                    task = generator.send(response)
                else:
                    try:
                        generator.send(response)
                    except StopIteration as done:
                        assert done.value == dict(zip(['assessment', 'plan'], replies))
                    else:
                        raise AssertionError('orchestrator did not finish')
            else:
                from agent_framework import AgentResponse
                replies.append(AgentResponse.from_dict(payload).text)
                if turn == 1:
                    task = submit('Make a fulfillment plan.')
        assert scheduled[0][0] == scheduled[1][0], 'turns used different entities'
        assert state
        print(json.dumps(replies))
    """)
    assert result == [
        "User turn 1: Assess the order.",
        "User turn 2: Make a fulfillment plan.",
    ]


@pytest.mark.parametrize("sample_path", _LOCAL_SAMPLES)
@pytest.mark.parametrize("body", ["{not json", "{}", '{"message":""}'])
def test_local_agent_endpoint_rejects_invalid_input(sample_path, body):
    result = _run_sample(sample_path, f"""
        import asyncio, json
        from unittest.mock import Mock
        import azure.functions as func
        import function_app
        handler = next(fn.get_user_function().__wrapped__
                       for fn in function_app.app.get_functions()
                       if fn.get_function_name() == 'http-orders')
        client = Mock()
        request = func.HttpRequest(method='POST', url='https://example.test',
                                  headers={{'Content-Type': 'application/json'}},
                                  body={body.encode()!r})
        response = asyncio.run(handler(request, client))
        client.signal_entity.assert_not_called()
        print(json.dumps(response.status_code))
    """)
    assert result == 400


def test_agent_framework_durable_sample_uses_prepared_order_and_shared_session():
    result = _run_sample("agent_samples_agent-framework_durable", """
        import json
        from types import SimpleNamespace
        import function_app
        calls = []
        session = object()
        class Agent:
            def create_session(self):
                return session
            def run(self, message, *, session):
                calls.append((json.loads(message), session))
                return f'turn-{len(calls)}'
        class Context:
            def get_input(self):
                return {'untrusted': 'order'}
            def call_activity(self, name, payload):
                assert name == 'prepare_order_activity'
                assert payload == self.get_input()
                return 'prepare'
        context = Context()
        def get_agent(received_context, name):
            assert received_context is context and name == 'order-fulfillment'
            return Agent()
        function_app.app.get_agent = get_agent
        handler = function_app.order_orchestrator._function.get_user_function()
        generator = handler.orchestrator_function(context)
        assert next(generator) == 'prepare'
        assert not calls
        prepared = {'order_id': 'D-2048', 'summary': {'subtotal': '49.90'}}
        assert generator.send(prepared) == 'turn-1'
        assert generator.send(SimpleNamespace(text='assessment')) == 'turn-2'
        try:
            generator.send(SimpleNamespace(text='plan'))
        except StopIteration as done:
            output = done.value
        else:
            raise AssertionError('orchestrator did not finish')
        assert len(calls) == 2
        assert all(payload['order'] == prepared and used_session is session
                   for payload, used_session in calls)
        assert calls[1][0]['risk_assessment'] == 'assessment'
        print(json.dumps(output))
    """)
    assert result == {
        "order_id": "D-2048",
        "risk_assessment": "assessment",
        "fulfillment_plan": "plan",
    }
