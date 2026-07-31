from __future__ import annotations

import pytest

from aipg import (
    EventBus,
    NodeKind,
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowNode,
    WorkflowStatus,
)


def make_workflow(*, max_retries: int = 1) -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="example-production",
        domain_id="visual-production",
        root=WorkflowNode(
            node_id="produce",
            kind=NodeKind.ACTION,
            action_id="produce-output",
        ),
        inputs=("prompt",),
        outputs=("artifact_id",),
        max_retries=max_retries,
    )


def test_engine_runs_action_and_completes_with_events() -> None:
    event_bus = EventBus()
    engine = WorkflowEngine(event_bus)
    engine.register_workflow(make_workflow())
    engine.register_action(
        "produce-output",
        lambda frame, arguments: {
            "artifact_id": f"artifact-{arguments['suffix']}",
            "prompt_seen": frame.local_context["prompt"],
        },
    )

    run = engine.create_run("example-production", {"prompt": "paint"})
    engine.start(run.run_id)
    result = engine.execute_action(
        run.run_id,
        "produce-output",
        {"suffix": "001"},
    )
    engine.complete(run.run_id, {"artifact_id": result["artifact_id"]})

    assert run.status is WorkflowStatus.COMPLETED
    assert run.outputs == {"artifact_id": "artifact-001"}
    assert run.frame.local_context["prompt_seen"] == "paint"
    assert run.frame.checkpoints[-1]["reason"] == "complete"
    assert [event.event_type for event in event_bus.history][-1] == "workflow.completed"


def test_engine_pause_resume_and_cancel() -> None:
    engine = WorkflowEngine()
    engine.register_workflow(make_workflow())
    run = engine.create_run("example-production", {"prompt": "paint"})

    engine.start(run.run_id)
    engine.pause(run.run_id, "human-review")
    assert run.status is WorkflowStatus.WAITING_FOR_APPROVAL
    assert run.frame.local_context["pause_reason"] == "human-review"

    engine.resume(run.run_id)
    assert run.status is WorkflowStatus.RUNNING
    assert "pause_reason" not in run.frame.local_context

    engine.cancel(run.run_id, "operator-cancelled")
    assert run.status is WorkflowStatus.CANCELLED


def test_engine_retry_is_bounded() -> None:
    engine = WorkflowEngine()
    engine.register_workflow(make_workflow(max_retries=1))
    run = engine.create_run("example-production", {"prompt": "paint"})

    engine.start(run.run_id)
    engine.fail(run.run_id, "provider unavailable")
    engine.retry(run.run_id)
    assert run.status is WorkflowStatus.RUNNING
    assert run.frame.retry_count == 1

    engine.fail(run.run_id, "provider unavailable again")
    with pytest.raises(RuntimeError, match="retry limit"):
        engine.retry(run.run_id)


def test_engine_rejects_invalid_lifecycle_and_missing_contract_values() -> None:
    engine = WorkflowEngine()
    engine.register_workflow(make_workflow())

    with pytest.raises(ValueError, match="Missing workflow inputs"):
        engine.create_run("example-production", {})

    run = engine.create_run("example-production", {"prompt": "paint"})
    with pytest.raises(RuntimeError, match="Invalid workflow transition"):
        engine.complete(run.run_id, {"artifact_id": "artifact-001"})

    engine.start(run.run_id)
    with pytest.raises(ValueError, match="Missing workflow outputs"):
        engine.complete(run.run_id, {})


def test_event_bus_supports_specific_and_wildcard_subscribers() -> None:
    bus = EventBus()
    seen: list[str] = []
    bus.subscribe("workflow.started", lambda event: seen.append(event.event_type))
    bus.subscribe("*", lambda event: seen.append(f"all:{event.event_type}"))

    engine = WorkflowEngine(bus)
    engine.register_workflow(make_workflow())
    run = engine.create_run("example-production", {"prompt": "paint"})
    engine.start(run.run_id)

    assert "workflow.started" in seen
    assert "all:workflow.started" in seen
