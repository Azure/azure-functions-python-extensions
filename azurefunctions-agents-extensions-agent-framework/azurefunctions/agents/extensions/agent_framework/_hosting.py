"""Narrow endpoint policy adapter for the pinned DAFX Functions host."""

import azure.functions as func
from agent_framework import Workflow
from agent_framework_azurefunctions import AgentFunctionApp


class HostedAgentFunctionApp(AgentFunctionApp):
    """Keep registration separate from generated HTTP exposure.

    DAFX currently registers workflow routes unconditionally. This single
    override is coupled to the pinned SDK 2 migration, not its execution engine.
    """

    def __init__(
        self, *, workflows: list[Workflow], exposed_workflows: set[str],
        http_auth_level: func.AuthLevel,
    ) -> None:
        self._exposed_workflows = exposed_workflows
        super().__init__(
            workflows=workflows, http_auth_level=http_auth_level,
            enable_health_check=False, enable_http_endpoints=False,
            enable_mcp_tool_trigger=False,
        )

    def _register_workflow_routes(self, workflow: Workflow) -> None:
        if workflow.name in self._exposed_workflows:
            super()._register_workflow_routes(workflow)
