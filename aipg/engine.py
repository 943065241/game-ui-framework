from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping
from uuid import uuid4

from .events import EventBus, RuntimeEvent
from .runtime import WorkflowDefinition, WorkflowFrame, WorkflowStack, WorkflowStatus


ActionHandler = Callable[[WorkflowFrame, Mapping[str, Any]], Mapping[str, Any] | None]


_ALLOWED_TRANSITIONS: dict[WorkflowStatus, frozenset[WorkflowStatus]] = {
    WorkflowStatus.PENDING: frozenset({WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED}),
    WorkflowStatus.RUNNING: frozenset(
        {
            WorkflowStatus.WAITING_FOR_CHILD,
            WorkflowStatus.WAITING_FOR_TOOL,
            WorkflowStatus.WAITING_FOR_APPROVAL,
            WorkflowStatus.REVIEWING,
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        }
    ),
    WorkflowStatus.WAITING_FOR_CHILD: frozenset(
        {WorkflowStatus.RUNNING, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED}
    ),
    WorkflowStatus.WAITING_FOR_TOOL: frozenset(
        {WorkflowStatus.RUNNING, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED}
    ),
    WorkflowStatus.WAITING_FOR_APPROVAL: frozenset(
        {WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED}
    ),
    WorkflowStatus.REVIEWING: frozenset(
        {WorkflowStatus.REVISING, WorkflowStatus.COMPLETED, WorkflowStatus.FAILED}
    ),
    WorkflowStatus.REVISING: frozenset(
        {WorkflowStatus.RUNNING, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED}
    ),
    WorkflowStatus.FAILED: frozenset({WorkflowStatus.RUNNING, WorkflowStatus.CANCELLED}),
    WorkflowStatus.COMPLETED: frozenset(),
    WorkflowStatus.CANCELLED: frozenset(),
}


@dataclass
class WorkflowRun:
    run_id: str
    definition: WorkflowDefinition
    stack: WorkflowStack
    inputs: dict[str, Any] = field(default_factory=dict)
    outputs: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    @property
    def frame(self) -> WorkflowFrame:
        current = self.stack.current
        if current is None:
            raise RuntimeError("Workflow run has no active frame")
        return current

    @property
    def status(self) -> WorkflowStatus:
        return self.frame.status


