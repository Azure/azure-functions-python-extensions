"""Publish YAML workflows with a private Markdown adapter for agent actions."""

from azurefunctions.agents.extensions.agent_framework import AgentFunctionApp

from local_chat_client import LocalChatClient

app = AgentFunctionApp(
    client_factory=LocalChatClient,
    discover_workflows=True,
)
