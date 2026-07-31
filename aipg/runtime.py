from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

from .capabilities import CapabilityRequirement


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_CHILD = "waiting-for-child"
    WAITING_FOR_TOOL = "waiting-for-tool"
    WAITING_FOR_APPROVAL = "waiting-for-approval"
    REVIEWING = "reviewing"
    REVISING = "revising"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class NodeKind(str, Enum):
    SEQUENCE = "sequence"
    SELECTOR = "selector"
    PARALLEL = "parallel"
    CONDITION = "condition"
    SUBWORKFLOW = "subworkflow"
    ACTION = "action"
    APPROVAL = "approval"
    REVIEW = "review"


@dataclass(frozen=True)
class WorkflowNode:
    node_id: str
    kind: NodeKind
    children: tuple["WorkflowNode", ...] = ()
    workflow_id: str | None = None
    action_id: str | None = None
    condition: str | None = None
    policy: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.kind is NodeKind.SUBWORKFLOW and not self.workflow_id:
            raise ValueError(f"Subworkflow node requires workflow_id: {self.node_id}")
        if self.kind is NodeKind.ACTION and not self.action_id:
            raise ValueError(f"Action node requires action_id: {self.node_id}")
        if self.kind is NodeKind.CONDITION and not self.condition:
            raise ValueError(f"Condition node requires condition: {self.node_id}")
        for child in self.children:
            child.validate()


@dataclass(frozen=True)
class WorkflowDefinition:
    workflow_id: str
    domain_id: str
    root: WorkflowNode
    inputs: tuple[str, ...] = ()
    outputs: tuple[str, ...] = ()
    required_capabilities: tuple[CapabilityRequirement, ...] = ()
    max_depth: int = 16
    max_retries: int = 2

    def validate(self) -> None:
        if self.max_depth < 1:
            raise ValueError("max_depth must be positive")
        if self.max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        self.root.validate()


@dataclass
class WorkflowFrame:
    workflow_id: str
    current_node_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    local_context: dict[str, Any] = field(default_factory=dict)
    child_result: dict[str, Any] | None = None
    retry_count: int = 0
    checkpoints: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class WorkflowStack:
    """Finite call stack used by the hierarchical workflow runtime."""

    max_depth: int = 16
    frames: list[WorkflowFrame] = field(default_factory=list)

    def push(self, frame: WorkflowFrame) -> None:
        if len(self.frames) >= self.max_depth:
            raise RuntimeError(f"Workflow nesting exceeds max depth {self.max_depth}")
        self.frames.append(frame)

    def pop(self) -> WorkflowFrame:
        if not self.frames:
            raise RuntimeError("Cannot pop an empty workflow stack")
        return self.frames.pop()

    @property
    def current(self) -> WorkflowFrame | None:
        return self.frames[-1] if self.frames else None


def validate_workflow_references(workflows: Sequence[WorkflowDefinition]) -> None:
    known = {workflow.workflow_id for workflow in workflows}
    for workflow in workflows:
        workflow.validate()
        stack = [workflow.root]
        while stack:
            node = stack.pop()
            if node.kind is NodeKind.SUBWORKFLOW and node.workflow_id not in known:
                raise ValueError(
                    f"Unknown child workflow {node.workflow_id!r} "
                    f"referenced by {workflow.workflow_id!r}"
                )
            stack.extend(node.children)
