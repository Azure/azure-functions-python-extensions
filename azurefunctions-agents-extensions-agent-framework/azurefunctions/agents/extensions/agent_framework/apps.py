from __future__ import annotations

import functools
import inspect
import os
import re
from collections.abc import Callable, Sequence
from pathlib import Path
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
from ._workflows import WorkflowLoader

if TYPE_CHECKING:
    from agent_framework_durabletask import DurableAgentTask, DurableAIAgent
    from durabletask.task import OrchestrationContext

    from ._durable import MarkdownDurableAgent
    from ._hosting import HostedAgentFunctionApp

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
        discover_agents: bool = False,
        discover_workflows: bool = False,
        expose_agent_endpoints: bool = True,
        expose_workflow_endpoints: bool = True,
        workflow_factory: WorkflowLoader | None = None,
    ) -> None:
        for name, value in (
            ("discover_agents", discover_agents),
            ("discover_workflows", discover_workflows),
            ("expose_agent_endpoints", expose_agent_endpoints),
            ("expose_workflow_endpoints", expose_workflow_endpoints),
        ):
            if not isinstance(value, bool):
                raise TypeError(f"{name} must be a bool")
        super().__init__(
            http_auth_level=http_auth_level,
        )
        self._durable_app: HostedAgentFunctionApp | None = None
        self._functions_indexed = False
        self._durable_agents: dict[str, SupportsAgentRun] = {}
        self._agent_http_endpoints: dict[str, bool] = {}
        self._markdown_agents: dict[str, MarkdownDurableAgent] = {}
        self._markdown_discovered = False
        self._hosted_workflows: dict[str, Workflow] = {}
        self._workflow_http_endpoints: dict[str, bool] = {}
        self._workflow_factory = workflow_factory
        configure_app(
            self,
            provider=AGENT_FRAMEWORK_PROVIDER_ID,
            app_root=app_root,
            provider_options=_provider_options(
                client_factory=client_factory,
                tools=tools,
            ),
        )
        if discover_agents or (discover_workflows and workflow_factory is None):
            self._discover_markdown_agents()
        if discover_agents:
            for agent in self._markdown_agents.values():
                self.add_durable_agent(
                    agent, expose_http_endpoint=expose_agent_endpoints,
                )
        if discover_workflows:
            from ._workflows import load_workflows

            for workflow in load_workflows(
                get_app_root(self), self._markdown_agents, factory=workflow_factory,
            ):
                self._register_workflow(
                    workflow, expose_http_endpoint=expose_workflow_endpoints,
                )

    def _check_registration_open(self) -> None:
        # A failed combined-name validation may already have cached the host.
        # Retrying indexing is safe, but changing that host's inputs is not.
        if self._functions_indexed or self._durable_app is not None:
            raise RuntimeError("Register durable bindings before function indexing.")

    def _discover_markdown_agents(self) -> None:
        if not self._markdown_discovered:
            for name in discover_agent_names(self):
                self._get_markdown_agent(name)
            self._markdown_discovered = True

    def _get_markdown_agent(self, name: str) -> MarkdownDurableAgent:
        from ._durable import MarkdownDurableAgent

        for registered_name, agent in self._markdown_agents.items():
            if registered_name.casefold() == name.casefold():
                if registered_name != name:
                    raise ValueError(f"Ambiguous agent name {name!r}.")
                return agent
        agent = MarkdownDurableAgent(self._compile_durable_markdown(name))
        self._markdown_agents[name] = agent
        return agent

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

    def durable_markdown_agent(
        self,
        *,
        arg_name: str,
        agent_name: str,
        context_name: str = "context",
        expose_http_endpoint: bool = False,
    ) -> Callable[[_F], _F]:
        """Declare a durable markdown agent and inject its orchestration proxy.

        Apply below orchestration_trigger, above a synchronous generator. The
        agent is private unless HTTP exposure is explicitly requested here or
        by bulk agent discovery. Repeated declarations reuse the same recipe.
        """
        if not isinstance(agent_name, str) or not agent_name.strip():
            raise ValueError("agent_name must be a non-empty string")
        if not isinstance(expose_http_endpoint, bool):
            raise TypeError("expose_http_endpoint must be a bool")

        def register() -> None:
            self.add_durable_agent(
                self._get_markdown_agent(agent_name),
                expose_http_endpoint=expose_http_endpoint,
            )

        return self._durable_binding(
            arg_name=arg_name,
            context_name=context_name,
            binding_name="durable_markdown_agent",
            register=register,
            get_proxy=lambda context: self.get_agent(context, agent_name),
        )

    def _register_workflow(
        self, workflow: Workflow, *, expose_http_endpoint: bool,
    ) -> None:
        self._check_registration_open()
        name = workflow.name
        if not isinstance(name, str) or re.fullmatch(
            r"[A-Za-z][A-Za-z0-9_-]{0,62}", name,
        ) is None:
            raise ValueError("A durable workflow must have a stable workflow name.")
        for registered_name, registered in self._hosted_workflows.items():
            if registered_name.casefold() == name.casefold():
                if registered_name != name:
                    raise ValueError(f"Ambiguous workflow name {name!r}.")
                if registered is not workflow:
                    raise ValueError(f"Workflow {name!r} is already registered.")
        self._hosted_workflows[name] = workflow
        self._workflow_http_endpoints[name] = (
            self._workflow_http_endpoints.get(name, False) or expose_http_endpoint
        )

    def durable_workflow(
        self,
        *,
        arg_name: str,
        workflow_name: str,
        context_name: str = "context",
        workflow_file: str | Path | None = None,
        expose_http_endpoint: bool = False,
    ) -> Callable[[_F], _F]:
        """Inject a private-by-default workflow proxy into an orchestrator.

        Reuse a registered graph, or selectively load a matching definition.
        workflow_file selects an app-root-relative file only for a new name;
        omit it when reusing a graph registered by discovery or another binding.
        """
        if not isinstance(workflow_name, str) or re.fullmatch(
            r"[A-Za-z][A-Za-z0-9_-]{0,62}", workflow_name,
        ) is None:
            raise ValueError(
                "workflow_name must be 1-63 ASCII letters, digits, hyphens or "
                "underscores, starting with a letter."
            )
        if not isinstance(expose_http_endpoint, bool):
            raise TypeError("expose_http_endpoint must be a bool")
        if workflow_file is not None and not isinstance(workflow_file, (str, Path)):
            raise TypeError("workflow_file must be a str or Path")

        def register() -> None:
            for name in self._hosted_workflows:
                if (
                    name.casefold() == workflow_name.casefold()
                    and name != workflow_name
                ):
                    raise ValueError(f"Ambiguous workflow name {workflow_name!r}.")
            workflow = self._hosted_workflows.get(workflow_name)
            if workflow is not None:
                if workflow_file is not None:
                    raise ValueError(
                        f"Workflow {workflow_name!r} is already registered; omit "
                        "workflow_file to reuse the registered graph."
                    )
            else:
                from ._workflows import load_workflows

                if self._workflow_factory is None:
                    self._discover_markdown_agents()
                workflows = load_workflows(
                    get_app_root(self), self._markdown_agents,
                    factory=self._workflow_factory,
                    workflow_name=workflow_name, workflow_file=workflow_file,
                )
                if len(workflows) != 1 or workflows[0].name != workflow_name:
                    raise ValueError(
                        f"The selected definition must return exactly one workflow "
                        f"named {workflow_name!r}."
                    )
                workflow = workflows[0]
            self._register_workflow(
                workflow, expose_http_endpoint=expose_http_endpoint,
            )

        def get_proxy(context: OrchestrationContext) -> Any:
            from ._workflow_client import DurableWorkflow

            return DurableWorkflow(context, workflow_name)

        return self._durable_binding(
            arg_name=arg_name,
            context_name=context_name,
            binding_name="durable_workflow",
            register=register,
            get_proxy=get_proxy,
        )

    def _durable_binding(
        self,
        *,
        arg_name: str,
        context_name: str,
        binding_name: str,
        register: Callable[[], None],
        get_proxy: Callable[[OrchestrationContext], Any],
    ) -> Callable[[_F], _F]:
        def decorate(handler: _F) -> _F:
            self._check_registration_open()
            if not inspect.isgeneratorfunction(handler):
                raise TypeError(
                    f"{binding_name} requires a synchronous generator "
                    "below orchestration_trigger."
                )
            pending = getattr(handler, "_durable_binding_args", ())
            if arg_name in pending:
                raise TypeError(f"Duplicate injected parameter {arg_name!r}.")
            existing_context = getattr(handler, "_durable_binding_context_name", None)
            if existing_context is not None and existing_context != context_name:
                raise TypeError("Durable bindings must use the same context_name.")
            signature = inspect.signature(handler)
            parameter = signature.parameters.get(arg_name)
            if parameter is None or parameter.kind not in {
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            }:
                raise TypeError(f"Invalid injected parameter {arg_name!r}.")
            context_parameter = signature.parameters.get(context_name)
            if arg_name == context_name or context_parameter is None:
                raise TypeError(f"Missing distinct context parameter {context_name!r}.")
            visible = signature.replace(parameters=[
                item for name, item in signature.parameters.items() if name != arg_name
            ])
            parameters = list(visible.parameters.values())
            if (
                not parameters or parameters[0].name != context_name
                or context_parameter.kind != inspect.Parameter.POSITIONAL_OR_KEYWORD
                or any(p.kind not in {
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    inspect.Parameter.KEYWORD_ONLY,
                } for p in parameters)
            ):
                raise TypeError(
                    "The orchestrator must accept context first and optionally input."
                )
            # Other visible parameters may be consumed by stacked bindings.
            # Only the outer trigger can validate the final native arity.
            register()

            @functools.wraps(handler)
            def inject(*args: Any, **kwargs: Any) -> Any:
                bound = visible.bind(*args, **kwargs)
                bound.apply_defaults()
                bound.arguments[arg_name] = get_proxy(bound.arguments[context_name])
                call = inspect.BoundArguments(signature, bound.arguments)
                return (yield from handler(*call.args, **call.kwargs))

            inject.__signature__ = visible  # type: ignore[attr-defined]
            setattr(inject, "_durable_binding_context_name", context_name)
            setattr(inject, "_durable_binding_args", (*pending, arg_name))
            return cast(_F, inject)

        return decorate

    def add_durable_agent(
        self, agent: SupportsAgentRun, *, expose_http_endpoint: bool = False,
    ) -> None:
        """Opt in to DAFX by registering an agent before function indexing.

        Unlike markdown bindings, this accepts a caller-owned agent instance.
        It does not construct or close the agent's clients or tools.
        """
        self._check_registration_open()
        if not isinstance(expose_http_endpoint, bool):
            raise TypeError("expose_http_endpoint must be a bool")
        name = getattr(agent, "name", None)
        if not isinstance(name, str) or not name.strip():
            raise ValueError("A durable agent must have a non-empty string name.")

        for registered_name, registered_agent in self._durable_agents.items():
            if registered_name.casefold() == name.casefold():
                if registered_name != name or registered_agent is not agent:
                    raise ValueError(f"Durable agent {name!r} is already registered.")
        self._durable_agents[name] = agent
        self._agent_http_endpoints[name] = (
            self._agent_http_endpoints.get(name, False) or expose_http_endpoint
        )

    def _ensure_durable_app(self) -> HostedAgentFunctionApp:
        if self._durable_app is None:
            try:
                from ._hosting import HostedAgentFunctionApp
            except ModuleNotFoundError as error:
                if error.name not in {
                    "agent_framework_azurefunctions", "agent_framework_durabletask",
                    "azure.durable_functions", "durabletask",
                }:
                    raise
                raise ImportError(
                    "DAFX support is not installed. Install "
                    "'azurefunctions-agents-extensions-agent-framework[durable]'."
                ) from error

            durable_app = HostedAgentFunctionApp(
                workflows=list(self._hosted_workflows.values()),
                exposed_workflows={
                    name for name, exposed in self._workflow_http_endpoints.items()
                    if exposed
                },
                http_auth_level=self.auth_level,
            )
            for name, agent in self._durable_agents.items():
                if any(key.casefold() == name.casefold() for key in durable_app.agents):
                    raise ValueError(
                        f"Standalone agent {name!r} collides with a workflow agent."
                    )
                durable_app.add_agent(
                    agent, enable_http_endpoint=self._agent_http_endpoints[name],
                )
            self._durable_app = durable_app
        return self._durable_app

    def get_agent(
        self,
        context: OrchestrationContext,
        agent_name: str,
    ) -> DurableAIAgent[DurableAgentTask]:
        """Get a DAFX proxy without registering functions during execution."""
        if agent_name not in self._durable_agents:
            raise ValueError(f"Agent {agent_name!r} is not registered with this app.")
        from agent_framework_durabletask import (
            DurableAIAgent, OrchestrationAgentExecutor,
        )

        return DurableAIAgent(OrchestrationAgentExecutor(context), agent_name)

    def get_functions(self) -> list[Function]:
        """Expose both registries through the single worker-indexed app."""
        # The SDK retains name-validation state between indexing calls. Start
        # each pass fresh, including retries after an indexing error.
        self.functions_bindings = None
        functions: list[Function] = super().get_functions()
        if self._durable_agents or self._hosted_workflows:
            durable_app = self._ensure_durable_app()
            durable_app.functions_bindings = None
            functions.extend(durable_app.get_functions())

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
            declared_context = getattr(handler, "_durable_binding_context_name", None)
            if declared_context is not None:
                if declared_context != context_name:
                    raise TypeError("Binding and trigger context_name must match.")
                parameters = list(inspect.signature(handler).parameters.values())
                if (
                    not parameters or parameters[0].name != context_name
                    or len(parameters) > 2
                    or any(p.kind != inspect.Parameter.POSITIONAL_OR_KEYWORD
                           for p in parameters)
                ):
                    raise TypeError(
                        "The orchestrator must accept context first "
                        "and optionally input."
                    )
            return decorator(handler)

        return decorate
