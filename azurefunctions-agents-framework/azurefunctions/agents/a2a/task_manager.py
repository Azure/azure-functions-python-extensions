# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""A2A Task Manager - handles task lifecycle and execution."""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from ..types import Task, TaskState


class A2ATask:
    """Represents an A2A task with SDK types."""

    def __init__(self, task_id: str, input_data: Dict[str, Any]):
        """Initialize an A2A task."""
        self.id = task_id
        self.state = TaskState.PENDING
        self.input = input_data
        self.output: Optional[Dict[str, Any]] = None
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
        self.error: Optional[str] = None

    def update_state(
        self,
        new_state: TaskState,
        output: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ):
        """Update the task state and metadata."""
        self.state = new_state
        self.updated_at = datetime.now(timezone.utc)

        if output is not None:
            self.output = output

        if error is not None:
            self.error = error


class A2ATaskManager:
    """
    Manages A2A tasks for an agent.

    Handles task creation, execution, status tracking, and cancellation.
    """

    def __init__(self):
        """Initialize the task manager."""
        self.tasks: Dict[str, A2ATask] = {}
        self.logger = logging.getLogger("A2ATaskManager")

    async def create_task(self, input_data: Dict[str, Any], agent_app) -> A2ATask:
        """
        Create a new A2A task.

        Args:
            input_data: Input data for the task
            agent_app: The agent application instance

        Returns:
            Created A2ATask instance
        """
        task_id = str(uuid.uuid4())
        task = A2ATask(task_id, input_data)
        self.tasks[task_id] = task

        self.logger.info(f"Created task {task_id}")
        return task

    async def execute_task(self, task_id: str, agent_app) -> bool:
        """
        Execute an A2A task.

        Args:
            task_id: ID of the task to execute
            agent_app: The agent application instance

        Returns:
            True if execution started successfully, False otherwise
        """
        task = self.tasks.get(task_id)
        if not task:
            self.logger.error(f"Task {task_id} not found")
            return False

        if task.state != TaskState.PENDING:
            self.logger.warning(f"Task {task_id} is not in pending state")
            return False

        # Update task state to running
        task.update_state(TaskState.RUNNING)

        try:
            # Execute the task in the background
            asyncio.create_task(self._execute_task_async(task, agent_app))
            return True

        except Exception as e:
            self.logger.error(f"Failed to start task execution for {task_id}: {e}")
            task.update_state(TaskState.FAILED, error=str(e))
            return False

    async def _execute_task_async(self, task: A2ATask, agent_app):
        """Execute the task asynchronously."""
        try:
            self.logger.info(f"Executing task {task.id}")

            # Process the task using the agent
            result = await agent_app._process_agent_request(task.input)

            # Update task with successful result
            task.update_state(TaskState.COMPLETED, output=result)
            self.logger.info(f"Task {task.id} completed successfully")

        except Exception as e:
            self.logger.error(f"Task {task.id} execution failed: {e}")
            task.update_state(TaskState.FAILED, error=str(e))

    def get_task(self, task_id: str) -> Optional[A2ATask]:
        """
        Get a task by ID.

        Args:
            task_id: ID of the task to retrieve

        Returns:
            A2ATask instance if found, None otherwise
        """
        return self.tasks.get(task_id)

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task.

        Args:
            task_id: ID of the task to cancel

        Returns:
            True if task was cancelled, False otherwise
        """
        task = self.tasks.get(task_id)
        if not task:
            self.logger.error(f"Task {task_id} not found")
            return False

        if task.state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED]:
            self.logger.warning(
                f"Task {task_id} is already in final state: {task.state}"
            )
            return False

        # Update task state to cancelled
        task.update_state(TaskState.CANCELLED)
        self.logger.info(f"Task {task_id} cancelled")
        return True

    def list_tasks(self, limit: Optional[int] = None) -> list[A2ATask]:
        """
        List all tasks.

        Args:
            limit: Optional limit on number of tasks to return

        Returns:
            List of A2ATask instances
        """
        tasks = list(self.tasks.values())

        # Sort by creation time (newest first)
        tasks.sort(key=lambda t: t.created_at, reverse=True)

        if limit:
            tasks = tasks[:limit]

        return tasks

    def get_task_stats(self) -> Dict[str, int]:
        """
        Get statistics about tasks.

        Returns:
            Dictionary with task counts by state
        """
        stats = {
            "total": len(self.tasks),
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
        }

        for task in self.tasks.values():
            if task.state == TaskState.PENDING:
                stats["pending"] += 1
            elif task.state == TaskState.RUNNING:
                stats["running"] += 1
            elif task.state == TaskState.COMPLETED:
                stats["completed"] += 1
            elif task.state == TaskState.FAILED:
                stats["failed"] += 1
            elif task.state == TaskState.CANCELLED:
                stats["cancelled"] += 1

        return stats

    def cleanup_completed_tasks(self, max_age_hours: int = 24):
        """
        Clean up completed tasks older than specified age.

        Args:
            max_age_hours: Maximum age in hours for completed tasks
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

        tasks_to_remove = []
        for task_id, task in self.tasks.items():
            if (
                task.state
                in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED]
                and task.updated_at < cutoff_time
            ):
                tasks_to_remove.append(task_id)

        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            self.logger.info(f"Cleaned up old task {task_id}")

        if tasks_to_remove:
            self.logger.info(f"Cleaned up {len(tasks_to_remove)} old tasks")
