from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from functools import lru_cache
from importlib import metadata
from typing import Any, Mapping, Protocol

from .capabilities import AgentCapabilities

AGENT_PROVIDER_ENTRY_POINT_GROUP = "azurefunctions.extensions.agents.providers"


@dataclass(frozen=True)
class InvocationMetadata:
    function_name: str | None = None
    invocation_id: str | None = None
    durable_instance_id: str | None = None


class CompiledAgent(Protocol):
    def open_agent(
        self,
        invocation: InvocationMetadata,
    ) -> AbstractAsyncContextManager[Any]:
        pass

    async def run_agent(
        self,
        prompt: str,
        invocation: InvocationMetadata,
    ) -> str:
        pass


class AgentProvider(Protocol):
    provider_id: str
    distribution_name: str
    supported_capabilities: frozenset[str]

    def compile_binding(
        self,
        *,
        instructions: str,
        agent_name: str,
        options: Mapping[str, Any],
        annotation: Any,
        capabilities: AgentCapabilities,
    ) -> CompiledAgent:
        pass


def _provider_distribution_name(provider_id: str) -> str:
    normalized = provider_id.replace("_", "-")
    if normalized.startswith("agent-"):
        normalized = normalized.removeprefix("agent-")
    return f"azurefunctions-extensions-agents-{normalized}"


def _entry_point_distribution(entry_point: metadata.EntryPoint) -> str:
    distribution = getattr(entry_point, "dist", None)
    name = getattr(distribution, "name", None)
    return str(name or entry_point.value)


@lru_cache(maxsize=1)
def _provider_entry_points() -> tuple[metadata.EntryPoint, ...]:
    return tuple(metadata.entry_points(group=AGENT_PROVIDER_ENTRY_POINT_GROUP))


def _validate_provider(provider: object, provider_id: str) -> AgentProvider:
    actual_id = getattr(provider, "provider_id", None)
    if actual_id != provider_id:
        raise ValueError(
            f"Agent provider entry point {provider_id!r} returned provider "
            f"{actual_id!r}"
        )
    distribution_name = getattr(provider, "distribution_name", None)
    if not isinstance(distribution_name, str) or not distribution_name:
        raise TypeError(f"Agent provider {provider_id!r} must define distribution_name")
    supported_capabilities = getattr(provider, "supported_capabilities", None)
    if not isinstance(supported_capabilities, frozenset) or any(
        not isinstance(capability, str) for capability in supported_capabilities
    ):
        raise TypeError(
            f"Agent provider {provider_id!r} must define supported_capabilities"
        )
    if not callable(getattr(provider, "compile_binding", None)):
        raise TypeError(f"Agent provider {provider_id!r} must define compile_binding()")
    return provider  # type: ignore[return-value]


@lru_cache(maxsize=None)
def load_provider(provider_id: str) -> AgentProvider:
    if not isinstance(provider_id, str) or not provider_id.strip():
        raise ValueError("Agent provider must be a non-empty string")

    matches = [
        entry_point
        for entry_point in _provider_entry_points()
        if entry_point.name == provider_id
    ]
    if not matches:
        distribution = _provider_distribution_name(provider_id)
        raise LookupError(
            f"Agent provider {provider_id!r} is not installed. "
            f"Install {distribution!r}."
        )
    if len(matches) > 1:
        distributions = sorted(_entry_point_distribution(match) for match in matches)
        raise RuntimeError(
            f"Multiple Agent providers are registered as {provider_id!r}: "
            f"{', '.join(distributions)}"
        )

    factory = matches[0].load()
    if not callable(factory):
        raise TypeError(
            f"Agent provider entry point {provider_id!r} must load a callable factory"
        )
    return _validate_provider(factory(), provider_id)
