"""Discover markdown agents and expose their DAFX endpoints without handlers."""

from azurefunctions.agents.extensions.agent_framework import AgentFunctionApp
from local_chat_client import LocalChatClient

app = AgentFunctionApp(client_factory=LocalChatClient, discover_agents=True)
