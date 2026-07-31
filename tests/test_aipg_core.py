from __future__ import annotations

import pytest

from aipg import (
    ArtifactRecord,
    ArtifactRegistry,
    ArtifactStatus,
    CapabilityRequirement,
    ContextMode,
    NodeKind,
    ProductionRequest,
    ToolAdapter,
    ToolRegistry,
    WorkflowDefinition,
    WorkflowFrame,
    WorkflowNode,
    WorkflowStack,
    WorkflowStatus,
    validate_workflow_references,
)


def test_tool_registry_resolves_by_capability_and_required_features() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolAdapter(
            adapter_id="provider-image-edit",
            provider="example",
            capabilities=("image-editing",),
            features=("mask-guided", "transparent-output"),
        )
    )
    result = registry.resolve(
        CapabilityRequirement("image-editing", required_features=("mask-guided",))
    )
    assert [adapter.adapter_id for adapter in result] == ["provider-image-edit"]


def test_nested_workflow_references_are_validated() -> None:
    child = WorkflowDefinition(
        workflow_id="mask-generation",
        domain_id="visual-production",
        root=WorkflowNode("segment", NodeKind.ACTION, action_id="segment-image"),
    )
    parent = WorkflowDefinition(
        workflow_id="localized-repaint",
        domain_id="visual-production",
        root=WorkflowNode(
            "root",
            NodeKind.SEQUENCE,
            children=(
                WorkflowNode(
                    "create-mask", NodeKind.SUBWORKFLOW, workflow_id="mask-generation"
                ),
                WorkflowNode("edit", NodeKind.ACTION, action_id="edit-image"),
            ),
        ),
    )
    validate_workflow_references([parent, child])


def test_unknown_child_workflow_is_rejected() -> None:
    parent = WorkflowDefinition(
        workflow_id="localized-repaint",
        domain_id="visual-production",
        root=WorkflowNode(
            "missing", NodeKind.SUBWORKFLOW, workflow_id="unknown-workflow"
        ),
    )
    with pytest.raises(ValueError, match="Unknown child workflow"):
        validate_workflow_references([parent])


def test_workflow_stack_returns_to_parent_frame() -> None:
    stack = WorkflowStack(max_depth=2)
    parent = WorkflowFrame(
        workflow_id="visual-production-task",
        current_node_id="repaint",
        status=WorkflowStatus.WAITING_FOR_CHILD,
    )
    child = WorkflowFrame(
        workflow_id="localized-repaint",
        current_node_id="mask",
        status=WorkflowStatus.RUNNING,
    )
    stack.push(parent)
    stack.push(child)
    assert stack.pop() is child
    assert stack.current is parent


def test_workflow_stack_enforces_finite_depth() -> None:
    stack = WorkflowStack(max_depth=1)
    stack.push(WorkflowFrame("parent", "start"))
    with pytest.raises(RuntimeError, match="max depth"):
        stack.push(WorkflowFrame("child", "start"))


def test_artifact_registry_returns_parent_first_lineage() -> None:
    registry = ArtifactRegistry()
    registry.register(
        ArtifactRecord(
            artifact_id="source",
            domain_id="visual-production",
            kind="image",
            status=ArtifactStatus.REGISTERED,
        )
    )
    registry.register(
        ArtifactRecord(
            artifact_id="edited",
            domain_id="visual-production",
            kind="image",
            status=ArtifactStatus.GENERATED,
            parent_ids=("source",),
        )
    )
    assert [record.artifact_id for record in registry.lineage("edited")] == [
        "source",
        "edited",
    ]


def test_context_modes_enforce_lifecycle_contract() -> None:
    ProductionRequest(
        domain_id="visual-production",
        workflow_id="localized-repaint",
        context_mode=ContextMode.STANDALONE,
        inputs={"source": "image-1"},
    ).validate()
    ProductionRequest(
        domain_id="visual-production",
        workflow_id="ui-production",
        context_mode=ContextMode.PROJECT,
        project_context_id="theme-1",
        inputs={},
    ).validate()
    with pytest.raises(ValueError, match="requires project_context_id"):
        ProductionRequest(
            domain_id="visual-production",
            workflow_id="ui-production",
            context_mode=ContextMode.PROJECT,
            inputs={},
        ).validate()
