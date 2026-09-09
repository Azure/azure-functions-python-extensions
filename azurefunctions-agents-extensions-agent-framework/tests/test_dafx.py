from __future__ import annotations

import base64
import json
import uuid
from types import SimpleNamespace
from unittest.mock import Mock

import azure.functions as func
import pytest
from agent_framework import Agent, AgentResponse, BaseChatClient, ChatResponse, Message
from azure.durable_functions import DurableOrchestrationContext
from durabletask.internal import orchestrator_service_pb2 as pb
from durabletask.task import CompletableTask
from google.protobuf.wrappers_pb2 import StringValue

from azurefunctions.agents.extensions.agent_framework import AgentFunctionApp
from azurefunctions.agents.extensions.base.durable import DurableAgentContext


class RecordingClient(BaseChatClient):
    """A local model substitute. DAFX and the Functions SDK are not mocked."""

    def __init__(self):
        super().__init__()
        self.inputs = []

    def _inner_get_response(self, *, messages, stream, options, **kwargs):
        if stream:
            raise TypeError("streaming is not supported by this test client")

        async def respond():
            self.inputs.append([message.text for message in messages])
            return ChatResponse(messages=[Message(
                role="assistant", contents=[f"reply-{len(self.inputs)}"]
            )])

        return respond()


@pytest.fixture
def app(tmp_path):
    return AgentFunctionApp(client_factory=RecordingClient, app_root=tmp_path)


def make_agent(name="Orders", client=None):
    return Agent(client=client or RecordingClient(), name=name)


def test_initialization_does_not_construct_dafx(app):
    assert app._durable_app is None
    assert app.get_functions() == []
    assert app._durable_app is None


def test_registration_owns_one_real_dafx_app(app):
    from agent_framework_azurefunctions import AgentFunctionApp as DafxApp

    first = make_agent()
    app.add_durable_agent(first)
    inner = app._durable_app
    assert isinstance(inner, DafxApp)
    app.add_durable_agent(first)
    app.add_durable_agent(make_agent("Shipping"))

    assert app._durable_app is inner
    assert set(inner.agents) == {"Orders", "Shipping"}
    assert not inner.enable_health_check
    assert not inner.enable_http_endpoints
    assert not inner.enable_mcp_tool_trigger
    assert inner.auth_level == app.auth_level
    functions = app.get_functions()
    entities = {
        function.get_function_name()
        for function in functions
        if function.get_bindings_dict()["bindings"][0]["type"] == "entityTrigger"
    }
    assert entities == {"dafx-Orders", "dafx-Shipping"}
    assert not any(function.is_http_function() for function in functions)


@pytest.mark.parametrize("name", [None, "", " ", 42])
def test_invalid_name_does_not_enable_dafx(app, name):
    with pytest.raises(ValueError, match="non-empty string name"):
        app.add_durable_agent(SimpleNamespace(name=name))
    assert app._durable_app is None


@pytest.mark.parametrize("name", ["Orders", "orders", "ORDERS"])
def test_different_agent_with_duplicate_name_is_rejected(app, name):
    app.add_durable_agent(make_agent())
    with pytest.raises(ValueError, match="already registered"):
        app.add_durable_agent(make_agent(name))
    assert len(app._durable_app.agents) == 1


def test_lookup_does_not_enable_dafx(app):
    with pytest.raises(RuntimeError, match="add_durable_agent"):
        app.get_agent(object(), "Orders")
    assert app._durable_app is None


def test_unknown_agent_uses_dafx_validation(app):
    app.add_durable_agent(make_agent())
    with pytest.raises(ValueError, match="not registered"):
        app.get_agent(object(), "Unknown")


def test_distinct_apps_do_not_share_durable_registries(app, tmp_path):
    other = AgentFunctionApp(client_factory=RecordingClient, app_root=tmp_path)
    app.add_durable_agent(make_agent("First"))
    assert other._durable_app is None
    other.add_durable_agent(make_agent("Second"))
    assert app._durable_app is not other._durable_app
    assert set(app._durable_app.agents) == {"First"}
    assert set(other._durable_app.agents) == {"Second"}


def test_indexing_recovers_after_collision_is_removed(app):
    @app.function_name(name="dafx-Orders")
    @app.route(route="collision")
    def collision(req):
        return func.HttpResponse("ok")

    app.add_durable_agent(make_agent())
    with pytest.raises(ValueError, match="Duplicate function name"):
        app.get_functions()
    # Test-only removal simulates correcting the conflicting declaration.
    app._function_builders.remove(collision)
    names = [fn.get_function_name() for fn in app.get_functions()]
    assert names.count("dafx-Orders") == 1
    assert app._functions_indexed


def test_duplicate_outer_names_are_still_validated_on_each_index(app):
    for route in ["first", "second"]:
        @app.route(route=route)
        def duplicate(req):
            return func.HttpResponse("ok")

    for _ in range(2):
        with pytest.raises(ValueError, match="unique function name"):
            app.get_functions()


@pytest.mark.parametrize("enable_dafx", [False, True])
def test_registration_after_indexing_is_rejected(app, enable_dafx):
    if enable_dafx:
        app.add_durable_agent(make_agent())
    app.get_functions()
    with pytest.raises(RuntimeError, match="before function indexing"):
        app.add_durable_agent(make_agent("Late"))


