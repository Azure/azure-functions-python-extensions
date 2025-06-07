"""HTTP agent caller implementation."""

import json
import logging
from typing import Any, Dict, Union
import aiohttp
import azure.functions as func
import azure.durable_functions as df

from .base import BaseAgentCaller
from ..types import AgentCallResponse


logger = logging.getLogger(__name__)


class HttpAgentCaller(BaseAgentCaller):
    """Agent caller for HTTP endpoints."""
    def register_activities(self) -> None:
        """Register HTTP activity function."""
        activity_name = self.get_activity_name("default")
        
        @self.app.activity_trigger(arg_name="req", activity_name=activity_name)
        async def http_activity(req: str) -> str:
            """Activity function for HTTP agent calls."""
            try:
                request_data = json.loads(req)
                response = await self._make_http_call(
                    request_data["method"],
                    request_data.get("args", {}),
                    request_data.get("kwargs", {})
                )
                return json.dumps(response.__dict__)
            except Exception as e:
                error_response = AgentCallResponse.error_response(str(e))
                return json.dumps(error_response.__dict__)
                
    def get_activity_name(self, method: str) -> str:
        """Get the activity name for HTTP calls."""
        return f"call_http_agent_{self.config.name}"
        
    def call_agent(self, context: df.DurableOrchestrationContext, method: str,
                        args: Dict[str, Any] = None, kwargs: Dict[str, Any] = None) -> Any:
        """Call the HTTP agent using the orchestrator context.
        
        Args:
            context: Durable orchestrator context (required)
            method: The method to call on the agent
            args: Positional arguments for the method
            kwargs: Keyword arguments for the method
            
        Returns:
            Result from the HTTP agent call
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
        return context.call_activity(activity_name, json.dumps(request_data))
    
    async def _make_http_call(self, method: str, args: Dict[str, Any], kwargs: Dict[str, Any]) -> AgentCallResponse:
        """Make the actual HTTP call."""
        try:
            headers = {}
            if self.config.auth_token:
                headers["Authorization"] = f"Bearer {self.config.auth_token}"
            
            payload = {
                "method": method,
                "args": args,
                "kwargs": kwargs
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.config.endpoint,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return AgentCallResponse.success_response(result)
                    else:
                        error_text = await response.text()
                        return AgentCallResponse.error_response(f"HTTP {response.status}: {error_text}")
        
        except aiohttp.ClientTimeout:
            return AgentCallResponse.error_response("Request timeout")
        except aiohttp.ClientError as e:
            return AgentCallResponse.error_response(f"HTTP client error: {str(e)}")
        except Exception as e:
            logger.exception(f"Unexpected error calling HTTP agent {self.config.name}")
            return AgentCallResponse.error_response(f"Unexpected error: {str(e)}")
