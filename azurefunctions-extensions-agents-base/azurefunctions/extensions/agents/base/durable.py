from __future__ import annotations

import functools
import inspect
import json
import math
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Dict, List, Literal, TypeVar, Union, cast

import azure.functions as func

from .bindings import _configured_state, _durable_agent
from .providers import InvocationMetadata

if TYPE_CHECKING:
    import azure.durable_functions as df
    from azure.durable_functions import (
        DurableOrchestrationContext as _DurableContextBase,
    )
    from azure.durable_functions.models.Task import TaskBase
else:

    class _DurableContextBase:
        pass


JSONPrimitive = Union[str, int, float, bool, None]
JSONValue = Union[JSONPrimitive, List["JSONValue"], Dict[str, "JSONValue"]]
_F = TypeVar("_F", bound=Callable[..., Any])

_INTERNAL_AGENT_ACTIVITY_NAME = "azurefunctions_agents_run_markdown_agent"
_ACTIVITY_PAYLOAD_VERSION: Literal[1] = 1


def _validate_json_value(value: object) -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("call_agent input cannot contain NaN or infinity")
        return
    if isinstance(value, list):
        for item in value:
            _validate_json_value(item)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("call_agent input object keys must be strings")
            _validate_json_value(item)
        return
    raise TypeError(
        "call_agent input must contain only JSON values "
        f"(received {type(value).__name__})"
    )


def _canonicalize_json_value(value: object) -> JSONValue:
    _validate_json_value(value)
    encoded = json.dumps(value, allow_nan=False, separators=(",", ":"), sort_keys=True)
    return cast(JSONValue, json.loads(encoded))


def _parse_activity_input(value: object) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError("Markdown Agent activity input must be a JSON object")
    expected_fields = {
        "schema_version",
        "agent_name",
        "input",
        "durable_instance_id",
    }
    if set(value) != expected_fields:
        raise ValueError(
            "Markdown Agent activity input must contain exactly: "
            + ", ".join(sorted(expected_fields))
        )
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ValueError(
            "Unsupported Markdown Agent activity payload schema_version; expected 1"
        )
    agent_name = value["agent_name"]
    if not isinstance(agent_name, str) or not agent_name.strip():
        raise ValueError(
            "Markdown Agent activity agent_name must be a non-empty string"
        )
    durable_instance_id = value["durable_instance_id"]
    if not isinstance(durable_instance_id, str) or not durable_instance_id:
        raise ValueError(
            "Markdown Agent activity durable_instance_id must be a non-empty string"
        )
    return {
        "schema_version": 1,
        "agent_name": agent_name,
        "input": _canonicalize_json_value(value["input"]),
        "durable_instance_id": durable_instance_id,
    }


def _normalize_agent_prompt(value: JSONValue) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, allow_nan=False, separators=(",", ":"), sort_keys=True)


class DurableAgentContext(_DurableContextBase):  # type: ignore[misc]
    def __init__(self, context: df.DurableOrchestrationContext) -> None:
        self._context = context

    def __getattr__(self, name: str) -> Any:
        return getattr(self._context, name)

    def call_agent(
        self,
        agent_name: str,
        input_: JSONValue,
        *,
        retry_options: df.RetryOptions | None = None,
    ) -> TaskBase:
        if not isinstance(agent_name, str) or not agent_name.strip():
            raise ValueError("call_agent agent_name must be a non-empty string")
        payload = {
            "schema_version": _ACTIVITY_PAYLOAD_VERSION,
            "agent_name": agent_name,
            "input": _canonicalize_json_value(input_),
            "durable_instance_id": str(self._context.instance_id),
        }
        if retry_options is None:
            return self._context.call_activity(_INTERNAL_AGENT_ACTIVITY_NAME, payload)
        from azure.durable_functions import RetryOptions

        if not isinstance(retry_options, RetryOptions):
            raise TypeError("call_agent retry_options must be RetryOptions or None")
        return self._context.call_activity_with_retry(
            _INTERNAL_AGENT_ACTIVITY_NAME,
            retry_options,
            payload,
        )


def configure_durable_app(app: func.FunctionApp) -> None:
    import azure.durable_functions as df

    state = _configured_state(app)
    with state.lock:
        if state.default_provider_id is None:
            raise RuntimeError(
                "Durable Agent support requires a default Agent provider"
            )
        if state.durable_activity_registered:
            return
        blueprint = df.Blueprint()

        @blueprint.activity_trigger(  # type: ignore[untyped-decorator]
            input_name="payload"
        )
        async def azurefunctions_agents_run_markdown_agent(
            payload: object,
            context: func.Context,
        ) -> str:
            parsed = _parse_activity_input(payload)
            compiled = _durable_agent(
                app,
                parsed["agent_name"],
            )
            invocation = InvocationMetadata(
                function_name=(
                    str(context.function_name or "") or _INTERNAL_AGENT_ACTIVITY_NAME
                ),
                invocation_id=str(context.invocation_id or "") or None,
                durable_instance_id=parsed["durable_instance_id"],
            )
            return await compiled.run_agent(
                _normalize_agent_prompt(parsed["input"]),
                invocation,
            )

        app.register_blueprint(blueprint)
        state.durable_activity_registered = True


def durable_orchestration_trigger(
    app: func.FunctionApp,
    *,
    sdk_decorator: Callable[..., Any],
    context_name: str,
    orchestration: str | None = None,
    input_type: type | None = None,
) -> Callable[[_F], Any]:
    configure_durable_app(app)
    sdk_parameters = inspect.signature(sdk_decorator).parameters
    if input_type is None:
        decorator = sdk_decorator(
            context_name=context_name,
            orchestration=orchestration,
        )
    elif "input_type" in sdk_parameters:
        decorator = sdk_decorator(
            context_name=context_name,
            orchestration=orchestration,
            input_type=input_type,
        )
    else:
        raise TypeError(
            "The installed azure-functions-durable version does not support "
            "orchestration_trigger(input_type=...)"
        )

    def decorate(handler: _F) -> Any:
        if not inspect.isgeneratorfunction(handler):
            raise TypeError(
                "DurableAiApp orchestration_trigger requires a synchronous "
                "generator function"
            )
        signature = inspect.signature(handler)
        parameter = signature.parameters.get(context_name)
        if parameter is None:
            raise TypeError(
                f"orchestration context_name {context_name!r} is not present "
                f"in handler {handler.__name__!r}"
            )
        if parameter.kind is not inspect.Parameter.POSITIONAL_OR_KEYWORD:
            raise TypeError(
                f"orchestration context parameter {context_name!r} must be "
                "positional-or-keyword"
            )

        @functools.wraps(handler)
        def proxy_orchestrator(*args: Any, **kwargs: Any) -> Any:
            bound = signature.bind(*args, **kwargs)
            context = cast(
                df.DurableOrchestrationContext,
                bound.arguments[context_name],
            )
            bound.arguments[context_name] = DurableAgentContext(context)
            return (yield from handler(*bound.args, **bound.kwargs))

        proxy_orchestrator.__signature__ = signature  # type: ignore[attr-defined]
        return decorator(proxy_orchestrator)

    return decorate