@pytest.mark.parametrize("auth", [func.AuthLevel.ANONYMOUS, func.AuthLevel.FUNCTION])
def test_combined_index_preserves_http_auth_and_is_repeatable(tmp_path, auth):
    app = AgentFunctionApp(
        client_factory=RecordingClient, app_root=tmp_path, http_auth_level=auth
    )

    @app.route(route="orders")
    def orders(req):
        return func.HttpResponse("ok")

    app.add_durable_agent(make_agent())
    first = app.get_functions()
    second = app.get_functions()
    assert [fn.get_function_name() for fn in first] == [
        fn.get_function_name() for fn in second
    ]
    assert len(first) == 4  # HTTP + entity + the SDK's two built-in functions.
    http = next(fn for fn in first if fn.get_function_name() == "orders")
    trigger = next(
        binding for binding in http.get_bindings_dict()["bindings"]
        if binding["type"] == "httpTrigger"
    )
    assert trigger["authLevel"] == auth
    assert http.get_user_function()(None).get_body() == b"ok"
    assert app._durable_app.auth_level == auth


@pytest.mark.parametrize("name", ["dafx-Orders", "DAFX-ORDERS"])
def test_cross_registry_collision_is_rejected_on_every_index(app, name):
    @app.function_name(name=name)
    @app.route(route="collision")
    def collision(req):
        return func.HttpResponse("ok")

    app.add_durable_agent(make_agent())
    for _ in range(2):
        with pytest.raises(ValueError, match="Duplicate function name"):
            app.get_functions()
    assert not app._functions_indexed


def test_sdk_builtin_names_cannot_be_shadowed(app, tmp_path):
    app.add_durable_agent(make_agent())
    # Derive the SDK-owned names rather than duplicating a hard-coded list.
    sdk_functions = app._durable_app.get_functions()
    builtins = [fn for fn in sdk_functions if fn.get_function_name() != "dafx-Orders"]
    assert builtins
    for index, builtin in enumerate(builtins):
        candidate = AgentFunctionApp(
            client_factory=RecordingClient, app_root=tmp_path
        )
        candidate.add_durable_agent(make_agent())

        @candidate.function_name(name=builtin.get_function_name())
        @candidate.route(route=f"collision/{index}")
        def collision(req):
            return func.HttpResponse("ok")

        with pytest.raises(ValueError, match="Duplicate function name"):
            candidate.get_functions()


def test_existing_activity_path_does_not_create_dafx(app):
    @app.orchestration_trigger(context_name="context")
    def orchestrator(context):
        yield context.call_agent("orders", "hello")

    names = {fn.get_function_name() for fn in app.get_functions()}
    assert names == {"orchestrator", "azurefunctions_agents_run_markdown_agent"}
    assert app._durable_app is None


def _execute_entity(handler, entity_id, request, state):
    """Invoke the indexed SDK handler using the host's protobuf wire format."""
    batch = pb.EntityBatchRequest(
        instanceId=str(entity_id),
        operations=[pb.OperationRequest(
            operation="run", input=StringValue(value=json.dumps(request))
        )],
    )
    if state is not None:
        batch.entityState.CopyFrom(StringValue(value=state))
    transport = func.EntityContext(base64.b64encode(batch.SerializeToString()))
    encoded_result = handler(transport)
    result = pb.EntityBatchResult.FromString(base64.b64decode(encoded_result))
    assert not result.HasField("failureDetails"), result
    assert len(result.results) == 1
    operation = result.results[0]
    assert operation.HasField("success"), operation
    return json.loads(operation.success.result.value), result.entityState.value


def test_proxy_runs_indexed_entity_and_restores_session_between_turns(app):
    client = RecordingClient()
    app.add_durable_agent(make_agent(client=client))
    entity = next(
        fn for fn in app.get_functions() if fn.get_function_name() == "dafx-Orders"
    )
    handler = entity.get_user_function()
    scheduled = []

    def call_entity(entity_id, operation, input_=None):
        assert operation == "run"
        task = CompletableTask()
        scheduled.append((entity_id, input_, task))
        return task

    # Only the scheduler is replaced. Use the SDK wrapper the PR receives,
    # its context proxy, real DAFX tasks, and the real indexed entity handler.
    scheduler = Mock(instance_id="workflow-1")
    scheduler.new_uuid.side_effect = [str(uuid.UUID(int=n)) for n in range(1, 5)]
    scheduler.call_entity.side_effect = call_entity
    context = DurableAgentContext(DurableOrchestrationContext(scheduler))
    agent = app.get_agent(context, "Orders")
    session = agent.create_session()
    state = None

    for turn, prompt in enumerate(["first", "second"], start=1):
        task = agent.run(prompt, session=session)
        assert not task.is_complete
        entity_id, request, pending = scheduled[-1]
        response, state = _execute_entity(handler, entity_id, request, state)
        pending.complete(response)
        result = task.get_result()
        assert isinstance(result, AgentResponse)
        assert result.text == f"reply-{turn}"

    assert scheduled[0][0] == scheduled[1][0]
    assert client.inputs == [["first"], ["first", "reply-1", "second"]]
    assert state
