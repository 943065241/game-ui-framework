from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


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


@dataclass
class Task:
    project: str
    requirement: str
    pipeline: str
    context: Any
    task_id: str = field(default_factory=lambda: f"task-{uuid4().hex[:12]}")
    state: dict[str, Any] = field(default_factory=dict)
    outputs: list[dict[str, Any]] = field(default_factory=list)
    events: list[TaskEvent] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    completed_at: str | None = None

    def record(self, agent: str, status: str, message: str) -> None:
        self.events.append(TaskEvent(agent=agent, status=status, message=message))

    def add_output(self, output_type: str, value: Any, *, agent: str) -> None:
        self.outputs.append({"type": output_type, "value": value, "agent": agent})

    def complete(self) -> None:
        self.completed_at = _now()

    def to_dict(self) -> dict[str, Any]:
        context = self.context.to_dict() if hasattr(self.context, "to_dict") else self.context
        return {
            "schema_version": 1,
            "task_id": self.task_id,
            "project": self.project,
            "requirement": self.requirement,
            "pipeline": self.pipeline,
            "context": context,
            "state": self.state,
            "outputs": self.outputs,
            "events": [event.to_dict() for event in self.events],
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }
