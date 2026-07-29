from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from PIL import Image

from guif.core import init_project
from guif.providers import ExecutionRequest, ExecutionResult, ProviderAdapter, ProviderRegistry
from guif.resource import create_resource_manifest
from guif.revision_review import RevisionReviewService
from guif.runtime import Runtime
from guif.theme import create_theme
from guif.visual_review import (
    VisualInspectionAdapter,
    VisualInspectionRequest,
    VisualInspectionResult,
    VisualInspectorRegistry,
)

REVIEW_CAPABILITIES = frozenset(
    {
        "theme-consistency",
        "composition-and-hierarchy",
        "content-correctness",
        "readability",
        "usability",
        "resource-compliance",
    }
)


class ImageProvider(ProviderAdapter):
    provider_id = "revision-source-image"
    capabilities = frozenset({"image-generation", "transparent-output"})
    requires_bound_references = False

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        canvas = request.job.get("canvas", {})
        width = int(canvas.get("width") or 108)
        height = int(canvas.get("height") or 234)
        image = Image.new("RGBA", (width, height), (80, 100, 120, 255))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return ExecutionResult(
            provider_id=self.provider_id,
            request_id="source-image",
            content=buffer.getvalue(),
            filename="source.png",
            mime_type="image/png",
            width=width,
            height=height,
            model_id="test-source",
            simulation=False,
            visual=True,
        )


class NeedsRevisionInspector(VisualInspectionAdapter):
    inspector_id = "needs-revision"
    capabilities = REVIEW_CAPABILITIES

    def inspect(self, request: VisualInspectionRequest, artifact_path: Path) -> VisualInspectionResult:
        return VisualInspectionResult(
            inspector_id=self.inspector_id,
            status="review-required",
            summary="Primary action hierarchy needs revision.",
            findings=(
                {
                    "id": "primary-action-hierarchy",
                    "severity": "review",
                    "category": "composition-and-hierarchy",
                    "code": "weak-primary-action",
                    "message": "Increase the hierarchy and contrast of the primary purchase action.",
                },
            ),
        )


class PassingInspector(VisualInspectionAdapter):
    inspector_id = "revision-passing"
    capabilities = REVIEW_CAPABILITIES

    def inspect(self, request: VisualInspectionRequest, artifact_path: Path) -> VisualInspectionResult:
        return VisualInspectionResult(
            inspector_id=self.inspector_id,
            status="passed",
            summary="Replacement satisfies the revision and visual contracts.",
        )


