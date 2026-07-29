from __future__ import annotations

import json
from pathlib import Path

import pytest

from guif.core import init_project
from guif.resource import create_resource_manifest
from guif.runtime import Runtime, TaskStore


PROJECT = "SampleGame"


def _create_ready_project(tmp_path: Path) -> None:
    init_project(tmp_path, PROJECT)
    Runtime(tmp_path).create_private_theme(
        "Fictional Geometric Arcade",
        {
            "description": "A synthetic abstract menu fixture for framework tests.",
            "palette": ["test blue", "test gray"],
            "materials": ["matte polymer"],
            "lighting": "flat studio light",
            "must_include": ["hexagonal navigation"],
            "avoid": ["real brands", "photoreal people"],
        },
        project=PROJECT,
        actor="test-host",
    )
    create_resource_manifest(
        tmp_path,
        PROJECT,
        "action-button",
        "button",
        264,
        134,
        "png",
        target_engine="unity",
    )


def _run_review_task(tmp_path: Path):
    return Runtime(tmp_path).run(
        PROJECT,
        "Create a 1080x2340 fictional geometric arcade menu, reuse the action button, and export Unity",
        pipeline="ui-production",
    )


def test_all_required_approvals_enable_prompt_jobs_without_side_effects(tmp_path: Path) -> None:
    _create_ready_project(tmp_path)
    resources_dir = tmp_path / "projects" / PROJECT / "production-assets"
    before_files = sorted(path.name for path in resources_dir.iterdir())

    task = _run_review_task(tmp_path)
    runtime = Runtime(tmp_path)
    summary = runtime.get_approvals(PROJECT, task.task_id)

    assert summary["status"] == "pending"
    assert summary["required_ids"]
    assert summary["pending_ids"] == sorted(summary["required_ids"])
    assert task.state["prompt_ir"]["status"] == "review-required"
    assert all(job["executable"] is False for job in task.state["prompt_ir"]["jobs"])

    for approval_id in summary["required_ids"]:
        task = runtime.approve(
            PROJECT,
            task.task_id,
            approval_id,
            actor="TestReviewer",
            comment=f"Approved {approval_id}",
        )

    approval_state = task.state["approval_state"]
    assert approval_state["status"] == "approved"
    assert approval_state["pending_ids"] == []
    assert approval_state["project_mutated"] is False
    assert approval_state["provider_executed"] is False
    assert task.status == "completed"
    assert task.state["prompt_ir"]["status"] == "ready"
    assert all(job["executable"] is True for job in task.state["prompt_ir"]["jobs"])
    assert task.state["qa_report"]["status"] == "passed"
    assert task.state["qa_report"]["artifact_review"]["status"] == "not-run"
    assert task.state["qa_report"]["export_gate"]["allowed"] is False
    assert len([output for output in task.outputs if output["type"] == "semantic-qa-report"]) == 1
    assert sorted(path.name for path in resources_dir.iterdir()) == before_files

    approval_path = TaskStore(tmp_path).run_dir(PROJECT, task.task_id) / "approvals.json"
    persisted = json.loads(approval_path.read_text(encoding="utf-8"))
    assert persisted["status"] == "approved"
    assert len(persisted["history"]) == len(summary["required_ids"])


def test_change_request_blocks_then_later_approval_recovers_gate(tmp_path: Path) -> None:
    _create_ready_project(tmp_path)
    task = _run_review_task(tmp_path)
    runtime = Runtime(tmp_path)
    required_ids = list(task.state["approval_state"]["required_ids"])
    target = required_ids[0]

    for approval_id in required_ids[1:]:
        task = runtime.approve(PROJECT, task.task_id, approval_id, actor="TestReviewer")

    task = runtime.request_changes(
        PROJECT,
        task.task_id,
        target,
        actor="TestReviewer",
        comment="Increase the primary action hierarchy.",
    )
    assert task.state["approval_state"]["status"] == "changes-requested"
    assert task.state["prompt_ir"]["status"] == "blocked"
    assert all(job["executable"] is False for job in task.state["prompt_ir"]["jobs"])
    assert any(
        blocker["code"] == "approval-changes-requested"
        for blocker in task.state["prompt_ir"]["blockers"]
    )
    assert task.state["qa_report"]["status"] == "blocked"

    task = runtime.approve(
        PROJECT,
        task.task_id,
        target,
        actor="TestReviewer",
        comment="Revised hierarchy accepted.",
    )
    assert task.state["approval_state"]["status"] == "approved"
    assert task.state["prompt_ir"]["status"] == "ready"
    assert not any(
        blocker.get("source") == "approval"
        for blocker in task.state["prompt_ir"]["blockers"]
    )
    history = task.state["approval_state"]["history"]
    assert [item["decision"] for item in history if item["approval_id"] == target] == [
        "changes-requested",
        "approved",
    ]


def test_approval_rejects_unknown_or_non_prompt_task(tmp_path: Path) -> None:
    _create_ready_project(tmp_path)
    task = _run_review_task(tmp_path)
    runtime = Runtime(tmp_path)

    with pytest.raises(ValueError, match="Unknown approval point"):
        runtime.approve(PROJECT, task.task_id, "unknown", actor="TestReviewer")

    planning_task = runtime.run(
        PROJECT,
        "Plan a 1080x2340 fictional menu page",
        pipeline="planning",
    )
    with pytest.raises(ValueError, match="does not contain a Prompt IR"):
        runtime.get_approvals(PROJECT, planning_task.task_id)
