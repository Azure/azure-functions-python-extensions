from __future__ import annotations

import asyncio
import base64
import inspect
import json
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import azure.functions as func
from agent_framework import (
    AgentResponse, AgentResponseUpdate, AgentSession, Content, Message, ResponseStream,
    SupportsAgentRun,
)

from azurefunctions.agents.extensions.agent_framework import AgentFunctionApp
from azurefunctions.agents.extensions.agent_framework._durable import (
    MarkdownDurableAgent,
)
from azurefunctions.agents.extensions.base import compile_agent, discover_agent_names


def make_app(tmp_path, **kwargs):
    return AgentFunctionApp(client_factory=lambda: None, app_root=tmp_path, **kwargs)


def definition(root, name="orders", text="Instructions"):
    root.mkdir(parents=True, exist_ok=True)
    (root / f"{name}.agent.md").write_text(text, encoding="utf-8")


def test_discovery_is_opt_in_and_creates_recipes_not_live_agents(tmp_path):
    definition(tmp_path)
    definition(tmp_path / "agents", "shipping")
    definition(tmp_path / "nested", "ignored")
    factory = Mock(side_effect=AssertionError("client created during indexing"))
    plain = AgentFunctionApp(client_factory=factory, app_root=tmp_path)
    assert plain.get_functions() == []
    assert plain._durable_app is None

    app = AgentFunctionApp(client_factory=factory, app_root=tmp_path, durable=True)
    assert set(app._durable_app.agents) == {"orders", "shipping"}
    indexed = app.get_functions()
    assert set(fn.get_function_name() for fn in indexed) == {
        "dafx-orders", "dafx-shipping", "http-orders", "http-shipping",
        "BuiltIn__HttpActivity", "BuiltIn__HttpPollOrchestrator",
    }
    factory.assert_not_called()
    assert all(isinstance(agent, SupportsAgentRun)
               for agent in app._durable_app.agents.values())


@pytest.mark.parametrize("value", [None, 0, 1, "true", [], {}])
def test_durable_flag_is_explicit_bool(tmp_path, value):
    with pytest.raises(TypeError, match="durable must be a bool"):
        make_app(tmp_path, durable=value)


@pytest.mark.parametrize("second", ["orders", "ORDERS"])
def test_discovery_rejects_ambiguous_names_before_registration(
    tmp_path, monkeypatch, second
):
    definition(tmp_path, "orders")
    definition(tmp_path / "agents", second)
    ensure = Mock(side_effect=AssertionError("partial durable registration"))
    monkeypatch.setattr(AgentFunctionApp, "_ensure_durable_app", ensure)
    with pytest.raises(ValueError, match="[Aa]mbiguous"):
        make_app(tmp_path, durable=True)
    ensure.assert_not_called()


def test_discovery_ignores_unrelated_files_and_rejects_definition_directories(tmp_path):
    (tmp_path / "readme.md").write_text("ignore", encoding="utf-8")
    (tmp_path / "orders.agent.md").mkdir()
    with pytest.raises(ValueError, match="not a file"):
        make_app(tmp_path, durable=True)


def test_discovery_rejects_escaping_symlink(tmp_path):
    outside = tmp_path.parent / f"{tmp_path.name}-outside.agent.md"
    outside.write_text("Outside", encoding="utf-8")
    try:
        (tmp_path / "orders.agent.md").symlink_to(outside)
    except OSError as error:
        pytest.skip(f"Symlinks unavailable: {error}")
    with pytest.raises(ValueError, match="outside app root"):
        make_app(tmp_path, durable=True)


def test_compile_preserves_raw_instructions(tmp_path):
    path = tmp_path / "orders.agent.md"
    path.write_bytes(b"---\r\nname: ignored\r\n---\r\nRaw instructions\r\n")
    app = make_app(tmp_path)
    assert discover_agent_names(app) == ["orders"]
    assert compile_agent(app, "orders").instructions == path.read_bytes().decode()


def test_binding_registers_once_and_hides_injected_parameter(tmp_path):
    definition(tmp_path)
    app = make_app(tmp_path)

    @app.durable_markdown_agent(arg_name="agent", agent_name="orders")
    def first(context, *, agent):
        yield agent

    @app.durable_markdown_agent(arg_name="agent", agent_name="orders")
    def second(context, agent):
        yield agent

    assert len(app._durable_app.agents) == 1
    assert list(inspect.signature(first).parameters) == ["context"]
    proxy = object()
    app.get_agent = Mock(return_value=proxy)
    context = object()
    assert next(first(context)) is proxy
    assert next(second(context=context)) is proxy
    app.get_agent.assert_called_with(context, "orders")
    with pytest.raises(TypeError):
        next(first(context, agent=object()))


def test_binding_and_discovery_share_one_entity(tmp_path):
    definition(tmp_path)
    app = make_app(tmp_path, durable=True)
    original = app._durable_app.agents["orders"]

    @app.orchestration_trigger(context_name="context")
    @app.durable_markdown_agent(arg_name="agent", agent_name="orders")
    def workflow(context, agent):
        yield agent.run("hello")

    assert app._durable_app.agents["orders"] is original
    assert len(app.get_functions()) == 5


