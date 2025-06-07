"""Base interface for agent callers."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Union, Optional
from azure.functions import FunctionApp
import azure.durable_functions as df

from ..types import AgentConfig, AgentCallResponse


class BaseAgentCaller(ABC):
    """Base class for all agent callers."""
    
    def __init__(self, config: AgentConfig, app: Union[FunctionApp, df.DFApp]):
        self.config = config
        self.app = app    @abstractmethod
    def call_agent(self, context: df.DurableOrchestrationContext, method: str, 
                        args: Dict[str, Any] = None, kwargs: Dict[str, Any] = None) -> Any:
        """Call the agent with the specified method and parameters.
        
        Args:
            context: Durable orchestrator context (required for this framework)
            method: The method to call on the agent
            args: Positional arguments for the method
            kwargs: Keyword arguments for the method
            
        Returns:
            Result from the agent call through the activity pattern
        """
        pass
    
    @abstractmethod
    def register_activities(self) -> None:
        """Register any required activity functions for this caller."""
        pass
    
    def get_activity_name(self, method: str) -> str:
        """Get the activity name for a specific method. Override in subclasses if needed."""
        # Default pattern: call_{call_mode}_{agent_name}
        call_mode = self.config.call_mode.value.lower()
        return f"call_{call_mode}_agent_{self.config.name}"