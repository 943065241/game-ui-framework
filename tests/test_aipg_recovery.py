from __future__ import annotations

import pytest

from aipg import (
    CapabilityRequirement,
    InMemoryCheckpointStore,
    NodeKind,
    RecoverableWorkflowEngine,
    ToolAdapter,
    ToolRegistry,
    WorkflowDefinition,
    WorkflowNode,
    WorkflowStatus,
)


def recovery_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="recoverable-production",
        domain_id="visual-production",
        root=WorkflowNode(
            node_id="root",
            kind=NodeKind.SEQUENCE,
            children=(
                WorkflowNode(node_id="prepare", kind=NodeKind.ACTION, action_id="prepare"),
                WorkflowNode(node_id="produce", kind=NodeKind.ACTION, action_id="produce"),
            ),
        ),
        outputs=("artifact_id",),
        max_retries=1,
    )


def test_restore_skips_nodes_completed_before_failure() -> None:
    store = InMemoryCheckpointStore()
    calls: list[str] = []
    engine = RecoverableWorkflowEngine(checkpoint_store=store)
    engine.register_workflow(recovery_workflow())
    engine.register_action("prepare", lambda frame, args: calls.append("prepare") or {"ready": True})

    def fail_once(frame, args):
        calls.append("produce")
        raise RuntimeError("provider unavailable")

    engine.register_action("produce", fail_once)
    run = engine.create_run("recoverable-production")
    with pytest.raises(RuntimeError, match="provider unavailable"):
        engine.execute(run.run_id)
    assert run.status is WorkflowStatus.FAILED
    assert calls == ["prepare", "produce"]

    restored_engine = RecoverableWorkflowEngine(checkpoint_store=store)
    restored_engine.register_workflow(recovery_workflow())
    restored_engine.register_action("prepare", lambda frame, args: calls.append("prepare-again") or {})
    restored_engine.register_action(
        "produce", lambda frame, args: calls.append("produce-again") or {"artifact_id": "asset-1"}
    )
    restored = restored_engine.restore_run(run.run_id)
    restored_engine.retry(restored.run_id)
    restored_engine.execute(restored.run_id)

    assert restored.status is WorkflowStatus.COMPLETED
    assert restored.outputs == {"artifact_id": "asset-1"}
    assert calls == ["prepare", "produce", "produce-again"]


def test_capability_execution_selects_highest_priority_adapter() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolAdapter(
            adapter_id="slow-image-provider",
            provider="slow-provider",
            capabilities=("image-generation",),
            priority=50,
            execute_handler=lambda args: {"artifact_id": "slow"},
        )
    )
    registry.register(
        ToolAdapter(
            adapter_id="preferred-image-provider",
            provider="preferred-provider",
            capabilities=("image-generation",),
            priority=10,
            execute_handler=lambda args: {"artifact_id": f"image-{args['prompt']}"},
        )
    )
    engine = RecoverableWorkflowEngine(tool_registry=registry)
    engine.register_workflow(
        WorkflowDefinition(
            workflow_id="capability-production",
            domain_id="visual-production",
            root=WorkflowNode(node_id="root", kind=NodeKind.SEQUENCE),
        )
    )
    run = engine.create_run("capability-production")
    engine.start(run.run_id)
    result = engine.execute_capability(
        run.run_id,
        CapabilityRequirement("image-generation"),
        {"prompt": "badge"},
    )

    assert result == {"artifact_id": "image-badge"}
    assert run.frame.local_context["artifact_id"] == "image-badge"
    completed = [event for event in engine.event_bus.history if event.event_type == "capability.completed"]
    assert completed[-1].payload["adapter_id"] == "preferred-image-provider"