def test_binding_custom_context_and_native_input_are_forwarded(tmp_path):
    definition(tmp_path)
    app = make_app(tmp_path)

    @app.orchestration_trigger(context_name="ctx")
    @app.durable_markdown_agent(
        arg_name="agent", agent_name="orders", context_name="ctx"
    )
    def workflow(ctx, input, agent):
        yield (ctx, input, agent)

    proxy = object()
    app.get_agent = Mock(return_value=proxy)
    context = object()
    original = workflow._function.get_user_function().orchestrator_function
    assert next(original(context, {"message": "hello"})) == (
        context, {"message": "hello"}, proxy
    )


@pytest.mark.parametrize("native_input", [False, True])
def test_indexed_orchestrator_transport_schedules_entity(tmp_path, native_input):
    from durabletask.internal import orchestrator_service_pb2 as pb
    from google.protobuf.timestamp_pb2 import Timestamp
    from google.protobuf.wrappers_pb2 import StringValue

    definition(tmp_path)
    factory = Mock(side_effect=AssertionError("live agent opened by orchestrator"))
    app = AgentFunctionApp(client_factory=factory, app_root=tmp_path)

    if native_input:
        def workflow(context, input, agent):
            yield agent.run(input["message"])
    else:
        def workflow(context, agent):
            yield agent.run(context.get_input()["message"])

    workflow = app.durable_markdown_agent(
        arg_name="agent", agent_name="orders"
    )(workflow)
    app.orchestration_trigger(context_name="context")(workflow)
    handler = next(fn.get_user_function() for fn in app.get_functions()
                   if fn.get_function_name() == "workflow")
    timestamp = Timestamp(seconds=1_700_000_000)
    request = pb.OrchestratorRequest(instanceId="test-workflow", newEvents=[
        pb.HistoryEvent(eventId=-1, timestamp=timestamp,
                        orchestratorStarted=pb.OrchestratorStartedEvent()),
        pb.HistoryEvent(eventId=0, timestamp=timestamp,
                        executionStarted=pb.ExecutionStartedEvent(
                            name="workflow",
                            input=StringValue(value=json.dumps({"message": "hello"})),
                            orchestrationInstance=pb.OrchestrationInstance(
                                instanceId="test-workflow",
                                executionId=StringValue(value="execution-1"),
                            ),
                        )),
    ])
    output = handler(func.OrchestrationContext(
        base64.b64encode(request.SerializeToString())
    ))
    result = pb.OrchestratorResponse.FromString(base64.b64decode(output))
    assert len(result.actions) == 1, result
    action = result.actions[0]
    assert action.HasField("sendEntityMessage"), result
    assert "dafx-orders" in str(action), result
    factory.assert_not_called()


def test_binding_trigger_context_mismatch_is_rejected(tmp_path):
    definition(tmp_path)
    app = make_app(tmp_path)

    @app.durable_markdown_agent(arg_name="agent", agent_name="orders")
    def workflow(context, agent):
        yield agent

    with pytest.raises(TypeError, match="context_name must match"):
        app.orchestration_trigger(context_name="wrong")(workflow)


@pytest.mark.parametrize("name", [
    None, "", " ", 1, "../orders", "/orders", "{order}", "a@b", "a b", "a#b",
])
def test_binding_invalid_or_escaping_names_fail_without_dafx(tmp_path, name):
    definition(tmp_path)
    app = make_app(tmp_path)

    def workflow(context, agent):
        yield agent

    with pytest.raises(ValueError):
        app.durable_markdown_agent(arg_name="agent", agent_name=name)(workflow)
    assert app._durable_app is None


def test_replay_only_schedules_tasks_without_opening_agents(tmp_path):
    from azure.durable_functions import DurableOrchestrationContext
    from durabletask.task import CompletableTask

    definition(tmp_path)
    factory = Mock(side_effect=AssertionError("agent opened in orchestration"))
    app = AgentFunctionApp(client_factory=factory, app_root=tmp_path)

    @app.orchestration_trigger(context_name="context")
    @app.durable_markdown_agent(arg_name="agent", agent_name="orders")
    def workflow(context, agent):
        session = agent.create_session()
        yield agent.run("hello", session=session)

    requests = []
    for replay in [False, True]:
        scheduler = Mock(instance_id="workflow-1", is_replaying=replay)
        scheduler.new_uuid.side_effect = ["session-key", "correlation-id"]
        scheduler.call_entity.return_value = CompletableTask()
        context = DurableOrchestrationContext(scheduler)
        handler = workflow._function.get_user_function().orchestrator_function
        next(handler(context))
        entity, operation, payload = scheduler.call_entity.call_args.args
        # Pinned DAFX's RunRequest supplies a wall-clock created_at by default.
        # Check stable routing/identity/input here, not byte-identical payloads.
        assert payload.pop("created_at")
        requests.append((str(entity), operation, payload))
    assert requests[0] == requests[1]
    factory.assert_not_called()


