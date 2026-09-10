"""Opt-in loading of MAF YAML workflows for the DAFX Functions host."""

from __future__ import annotations

import re
import sys
from collections.abc import Callable, Iterable, Iterator
from importlib import import_module
from pathlib import Path
from typing import Any

from agent_framework import SupportsAgentRun, Workflow

_SUFFIXES = (".workflow.yaml", ".workflow.yml")
_WORKFLOW_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,62}")


def _definition_paths(root: Path) -> list[Path]:
    paths = []
    for directory in (root, root / "workflows"):
        if not directory.is_dir():
            continue
        for path in sorted(directory.iterdir()):
            if not path.name.endswith(_SUFFIXES):
                continue
            if not path.is_file():
                raise ValueError(f"Workflow definition {path.name!r} is not a file.")
            if not path.resolve().is_relative_to(root):
                raise ValueError(f"Workflow definition {path.name!r} escapes app root.")
            paths.append(path)
    return paths


def _nodes(
    value: Any, ancestors: frozenset[int] = frozenset(),
) -> Iterator[dict[str, Any]]:
    """Walk definitions without recursively following a cyclic YAML alias."""
    if not isinstance(value, (dict, list)):
        return
    if id(value) in ancestors:
        raise ValueError("Cyclic YAML aliases are not supported in workflows.")
    ancestors = ancestors | {id(value)}
    children: Iterable[Any]
    if isinstance(value, dict):
        yield value
        children = value.values()
    else:
        children = value
    for child in children:
        yield from _nodes(child, ancestors)


def load_workflows(
    root: Path,
    resolve_agent: Callable[[str], SupportsAgentRun],
) -> list[Workflow]:
    """Load selected definitions without instantiating live agents or clients.

    YAML agent actions reference markdown names. Inline/file-based YAML agent
    construction and implicit HTTP/MCP action handlers are intentionally excluded.
    The factory still validates the supported YAML action schemas.
    """
    # MAF currently omits its PowerFx dependency on 3.14. Refuse this opt-in
    # rather than silently treating expressions as literal strings.
    if sys.version_info >= (3, 14):
        raise RuntimeError("YAML workflows currently require Python 3.13 (PowerFx).")
    paths = _definition_paths(root)
    try:
        import yaml
        from agent_framework.declarative import WorkflowFactory
        builder = import_module(
            "agent_framework_declarative._workflows._declarative_builder"
        )
    except ModuleNotFoundError as error:
        if error.name not in {"yaml", "agent_framework_declarative"}:
            raise
        raise ImportError(
            "YAML workflow support is not installed. Install "
            "'azurefunctions-agents-extensions-agent-framework[durable,workflows]'."
        ) from error

    class UniqueKeyLoader(yaml.SafeLoader):
        def construct_mapping(self, node: Any, deep: bool = False) -> Any:
            self.flatten_mapping(node)
            keys: set[Any] = set()
            for key_node, _ in node.value:
                key = self.construct_object(key_node, deep=deep)
                if not isinstance(key, (str, int, float, bool, type(None))):
                    raise ValueError("Workflow YAML keys must be scalar values.")
                if key in keys:
                    raise ValueError(f"Duplicate YAML key {key!r}.")
                keys.add(key)
            return super().construct_mapping(node, deep=deep)

    definitions: list[tuple[Path, dict[str, Any], set[str]]] = []
    names: set[str] = set()
    for path in paths:
        definition = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
        if not isinstance(definition, dict):
            raise ValueError(f"Workflow {path.name!r} must contain a YAML mapping.")
        name = definition.get("name")
        if not isinstance(name, str) or _WORKFLOW_NAME.fullmatch(name) is None:
            raise ValueError(
                f"Workflow {path.name!r} needs an explicit name of 1-63 ASCII "
                "letters, digits, hyphens or underscores, starting with a letter."
            )
        if name.casefold() in names:
            raise ValueError(f"Duplicate workflow name {name!r}.")
        names.add(name.casefold())
        if definition.get("agents"):
            raise ValueError(
                f"Workflow {name!r}: inline/file agent definitions are not supported; "
                "reference a markdown agent by name in InvokeAzureAgent instead."
            )
        # Force cycle validation before inspecting action schema fields.
        list(_nodes(definition))
        references: set[str] = set()
        # MAF logs and skips unknown actions. Reject them instead of publishing
        # an incomplete graph. The registry is internal to the pinned loader;
        # structural actions are handled separately by its graph builder.
        action_kinds = set(builder.ALL_ACTION_EXECUTORS) | {
            "If", "ConditionGroup", "Foreach", "GotoAction",
            "BreakLoop", "ContinueLoop",
        }

        def actions_in(container: dict[str, Any]) -> Iterator[dict[str, Any]]:
            container_kind = container.get("kind")
            if container_kind == "If":
                if "elseActions" in container:
                    raise ValueError("If uses 'else', not 'elseActions'.")
                if "then" in container and "actions" in container:
                    raise ValueError("If cannot define both 'then' and 'actions'.")
                fields = (
                    ("then", "else") if "then" in container else ("actions", "else")
                )
            else:
                fields = ("actions", "elseActions")
            for field in fields:
                actions = container.get(field)
                if isinstance(actions, list):
                    for action in actions:
                        kind = action.get("kind") if isinstance(action, dict) else None
                        if not isinstance(kind, str) or kind not in action_kinds:
                            raise ValueError(f"Unknown workflow action kind {kind!r}.")
                        if kind in {
                            "InvokeFunctionTool", "HttpRequestAction", "InvokeMcpTool",
                        }:
                            raise ValueError(
                                f"{kind} requires a workflow handler that this loader "
                                "does not configure. Agent tools remain supported."
                            )
                        yield action
                        yield from actions_in(action)
                        if kind == "ConditionGroup":
                            for condition in action.get("conditions", []):
                                if isinstance(condition, dict):
                                    yield from actions_in(condition)

        if "actions" in definition and "trigger" in definition:
            raise ValueError("Workflow cannot define both root actions and trigger.")
        container = definition.get("trigger", definition)
        if not isinstance(container, dict):
            raise ValueError("Workflow trigger must be a mapping.")
        for node in actions_in(container):
            if node.get("kind") != "InvokeAzureAgent":
                continue
            agent = node.get("agent", node.get("agentName"))
            if isinstance(agent, dict):
                agent = agent.get("name")
            if not isinstance(agent, str) or not agent or agent.startswith("="):
                raise ValueError(
                    f"Workflow {name!r}: InvokeAzureAgent requires a static markdown "
                    "agent name (dynamic names are not supported)."
                )
            references.add(agent)
        definitions.append((path, definition, references))

    workflows = []
    for path, definition, references in definitions:
        agents = {name: resolve_agent(name) for name in sorted(references)}
        factory = WorkflowFactory(agents=agents)
        workflows.append(factory.create_workflow_from_definition(
            definition, base_path=path.parent,
        ))
    return workflows
