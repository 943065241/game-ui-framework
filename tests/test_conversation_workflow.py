from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from PIL import Image

from guif.conversation_workflow import (
    ConversationWorkflowError,
    ConversationWorkflowService,
)
from guif.core import init_project
from guif.runtime import Runtime

PROJECT = "SampleGame"
CONVERSATION = "conversation-fictional-001"
THEME = {
    "description": "A wholly fictional orbital kiosk interface.",
    "palette": ["test violet", "test silver"],
    "materials": ["matte composite"],
    "lighting": "soft synthetic daylight",
    "must_include": ["circular menu"],
    "avoid": ["real brands"],
}
CAPABILITIES = (
    "approval:decide",
    "export:execute",
    "host-work:claim",
    "host-work:complete",
    "host-work:read",
    "revision:decide",
    "task:lease",
    "task:resume",
    "tool:execute",
    "tool-result:submit",
    "visual-inspection:submit",
)


def _png_bytes(width: int = 1080, height: int = 2340) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", (width, height), (80, 90, 120, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def _service(tmp_path: Path) -> tuple[Runtime, ConversationWorkflowService]:
    init_project(tmp_path, PROJECT)
    runtime = Runtime(tmp_path)
    issued = runtime.register_host_credential(
        "conversation-host",
        "chatgpt",
        CAPABILITIES,
        roles=("conversation-orchestrator",),
    )
    return runtime, ConversationWorkflowService(
        tmp_path,
        runtime=runtime,
        bearer_token=issued["bearer_token"],
    )


def _ready_request(tmp_path: Path) -> tuple[Runtime, ConversationWorkflowService, dict]:
    runtime, service = _service(tmp_path)
    opened = service.open(PROJECT, CONVERSATION)
    assert opened["stage"] == "theme-confirmation"
    themed = service.create_theme(
        PROJECT,
        CONVERSATION,
        "Fictional Orbital Fixture",
        THEME,
    )
    assert themed["stage"] == "ready-for-request"
    submitted = service.submit(
        PROJECT,
        CONVERSATION,
        "Create a 1080x2340 fictional orbital shop page and export Unity",
        request_key="turn-fictional-001",
    )
    return runtime, service, submitted


def _image_executor(work: dict, attachments: tuple[dict, ...]) -> dict:
    if work["kind"] == "image-editing":
        assert attachments
        assert attachments[0]["descriptor"]["sha256"]
    return {
        "content": _png_bytes(),
        "filename": f"{work['kind']}-result.png",
        "mime_type": "image/png",
        "width": 1080,
        "height": 2340,
        "model_id": "chatgpt-image",
        "metadata": {"fictional_fixture": True},
    }


def _passing_inspector(work: dict, attachments: tuple[dict, ...]) -> dict:
    assert work["kind"] == "visual-inspection"
    assert len(attachments) == 1
    return {
        "inspector_id": "chatgpt-vision",
        "status": "passed",
        "summary": "The fictional interface satisfies every supplied review dimension.",
        "findings": [],
        "metadata": {"semantic_pixels_inspected": True},
    }


def test_conversation_view_hides_low_level_runtime_identity(tmp_path: Path) -> None:
    runtime, service, submitted = _ready_request(tmp_path)

    assert submitted["stage"] == "approval-required"
    serialized = json.dumps(submitted)
    assert "task_id" not in serialized
    assert "task-sha256" not in serialized
    assert "lease_token" not in serialized
    assert "claim_token" not in serialized
    assert "handoff_id" not in serialized

    diagnostics = service.status(
        PROJECT,
        CONVERSATION,
        include_diagnostics=True,
    )
    assert diagnostics["diagnostics"]["task_id"]
    private_path = service.store._path(PROJECT, CONVERSATION)
    assert private_path.is_file()
    assert not str(private_path).startswith(str((tmp_path / "projects" / PROJECT).resolve()))


def test_request_key_is_idempotent_and_conflict_safe(tmp_path: Path) -> None:
    runtime, service, submitted = _ready_request(tmp_path)
    first = service.status(PROJECT, CONVERSATION, include_diagnostics=True)
    first_task = first["diagnostics"]["task_id"]

    replayed = service.submit(
        PROJECT,
        CONVERSATION,
        "Create a 1080x2340 fictional orbital shop page and export Unity",
        request_key="turn-fictional-001",
    )
    second = service.status(PROJECT, CONVERSATION, include_diagnostics=True)

    assert replayed["stage"] == "approval-required"
    assert second["diagnostics"]["task_id"] == first_task
    assert len(runtime.list_runs(PROJECT)) == 1

    with pytest.raises(ConversationWorkflowError):
        service.submit(
            PROJECT,
            CONVERSATION,
            "Create a different fictional screen",
            request_key="turn-fictional-001",
        )