def test_binding_missing_file_fails_before_registration(tmp_path):
    app = make_app(tmp_path)

    def workflow(context, agent):
        yield agent

    with pytest.raises(FileNotFoundError):
        app.durable_markdown_agent(arg_name="agent", agent_name="missing")(workflow)
    assert app._durable_app is None


def test_binding_invalid_handler_shapes_do_not_register(tmp_path):
    definition(tmp_path)
    app = make_app(tmp_path)
    bind = app.durable_markdown_agent(arg_name="agent", agent_name="orders")

    async def async_handler(context, agent):
        return agent

    def nongenerator(context, agent):
        return agent

    def missing_agent(context):
        yield context

    def missing_context(agent):
        yield agent

    def wrong_order(input, context, agent):
        yield agent

    def variadic(context, *agent):
        yield agent

    for handler in [async_handler, nongenerator, missing_agent,
                    missing_context, wrong_order, variadic]:
        with pytest.raises(TypeError):
            bind(handler)
        assert app._durable_app is None


def test_binding_late_declaration_fails(tmp_path):
    definition(tmp_path)
    app = make_app(tmp_path)
    app.get_functions()

    def workflow(context, agent):
        yield agent

    with pytest.raises(RuntimeError, match="before function indexing"):
        app.durable_markdown_agent(arg_name="agent", agent_name="orders")(workflow)
    assert app._durable_app is None


def test_generated_http_function_name_collision_is_not_silent(tmp_path):
    definition(tmp_path, "order-one")
    definition(tmp_path, "order_one")
    app = make_app(tmp_path, durable=True)
    with pytest.raises(ValueError, match="unique function name"):
        app.get_functions()


def lifecycle_adapter(*, failure=None):
    """Exercise adapter lifetimes separately from the real SDK sample tests."""
    events = []
    calls = []
    response = AgentResponse(
        messages=[Message(role="assistant", contents=["done"])], value={"answer": 42}
    )

    @asynccontextmanager
    async def open_agent(invocation):
        instance = len(calls)
        events.append((instance, "open"))
        if failure == "open":
            raise RuntimeError("open failed")

        def run(messages, *, stream=False, session=None, **kwargs):
            calls.append((messages, session, kwargs))

            async def updates():
                events.append((instance, "pull"))
                yield AgentResponseUpdate(contents=[Content.from_text("done")])
                if failure == "stream":
                    raise RuntimeError("stream failed")
                if failure == "cancel":
                    await asyncio.Event().wait()

            def finalize(_):
                assert (instance, "close") not in events
                events.append((instance, "finalize"))
                if failure == "finalize":
                    raise RuntimeError("finalize failed")
                return response

            async def invoke():
                if failure == "run":
                    raise RuntimeError("run failed")
                return response

            return ResponseStream(updates(), finalizer=finalize) if stream else invoke()

        try:
            yield SimpleNamespace(run=run)
        finally:
            events.append((instance, "close"))

    recipe = SimpleNamespace(agent_name="orders", open_agent=open_agent)
    return MarkdownDurableAgent(recipe), events, calls, response


def test_adapter_stream_keeps_resources_alive_through_finalization():
    adapter, events, calls, expected = lifecycle_adapter()
    session = AgentSession()

    async def invoke():
        for _ in range(2):
            stream = adapter.run(
                "hello", stream=True, session=session, options={"x": 1}
            )
            # Constructing and awaiting the stream must not create live resources.
            assert len(events) == 4 * len(calls)
            await stream
            result = await stream.get_final_response()
            assert result is expected
            assert result.value == {"answer": 42}

    asyncio.run(invoke())
    assert events == [(i, event) for i in range(2)
                      for event in ["open", "pull", "finalize", "close"]]
    assert calls == [("hello", session, {"options": {"x": 1}})] * 2


@pytest.mark.parametrize("failure", ["stream", "finalize"])
def test_adapter_closes_resources_on_stream_failure(failure):
    adapter, events, _, _ = lifecycle_adapter(failure=failure)

    async def invoke():
        with pytest.raises(RuntimeError, match=failure):
            await adapter.run("hello", stream=True).get_final_response()

    asyncio.run(invoke())
    assert events[-1] == (0, "close")


def test_adapter_closes_resources_on_cancelled_pull():
    adapter, events, _, _ = lifecycle_adapter(failure="cancel")

    async def invoke():
        stream = adapter.run("hello", stream=True)
        await anext(stream)
        started = asyncio.Event()

        async def pull():
            started.set()
            return await anext(stream)

        task = asyncio.create_task(pull())
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(invoke())
    assert events[-1] == (0, "close")


@pytest.mark.parametrize("failure", [None, "run", "open"])
def test_adapter_nonstream_response_and_cleanup(failure):
    adapter, events, _, expected = lifecycle_adapter(failure=failure)

    async def invoke():
        if failure:
            with pytest.raises(RuntimeError, match=failure):
                await adapter.run("hello")
        else:
            assert await adapter.run("hello") is expected

    asyncio.run(invoke())
    if failure != "open":
        assert events[-1] == (0, "close")
