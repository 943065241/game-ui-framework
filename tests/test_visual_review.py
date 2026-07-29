from __future__ import annotations

import io
import json
from pathlib import Path

from PIL import Image

from guif.core import init_project
from guif.providers import ExecutionRequest, ExecutionResult, ProviderAdapter, ProviderRegistry
from guif.resource import create_resource_manifest
from guif.runtime import Runtime
from guif.theme import create_theme
from guif.visual_review import (
    VisualInspectionAdapter,
    VisualInspectionRequest,
    VisualInspectionResult,
    VisualInspectorRegistry,
    VisualReviewService,
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
    provider_id = "test-image"
    capabilities = frozenset({"image-generation", "transparent-output"})
    requires_bound_references = False

    def __init__(self, *, wrong_size: bool = False) -> None:
        self.wrong_size = wrong_size
        self.calls = 0

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        self.calls += 1
        canvas = request.job.get("canvas", {})
        width = int(canvas.get("width") or 64)
        height = int(canvas.get("height") or 64)
        if self.wrong_size:
            width = max(1, width - 1)
        image = Image.new("RGBA", (width, height), (40 + self.calls, 80, 120, 255))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return ExecutionResult(
            provider_id=self.provider_id,
            request_id=f"image-{self.calls}",
            content=buffer.getvalue(),
            filename=f"{request.job_id}-{self.calls}.png",
            mime_type="image/png",
            width=width,
            height=height,
            model_id="test-model",
            simulation=False,
            visual=True,
        )


class PassingInspector(VisualInspectionAdapter):
    inspector_id = "passing"
    capabilities = REVIEW_CAPABILITIES

    def inspect(self, request: VisualInspectionRequest, artifact_path: Path) -> VisualInspectionResult:
        assert artifact_path.is_file()
        assert request.global_contract["page"]["type"] == "shop"
        return VisualInspectionResult(
            inspector_id=self.inspector_id,
            status="passed",
            summary="Visual contract passed in the test inspector.",
        )


class RevisionInspector(VisualInspectionAdapter):
    inspector_id = "revision"
    capabilities = REVIEW_CAPABILITIES

    def inspect(self, request: VisualInspectionRequest, artifact_path: Path) -> VisualInspectionResult:
        return VisualInspectionResult(
            inspector_id=self.inspector_id,
            status="review-required",
            summary="Primary action hierarchy needs revision.",
            findings=(
                {
                    "id": "purchase-hierarchy",
                    "severity": "review",
                    "category": "composition-and-hierarchy",
                    "code": "weak-primary-action",
                    "message": "Increase the primary purchase action hierarchy.",
                },
            ),
        )


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


def _approved_task(tmp_path: Path, provider: ProviderAdapter | None = None):
    providers = ProviderRegistry((provider,)) if provider is not None else None
    runtime = Runtime(tmp_path, providers=providers)
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
    return runtime, task


def test_dry_run_artifact_is_not_visual_review_eligible(tmp_path: Path) -> None:
    _create_project(tmp_path)
    runtime, task = _approved_task(tmp_path)
    job_id = task.state["prompt_ir"]["jobs"][0]["id"]
    task = runtime.execute_job("LeekParty", task.task_id, job_id, provider_id="dry-run")
    artifact_id = runtime.list_artifacts("LeekParty", task.task_id)[0]["artifact_id"]

    task = VisualReviewService(tmp_path).review("LeekParty", task.task_id, artifact_id)
    review = task.state["visual_reviews"]["records"][0]

    assert review["status"] == "not-applicable"
    assert review["visual_conclusion_claimed"] is False
    assert task.state["artifact_registry"]["records"][0]["qa"]["status"] == "not-applicable"
    assert task.state["qa_report"]["artifact_review"]["status"] == "not-applicable"
    assert task.state["qa_report"]["export_gate"]["allowed"] is False
    run_dir = tmp_path / "projects" / "LeekParty" / "runs" / task.task_id
    assert (run_dir / "visual-reviews.json").is_file()


def test_real_image_metadata_passes_but_semantic_review_stays_not_run(tmp_path: Path) -> None:
    _create_project(tmp_path)
    provider = ImageProvider()
    runtime, task = _approved_task(tmp_path, provider)
    job_id = task.state["prompt_ir"]["jobs"][0]["id"]
    task = runtime.execute_job("LeekParty", task.task_id, job_id, provider_id=provider.provider_id)
    artifact_id = runtime.list_artifacts("LeekParty", task.task_id)[0]["artifact_id"]

    task = VisualReviewService(tmp_path).review("LeekParty", task.task_id, artifact_id)
    review = task.state["visual_reviews"]["records"][0]

    assert review["eligibility"]["status"] == "passed"
    assert review["metadata_review"]["status"] == "passed"
    assert review["semantic_review"]["status"] == "not-run"
    assert review["status"] == "not-run"
    assert review["visual_conclusion_claimed"] is False
    assert task.state["qa_report"]["export_gate"]["allowed"] is False


def test_visual_inspector_can_pass_artifact_and_open_export_gate(tmp_path: Path) -> None:
    _create_project(tmp_path)
    provider = ImageProvider()
    runtime, task = _approved_task(tmp_path, provider)
    job_id = task.state["prompt_ir"]["jobs"][0]["id"]
    task = runtime.execute_job("LeekParty", task.task_id, job_id, provider_id=provider.provider_id)
    artifact_id = runtime.list_artifacts("LeekParty", task.task_id)[0]["artifact_id"]
    registry = VisualInspectorRegistry((PassingInspector(),))

    task = VisualReviewService(tmp_path, inspectors=registry).review(
        "LeekParty",
        task.task_id,
        artifact_id,
        inspector_id="passing",
    )

    review = task.state["visual_reviews"]["records"][0]
    assert review["status"] == "passed"
    assert review["visual_conclusion_claimed"] is True
    assert task.state["qa_report"]["artifact_review"]["status"] == "passed"
    assert task.state["qa_report"]["export_gate"]["allowed"] is True
    assert runtime.list_runs("LeekParty")[0]["artifact_review_status"] == "passed"


def test_visual_finding_creates_persisted_revision_plan(tmp_path: Path) -> None:
    _create_project(tmp_path)
    provider = ImageProvider()
    runtime, task = _approved_task(tmp_path, provider)
    job_id = task.state["prompt_ir"]["jobs"][0]["id"]
    task = runtime.execute_job("LeekParty", task.task_id, job_id, provider_id=provider.provider_id)
    artifact_id = runtime.list_artifacts("LeekParty", task.task_id)[0]["artifact_id"]
    registry = VisualInspectorRegistry((RevisionInspector(),))

    task = VisualReviewService(tmp_path, inspectors=registry).review(
        "LeekParty",
        task.task_id,
        artifact_id,
        inspector_id="revision",
    )

    review = task.state["visual_reviews"]["records"][0]
    plan = task.state["revision_plans"]["records"][0]
    assert review["status"] == "review-required"
    assert plan["source_artifact_id"] == artifact_id
    assert plan["source_job_id"] == job_id
    assert plan["finding_ids"] == ["purchase-hierarchy"]
    assert task.state["qa_report"]["revision_request"]["required"] is True
    assert task.state["qa_report"]["export_gate"]["allowed"] is False
    run_dir = tmp_path / "projects" / "LeekParty" / "runs" / task.task_id
    assert (run_dir / "revision-plans.json").is_file()


def test_metadata_mismatch_blocks_review_and_proposes_revision(tmp_path: Path) -> None:
    _create_project(tmp_path)
    provider = ImageProvider(wrong_size=True)
    runtime, task = _approved_task(tmp_path, provider)
    job_id = task.state["prompt_ir"]["jobs"][0]["id"]
    task = runtime.execute_job("LeekParty", task.task_id, job_id, provider_id=provider.provider_id)
    artifact_id = runtime.list_artifacts("LeekParty", task.task_id)[0]["artifact_id"]

    task = VisualReviewService(tmp_path).review("LeekParty", task.task_id, artifact_id)
    review = task.state["visual_reviews"]["records"][0]

    assert review["status"] == "blocked"
    assert review["metadata_review"]["status"] == "failed"
    assert review["findings"][0]["code"] == "image-metadata-mismatch"
    assert task.state["revision_plans"]["records"][0]["source_artifact_id"] == artifact_id


def test_new_artifact_can_explicitly_supersede_older_artifact(tmp_path: Path) -> None:
    _create_project(tmp_path)
    provider = ImageProvider()
    runtime, task = _approved_task(tmp_path, provider)
    job_id = task.state["prompt_ir"]["jobs"][0]["id"]
    task = runtime.execute_job("LeekParty", task.task_id, job_id, provider_id=provider.provider_id)
    first = runtime.list_artifacts("LeekParty", task.task_id)[0]
    task = runtime.execute_job("LeekParty", task.task_id, job_id, provider_id=provider.provider_id)
    artifacts = runtime.list_artifacts("LeekParty", task.task_id)
    second = next(item for item in artifacts if item["artifact_id"] != first["artifact_id"])

    task = VisualReviewService(tmp_path).supersede(
        "LeekParty",
        task.task_id,
        first["artifact_id"],
        second["artifact_id"],
    )
    by_id = {item["artifact_id"]: item for item in task.state["artifact_registry"]["records"]}

    assert by_id[first["artifact_id"]]["status"] == "stale"
    assert by_id[first["artifact_id"]]["superseded_by"] == second["artifact_id"]
    assert by_id[second["artifact_id"]]["supersedes"] == [first["artifact_id"]]
