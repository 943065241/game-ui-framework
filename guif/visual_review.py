from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from guif.artifacts import get_artifact, list_artifacts
from guif.runtime.store import TaskStore

VISUAL_REVIEW_SCHEMA_VERSION = 1
VISUAL_INSPECTION_REQUEST_SCHEMA_VERSION = 1
VISUAL_INSPECTION_RESULT_SCHEMA_VERSION = 1
REVISION_PLAN_SCHEMA_VERSION = 1
SUPPORTED_IMAGE_MIME_TYPES = frozenset({"image/png", "image/jpeg", "image/webp"})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _image_module():
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "Visual image metadata inspection requires Pillow. Install with: pip install -e .[image]"
        ) from exc
    return Image


def _has_alpha(image: Any) -> bool:
    if image.mode in {"RGBA", "LA"}:
        return True
    if image.mode == "P" and "transparency" in image.info:
        return True
    return "A" in image.getbands()


def _normalize_format(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.lower().lstrip(".")
    return "jpg" if normalized == "jpeg" else normalized


@dataclass(frozen=True)
class VisualInspectionRequest:
    request_id: str
    task_id: str
    project: str
    artifact_id: str
    job_id: str
    artifact_kind: str | None
    file: dict[str, Any]
    output_contract: dict[str, Any]
    global_contract: dict[str, Any]
    instructions: dict[str, Any]
    negative_constraints: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    review_dimensions: tuple[str, ...] = (
        "theme-consistency",
        "composition-and-hierarchy",
        "content-correctness",
        "readability",
        "usability",
        "resource-compliance",
    )
    schema_version: int = VISUAL_INSPECTION_REQUEST_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["negative_constraints"] = list(self.negative_constraints)
        payload["acceptance_criteria"] = list(self.acceptance_criteria)
        payload["review_dimensions"] = list(self.review_dimensions)
        return payload


@dataclass(frozen=True)
class VisualInspectionResult:
    inspector_id: str
    status: str
    findings: tuple[dict[str, Any], ...] = ()
    summary: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = VISUAL_INSPECTION_RESULT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["findings"] = [dict(item) for item in self.findings]
        return payload


class VisualInspectionAdapter(ABC):
    inspector_id: str
    capabilities: frozenset[str]

    def describe(self) -> dict[str, Any]:
        return {
            "inspector_id": self.inspector_id,
            "capabilities": sorted(self.capabilities),
        }

    def missing_capabilities(self, required: Iterable[str]) -> tuple[str, ...]:
        return tuple(sorted(set(required) - set(self.capabilities)))

    @abstractmethod
    def inspect(self, request: VisualInspectionRequest, artifact_path: Path) -> VisualInspectionResult:
        raise NotImplementedError


class VisualInspectorRegistry:
    def __init__(self, inspectors: Iterable[VisualInspectionAdapter] = ()) -> None:
        self._inspectors: dict[str, VisualInspectionAdapter] = {}
        for inspector in inspectors:
            self.register(inspector)

    def register(self, inspector: VisualInspectionAdapter) -> None:
        if not inspector.inspector_id.strip():
            raise ValueError("Visual inspector ID must not be empty")
        if inspector.inspector_id in self._inspectors:
            raise ValueError(f"Duplicate Visual inspector: {inspector.inspector_id}")
        self._inspectors[inspector.inspector_id] = inspector

    def get(self, inspector_id: str) -> VisualInspectionAdapter:
        try:
            return self._inspectors[inspector_id]
        except KeyError as exc:
            raise ValueError(f"Unknown Visual inspector: {inspector_id}") from exc

    def describe(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._inspectors[key].describe() for key in sorted(self._inspectors))


def _find_job(task: Any, job_id: str) -> dict[str, Any]:
    prompt_ir = task.state.get("prompt_ir")
    if not isinstance(prompt_ir, dict):
        raise ValueError("Visual review requires Prompt IR")
    for job in prompt_ir.get("jobs", []):
        if isinstance(job, dict) and job.get("id") == job_id:
            return job
    raise ValueError(f"Unknown Prompt job for Artifact: {job_id}")


def _artifact_path(run_dir: Path, artifact: dict[str, Any]) -> Path:
    file_data = artifact.get("file") if isinstance(artifact.get("file"), dict) else {}
    path_value = file_data.get("path")
    if not isinstance(path_value, str) or not path_value.strip():
        raise ValueError("Artifact file path is missing")
    root = run_dir.resolve()
    candidate = (run_dir / path_value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Artifact file path escapes the Run directory") from exc
    return candidate


def _eligibility(run_dir: Path, artifact: dict[str, Any]) -> tuple[dict[str, Any], Path | None]:
    if artifact.get("status") == "stale":
        return {
            "status": "failed",
            "eligible": False,
            "reason": "Stale Artifacts are retained for provenance but are not eligible for active review.",
        }, None
    if artifact.get("simulation") is True or artifact.get("visual") is not True:
        return {
            "status": "not-applicable",
            "eligible": False,
            "reason": "Simulation or non-visual Artifact does not contain visual pixels to inspect.",
        }, None
    file_data = artifact.get("file") if isinstance(artifact.get("file"), dict) else {}
    mime_type = str(file_data.get("mime_type") or "").lower()
    if mime_type not in SUPPORTED_IMAGE_MIME_TYPES:
        return {
            "status": "failed",
            "eligible": False,
            "reason": f"Unsupported visual Artifact MIME type: {mime_type or 'missing'}.",
        }, None
    try:
        path = _artifact_path(run_dir, artifact)
    except ValueError as exc:
        return {"status": "failed", "eligible": False, "reason": str(exc)}, None
    if not path.is_file():
        return {
            "status": "failed",
            "eligible": False,
            "reason": "Artifact file does not exist in the persisted Run.",
        }, None
    content = path.read_bytes()
    expected_hash = str(file_data.get("sha256") or "")
    actual_hash = _sha256(content)
    if not expected_hash or expected_hash != actual_hash:
        return {
            "status": "failed",
            "eligible": False,
            "reason": "Artifact file SHA-256 does not match the registered record.",
            "expected_sha256": expected_hash,
            "actual_sha256": actual_hash,
        }, None
    return {
        "status": "passed",
        "eligible": True,
        "reason": "Artifact is a registered visual image with a valid file identity.",
        "mime_type": mime_type,
        "sha256": actual_hash,
    }, path


def _metadata_review(path: Path, artifact: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
    Image = _image_module()
    with Image.open(path) as image:
        width, height = image.size
        actual_format = _normalize_format(image.format or path.suffix)
        has_alpha = _has_alpha(image)
        mode = image.mode

    contract = job.get("output_contract") if isinstance(job.get("output_contract"), dict) else {}
    canvas = job.get("canvas") if isinstance(job.get("canvas"), dict) else {}
    expected_width = contract.get("width") or canvas.get("width")
    expected_height = contract.get("height") or canvas.get("height")
    expected_format = _normalize_format(str(contract.get("format") or ""))
    alpha_required = contract.get("alpha_required") is True
    registered_file = artifact.get("file") if isinstance(artifact.get("file"), dict) else {}

    checks = [
        {
            "id": "dimension",
            "status": "passed" if not expected_width or not expected_height or (width, height) == (expected_width, expected_height) else "failed",
            "expected": {"width": expected_width, "height": expected_height},
            "actual": {"width": width, "height": height},
        },
        {
            "id": "format",
            "status": "passed" if not expected_format or actual_format == expected_format else "failed",
            "expected": expected_format,
            "actual": actual_format,
        },
        {
            "id": "alpha",
            "status": "passed" if not alpha_required or has_alpha else "failed",
            "expected": {"required": alpha_required},
            "actual": {"has_alpha": has_alpha, "mode": mode},
        },
        {
            "id": "registered-dimension",
            "status": "passed"
            if (registered_file.get("width") in {None, width} and registered_file.get("height") in {None, height})
            else "failed",
            "expected": {"width": registered_file.get("width"), "height": registered_file.get("height")},
            "actual": {"width": width, "height": height},
        },
    ]
    failed = [item for item in checks if item["status"] == "failed"]
    return {
        "status": "failed" if failed else "passed",
        "width": width,
        "height": height,
        "format": actual_format,
        "has_alpha": has_alpha,
        "mode": mode,
        "checks": checks,
    }


def _request(task: Any, artifact: dict[str, Any], job: dict[str, Any]) -> VisualInspectionRequest:
    prompt_ir = task.state.get("prompt_ir") if isinstance(task.state.get("prompt_ir"), dict) else {}
    identity = f"{task.task_id}:{artifact['artifact_id']}:{artifact['file'].get('sha256')}"
    request_id = "visual-review-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return VisualInspectionRequest(
        request_id=request_id,
        task_id=task.task_id,
        project=task.project,
        artifact_id=str(artifact["artifact_id"]),
        job_id=str(artifact["job_id"]),
        artifact_kind=artifact.get("artifact_kind"),
        file=dict(artifact.get("file", {})),
        output_contract=dict(job.get("output_contract", {})),
        global_contract=dict(prompt_ir.get("global_contract", {})),
        instructions=dict(job.get("instructions", {})),
        negative_constraints=tuple(str(value) for value in job.get("negative_constraints", [])),
        acceptance_criteria=tuple(str(value) for value in job.get("acceptance_criteria", [])),
    )


def _normalize_findings(values: Iterable[dict[str, Any]], *, source: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for index, item in enumerate(values):
        if not isinstance(item, dict):
            continue
        severity = str(item.get("severity") or "review")
        if severity not in {"blocking", "review", "warning", "info"}:
            severity = "review"
        findings.append(
            {
                "id": str(item.get("id") or f"finding-{index + 1}"),
                "severity": severity,
                "category": str(item.get("category") or "visual"),
                "code": str(item.get("code") or "visual-review-finding"),
                "message": str(item.get("message") or "Visual review requires attention."),
                "evidence": item.get("evidence"),
                "source": source,
            }
        )
    return findings


def _revision_plan(task: Any, artifact: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any] | None:
    actionable = [item for item in findings if item["severity"] in {"blocking", "review", "warning"}]
    if not actionable:
        return None
    identity = ":".join(
        [task.task_id, str(artifact["artifact_id"])]
        + sorted(str(item["id"]) for item in actionable)
    )
    plan_id = "revision-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return {
        "schema_version": REVISION_PLAN_SCHEMA_VERSION,
        "revision_id": plan_id,
        "task_id": task.task_id,
        "project": task.project,
        "source_job_id": artifact.get("job_id"),
        "source_artifact_id": artifact.get("artifact_id"),
        "status": "proposed",
        "operation": "edit",
        "finding_ids": [item["id"] for item in actionable],
        "objectives": [item["message"] for item in actionable],
        "constraints": {
            "preserve_source_provenance": True,
            "do_not_overwrite_source_artifact": True,
            "new_artifact_must_supersede_source_after_review": True,
        },
        "next_step": "Create a revision Prompt job linked to this plan, execute it after approval, then review the new Artifact.",
        "created_at": _now(),
    }


def _replace_output(task: Any, output_type: str, value: dict[str, Any], identity_field: str) -> None:
    identity = value.get(identity_field)
    for output in task.outputs:
        if (
            isinstance(output, dict)
            and output.get("type") == output_type
            and isinstance(output.get("value"), dict)
            and output["value"].get(identity_field) == identity
        ):
            output["value"] = value
            return
    task.add_output(output_type, value, agent="visual-review")


def _aggregate_into_qa(task: Any) -> None:
    report = task.state.get("qa_report")
    if not isinstance(report, dict):
        return
    active = [item for item in list_artifacts(task) if item.get("status") == "registered"]
    visual = [item for item in active if item.get("visual") is True and item.get("simulation") is not True]
    reviews = [item.get("qa") for item in visual if isinstance(item.get("qa"), dict)]
    statuses = [str(item.get("status") or "not-run") for item in reviews]
    if not active:
        aggregate_status = "not-run"
        reason = "No Artifact is registered."
    elif not visual:
        aggregate_status = "not-applicable"
        reason = "Registered Artifacts are simulations or non-visual receipts."
    elif any(status == "blocked" for status in statuses):
        aggregate_status = "blocked"
        reason = "At least one active visual Artifact failed eligibility, metadata, or semantic review."
    elif any(status == "review-required" for status in statuses):
        aggregate_status = "review-required"
        reason = "At least one active visual Artifact requires human or revision review."
    elif reviews and len(reviews) == len(visual) and all(status == "passed" for status in statuses):
        aggregate_status = "passed"
        reason = "Every active visual Artifact passed metadata and semantic inspection."
    else:
        aggregate_status = "not-run"
        reason = "One or more active visual Artifacts have not completed semantic inspection."

    report["artifact_review"] = {
        "status": aggregate_status,
        "artifact_count": len(active),
        "visual_artifact_count": len(visual),
        "reviewed_visual_artifact_count": len(reviews),
        "reason": reason,
        "artifact_statuses": {
            str(item.get("artifact_id")): str(item.get("qa", {}).get("status") or "not-run")
            for item in active
        },
    }
    export_allowed = report.get("status") == "passed" and aggregate_status == "passed"
    report["export_gate"] = {
        "allowed": export_allowed,
        "reasons": [] if export_allowed else [
            "Contract QA must pass and every active visual Artifact must pass visual review."
        ],
    }
    plans = task.state.get("revision_plans", {}).get("records", []) if isinstance(task.state.get("revision_plans"), dict) else []
    report["revision_request"] = {
        "required": any(isinstance(item, dict) and item.get("status") == "proposed" for item in plans),
        "revision_plan_ids": [item.get("revision_id") for item in plans if isinstance(item, dict) and item.get("status") == "proposed"],
        "next_step": (
            "Resolve proposed Revision Plans, generate a new Artifact, then review it."
            if plans
            else "No visual revision is currently proposed."
        ),
    }


def _persist_review(task: Any, review: dict[str, Any], revision: dict[str, Any] | None) -> None:
    state = task.state.get("visual_reviews")
    if not isinstance(state, dict):
        state = {
            "schema_version": VISUAL_REVIEW_SCHEMA_VERSION,
            "task_id": task.task_id,
            "project": task.project,
            "records": [],
            "latest_by_artifact": {},
            "updated_at": _now(),
        }
        task.state["visual_reviews"] = state
    records = state.setdefault("records", [])
    latest = state.setdefault("latest_by_artifact", {})
    if not isinstance(records, list) or not isinstance(latest, dict):
        raise ValueError("Invalid persisted Visual Review state")
    records.append(review)
    latest[str(review["artifact_id"])] = review["review_id"]
    state["updated_at"] = _now()
    _replace_output(task, "visual-artifact-review", review, "review_id")

    if revision is not None:
        revision_state = task.state.get("revision_plans")
        if not isinstance(revision_state, dict):
            revision_state = {
                "schema_version": REVISION_PLAN_SCHEMA_VERSION,
                "task_id": task.task_id,
                "project": task.project,
                "records": [],
                "updated_at": _now(),
            }
            task.state["revision_plans"] = revision_state
        revision_records = revision_state.setdefault("records", [])
        if not isinstance(revision_records, list):
            raise ValueError("Invalid persisted Revision Plan state")
        if not any(
            isinstance(item, dict) and item.get("revision_id") == revision["revision_id"]
            for item in revision_records
        ):
            revision_records.append(revision)
        revision_state["updated_at"] = _now()
        _replace_output(task, "revision-plan", revision, "revision_id")


class VisualReviewService:
    def __init__(
        self,
        workspace: Path,
        *,
        store: TaskStore | None = None,
        inspectors: VisualInspectorRegistry | None = None,
    ) -> None:
        self.workspace = workspace
        self.store = store or TaskStore(workspace)
        self.inspectors = inspectors or VisualInspectorRegistry()

    def list_inspectors(self) -> tuple[dict[str, Any], ...]:
        return self.inspectors.describe()

    def review(
        self,
        project: str,
        task_id: str,
        artifact_id: str,
        *,
        inspector_id: str | None = None,
    ) -> Any:
        task = self.store.load(project, task_id)
        artifact = get_artifact(task, artifact_id)
        job = _find_job(task, str(artifact.get("job_id")))
        run_dir = self.store.run_dir(project, task_id)
        eligibility, path = _eligibility(run_dir, artifact)
        request = _request(task, artifact, job)
        metadata: dict[str, Any] = {"status": "not-run", "checks": []}
        semantic: dict[str, Any] = {
            "status": "not-run",
            "inspector_id": inspector_id,
            "summary": "No Visual Inspection Adapter was selected.",
            "findings": [],
        }
        findings: list[dict[str, Any]] = []

        if eligibility["status"] == "not-applicable":
            status = "not-applicable"
            semantic["status"] = "not-applicable"
            semantic["summary"] = eligibility["reason"]
        elif eligibility["status"] == "failed" or path is None:
            status = "blocked"
            findings.append(
                {
                    "id": "artifact-eligibility",
                    "severity": "blocking",
                    "category": "artifact-integrity",
                    "code": "visual-artifact-ineligible",
                    "message": eligibility["reason"],
                    "evidence": eligibility,
                    "source": "visual-review",
                }
            )
        else:
            try:
                metadata = _metadata_review(path, artifact, job)
            except (RuntimeError, OSError) as exc:
                metadata = {"status": "failed", "checks": [], "error": str(exc)}
            if metadata["status"] == "failed":
                findings.append(
                    {
                        "id": "image-metadata-contract",
                        "severity": "blocking",
                        "category": "resource-compliance",
                        "code": "image-metadata-mismatch",
                        "message": "Image dimensions, format, alpha, or registered metadata do not match the Output Contract.",
                        "evidence": metadata,
                        "source": "visual-review",
                    }
                )
                status = "blocked"
            elif inspector_id is None:
                status = "not-run"
            else:
                inspector = self.inspectors.get(inspector_id)
                required = request.review_dimensions
                missing = inspector.missing_capabilities(required)
                if missing:
                    raise ValueError(
                        f"Visual inspector {inspector_id} lacks required capabilities: {', '.join(missing)}"
                    )
                result = inspector.inspect(request, path)
                if result.inspector_id != inspector_id:
                    raise ValueError(
                        f"Visual inspector result identity mismatch: expected {inspector_id}, got {result.inspector_id}"
                    )
                if result.status not in {"passed", "review-required", "blocked"}:
                    raise ValueError(f"Invalid Visual inspection status: {result.status}")
                normalized = _normalize_findings(result.findings, source=f"inspector:{inspector_id}")
                findings.extend(normalized)
                semantic = result.to_dict()
                semantic["findings"] = normalized
                status = result.status
                if any(item["severity"] == "blocking" for item in normalized):
                    status = "blocked"
                elif status == "passed" and any(item["severity"] in {"review", "warning"} for item in normalized):
                    status = "review-required"

        review_identity = f"{request.request_id}:{inspector_id or 'none'}:{len(task.state.get('visual_reviews', {}).get('records', []))}"
        review_id = "review-" + hashlib.sha256(review_identity.encode("utf-8")).hexdigest()[:16]
        review = {
            "schema_version": VISUAL_REVIEW_SCHEMA_VERSION,
            "review_id": review_id,
            "request": request.to_dict(),
            "task_id": task.task_id,
            "project": task.project,
            "artifact_id": artifact_id,
            "job_id": artifact.get("job_id"),
            "status": status,
            "eligibility": eligibility,
            "metadata_review": metadata,
            "semantic_review": semantic,
            "findings": findings,
            "visual_conclusion_claimed": status in {"passed", "review-required", "blocked"} and inspector_id is not None,
            "created_at": _now(),
        }
        revision = _revision_plan(task, artifact, findings)
        artifact["qa"] = {
            "status": status,
            "review_id": review_id,
            "metadata_status": metadata.get("status"),
            "semantic_status": semantic.get("status"),
            "inspector_id": inspector_id,
            "revision_id": revision.get("revision_id") if revision else None,
            "reviewed_at": review["created_at"],
        }
        _persist_review(task, review, revision)
        _aggregate_into_qa(task)
        task.record(
            "visual-review",
            status,
            f"Artifact {artifact_id} visual review completed with status {status}.",
        )
        self.store.save(task)
        return task

    def supersede(
        self,
        project: str,
        task_id: str,
        old_artifact_id: str,
        new_artifact_id: str,
    ) -> Any:
        if old_artifact_id == new_artifact_id:
            raise ValueError("An Artifact cannot supersede itself")
        task = self.store.load(project, task_id)
        old = get_artifact(task, old_artifact_id)
        new = get_artifact(task, new_artifact_id)
        if old.get("job_id") != new.get("job_id"):
            raise ValueError("Artifacts from different Prompt jobs cannot supersede one another")
        old["status"] = "stale"
        old["superseded_by"] = new_artifact_id
        old["stale_at"] = _now()
        supersedes = new.setdefault("supersedes", [])
        if not isinstance(supersedes, list):
            raise ValueError("Invalid Artifact supersession metadata")
        if old_artifact_id not in supersedes:
            supersedes.append(old_artifact_id)
        new["status"] = "registered"
        task.record(
            "artifact",
            "superseded",
            f"Artifact {old_artifact_id} became stale and was superseded by {new_artifact_id}.",
        )
        _aggregate_into_qa(task)
        self.store.save(task)
        return task

    def list_reviews(self, project: str, task_id: str) -> tuple[dict[str, Any], ...]:
        task = self.store.load(project, task_id)
        state = task.state.get("visual_reviews")
        if not isinstance(state, dict):
            return ()
        return tuple(item for item in state.get("records", []) if isinstance(item, dict))

    def list_revision_plans(self, project: str, task_id: str) -> tuple[dict[str, Any], ...]:
        task = self.store.load(project, task_id)
        state = task.state.get("revision_plans")
        if not isinstance(state, dict):
            return ()
        return tuple(item for item in state.get("records", []) if isinstance(item, dict))
