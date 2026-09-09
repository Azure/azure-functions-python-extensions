from __future__ import annotations

import os
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, TypeVar

import azure.functions as func
from agent_framework import SupportsAgentRun, ToolTypes
from azure.functions.decorators.function_app import Function

from azurefunctions.agents.extensions.base import (
    configure_app,
    durable_orchestration_trigger,
)
from azurefunctions.agents.extensions.base import markdown_agent as base_markdown_agent

from .provider import AGENT_FRAMEWORK_PROVIDER_ID, ClientFactory

if TYPE_CHECKING:
    from agent_framework_azurefunctions import (
        AgentFunctionApp as DurableAgentFunctionApp,
    )
    from agent_framework_durabletask import DurableAgentTask, DurableAIAgent
    from durabletask.task import OrchestrationContext

_F = TypeVar("_F", bound=Callable[..., Any])


def _provider_options(
    *,
    client_factory: ClientFactory | None = None,
    tools: (
        ToolTypes | Callable[..., Any] | Sequence[ToolTypes | Callable[..., Any]] | None
    ) = None,
) -> dict[str, object]:
    options: dict[str, object] = {}
    if client_factory is not None:
        options["client_factory"] = client_factory
    if tools is not None:
        options["tools"] = tools
    return options


class _AgentFrameworkAppMixin:
    def markdown_agent(
        self,
        *,
        arg_name: str,
        agent_name: str,
        client_factory: ClientFactory | None = None,
        tools: (
            ToolTypes
            | Callable[..., Any]
            | Sequence[ToolTypes | Callable[..., Any]]
            | None
        ) = None,
    ) -> Callable[[_F], _F]:
        return base_markdown_agent(
            self,
            provider=AGENT_FRAMEWORK_PROVIDER_ID,
            arg_name=arg_name,
            agent_name=agent_name,
            **_provider_options(client_factory=client_factory, tools=tools),
        )


class AgentFunctionApp(
    _AgentFrameworkAppMixin,
    func.FunctionApp,
):
    """Azure Functions app configured for Microsoft Agent Framework Agents."""

    def __init__(
        self,
        *,
        client_factory: ClientFactory,
        app_root: str | os.PathLike[str] | None = None,
        tools: (
            ToolTypes
            | Callable[..., Any]
            | Sequence[ToolTypes | Callable[..., Any]]
            | None
        ) = None,
        http_auth_level: func.AuthLevel | str = func.AuthLevel.FUNCTION,
    ) -> None:
        super().__init__(
            http_auth_level=http_auth_level,
        )
        self._durable_app: DurableAgentFunctionApp | None = None
        self._functions_indexed = False
        configure_app(
            self,
            provider=AGENT_FRAMEWORK_PROVIDER_ID,
            app_root=app_root,
            provider_options=_provider_options(
                client_factory=client_factory,
                tools=tools,
            ),
        )

    def add_durable_agent(self, agent: SupportsAgentRun) -> None:
        """Opt in to DAFX by registering an agent before function indexing.

        Unlike markdown bindings, this accepts a caller-owned agent instance.
        It does not construct or close the agent's clients or tools.
        """
        if self._functions_indexed:
            raise RuntimeError("Register durable agents before function indexing.")
        name = getattr(agent, "name", None)
        if not isinstance(name, str) or not name.strip():
            raise ValueError("A durable agent must have a non-empty string name.")

        durable_app = self._ensure_durable_app()
        for registered_name, registered_agent in durable_app.agents.items():
            if registered_name.casefold() == name.casefold():
                if registered_agent is agent:
                    return
                raise ValueError(f"Durable agent {name!r} is already registered.")
        durable_app.add_agent(agent)

    def _ensure_durable_app(self) -> DurableAgentFunctionApp:
        if self._durable_app is None:
            try:
                from agent_framework_azurefunctions import (
                    AgentFunctionApp as DurableAgentFunctionApp,
                )
            except ModuleNotFoundError as error:
                if error.name != "agent_framework_azurefunctions":
                    raise
                raise ImportError(
                    "DAFX support is not installed. Install "
                    "'azurefunctions-agents-extensions-agent-framework[durable]'."
                ) from error

            self._durable_app = DurableAgentFunctionApp(
                http_auth_level=self.auth_level,
                enable_health_check=False,
                enable_http_endpoints=False,
                enable_mcp_tool_trigger=False,
            )
        return self._durable_app

    def get_agent(
        self,
        context: OrchestrationContext,
        agent_name: str,
    ) -> DurableAIAgent[DurableAgentTask]:
        """Get a DAFX proxy without registering functions during execution."""
        if self._durable_app is None:
            raise RuntimeError("Call add_durable_agent() during app configuration.")
        return self._durable_app.get_agent(context, agent_name)

    def get_functions(self) -> list[Function]:
        """Expose both registries through the single worker-indexed app."""
        # The SDK retains name-validation state between indexing calls. Start
        # each pass fresh, including retries after an indexing error.
        self.functions_bindings = None
        functions: list[Function] = super().get_functions()
        if self._durable_app is not None:
            self._durable_app.functions_bindings = None
            functions.extend(self._durable_app.get_functions())

        names: set[str] = set()
        for function in functions:
            name = function.get_function_name()
            if not name:
                raise ValueError("An indexed function must have a name.")
            if name.casefold() in names:
                raise ValueError(
                    f"Duplicate function name across app registries: {name}"
                )
            names.add(name.casefold())
        self._functions_indexed = True
        return functions

    def orchestration_trigger(
        self,
        context_name: str,
        orchestration: str | None = None,
        input_type: type | None = None,
    ) -> Callable[..., Any]:
        return durable_orchestration_trigger(
            self,
            sdk_decorator=super().orchestration_trigger,
            context_name=context_name,
            orchestration=orchestration,
            input_type=input_type,
        )