class WorkflowEngine:
    """Domain-neutral workflow lifecycle engine.

    This first executable runtime deliberately owns lifecycle, retries,
    checkpoints and events, but does not embed provider or visual-domain logic.
    Domain packs bind actions through ``register_action``.
    """

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self.event_bus = event_bus or EventBus()
        self._definitions: dict[str, WorkflowDefinition] = {}
        self._actions: dict[str, ActionHandler] = {}
        self._runs: dict[str, WorkflowRun] = {}

    def register_workflow(self, definition: WorkflowDefinition) -> None:
        definition.validate()
        if definition.workflow_id in self._definitions:
            raise ValueError(f"Workflow already registered: {definition.workflow_id}")
        self._definitions[definition.workflow_id] = definition

    def register_action(self, action_id: str, handler: ActionHandler) -> None:
        if action_id in self._actions:
            raise ValueError(f"Action already registered: {action_id}")
        self._actions[action_id] = handler

    def create_run(
        self, workflow_id: str, inputs: Mapping[str, Any] | None = None
    ) -> WorkflowRun:
        try:
            definition = self._definitions[workflow_id]
        except KeyError as exc:
            raise ValueError(f"Unknown workflow: {workflow_id}") from exc

        supplied = dict(inputs or {})
        missing = [name for name in definition.inputs if name not in supplied]
        if missing:
            raise ValueError(f"Missing workflow inputs: {', '.join(missing)}")

        frame = WorkflowFrame(
            workflow_id=workflow_id,
            current_node_id=definition.root.node_id,
            local_context=dict(supplied),
        )
        stack = WorkflowStack(max_depth=definition.max_depth)
        stack.push(frame)
        run = WorkflowRun(
            run_id=uuid4().hex,
            definition=definition,
            stack=stack,
            inputs=supplied,
        )
        self._runs[run.run_id] = run
        self._emit(run, "workflow.created")
        return run

    def start(self, run_id: str) -> WorkflowRun:
        run = self.get_run(run_id)
        self._transition(run, WorkflowStatus.RUNNING)
        self._emit(run, "workflow.started")
        return run

    def pause(self, run_id: str, reason: str = "manual") -> WorkflowRun:
        run = self.get_run(run_id)
        self._transition(run, WorkflowStatus.WAITING_FOR_APPROVAL)
        run.frame.local_context["pause_reason"] = reason
        self._checkpoint(run, "pause")
        self._emit(run, "workflow.paused", {"reason": reason})
        return run

    def resume(self, run_id: str) -> WorkflowRun:
        run = self.get_run(run_id)
        self._transition(run, WorkflowStatus.RUNNING)
        run.frame.local_context.pop("pause_reason", None)
        self._emit(run, "workflow.resumed")
        return run

    def complete(
        self, run_id: str, outputs: Mapping[str, Any] | None = None
    ) -> WorkflowRun:
        run = self.get_run(run_id)
        supplied = dict(outputs or {})
        missing = [name for name in run.definition.outputs if name not in supplied]
        if missing:
            raise ValueError(f"Missing workflow outputs: {', '.join(missing)}")
        run.outputs = supplied
        self._transition(run, WorkflowStatus.COMPLETED)
        self._checkpoint(run, "complete")
        self._emit(run, "workflow.completed", {"outputs": supplied})
        return run

    def fail(self, run_id: str, error: Exception | str) -> WorkflowRun:
        run = self.get_run(run_id)
        run.error = str(error)
        self._transition(run, WorkflowStatus.FAILED)
        self._checkpoint(run, "failed")
        self._emit(run, "workflow.failed", {"error": run.error})
        return run

    def retry(self, run_id: str) -> WorkflowRun:
        run = self.get_run(run_id)
        if run.status is not WorkflowStatus.FAILED:
            raise RuntimeError("Only failed workflows can be retried")
        if run.frame.retry_count >= run.definition.max_retries:
            raise RuntimeError(
                f"Workflow retry limit reached: {run.definition.max_retries}"
            )
        run.frame.retry_count += 1
        run.error = None
        self._transition(run, WorkflowStatus.RUNNING)
        self._emit(run, "workflow.retried", {"retry_count": run.frame.retry_count})
        return run

    def cancel(self, run_id: str, reason: str = "manual") -> WorkflowRun:
        run = self.get_run(run_id)
        self._transition(run, WorkflowStatus.CANCELLED)
        run.error = reason
        self._checkpoint(run, "cancelled")
        self._emit(run, "workflow.cancelled", {"reason": reason})
        return run

    def execute_action(
        self,
        run_id: str,
        action_id: str,
        arguments: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        run = self.get_run(run_id)
        if run.status is not WorkflowStatus.RUNNING:
            raise RuntimeError("Workflow must be running before executing actions")
        try:
            handler = self._actions[action_id]
        except KeyError as exc:
            raise ValueError(f"Unknown action: {action_id}") from exc

        self._transition(run, WorkflowStatus.WAITING_FOR_TOOL)
        self._emit(run, "action.started", {"action_id": action_id})
        try:
            result = dict(handler(run.frame, dict(arguments or {})) or {})
        except Exception as exc:
            self.fail(run_id, exc)
            raise
        self._transition(run, WorkflowStatus.RUNNING)
        run.frame.local_context.update(result)
        self._checkpoint(run, f"action:{action_id}")
        self._emit(
            run,
            "action.completed",
            {"action_id": action_id, "result": result},
        )
        return result

    def get_run(self, run_id: str) -> WorkflowRun:
        try:
            return self._runs[run_id]
        except KeyError as exc:
            raise ValueError(f"Unknown workflow run: {run_id}") from exc

    def _transition(self, run: WorkflowRun, target: WorkflowStatus) -> None:
        current = run.status
        if target not in _ALLOWED_TRANSITIONS[current]:
            raise RuntimeError(f"Invalid workflow transition: {current} -> {target}")
        run.frame.status = target
        self._emit(
            run,
            "workflow.status_changed",
            {"from": current.value, "to": target.value},
        )

    def _checkpoint(self, run: WorkflowRun, reason: str) -> None:
        run.frame.checkpoints.append(
            {
                "reason": reason,
                "status": run.status.value,
                "current_node_id": run.frame.current_node_id,
                "retry_count": run.frame.retry_count,
                "local_context": dict(run.frame.local_context),
            }
        )

    def _emit(
        self,
        run: WorkflowRun,
        event_type: str,
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        self.event_bus.publish(
            RuntimeEvent(
                event_type=event_type,
                workflow_id=run.definition.workflow_id,
                run_id=run.run_id,
                payload=dict(payload or {}),
            )
        )