def test_approve_runs_real_image_and_visual_loop_without_manual_ids(tmp_path: Path) -> None:
    runtime, service, submitted = _ready_request(tmp_path)

    approved = service.approve(PROJECT, CONVERSATION, comment="Proceed with the fixture.")
    assert approved["stage"] == "image-production"

    reviewed = service.run_host_until_blocked(
        PROJECT,
        CONVERSATION,
        image_executor=_image_executor,
        visual_inspector=_passing_inspector,
    )

    assert reviewed["stage"] == "ready-to-export"
    assert reviewed["artifacts"] == [
        {
            "kind": reviewed["artifacts"][0]["kind"],
            "operation": "generate",
            "status": "registered",
            "review_status": "passed",
            "mime_type": "image/png",
            "width": 1080,
            "height": 2340,
        }
    ]
    assert runtime.verify_operation_ledger()["status"] == "valid"


def test_visual_finding_requires_separate_revision_approval(tmp_path: Path) -> None:
    runtime, service, submitted = _ready_request(tmp_path)
    service.approve(PROJECT, CONVERSATION)

    revision = service.run_host_until_blocked(
        PROJECT,
        CONVERSATION,
        image_executor=_image_executor,
        visual_inspector=lambda work, attachments: {
            "inspector_id": "chatgpt-vision",
            "status": "review-required",
            "summary": "The fictional primary action needs stronger hierarchy.",
            "findings": [
                {
                    "id": "fixture-hierarchy-1",
                    "severity": "review",
                    "category": "composition-and-hierarchy",
                    "code": "primary-action-too-weak",
                    "message": "Increase the fictional primary action prominence.",
                    "evidence": {"region": "lower-center"},
                }
            ],
        },
    )
    assert revision["stage"] == "revision-approval-required"

    editing = service.approve(PROJECT, CONVERSATION, comment="Approve controlled edit.")
    assert editing["stage"] == "image-production"

    completed = service.run_host_until_blocked(
        PROJECT,
        CONVERSATION,
        image_executor=_image_executor,
        visual_inspector=_passing_inspector,
    )
    assert completed["stage"] == "ready-to-export"

    task_id = service.status(PROJECT, CONVERSATION, include_diagnostics=True)["diagnostics"]["task_id"]
    artifacts = runtime.list_artifacts(PROJECT, task_id)
    assert len(artifacts) == 2
    assert sum(item["status"] == "stale" for item in artifacts) == 1
    assert sum(item["status"] == "registered" for item in artifacts) == 1


def test_recovery_reconciles_private_session_with_persisted_task(tmp_path: Path) -> None:
    runtime, service, submitted = _ready_request(tmp_path)
    diagnostic = service.status(PROJECT, CONVERSATION, include_diagnostics=True)
    original_task = diagnostic["diagnostics"]["task_id"]

    record = service.store.get(PROJECT, CONVERSATION)
    assert record is not None
    record["active_task_id"] = None
    service.store.save(record)

    recovered = service.recover(PROJECT, CONVERSATION)
    assert recovered["stage"] == "approval-required"
    diagnostic = service.status(PROJECT, CONVERSATION, include_diagnostics=True)
    assert diagnostic["diagnostics"]["task_id"] == original_task


def test_host_loop_task_filter_does_not_consume_other_conversation_work(tmp_path: Path) -> None:
    runtime, service, submitted = _ready_request(tmp_path)
    service.approve(PROJECT, CONVERSATION)

    second_conversation = "conversation-fictional-002"
    service.select_theme(
        PROJECT,
        second_conversation,
        runtime.list_private_themes()[0]["theme_id"],
    )
    service.submit(
        PROJECT,
        second_conversation,
        "Create another 1080x2340 fictional orbital page and export Unity",
        request_key="turn-fictional-002",
    )
    service.approve(PROJECT, second_conversation)

    first_task = service.status(
        PROJECT,
        CONVERSATION,
        include_diagnostics=True,
    )["diagnostics"]["task_id"]
    second_task = service.status(
        PROJECT,
        second_conversation,
        include_diagnostics=True,
    )["diagnostics"]["task_id"]

    result = service.run_host_until_blocked(
        PROJECT,
        CONVERSATION,
        image_executor=_image_executor,
        max_steps=1,
    )
    assert result["stage"] == "visual-review"

    first_work = [
        item
        for item in runtime.list_host_work(PROJECT, statuses=("available", "completed"), limit=100)
        if item["task_id"] == first_task and item["kind"] == "image-generation"
    ]
    second_work = [
        item
        for item in runtime.list_host_work(PROJECT, statuses=("available", "completed"), limit=100)
        if item["task_id"] == second_task and item["kind"] == "image-generation"
    ]
    assert first_work[0]["status"] == "completed"
    assert second_work[0]["status"] == "available"
