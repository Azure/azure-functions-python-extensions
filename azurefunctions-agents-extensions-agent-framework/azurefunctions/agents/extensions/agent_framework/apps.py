from __future__ import annotations

import functools
import inspect
import os
import re
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, TypeVar, cast

import azure.functions as func
from agent_framework import SupportsAgentRun, ToolTypes, Workflow
from azure.functions.decorators.function_app import Function

from azurefunctions.agents.extensions.base import (
    compile_agent,
    configure_app,
    discover_agent_names,
    get_app_root,
)
from azurefunctions.agents.extensions.base import markdown_agent as base_markdown_agent

from .provider import AGENT_FRAMEWORK_PROVIDER_ID, AgentFrameworkBinding, ClientFactory

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
        durable: bool = False,
        workflows: bool = False,
    ) -> None:
        if not isinstance(durable, bool):
            raise TypeError("durable must be a bool")
        if not isinstance(workflows, bool):
            raise TypeError("workflows must be a bool")
        if workflows and not durable:
            raise ValueError("workflows=True requires durable=True.")
        super().__init__(
            http_auth_level=http_auth_level,
        )
        self._durable_app: DurableAgentFunctionApp | None = None
        self._functions_indexed = False
        self._markdown_agents: dict[str, str] = {}
        self._hosted_workflows: list[Workflow] = []
        configure_app(
            self,
            provider=AGENT_FRAMEWORK_PROVIDER_ID,
            app_root=app_root,
            provider_options=_provider_options(
                client_factory=client_factory,
                tools=tools,
            ),
        )
        if durable:
            # Validate/compile the complete discovery set before registering any
            # endpoints. Compilation creates recipes, not clients or live agents.
            bindings = [
                self._compile_durable_markdown(name)
                for name in discover_agent_names(self)
            ]
            if workflows:
                from ._durable import MarkdownDurableAgent
                from ._workflows import load_workflows

                recipes = {binding.agent_name: binding for binding in bindings}

                def resolve_agent(name: str) -> SupportsAgentRun:
                    if name not in recipes:
                        # Use the same validation/error for missing and mis-cased
                        # references as a standalone markdown declaration.
                        recipes[name] = self._compile_durable_markdown(name)
                    return MarkdownDurableAgent(recipes[name])

                self._hosted_workflows = load_workflows(
                    get_app_root(self), resolve_agent,
                )
            self._ensure_durable_app()
            for binding in bindings:
                self._register_durable_markdown(binding)

    def _compile_durable_markdown(self, name: str) -> AgentFrameworkBinding:
        # The name is also used in an HTTP route and a Durable Entity ID, not
        # only a filename. Reject route placeholders and entity-ID separators.
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", name) is None:
            raise ValueError(
                "Durable agent names must start with a letter or digit and "
                "contain only ASCII letters, digits, hyphens, and underscores."
            )
        compiled = compile_agent(self, name)
        if not isinstance(compiled, AgentFrameworkBinding):
            raise TypeError("Durable markdown agents require the MAF provider.")
        return compiled

    def _register_durable_markdown(self, binding: AgentFrameworkBinding) -> None:
        from ._durable import MarkdownDurableAgent

        self.add_durable_agent(MarkdownDurableAgent(binding))
        self._markdown_agents[binding.agent_name.casefold()] = binding.agent_name

    def durable_markdown_agent(
        self,
        *,
        arg_name: str,
        agent_name: str,
        context_name: str = "context",
    ) -> Callable[[_F], _F]:
        """Declare a durable markdown agent and inject its orchestration proxy.

        Apply below orchestration_trigger, above a synchronous generator. The
        declaration also publishes DAFX's default agent HTTP endpoint.
        """
        if not isinstance(agent_name, str) or not agent_name.strip():
            raise ValueError("agent_name must be a non-empty string")

        def decorate(handler: _F) -> _F:
            if self._functions_indexed:
                raise RuntimeError("Declare durable agents before function indexing.")
            if not inspect.isgeneratorfunction(handler):
                raise TypeError(
                    "durable_markdown_agent requires a synchronous generator "
                    "below orchestration_trigger."
                )
            signature = inspect.signature(handler)
            parameter = signature.parameters.get(arg_name)
            if parameter is None or parameter.kind not in {
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            }:
                raise TypeError(f"Invalid injected agent parameter {arg_name!r}.")
            context_parameter = signature.parameters.get(context_name)
            if arg_name == context_name or context_parameter is None:
                raise TypeError(f"Missing distinct context parameter {context_name!r}.")
            visible = signature.replace(parameters=[
                item for name, item in signature.parameters.items() if name != arg_name
            ])
            parameters = list(visible.parameters.values())
            if (
                not parameters or parameters[0].name != context_name
                or len(parameters) > 2
                or any(p.kind != inspect.Parameter.POSITIONAL_OR_KEYWORD
                       for p in parameters)
            ):
                raise TypeError(
                    "The orchestrator must accept context first and optionally input."
                )
            existing_context = getattr(handler, "_durable_agent_context_name", None)
            if existing_context is not None and existing_context != context_name:
                raise TypeError("Durable bindings must use the same context_name.")

            if agent_name.casefold() in self._markdown_agents:
                if self._markdown_agents[agent_name.casefold()] != agent_name:
                    raise ValueError(f"Ambiguous agent name {agent_name!r}.")
            else:
                self._register_durable_markdown(
                    self._compile_durable_markdown(agent_name)
                )

            @functools.wraps(handler)
            def inject(*args: Any, **kwargs: Any) -> Any:
                bound = visible.bind(*args, **kwargs)
                bound.apply_defaults()
                bound.arguments[arg_name] = self.get_agent(
                    bound.arguments[context_name], agent_name
                )
                call = inspect.BoundArguments(signature, bound.arguments)
                return (yield from handler(*call.args, **call.kwargs))

            inject.__signature__ = visible  # type: ignore[attr-defined]
            setattr(inject, "_durable_agent_context_name", context_name)
            return cast(_F, inject)

        return decorate

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
                workflows=self._hosted_workflows,
                http_auth_level=self.auth_level,
                enable_health_check=False,
                enable_http_endpoints=True,
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
            raise RuntimeError(
                "Enable durable=True or declare a durable markdown agent."
            )
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
        # Keep the native SDK context and task semantics; no hidden activity or
        # custom call_agent context wrapper is installed.
        sdk = super().orchestration_trigger
        options: dict[str, Any] = {
            "context_name": context_name, "orchestration": orchestration,
        }
        if input_type is not None:
            if "input_type" not in inspect.signature(sdk).parameters:
                raise TypeError("The installed SDK does not support input_type.")
            options["input_type"] = input_type
        decorator = sdk(**options)

        def decorate(handler: _F) -> Any:
            declared_context = getattr(handler, "_durable_agent_context_name", None)
            if declared_context is not None and declared_context != context_name:
                raise TypeError("Binding and trigger context_name must match.")
            return decorator(handler)

        return decorate
