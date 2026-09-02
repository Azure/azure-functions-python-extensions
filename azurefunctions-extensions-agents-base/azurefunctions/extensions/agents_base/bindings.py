from __future__ import annotations

import functools
import inspect
import os
import threading
import weakref
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath, PureWindowsPath
from types import MappingProxyType
from typing import Any, TypeVar, cast, get_type_hints

import azure.functions as func

from .providers import AgentProvider, CompiledAgent, InvocationMetadata, load_provider

_F = TypeVar("_F", bound=Callable[..., Any])
_INVALID_FILENAME_CHARACTERS = frozenset('<>:"/\\|?*')


@dataclass
class _AppState:
    provider_id: str
    provider: AgentProvider
    app_root: Path
    provider_defaults: Mapping[str, Any]
    durable_agents: dict[str, CompiledAgent] = field(default_factory=dict)
    durable_activity_registered: bool = False
    lock: threading.RLock = field(default_factory=threading.RLock)


_APP_STATES: weakref.WeakKeyDictionary[func.FunctionApp, _AppState] = (
    weakref.WeakKeyDictionary()
)
_APP_STATES_LOCK = threading.Lock()


def _resolve_app_root(app_root: str | os.PathLike[str] | None) -> Path:
    if app_root is not None:
        return Path(app_root).resolve()
    script_root = os.environ.get("AzureWebJobsScriptRoot")
    if script_root:
        return Path(script_root).resolve()
    return Path.cwd().resolve()


def _state_for(
    app: func.FunctionApp,
    *,
    provider: str,
    app_root: str | os.PathLike[str] | None = None,
    provider_defaults: Mapping[str, Any] | None = None,
) -> _AppState:
    resolved_root = _resolve_app_root(app_root)
    defaults = dict(provider_defaults or {})
    with _APP_STATES_LOCK:
        state = _APP_STATES.get(app)
        if state is None:
            state = _AppState(
                provider_id=provider,
                provider=load_provider(provider),
                app_root=resolved_root,
                provider_defaults=MappingProxyType(defaults),
            )
            _APP_STATES[app] = state
            return state
        if state.provider_id != provider:
            raise ValueError(
                f"FunctionApp is already configured for Agent provider "
                f"{state.provider_id!r}; it cannot also use {provider!r}"
            )
        if app_root is not None and state.app_root != resolved_root:
            raise ValueError(
                f"FunctionApp is already configured with app_root "
                f"{str(state.app_root)!r}; it cannot also use "
                f"{str(resolved_root)!r}"
            )
        if provider_defaults is not None and state.provider_defaults != defaults:
            raise ValueError(
                "FunctionApp Agent provider defaults are already configured"
            )
        return state


def configure_app(
    app: func.FunctionApp,
    *,
    provider: str,
    app_root: str | os.PathLike[str] | None = None,
    provider_options: Mapping[str, Any] | None = None,
) -> None:
    _state_for(
        app,
        provider=provider,
        app_root=app_root,
        provider_defaults=provider_options,
    )


def _configured_state(app: func.FunctionApp) -> _AppState:
    with _APP_STATES_LOCK:
        state = _APP_STATES.get(app)
    if state is None:
        raise RuntimeError("FunctionApp is not configured for an Agent provider")
    return state


def _durable_agent(app: func.FunctionApp, agent_name: str) -> CompiledAgent:
    state = _configured_state(app)
    with state.lock:
        compiled = state.durable_agents.get(agent_name)
        if compiled is None:
            compiled = state.provider.compile_binding(
                instructions=_resolve_instructions(state.app_root, agent_name),
                agent_name=agent_name,
                options=state.provider_defaults,
                annotation=inspect.Signature.empty,
            )
            state.durable_agents[agent_name] = compiled
        return compiled


def _validate_agent_name(agent_name: str) -> str:
    if not isinstance(agent_name, str) or not agent_name:
        raise ValueError("agent_name must be a non-empty string")
    if agent_name in {".", ".."}:
        raise ValueError("agent_name must be a filename component")
    if (
        PurePosixPath(agent_name).is_absolute()
        or PureWindowsPath(agent_name).is_absolute()
        or any(
            character in _INVALID_FILENAME_CHARACTERS or ord(character) < 32
            for character in agent_name
        )
    ):
        raise ValueError("agent_name must be a portable filename component")
    return agent_name


def _find_exact_file(directory: Path, expected_name: str) -> Path | None:
    if not directory.is_dir():
        return None
    for entry in directory.iterdir():
        if entry.name == expected_name and entry.is_file():
            return entry
    return None


