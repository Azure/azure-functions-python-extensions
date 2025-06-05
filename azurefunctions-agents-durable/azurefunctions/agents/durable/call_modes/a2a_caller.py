"""Agent-to-Agent (A2A) caller implementations."""

import json
import logging
from typing import Any, Dict, Optional, Union
import azure.functions as func
import azure.durable_functions as df
from azure.durable_functions import DurableOrchestrationClient

from .base import BaseAgentCaller
from ..types import AgentCallResponse


logger = logging.getLogger(__name__)


class A2ATaskAgentCaller(BaseAgentCaller):
    """Agent caller for task-based A2A communication."""
    def register_activities(self) -> None:
        """Register A2A task activity function."""
        activity_name = self.get_activity_name("default")
        
        @self.app.activity_trigger(arg_name="req", activity_name=activity_name)
        async def a2a_task_activity(req: str) -> str:
            """Activity function for A2A task agent calls."""
            try:
                request_data = json.loads(req)
                response = await self._execute_a2a_task_call(
                    request_data["method"],
                    request_data.get("args", {}),
                    request_data.get("kwargs", {})
                )
                return json.dumps(response.__dict__)
            except Exception as e:
                logger.exception(f"Error in A2A task activity for {self.config.name}")
                error_response = AgentCallResponse.error_response(str(e))
                return json.dumps(error_response.__dict__)
                
    def get_activity_name(self, method: str) -> str:
        """Get the activity name for A2A task calls."""
        return f"call_a2a_task_agent_{self.config.name}"
        
    async def call_agent(self, context: df.DurableOrchestrationContext, method: str, 
                        args: Dict[str, Any] = None, kwargs: Dict[str, Any] = None) -> Any:
        """Call the A2A task agent using the orchestrator context.
        
        Args:
            context: Durable orchestrator context (required)
            method: The method to call on the agent
            args: Positional arguments for the method
            kwargs: Keyword arguments for the method  
            
        Returns:
            Result from the A2A task agent call
        """
        args = args or {}
        kwargs = kwargs or {}
        
        if context is None:
            raise ValueError("context parameter is required for durable orchestrator framework")
            
        # Use activity pattern with orchestrator context
        activity_name = self.get_activity_name("default")
        request_data = {
            "method": method,
            "args": args,
            "kwargs": kwargs
        }
        result = yield context.call_activity(activity_name, json.dumps(request_data))
        return json.loads(result)
    
    async def _execute_a2a_task_call(self, method: str, args: Dict[str, Any], kwargs: Dict[str, Any]) -> AgentCallResponse:
        """Execute A2A task call by starting a new orchestration."""
        try:
            # Extract orchestration function name from config
            extra_config = self.config.extra_config or {}
            orchestration_name = extra_config.get("orchestration_name", "agent_orchestrator")
            
            # Prepare the input for the target orchestration
            orchestration_input = {
                "method": method,
                "args": args,
                "kwargs": kwargs,
                "agent_name": self.config.name
            }
            
            # This would typically be called from an orchestrator context
            # For now, we'll simulate the call
            # In a real scenario, you'd use:
            # client = DurableOrchestrationClient(...)
            # instance_id = await client.start_new(orchestration_name, None, orchestration_input)
            # result = await client.wait_for_completion_or_create_check_status_response(instance_id, timeout_in_milliseconds=30000)
            
            # Simulated response for demonstration
            return AgentCallResponse.success_response({
                "message": f"A2A task call to {self.config.name}.{method} initiated",
                "orchestration_name": orchestration_name,
                "input": orchestration_input
            })
        
        except Exception as e:
            logger.exception(f"Error executing A2A task call for {self.config.name}")
            return AgentCallResponse.error_response(str(e))


class A2ASyncAgentCaller(BaseAgentCaller):
    """Agent caller for synchronous A2A communication."""
    def register_activities(self) -> None:
        """Register A2A sync activity function."""
        activity_name = self.get_activity_name("default")
        
        @self.app.activity_trigger(arg_name="req", activity_name=activity_name)
        async def a2a_sync_activity(req: str) -> str:
            """Activity function for A2A sync agent calls."""
            try:
                request_data = json.loads(req)
                response = await self._execute_a2a_sync_call(
                    request_data["method"],
                    request_data.get("args", {}),
                    request_data.get("kwargs", {})
                )
                return json.dumps(response.__dict__)
            except Exception as e:
                logger.exception(f"Error in A2A sync activity for {self.config.name}")
                error_response = AgentCallResponse.error_response(str(e))
                return json.dumps(error_response.__dict__)
                
    def get_activity_name(self, method: str) -> str:
        """Get the activity name for A2A sync calls."""
        return f"call_a2a_sync_agent_{self.config.name}"
        
    async def call_agent(self, context: df.DurableOrchestrationContext, method: str, 
                        args: Dict[str, Any] = None, kwargs: Dict[str, Any] = None) -> Any:
        """Call the A2A sync agent using the orchestrator context.
        
        Args:
            context: Durable orchestrator context (required)
            method: The method to call on the agent
            args: Positional arguments for the method
            kwargs: Keyword arguments for the method  
            
        Returns:
            Result from the A2A sync agent call
        """
        args = args or {}
        kwargs = kwargs or {}
        
        if context is None:
            raise ValueError("context parameter is required for durable orchestrator framework")
            
        # Use activity pattern with orchestrator context
        activity_name = self.get_activity_name("default")
        request_data = {
            "method": method,
            "args": args,
            "kwargs": kwargs
        }
        result = yield context.call_activity(activity_name, json.dumps(request_data))
        return json.loads(result)
    
    async def _execute_a2a_sync_call(self, method: str, args: Dict[str, Any], kwargs: Dict[str, Any]) -> AgentCallResponse:
        """Execute synchronous A2A call through sub-orchestration."""
        try:
            # Extract sub-orchestration details from config
            extra_config = self.config.extra_config or {}
            sub_orchestration_name = extra_config.get("sub_orchestration_name", "agent_sub_orchestrator")
            
            # Prepare the input for the sub-orchestration
            sub_orchestration_input = {
                "method": method,
                "args": args,
                "kwargs": kwargs,
                "agent_name": self.config.name
            }
            
            # This would typically be called from an orchestrator context using:
            # result = await context.call_sub_orchestrator(sub_orchestration_name, sub_orchestration_input)
            
            # Simulated response for demonstration
            return AgentCallResponse.success_response({
                "message": f"A2A sync call to {self.config.name}.{method} completed",
                "sub_orchestration_name": sub_orchestration_name,
                "input": sub_orchestration_input
            })
        
        except Exception as e:
            logger.exception(f"Error executing A2A sync call for {self.config.name}")
            return AgentCallResponse.error_response(str(e))