def _png(width: int = 108, height: int = 234) -> bytes:
    image = Image.new("RGBA", (width, height), (90, 110, 130, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _create_project(tmp_path: Path) -> None:
    root = init_project(tmp_path, "LeekParty")
    theme_path = create_theme(
        tmp_path,
        "LeekParty",
        "Medieval Harbor",
        "Warm medieval harbor UI direction.",
    )
    theme = json.loads(theme_path.read_text(encoding="utf-8"))
    theme.update(
        {
            "palette": ["warm gold", "deep sea blue"],
            "materials": ["weathered wood", "aged brass"],
            "lighting": "warm sunset",
            "must_include": ["harbor view", "gold coins"],
            "avoid": ["pirate skulls", "dirty visual noise"],
        }
    )
    theme_path.write_text(json.dumps(theme), encoding="utf-8")
    source_dir = root / "source"
    source_dir.mkdir()
    (source_dir / "purchase-button.png").write_bytes(b"reference")
    create_resource_manifest(
        tmp_path,
        "LeekParty",
        "purchase-button",
        "button",
        264,
        134,
        "png",
        target_engine="unity",
        source="source/purchase-button.png",
    )


def _revision_ready_task(tmp_path: Path):
    _create_project(tmp_path)
    provider = ImageProvider()
    runtime = Runtime(tmp_path, providers=ProviderRegistry((provider,)))
    task = runtime.run(
        "LeekParty",
        "Create a 108x234 portrait medieval harbor shop page, reuse the purchase button, and export Unity",
        pipeline="ui-production",
    )
    for approval_id in list(task.state["approval_state"]["required_ids"]):
        task = runtime.approve(
            "LeekParty",
            task.task_id,
            approval_id,
            actor="Reviewer",
        )
    source_job_id = task.state["prompt_ir"]["jobs"][0]["id"]
    task = runtime.execute_job(
        "LeekParty",
        task.task_id,
        source_job_id,
        provider_id=provider.provider_id,
    )
    source_artifact = runtime.list_artifacts("LeekParty", task.task_id)[0]
    inspectors = VisualInspectorRegistry((NeedsRevisionInspector(),))
    task = RevisionReviewService(tmp_path, inspectors=inspectors).review(
        "LeekParty",
        task.task_id,
        source_artifact["artifact_id"],
        inspector_id="needs-revision",
    )
    revision_id = task.state["revision_plans"]["records"][0]["revision_id"]
    return runtime, task, source_artifact["artifact_id"], revision_id


def test_revision_job_requires_its_own_approval_gate(tmp_path: Path) -> None:
    runtime, task, source_artifact_id, revision_id = _revision_ready_task(tmp_path)

    task = runtime.create_revision_job("LeekParty", task.task_id, revision_id)
    job = task.state["revision_execution"]["jobs"][0]
    approval = task.state["revision_execution"]["approvals"][revision_id]

    assert job["operation"] == "edit"
    assert job["executable"] is False
    assert job["status"] == "approval-pending"
    assert job["revision"]["source_artifact_id"] == source_artifact_id
    assert job["references"][0]["immutable"] is True
    assert approval["status"] == "pending"
    with pytest.raises(ValueError, match="Revision approval gate"):
        runtime.execute_revision("LeekParty", task.task_id, revision_id)


def test_approved_revision_creates_chatgpt_edit_handoff(tmp_path: Path) -> None:
    runtime, task, source_artifact_id, revision_id = _revision_ready_task(tmp_path)
    task = runtime.create_revision_job("LeekParty", task.task_id, revision_id)
    task = runtime.approve_revision(
        "LeekParty",
        task.task_id,
        revision_id,
        actor="Art Director",
        comment="Proceed with the controlled edit.",
    )

    task = runtime.execute_revision("LeekParty", task.task_id, revision_id)
    job = task.state["revision_execution"]["jobs"][0]
    handoff = task.state["tool_handoffs"]["records"][0]
    bound_reference = handoff["request"]["references"][0]

    assert task.status == "waiting-for-tool-result"
    assert job["status"] == "waiting-for-result"
    assert handoff["tool_id"] == "chatgpt-image"
    assert handoff["instructions"]["operation"] == "edit"
    assert bound_reference["artifact_id"] == source_artifact_id
    assert bound_reference["status"] == "bound"
    assert bound_reference["sha256"] == bound_reference["expected_sha256"]


def test_replacement_is_rechecked_and_supersedes_only_after_passing_review(tmp_path: Path) -> None:
    runtime, task, source_artifact_id, revision_id = _revision_ready_task(tmp_path)
    task = runtime.create_revision_job("LeekParty", task.task_id, revision_id)
    task = runtime.approve_revision("LeekParty", task.task_id, revision_id, actor="Art Director")
    task = runtime.execute_revision("LeekParty", task.task_id, revision_id)
    handoff_id = task.state["tool_handoffs"]["records"][0]["handoff_id"]

    task = runtime.submit_tool_result(
        "LeekParty",
        task.task_id,
        handoff_id,
        content=_png(),
        filename="shop-revision.png",
        mime_type="image/png",
        width=108,
        height=234,
        model_id="chatgpt-image",
    )
    artifacts = {item["artifact_id"]: item for item in runtime.list_artifacts("LeekParty", task.task_id)}
    replacement = next(item for item in artifacts.values() if item["artifact_id"] != source_artifact_id)

    assert replacement["revision"]["source_artifact_id"] == source_artifact_id
    assert replacement["qa"]["status"] == "not-run"
    assert artifacts[source_artifact_id]["status"] == "registered"
    assert task.state["revision_execution"]["jobs"][0]["status"] == "review-pending"

    inspectors = VisualInspectorRegistry((PassingInspector(),))
    task = RevisionReviewService(tmp_path, inspectors=inspectors).review(
        "LeekParty",
        task.task_id,
        replacement["artifact_id"],
        inspector_id="revision-passing",
    )
    artifacts = {item["artifact_id"]: item for item in task.state["artifact_registry"]["records"]}
    plan = task.state["revision_plans"]["records"][0]

    assert artifacts[source_artifact_id]["status"] == "stale"
    assert artifacts[source_artifact_id]["superseded_by"] == replacement["artifact_id"]
    assert artifacts[replacement["artifact_id"]]["supersedes"] == [source_artifact_id]
    assert plan["status"] == "resolved"
    assert task.state["revision_execution"]["jobs"][0]["status"] == "passed"
    assert task.state["qa_report"]["artifact_review"]["status"] == "passed"
    assert task.state["qa_report"]["export_gate"]["allowed"] is True
    run_dir = tmp_path / "projects" / "LeekParty" / "runs" / task.task_id
    assert (run_dir / "revision-execution.json").is_file()


def test_tampered_revision_source_fails_closed(tmp_path: Path) -> None:
    runtime, task, source_artifact_id, revision_id = _revision_ready_task(tmp_path)
    task = runtime.create_revision_job("LeekParty", task.task_id, revision_id)
    task = runtime.approve_revision("LeekParty", task.task_id, revision_id, actor="Art Director")
    source = runtime.get_artifact("LeekParty", task.task_id, source_artifact_id)
    run_dir = tmp_path / "projects" / "LeekParty" / "runs" / task.task_id
    (run_dir / source["file"]["path"]).write_bytes(b"tampered")

    task = runtime.execute_revision("LeekParty", task.task_id, revision_id)

    assert task.status == "waiting-for-tool"
    assert task.state["revision_execution"]["jobs"][0]["status"] == "waiting-for-tool"
    assert "bound reference files" in task.state["tool_resolution"]["reason"]
    assert runtime.list_artifacts("LeekParty", task.task_id)[0]["artifact_id"] == source_artifact_id


def test_rejected_revision_never_reaches_tool_router(tmp_path: Path) -> None:
    runtime, task, _, revision_id = _revision_ready_task(tmp_path)
    task = runtime.create_revision_job("LeekParty", task.task_id, revision_id)
    task = runtime.reject_revision(
        "LeekParty",
        task.task_id,
        revision_id,
        actor="Art Director",
        comment="Revise the objectives first.",
    )

    with pytest.raises(ValueError, match="Revision approval gate"):
        runtime.execute_revision("LeekParty", task.task_id, revision_id)
    assert task.state["revision_execution"]["jobs"][0]["executable"] is False
    assert "tool_handoffs" not in task.state