def _resolve_instructions(app_root: Path, agent_name: str) -> str:
    expected_name = f"{_validate_agent_name(agent_name)}.agent.md"
    matches = [
        match
        for match in (
            _find_exact_file(app_root, expected_name),
            _find_exact_file(app_root / "agents", expected_name),
        )
        if match is not None
    ]
    if not matches:
        raise FileNotFoundError(
            f"Agent {agent_name!r} was not found as {expected_name!r} in "
            f"{str(app_root)!r} or its 'agents' directory"
        )
    if len(matches) > 1:
        raise ValueError(
            f"Agent {agent_name!r} is ambiguous: both "
            f"{str(matches[0])!r} and {str(matches[1])!r} exist"
        )

    source = matches[0].resolve(strict=True)
    if not source.is_relative_to(app_root):
        raise ValueError(
            f"Agent file {str(source)!r} resolves outside app root {str(app_root)!r}"
        )
    return source.read_text(encoding="utf-8")


def _worker_signature(handler: Callable[..., Any], arg_name: str) -> inspect.Signature:
    signature = inspect.signature(handler)
    parameter = signature.parameters.get(arg_name)
    if parameter is None:
        raise TypeError(
            f"markdown_agent arg_name {arg_name!r} is not present in handler "
            f"{handler.__name__!r}"
        )
    if parameter.kind in {
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.VAR_POSITIONAL,
        inspect.Parameter.VAR_KEYWORD,
    }:
        raise TypeError(
            f"markdown_agent parameter {arg_name!r} must be "
            "positional-or-keyword or keyword-only"
        )
    return signature.replace(
        parameters=[
            candidate
            for candidate in signature.parameters.values()
            if candidate.name != arg_name
        ]
    )


def _source_call(
    handler: Callable[..., Any],
    source_signature: inspect.Signature,
    worker_signature: inspect.Signature,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    arg_name: str,
    injected: Any,
) -> Any:
    if arg_name in kwargs:
        raise TypeError(f"markdown_agent parameter {arg_name!r} is runtime-managed")
    bound = worker_signature.bind(*args, **kwargs)
    bound.apply_defaults()
    values = dict(bound.arguments)
    values[arg_name] = injected
    positional: list[Any] = []
    keywords: dict[str, Any] = {}
    for parameter in source_signature.parameters.values():
        if parameter.kind is inspect.Parameter.POSITIONAL_ONLY:
            positional.append(values[parameter.name])
        elif parameter.kind is inspect.Parameter.VAR_POSITIONAL:
            positional.extend(values.get(parameter.name, ()))
        elif parameter.kind is inspect.Parameter.VAR_KEYWORD:
            keywords.update(values.get(parameter.name, {}))
        elif parameter.name in values:
            keywords[parameter.name] = values[parameter.name]
    return handler(*positional, **keywords)


def _invocation_metadata(
    worker_signature: inspect.Signature,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> InvocationMetadata:
    bound = worker_signature.bind(*args, **kwargs)
    for value in bound.arguments.values():
        if isinstance(value, func.Context):
            return InvocationMetadata(
                function_name=str(value.function_name or "") or None,
                invocation_id=str(value.invocation_id or "") or None,
            )
    return InvocationMetadata()


def markdown_agent(
    app: func.FunctionApp,
    *,
    provider: str,
    arg_name: str,
    agent_name: str,
    app_root: str | os.PathLike[str] | None = None,
    **provider_options: Any,
) -> Callable[[_F], _F]:
    state = _state_for(app, provider=provider, app_root=app_root)

    def decorate(handler: _F) -> _F:
        if not inspect.isfunction(handler):
            raise TypeError(
                "markdown_agent must be the innermost decorator, immediately "
                "above the handler"
            )
        if not inspect.iscoroutinefunction(handler):
            raise TypeError("markdown_agent requires an async def handler")

        source_signature = inspect.signature(handler)
        visible_signature = _worker_signature(handler, arg_name)
        annotation = source_signature.parameters[arg_name].annotation
        try:
            annotation = get_type_hints(handler).get(arg_name, annotation)
        except (NameError, TypeError):
            pass
        options = {**state.provider_defaults, **provider_options}
        instructions = _resolve_instructions(state.app_root, agent_name)
        compiled = state.provider.compile_binding(
            instructions=instructions,
            agent_name=agent_name,
            options=options,
            annotation=annotation,
        )

        @functools.wraps(handler)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            invocation = _invocation_metadata(visible_signature, args, kwargs)
            async with compiled.open_agent(invocation) as agent:
                return await _source_call(
                    handler,
                    source_signature,
                    visible_signature,
                    args,
                    kwargs,
                    arg_name,
                    agent,
                )

        async_wrapper.__signature__ = visible_signature  # type: ignore[attr-defined]
        return cast(_F, async_wrapper)

    return decorate
