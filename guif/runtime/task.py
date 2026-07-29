from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

TASK_SCHEMA_VERSION = 3
SUPPORTED_TASK_SCHEMA_VERSIONS = {2, 3}
TASK_STATUSES = (
    "pending",
    "running",
    "waiting-for-tool",
    "waiting-for-tool-result",
    "failed",
    "completed",
    "cancelled",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class TaskEvent:
    agent: str
    status: str
    message: str
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, str]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TaskEvent":
        return cls(
            agent=str(payload["agent"]),
            status=str(payload["status"]),
            message=str(payload["message"]),
            created_at=str(payload.get("created_at") or _now()),
        )


@dataclass
class Task:
    project: str
    requirement: str
    pipeline: str
    context: Any
    task_id: str = field(default_factory=lambda: f"task-{uuid4().hex[:12]}")
    status: str = "pending"
    current_agent: str | None = None
    next_agent_index: int = 0
    state: dict[str, Any] = field(default_factory=dict)
    outputs: list[dict[str, Any]] = field(default_factory=list)
    events: list[TaskEvent] = field(default_factory=list)
    error: dict[str, Any] | None = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    completed_at: str | None = None

    def _touch(self) -> None:
        self.updated_at = _now()

    def record(self, agent: str, status: str, message: str) -> None:
        self.events.append(TaskEvent(agent=agent, status=status, message=message))
        self._touch()

    def add_output(self, output_type: str, value: Any, *, agent: str) -> None:
        self.outputs.append({"type": output_type, "value": value, "agent": agent})
        self._touch()

    def start(self) -> None:
        self.status = "running"
        self.current_agent = None
        self.error = None
        self.completed_at = None
        self._touch()

    def begin_agent(self, agent: str, index: int) -> None:
        self.status = "running"
        self.current_agent = agent
        self.next_agent_index = index
        self.record(agent, "started", f"Executing agent in pipeline {self.pipeline}")

    def finish_agent(self, index: int) -> None:
        self.next_agent_index = index + 1
        self.current_agent = None
        self._touch()

    def fail(self, agent: str, exc: Exception) -> None:
        self.status = "failed"
        self.current_agent = agent
        self.error = {
            "agent": agent,
            "type": type(exc).__name__,
            "message": str(exc),
        }
        self.record(agent, "failed", str(exc))

    def wait_for_tool(self, message: str) -> None:
        self.status = "waiting-for-tool"
        self.current_agent = "tool-router"
        self.error = None
        self.record("tool-router", "waiting-for-tool", message)

    def wait_for_tool_result(self, message: str) -> None:
        self.status = "waiting-for-tool-result"
        self.current_agent = "tool-router"
        self.error = None
        self.record("tool-router", "waiting-for-tool-result", message)

    def restore_completed(self, message: str) -> None:
        self.status = "completed"
        self.current_agent = None
        self.error = None
        if self.completed_at is None:
            self.completed_at = _now()
        self.record("tool-router", "completed", message)

    def cancel(self, message: str) -> None:
        self.status = "cancelled"
        self.current_agent = None
        self.error = None
        self.record("runtime", "cancelled", message)

    def complete(self) -> None:
        self.status = "completed"
        self.current_agent = None
        self.error = None
        self.completed_at = _now()
        self._touch()

    def to_dict(self) -> dict[str, Any]:
        context = self.context.to_dict() if hasattr(self.context, "to_dict") else self.context
        return {
            "schema_version": TASK_SCHEMA_VERSION,
            "task_id": self.task_id,
            "project": self.project,
            "requirement": self.requirement,
            "pipeline": self.pipeline,
            "status": self.status,
            "current_agent": self.current_agent,
            "next_agent_index": self.next_agent_index,
            "context": context,
            "state": self.state,
            "outputs": self.outputs,
            "events": [event.to_dict() for event in self.events],
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Task":
        from guif.runtime.context import RuntimeContext

        schema_version = int(payload.get("schema_version", 2))
        if schema_version not in SUPPORTED_TASK_SCHEMA_VERSIONS:
            raise ValueError(f"Unsupported task schema_version: {schema_version}")
        context_payload = payload.get("context")
        context = (
            RuntimeContext.from_dict(context_payload)
            if isinstance(context_payload, dict) and "project_root" in context_payload
            else context_payload
        )
        completed_at = payload.get("completed_at")
        status = str(payload.get("status") or ("completed" if completed_at else "pending"))
        if status not in TASK_STATUSES:
            raise ValueError(f"Unsupported task status: {status}")
        return cls(
            project=str(payload["project"]),
            requirement=str(payload["requirement"]),
            pipeline=str(payload["pipeline"]),
            context=context,
            task_id=str(payload["task_id"]),
            status=status,
            current_agent=payload.get("current_agent"),
            next_agent_index=int(payload.get("next_agent_index", 0)),
            state=dict(payload.get("state", {})),
            outputs=list(payload.get("outputs", [])),
            events=[TaskEvent.from_dict(event) for event in payload.get("events", [])],
            error=payload.get("error"),
            created_at=str(payload.get("created_at") or _now()),
            updated_at=str(payload.get("updated_at") or payload.get("created_at") or _now()),
            completed_at=completed_at,
        )
