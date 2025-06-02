# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""A2A Client - for calling other A2A compliant agents."""

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx

from ..types import TaskState


class A2AClient:
    """
    Client for interacting with other A2A compliant agents.

    Provides methods to:
    - Discover agent capabilities
    - Send tasks to other agents
    - Monitor task status
    - Cancel tasks
    """

    def __init__(self, timeout: int = 30):
        """
        Initialize the A2A client.

        Args:
            timeout: HTTP request timeout in seconds
        """
        self.timeout = timeout
        self.logger = logging.getLogger("A2AClient")
        self._http_client = httpx.AsyncClient(timeout=timeout)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the HTTP client."""
        await self._http_client.aclose()

    async def discover_agent(self, agent_url: str) -> Optional[Dict[str, Any]]:
        """
        Discover an agent's capabilities by fetching its agent card.

        Args:
            agent_url: Base URL of the agent (e.g., https://agent.example.com/api)

        Returns:
            Agent card dictionary if successful, None otherwise
        """
        try:
            # Construct the well-known agent metadata URL
            metadata_url = f"{agent_url.rstrip('/')}/.well-known/agent.json"

            self.logger.info(f"Discovering agent at {metadata_url}")

            response = await self._http_client.get(metadata_url)
            response.raise_for_status()

            agent_card = response.json()
            self.logger.info(f"Discovered agent: {agent_card.get('name', 'Unknown')}")

            return agent_card

        except Exception as e:
            self.logger.error(f"Failed to discover agent at {agent_url}: {e}")
            return None

    async def send_task(
        self, agent_url: str, task_data: Dict[str, Any], subscribe: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Send a task to another agent.

        Args:
            agent_url: Base URL of the target agent
            task_data: Task input data
            subscribe: Whether to subscribe to task updates

        Returns:
            Task response dictionary if successful, None otherwise
        """
        try:
            # Construct the task endpoint URL
            endpoint = "tasks/subscribe" if subscribe else "tasks"
            task_url = f"{agent_url.rstrip('/')}/{endpoint}"

            self.logger.info(f"Sending task to {task_url}")

            response = await self._http_client.post(
                task_url, json=task_data, headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()

            task_response = response.json()
            task_id = task_response.get("taskId")

            self.logger.info(f"Task sent successfully, ID: {task_id}")
            return task_response

        except Exception as e:
            self.logger.error(f"Failed to send task to {agent_url}: {e}")
            return None

    async def get_task_status(
        self, agent_url: str, task_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get the status of a task on another agent.

        Args:
            agent_url: Base URL of the target agent
            task_id: ID of the task to check

        Returns:
            Task status dictionary if successful, None otherwise
        """
        try:
            # Construct the task status URL
            status_url = f"{agent_url.rstrip('/')}/tasks/{task_id}"

            self.logger.debug(f"Checking task status at {status_url}")

            response = await self._http_client.get(status_url)
            response.raise_for_status()

            task_status = response.json()
            return task_status

        except Exception as e:
            self.logger.error(f"Failed to get task status from {agent_url}: {e}")
            return None

    async def cancel_task(self, agent_url: str, task_id: str) -> bool:
        """
        Cancel a task on another agent.

        Args:
            agent_url: Base URL of the target agent
            task_id: ID of the task to cancel

        Returns:
            True if cancellation was successful, False otherwise
        """
        try:
            # Construct the task cancellation URL
            cancel_url = f"{agent_url.rstrip('/')}/tasks/{task_id}/cancel"

            self.logger.info(f"Cancelling task at {cancel_url}")

            response = await self._http_client.post(cancel_url)
            response.raise_for_status()

            self.logger.info(f"Task {task_id} cancelled successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to cancel task {task_id} on {agent_url}: {e}")
            return False

    async def wait_for_task_completion(
        self,
        agent_url: str,
        task_id: str,
        max_wait_time: int = 300,
        poll_interval: int = 5,
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for a task to complete by polling its status.

        Args:
            agent_url: Base URL of the target agent
            task_id: ID of the task to wait for
            max_wait_time: Maximum time to wait in seconds
            poll_interval: How often to poll in seconds

        Returns:
            Final task status if completed, None if timeout or error
        """
        start_time = datetime.now(timezone.utc)
        max_duration = timedelta(seconds=max_wait_time)

        self.logger.info(
            f"Waiting for task {task_id} to complete (max {max_wait_time}s)"
        )

        while (datetime.now(timezone.utc) - start_time) < max_duration:
            task_status = await self.get_task_status(agent_url, task_id)

            if not task_status:
                self.logger.error(f"Failed to get task status for {task_id}")
                return None

            state = task_status.get("state")

            if state in ["completed", "failed", "cancelled"]:
                self.logger.info(f"Task {task_id} finished with state: {state}")
                return task_status

            # Wait before next poll
            await asyncio.sleep(poll_interval)

        self.logger.warning(
            f"Task {task_id} did not complete within {max_wait_time} seconds"
        )
        return None

    async def delegate_task(
        self,
        agent_url: str,
        task_data: Dict[str, Any],
        wait_for_completion: bool = True,
        max_wait_time: int = 300,
    ) -> Optional[Dict[str, Any]]:
        """
        Delegate a task to another agent and optionally wait for completion.

        Args:
            agent_url: Base URL of the target agent
            task_data: Task input data
            wait_for_completion: Whether to wait for the task to complete
            max_wait_time: Maximum time to wait for completion

        Returns:
            Task result if successful, None otherwise
        """
        # First, send the task
        task_response = await self.send_task(agent_url, task_data)

        if not task_response:
            return None

        task_id = task_response.get("taskId")
        if not task_id:
            self.logger.error("No task ID in response")
            return task_response

        # If we don't need to wait, return the initial response
        if not wait_for_completion:
            return task_response

        # Wait for completion
        final_status = await self.wait_for_task_completion(
            agent_url, task_id, max_wait_time
        )

        return final_status or task_response
