"""Opt-in loading of MAF YAML workflows for the DAFX Functions host."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from agent_framework import SupportsAgentRun, Workflow

_SUFFIXES = (".workflow.yaml", ".workflow.yml")
_WORKFLOW_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,62}")


class WorkflowLoader(Protocol):
    """Public loading surface implemented by MAF's WorkflowFactory."""

    def create_workflow_from_yaml_path(self, yaml_path: str | Path) -> Workflow:
        ...


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


def load_workflows(
    root: Path,
    agents: Mapping[str, SupportsAgentRun],
    factory: WorkflowLoader | None = None,
) -> list[Workflow]:
    """Discover files and hand them to MAF without interpreting its YAML schema.

    The default factory receives markdown recipes as a convenience registry.
    A caller-supplied factory is used unchanged, including its agent registry,
    agent factory, tools, handlers, configuration, and resource ownership.
    MAF owns parsing, relative references, validation and agent construction.
    """
    paths = _definition_paths(root)
    if factory is None:
        try:
            from agent_framework.declarative import WorkflowFactory
        except ModuleNotFoundError as error:
            if error.name != "agent_framework_declarative":
                raise
            raise ImportError(
                "YAML workflow support is not installed. Install "
                "'azurefunctions-agents-extensions-agent-framework[durable,workflows]'."
            ) from error
        factory = WorkflowFactory(agents=agents)

    workflows = []
    names: set[str] = set()
    for path in paths:
        workflow = factory.create_workflow_from_yaml_path(path)
        if not isinstance(workflow, Workflow):
            raise TypeError("The workflow factory must return a MAF Workflow.")
        name = workflow.name
        if not isinstance(name, str) or _WORKFLOW_NAME.fullmatch(name) is None:
            raise ValueError(
                f"Workflow {path.name!r} needs a stable name of 1-63 ASCII "
                "letters, digits, hyphens or underscores, starting with a letter."
            )
        if name.casefold() in names:
            raise ValueError(f"Duplicate workflow name {name!r}.")
        names.add(name.casefold())
        workflows.append(workflow)
    return workflows
