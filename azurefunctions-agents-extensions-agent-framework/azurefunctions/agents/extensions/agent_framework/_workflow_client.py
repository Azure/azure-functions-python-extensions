"""Orchestration-only invocation of a registered DAFX workflow."""

from typing import Any

from azure.durable_functions import DurableOrchestrationContext
from agent_framework_durabletask import deserialize_workflow_output
from agent_framework_durabletask._workflows.serialization import (
    strip_pickle_markers, strip_subworkflow_markers,
)
from durabletask.task import CompletableTask, CompositeTask, OrchestrationContext, Task


class WorkflowTask(CompositeTask[Any], CompletableTask[Any]):
    """Decode only the trusted child orchestration result into MAF outputs."""

    def on_child_completed(self, task: Task[Any]) -> None:
        if self.is_complete:
            return
        if task.is_failed:
            self.fail("Workflow child orchestration failed", task.get_exception())
        else:
            try:
                self.complete(deserialize_workflow_output(task.get_result()))
            except Exception as error:
                self.fail("Workflow output decoding failed", error)


class DurableWorkflow:
    """A workflow handle bound to the calling durable orchestration context.

    run() returns a yieldable task. It never calls Workflow.run() in-process.
    Each invocation starts a child workflow with its own workflow state.
    """

    def __init__(
        self, context: OrchestrationContext | DurableOrchestrationContext,
        workflow_name: str,
    ) -> None:
        self._context = context
        self.name = workflow_name

    def run(
        self, input_: Any = None, *, instance_id: str | None = None,
    ) -> WorkflowTask:
        # Match DAFX's public workflow-entry trust boundary. Parent input may
        # originate in an HTTP request; it is not an internal checkpoint envelope.
        input_ = strip_subworkflow_markers(strip_pickle_markers(input_))
        # The native SDK takes keyword-only input; the Functions compatibility
        # context exposes input_ instead. Neither path runs a local Workflow.
        if isinstance(self._context, DurableOrchestrationContext):
            child = self._context.call_sub_orchestrator(
                f"dafx-{self.name}", input_=input_, instance_id=instance_id,
            )
        else:
            child = self._context.call_sub_orchestrator(
                f"dafx-{self.name}", input=input_, instance_id=instance_id,
            )
        return WorkflowTask([child])
