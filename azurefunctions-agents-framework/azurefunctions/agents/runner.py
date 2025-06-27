import asyncio
from typing import Any, Dict, Union

from .types import MessageRequest

# Type alias for request data
Request = Union[str, Dict[str, Any], MessageRequest]

class Runner:
    """
    Simple runner to execute an Agent with a given request.
    Supports both async and sync execution, and flexible input types.
    """
    def __init__(self, agent):
        self.agent = agent

    async def run(self, request: Request) -> Dict[str, Any]:
        """
        Run the agent with the provided request.
        Accepts either a string (user message), a full request dict, or a MessageRequest object.
        """
        if isinstance(request, str):
            request_data = {"message": request}
        elif isinstance(request, MessageRequest):
            request_data = request.to_dict()
        elif isinstance(request, dict):
            request_data = request
        else:
            raise ValueError("Request must be a string, dict, or MessageRequest object.")
        return await self.agent.process_request(request_data)

    def run_sync(self, request: Request) -> Dict[str, Any]:
        """
        Synchronous version of run().
        """
        try:
            # Try to get the existing event loop
            loop = asyncio.get_running_loop()
            # If there's already a running loop, we need to use a different approach
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.run(request))
                return future.result()
        except RuntimeError:
            # No running event loop, we can create a new one
            return asyncio.run(self.run(request))
