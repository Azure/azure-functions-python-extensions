"""Discover Markdown agents and YAML workflows without handwritten handlers."""

from azurefunctions.agents.extensions.agent_framework import AgentFunctionApp

from local_chat_client import LocalChatClient

app = AgentFunctionApp(
    client_factory=LocalChatClient,
    durable=True,
    workflows=True,
)
