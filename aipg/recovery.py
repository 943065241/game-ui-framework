from __future__ import annotations

from typing import Any, Mapping

from .capabilities import (
    CapabilityRequirement,
    ToolExecutionPolicy,
    ToolRegistry,
)
from .engine import WorkflowEngine, WorkflowRun
from .runtime import WorkflowFrame, WorkflowNode, WorkflowStack, WorkflowStatus


class RecoverableWorkflowEngine(WorkflowEngine):
    """Workflow engine with resumable graph cursors and capability execution."""

    def __init__(self, *args: Any, tool_registry: ToolRegistry | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.tool_registry = tool_registry or ToolRegistry()

    def execute_capability(
        self,
        run_id: str,
        requirement: CapabilityRequirement,
        arguments: Mapping[str, Any] | None = None,
        policy: ToolExecutionPolicy | None = None,
    ) -> Mapping[str, Any]:
        run = self.get_run(run_id)
        if run.status is not WorkflowStatus.RUNNING:
            raise RuntimeError("Workflow must be running before executing capabilities")
        self._transition(run, WorkflowStatus.WAITING_FOR_TOOL)
        self._emit(
            run,
            "capability.started",
            {"capability_id": requirement.capability_id},
        )
        try:
            execution = self.tool_registry.execute(requirement, arguments, policy)
        except Exception as exc:
            self.fail(run_id, exc)
            raise
        result = dict(execution.output)
        self._transition(run, WorkflowStatus.RUNNING)
        run.frame.local_context.update(result)
        self._checkpoint(run, f"capability:{requirement.capability_id}")
        self._emit(
            run,
            "capability.completed",
            {
                "capability_id": requirement.capability_id,
                "adapter_id": execution.adapter_id,
                "provider": execution.provider,
                "attempts": execution.attempts,
                "duration_seconds": execution.duration_seconds,
                "result": result,
            },
        )
        return result

    def restore_run(self, run_id: str) -> WorkflowRun:
        checkpoint = self.checkpoint_store.latest(run_id)
        if checkpoint is None:
            raise ValueError(f"No checkpoint found for workflow run: {run_id}")
        workflow_id = str(checkpoint["root_workflow_id"])
        definition = self._definition(workflow_id)
        frames = []
        for item in checkpoint["frames"]:
            frames.append(
                WorkflowFrame(
                    workflow_id=str(item["workflow_id"]),
                    current_node_id=str(item["current_node_id"]),
                    status=WorkflowStatus(str(item["status"])),
                    local_context=dict(item.get("local_context", {})),
                    child_result=item.get("child_result"),
                    retry_count=int(item.get("retry_count", 0)),
                    checkpoints=[],
                )
            )
        stack = WorkflowStack(max_depth=definition.max_depth, frames=frames)
        run = WorkflowRun(
            run_id=run_id,
            definition=definition,
            stack=stack,
            inputs=dict(checkpoint.get("inputs", {})),
            outputs=dict(checkpoint.get("outputs", {})),
            error=checkpoint.get("error"),
        )
        self._runs[run_id] = run
        self._emit(run, "workflow.restored", {"reason": checkpoint.get("reason")})
        return run

    def _execute_node(self, run: WorkflowRun, definition: Any, node: WorkflowNode) -> None:
        completed = set(run.frame.local_context.get("_completed_node_ids", ()))
        cursor_key = f"{run.frame.workflow_id}:{node.node_id}"
        if cursor_key in completed:
            self._emit(run, "node.skipped", {"node_id": node.node_id, "reason": "checkpoint"})
            return
        super()._execute_node(run, definition, node)
        completed = set(run.frame.local_context.get("_completed_node_ids", ()))
        completed.add(cursor_key)
        run.frame.local_context["_completed_node_ids"] = sorted(completed)
        self._checkpoint(run, f"node:{cursor_key}")

    def _checkpoint(self, run: WorkflowRun, reason: str) -> None:
        checkpoint = {
            "schema_version": 2,
            "reason": reason,
            "root_workflow_id": run.definition.workflow_id,
            "inputs": dict(run.inputs),
            "outputs": dict(run.outputs),
            "error": run.error,
            "frames": [
                {
                    "workflow_id": frame.workflow_id,
                    "current_node_id": frame.current_node_id,
                    "status": frame.status.value,
                    "retry_count": frame.retry_count,
                    "local_context": dict(frame.local_context),
                    "child_result": frame.child_result,
                }
                for frame in run.stack.frames
            ],
        }
        run.frame.checkpoints.append(checkpoint)
        self.checkpoint_store.save(run.run_id, checkpoint)
