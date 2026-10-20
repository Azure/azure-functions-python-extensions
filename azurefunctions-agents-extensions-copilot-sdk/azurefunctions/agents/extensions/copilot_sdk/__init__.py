from azurefunctions.agents.extensions.base.durable import DurableAgentContext

from .apps import AgentFunctionApp
from .provider import COPILOT_SDK_PROVIDER_ID, ClientFactory

__all__ = [
    "COPILOT_SDK_PROVIDER_ID",
    "AgentFunctionApp",
    "ClientFactory",
    "DurableAgentContext",
]

__version__ = "1.0.0b1"
