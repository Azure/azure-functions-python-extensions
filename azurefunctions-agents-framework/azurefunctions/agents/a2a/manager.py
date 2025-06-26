# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""A2A Manager - handles A2A protocol endpoints and capabilities for the agent."""

import json
import logging
import os
from typing import Any, Dict, Optional

from azure.functions import AuthLevel, HttpRequest, HttpResponse

from ..types import AgentCapabilities, AgentCard, AgentProvider, AgentSkill
from .task_manager import A2ATaskManager


class A2AManager:
    """
    Manages A2A protocol compliance for an agent.

    Handles:
    - Agent metadata exposure (/.well-known/agent.json)
    - Task management endpoints
    - A2A protocol compliance
    """

    def __init__(self, agent_app):
        """
        Initialize the A2A manager.

        Args:
            agent_app: The parent AgentFunctionApp instance
        """
        self.agent_app = agent_app
        # Get the single agent (A2A mode only supports single agent)
        self.agent = next(iter(agent_app.agents.values()))
        self.logger = logging.getLogger(f"A2AManager.{self.agent.name}")
        self.task_manager = A2ATaskManager()
        self.agent_card = self._create_agent_card()

        # Register A2A endpoints
        self._register_a2a_endpoints()

    def _create_agent_card(self):
        """Create an AgentCard for A2A protocol using SDK types."""
        # Determine the base URL (this would typically come from environment or configuration)
        base_url = os.getenv(
            "AGENT_BASE_URL", "https://your-function-app.azurewebsites.net/api"
        )

        # Convert tools to skills format using SDK AgentSkill
        skills = []
        for tool_name in self.agent.tool_registry.list_all_tools():
            tool_info = self.agent.tool_registry.get_tool_info(tool_name)
            if tool_info:
                skill = AgentSkill(
                    id=tool_info["name"],
                    name=tool_info["name"],
                    description=tool_info["description"],
                    inputModes=["text"],
                    outputModes=["text"],
                    tags=["function", "tool"],
                    examples=[],
                )
                skills.append(skill)

        # Create capabilities using SDK AgentCapabilities model
        capabilities = AgentCapabilities(
            pushNotifications=False, stateTransitionHistory=True, streaming=False
        )

        # Create provider using SDK AgentProvider model
        provider = AgentProvider(
            organization="Azure Functions Agent Framework",
            url="https://github.com/microsoft/azfunctions-agents-framework",
        )

        # Create the AgentCard using SDK structure
        return AgentCard(
            name=self.agent.name,
            description=self.agent.description,
            version=self.agent.version,
            url=f"{base_url}/.well-known/agent.json",
            documentationUrl=None,
            provider=provider,
            capabilities=capabilities,
            defaultInputModes=["text"],
            defaultOutputModes=["text"],
            skills=skills,
            security=[],
            securitySchemes={},
            supportsAuthenticatedExtendedCard=False,
        )

    def _register_a2a_endpoints(self):
        """Register A2A protocol endpoints."""

        # Agent metadata endpoint (/.well-known/agent.json)
        @self.agent_app.route(
            route=".well-known/agent.json",
            auth_level=AuthLevel.ANONYMOUS,
            methods=["GET"],
        )
        async def agent_metadata(req: HttpRequest) -> HttpResponse:
            """Return agent metadata in A2A format."""
            try:
                return HttpResponse(
                    self.agent_card.model_dump_json(indent=2),
                    status_code=200,
                    headers={"Content-Type": "application/json"},
                )
            except Exception as e:
                self.logger.error(f"Error serving agent metadata: {e}")
                return HttpResponse(
                    json.dumps({"error": "Failed to retrieve agent metadata"}),
                    status_code=500,
                    headers={"Content-Type": "application/json"},
                )

        # Task endpoints
        @self.agent_app.route(
            route="tasks", auth_level=self.agent_app._auth_level, methods=["POST"]
        )
        async def send_task(req: HttpRequest) -> HttpResponse:
            """Send a task to this agent (A2A protocol)."""
            return await self._handle_a2a_task_send(req, subscribe=False)

        @self.agent_app.route(
            route="tasks/subscribe",
            auth_level=self.agent_app._auth_level,
            methods=["POST"],
        )
        async def subscribe_task(req: HttpRequest) -> HttpResponse:
            """Subscribe to a task on this agent (A2A protocol)."""
            return await self._handle_a2a_task_send(req, subscribe=True)

        @self.agent_app.route(
            route="tasks/{task_id}",
            auth_level=self.agent_app._auth_level,
            methods=["GET"],
        )
        async def get_task(req: HttpRequest) -> HttpResponse:
            """Get task status (A2A protocol)."""
            return await self._handle_a2a_task_get(req)

        @self.agent_app.route(
            route="tasks/{task_id}/cancel",
            auth_level=self.agent_app._auth_level,
            methods=["POST"],
        )
        async def cancel_task(req: HttpRequest) -> HttpResponse:
            """Cancel a task (A2A protocol)."""
            return await self._handle_a2a_task_cancel(req)

    async def _handle_a2a_task_send(
        self, req: HttpRequest, subscribe: bool = False
    ) -> HttpResponse:
        """Handle A2A task send/subscribe requests."""
        try:
            # Parse request body
            try:
                request_data = req.get_json() or {}
            except ValueError:
                return HttpResponse(
                    json.dumps({"error": "Invalid JSON in request body"}),
                    status_code=400,
                    headers={"Content-Type": "application/json"},
                )

            # Create and execute task
            task = await self.task_manager.create_task(
                input_data=request_data, agent_app=self.agent_app
            )

            # Execute the task
            await self.task_manager.execute_task(task.id, self.agent_app)

            # Return task response
            response_data = {
                "taskId": task.id,
                "state": task.state.value,
                "input": task.input,
                "output": task.output,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
            }

            if task.error:
                response_data["error"] = task.error

            return HttpResponse(
                json.dumps(response_data, indent=2),
                status_code=200,
                headers={"Content-Type": "application/json"},
            )

        except Exception as e:
            self.logger.error(f"A2A task send failed: {e}")
            return HttpResponse(
                json.dumps({"error": f"Task execution failed: {str(e)}"}),
                status_code=500,
                headers={"Content-Type": "application/json"},
            )

    async def _handle_a2a_task_get(self, req: HttpRequest) -> HttpResponse:
        """Handle A2A task status requests."""
        try:
            task_id = req.route_params.get("task_id")
            if not task_id:
                return HttpResponse(
                    json.dumps({"error": "Task ID is required"}),
                    status_code=400,
                    headers={"Content-Type": "application/json"},
                )

            task = self.task_manager.get_task(task_id)
            if not task:
                return HttpResponse(
                    json.dumps({"error": "Task not found"}),
                    status_code=404,
                    headers={"Content-Type": "application/json"},
                )

            response_data = {
                "taskId": task.id,
                "state": task.state.value,
                "input": task.input,
                "output": task.output,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
            }

            if task.error:
                response_data["error"] = task.error

            return HttpResponse(
                json.dumps(response_data, indent=2),
                status_code=200,
                headers={"Content-Type": "application/json"},
            )

        except Exception as e:
            self.logger.error(f"A2A task get failed: {e}")
            return HttpResponse(
                json.dumps({"error": f"Failed to retrieve task: {str(e)}"}),
                status_code=500,
                headers={"Content-Type": "application/json"},
            )

    async def _handle_a2a_task_cancel(self, req: HttpRequest) -> HttpResponse:
        """Handle A2A task cancellation requests."""
        try:
            task_id = req.route_params.get("task_id")
            if not task_id:
                return HttpResponse(
                    json.dumps({"error": "Task ID is required"}),
                    status_code=400,
                    headers={"Content-Type": "application/json"},
                )

            success = await self.task_manager.cancel_task(task_id)
            if not success:
                return HttpResponse(
                    json.dumps({"error": "Task not found or cannot be cancelled"}),
                    status_code=404,
                    headers={"Content-Type": "application/json"},
                )

            task = self.task_manager.get_task(task_id)
            response_data = {
                "taskId": task.id,
                "state": task.state.value,
                "cancelled": True,
            }

            return HttpResponse(
                json.dumps(response_data, indent=2),
                status_code=200,
                headers={"Content-Type": "application/json"},
            )

        except Exception as e:
            self.logger.error(f"A2A task cancel failed: {e}")
            return HttpResponse(
                json.dumps({"error": f"Failed to cancel task: {str(e)}"}),
                status_code=500,
                headers={"Content-Type": "application/json"},
            )
