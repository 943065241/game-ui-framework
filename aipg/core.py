from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


class ContextMode(str, Enum):
    """Lifecycle mode for one production request."""

    PROJECT = "project"
    STANDALONE = "standalone"


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


class ArtifactStatus(str, Enum):
    REGISTERED = "registered"
    DRAFT = "draft"
    GENERATED = "generated"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    EXPORTED = "exported"


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
class CapabilityRequirement:
    capability_id: str
    required_features: tuple[str, ...] = ()
    optional_features: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolAdapter:
    """A provider-specific implementation behind a stable capability."""

    adapter_id: str
    provider: str
    capabilities: tuple[str, ...]
    features: tuple[str, ...] = ()
    configuration_schema: Mapping[str, Any] = field(default_factory=dict)

    def supports(self, requirement: CapabilityRequirement) -> bool:
        return requirement.capability_id in self.capabilities and set(
            requirement.required_features
        ).issubset(self.features)


@dataclass
class ToolRegistry:
    adapters: dict[str, ToolAdapter] = field(default_factory=dict)

    def register(self, adapter: ToolAdapter) -> None:
        if adapter.adapter_id in self.adapters:
            raise ValueError(f"Tool adapter already registered: {adapter.adapter_id}")
        self.adapters[adapter.adapter_id] = adapter

    def resolve(self, requirement: CapabilityRequirement) -> list[ToolAdapter]:
        return [
            adapter
            for adapter in self.adapters.values()
            if adapter.supports(requirement)
        ]


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
    """Finite, explicit call stack for nested workflow execution."""

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


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_id: str
    domain_id: str
    kind: str
    status: ArtifactStatus
    parent_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class ArtifactRegistry:
    records: dict[str, ArtifactRecord] = field(default_factory=dict)

    def register(self, artifact: ArtifactRecord) -> None:
        if artifact.artifact_id in self.records:
            raise ValueError(f"Artifact already registered: {artifact.artifact_id}")
        missing = [parent for parent in artifact.parent_ids if parent not in self.records]
        if missing:
            raise ValueError(f"Unknown parent artifacts: {', '.join(missing)}")
        self.records[artifact.artifact_id] = artifact

    def lineage(self, artifact_id: str) -> list[ArtifactRecord]:
        if artifact_id not in self.records:
            raise ValueError(f"Unknown artifact: {artifact_id}")
        ordered: list[ArtifactRecord] = []
        visited: set[str] = set()

        def visit(current_id: str) -> None:
            if current_id in visited:
                return
            visited.add(current_id)
            current = self.records[current_id]
            for parent_id in current.parent_ids:
                visit(parent_id)
            ordered.append(current)

        visit(artifact_id)
        return ordered


@dataclass(frozen=True)
class DomainPackDefinition:
    domain_id: str
    name: str
    context_types: tuple[str, ...]
    artifact_kinds: tuple[str, ...]
    workflow_ids: tuple[str, ...]
    capability_ids: tuple[str, ...]


@dataclass(frozen=True)
class ProductionRequest:
    domain_id: str
    workflow_id: str
    context_mode: ContextMode
    inputs: Mapping[str, Any]
    project_context_id: str | None = None

    def validate(self) -> None:
        if self.context_mode is ContextMode.PROJECT and not self.project_context_id:
            raise ValueError("Project context mode requires project_context_id")
        if self.context_mode is ContextMode.STANDALONE and self.project_context_id:
            raise ValueError("Standalone mode cannot bind a project_context_id")


def validate_workflow_references(
    workflows: Sequence[WorkflowDefinition],
) -> None:
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
