"""Host a tool-only YAML workflow with a configured public MAF factory."""

from typing import NoReturn

from agent_framework.declarative import WorkflowFactory
from azurefunctions.agents.extensions.agent_framework import AgentFunctionApp


def format_order(order: str, prefix: str) -> str:
    """Format local input without a model or external service."""
    return f"{prefix} order {order}."


def no_agent_client() -> NoReturn:
    raise AssertionError("This tool-only workflow must not create an agent client.")


workflow_factory = WorkflowFactory(
    configuration={"ORDER_PREFIX": "Local"},
    restrict_env_to_configuration=True,
)
workflow_factory.register_tool("format_order", format_order)

app = AgentFunctionApp(
    client_factory=no_agent_client,
    discover_workflows=True,
    workflow_factory=workflow_factory,
)
