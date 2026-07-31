from __future__ import annotations

from aipg import (
    InMemoryCheckpointStore,
    NodeKind,
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowNode,
    WorkflowStatus,
)


def action(node_id: str, action_id: str) -> WorkflowNode:
    return WorkflowNode(node_id=node_id, kind=NodeKind.ACTION, action_id=action_id)


def test_execute_traverses_sequence_and_completes_outputs() -> None:
    engine = WorkflowEngine()
    engine.register_workflow(
        WorkflowDefinition(
            workflow_id="sequence",
            domain_id="visual-production",
            root=WorkflowNode(
                node_id="root",
                kind=NodeKind.SEQUENCE,
                children=(action("prepare", "prepare"), action("render", "render")),
            ),
            inputs=("prompt",),
            outputs=("artifact_id",),
        )
    )
    engine.register_action("prepare", lambda frame, _: {"prepared": True})
    engine.register_action(
        "render",
        lambda frame, _: {"artifact_id": f"artifact:{frame.local_context['prompt']}"},
    )

    run = engine.create_run("sequence", {"prompt": "button"})
    engine.execute(run.run_id)

    assert run.status is WorkflowStatus.COMPLETED
    assert run.outputs == {"artifact_id": "artifact:button"}
    assert run.frame.local_context["prepared"] is True


def test_condition_selects_true_or_false_branch() -> None:
    engine = WorkflowEngine()
    engine.register_workflow(
        WorkflowDefinition(
            workflow_id="conditional",
            domain_id="visual-production",
            root=WorkflowNode(
                node_id="choose",
                kind=NodeKind.CONDITION,
                condition="high-quality",
                children=(action("hq", "hq"), action("draft", "draft")),
            ),
            inputs=("quality",),
            outputs=("mode",),
        )
    )
    engine.register_condition(
        "high-quality", lambda frame: frame.local_context["quality"] == "high"
    )
    engine.register_action("hq", lambda frame, _: {"mode": "hq"})
    engine.register_action("draft", lambda frame, _: {"mode": "draft"})

    high = engine.create_run("conditional", {"quality": "high"})
    engine.execute(high.run_id)
    draft = engine.create_run("conditional", {"quality": "low"})
    engine.execute(draft.run_id)

    assert high.outputs == {"mode": "hq"}
    assert draft.outputs == {"mode": "draft"}


def test_subworkflow_uses_finite_stack_and_returns_child_context() -> None:
    engine = WorkflowEngine()
    engine.register_workflow(
        WorkflowDefinition(
            workflow_id="child",
            domain_id="visual-production",
            root=action("segment", "segment"),
        )
    )
    engine.register_workflow(
        WorkflowDefinition(
            workflow_id="parent",
            domain_id="visual-production",
            root=WorkflowNode(
                node_id="call-child",
                kind=NodeKind.SUBWORKFLOW,
                workflow_id="child",
            ),
            inputs=("image_id",),
            outputs=("mask_id",),
            max_depth=4,
        )
    )
    engine.register_action(
        "segment",
        lambda frame, _: {"mask_id": f"mask:{frame.local_context['image_id']}"},
    )

    run = engine.create_run("parent", {"image_id": "hero"})
    engine.execute(run.run_id)

    assert run.status is WorkflowStatus.COMPLETED
    assert run.outputs == {"mask_id": "mask:hero"}
    assert run.frame.child_result is not None
    assert run.frame.child_result["mask_id"] == "mask:hero"
    assert len(run.stack.frames) == 1


def test_approval_node_pauses_without_auto_completion() -> None:
    engine = WorkflowEngine()
    engine.register_workflow(
        WorkflowDefinition(
            workflow_id="approval",
            domain_id="visual-production",
            root=WorkflowNode(
                node_id="approve",
                kind=NodeKind.APPROVAL,
                policy={"reason": "visual-approval"},
            ),
        )
    )

    run = engine.create_run("approval")
    engine.execute(run.run_id)

    assert run.status is WorkflowStatus.WAITING_FOR_APPROVAL
    assert run.frame.local_context["pause_reason"] == "visual-approval"


def test_checkpoint_store_receives_action_child_and_completion_snapshots() -> None:
    store = InMemoryCheckpointStore()
    engine = WorkflowEngine(checkpoint_store=store)
    engine.register_workflow(
        WorkflowDefinition(
            workflow_id="checkpointed",
            domain_id="visual-production",
            root=action("produce", "produce"),
            outputs=("artifact_id",),
        )
    )
    engine.register_action("produce", lambda frame, _: {"artifact_id": "artifact-1"})

    run = engine.create_run("checkpointed")
    engine.execute(run.run_id)

    checkpoints = store.list(run.run_id)
    assert [item["reason"] for item in checkpoints] == ["action:produce", "complete"]
    assert engine.latest_checkpoint(run.run_id) == checkpoints[-1]
