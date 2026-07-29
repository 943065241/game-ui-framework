from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from guif.artifacts import get_artifact

REVISION_EXECUTION_SCHEMA_VERSION = 1
REVISION_JOB_SCHEMA_VERSION = 1
REVISION_APPROVAL_DECISIONS = {"approved", "rejected", "changes-requested"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state(task: Any) -> dict[str, Any]:
    state = task.state.get("revision_execution")
    if not isinstance(state, dict):
        state = {
            "schema_version": REVISION_EXECUTION_SCHEMA_VERSION,
            "task_id": task.task_id,
            "project": task.project,
            "jobs": [],
            "approvals": {},
            "history": [],
            "updated_at": _now(),
        }
        task.state["revision_execution"] = state
    return state


def _plans(task: Any) -> list[dict[str, Any]]:
    state = task.state.get("revision_plans")
    if not isinstance(state, dict):
        return []
    return [item for item in state.get("records", []) if isinstance(item, dict)]


def get_revision_plan(task: Any, revision_id: str) -> dict[str, Any]:
    for plan in _plans(task):
        if plan.get("revision_id") == revision_id:
            return plan
    raise ValueError(f"Unknown Revision Plan: {revision_id}")


def list_revision_jobs(task: Any) -> tuple[dict[str, Any], ...]:
    state = task.state.get("revision_execution")
    if not isinstance(state, dict):
        return ()
    return tuple(item for item in state.get("jobs", []) if isinstance(item, dict))


def get_revision_job(task: Any, job_id: str) -> dict[str, Any]:
    for job in list_revision_jobs(task):
        if job.get("id") == job_id:
            return job
    raise ValueError(f"Unknown Revision job: {job_id}")


def get_revision_job_by_plan(task: Any, revision_id: str) -> dict[str, Any]:
    for job in list_revision_jobs(task):
        if job.get("revision", {}).get("revision_id") == revision_id:
            return job
    raise ValueError(f"Revision Plan has no constructed job: {revision_id}")


def _find_prompt_job(task: Any, job_id: str) -> dict[str, Any]:
    prompt_ir = task.state.get("prompt_ir")
    if not isinstance(prompt_ir, dict):
        raise ValueError("Revision construction requires Prompt IR")
    for job in prompt_ir.get("jobs", []):
        if isinstance(job, dict) and job.get("id") == job_id:
            return job
    raise ValueError(f"Unknown source Prompt job: {job_id}")


def _source_reference(task: Any, artifact: dict[str, Any]) -> dict[str, Any]:
    file_data = artifact.get("file") if isinstance(artifact.get("file"), dict) else {}
    path = file_data.get("path")
    sha256 = file_data.get("sha256")
    if not isinstance(path, str) or not path:
        raise ValueError("Source Artifact is missing its persisted file path")
    if not isinstance(sha256, str) or not sha256:
        raise ValueError("Source Artifact is missing its SHA-256 identity")
    return {
        "resource_id": artifact.get("artifact_id"),
        "artifact_id": artifact.get("artifact_id"),
        "role": "revision-source-artifact",
        "expected_sha256": sha256,
        "immutable": True,
        "manifest": {
            "id": artifact.get("artifact_id"),
            "type": artifact.get("artifact_kind") or "effect-image",
            "source": f"runs/{task.task_id}/{path}",
            "format": str(file_data.get("mime_type") or "image/png").split("/")[-1],
            "width": file_data.get("width"),
            "height": file_data.get("height"),
            "alpha_required": artifact.get("output_contract", {}).get("alpha_required", False),
        },
    }


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = " ".join(str(value).split())
        key = normalized.casefold()
        if normalized and key not in seen:
            seen.add(key)
            result.append(normalized)
    return result


def create_revision_job(task: Any, revision_id: str) -> dict[str, Any]:
    normalized_id = revision_id.strip()
    if not normalized_id:
        raise ValueError("revision_id must not be empty")
    for existing in list_revision_jobs(task):
        if existing.get("revision", {}).get("revision_id") == normalized_id:
            return existing

    plan = get_revision_plan(task, normalized_id)
    if plan.get("status") not in {"proposed", "job-created", "approval-pending", "changes-requested"}:
        raise ValueError(f"Revision Plan cannot create a job from status: {plan.get('status')}")
    source_artifact = get_artifact(task, str(plan.get("source_artifact_id") or ""))
    if source_artifact.get("status") != "registered":
        raise ValueError("Revision source Artifact must be active and registered")
    if source_artifact.get("simulation") is True or source_artifact.get("visual") is not True:
        raise ValueError("Revision source must contain real visual pixels")
    source_job = _find_prompt_job(task, str(plan.get("source_job_id") or ""))

    identity = f"{task.task_id}:{normalized_id}:{source_artifact['artifact_id']}"
    job_id = f"{source_job['id']}-revision-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:10]}"
    instructions = {
        key: list(value) if isinstance(value, list) else value
        for key, value in dict(source_job.get("instructions", {})).items()
    }
    instructions["revision"] = list(plan.get("objectives", []))
    technical = list(instructions.get("technical", []))
    technical.extend(
        [
            "Use the registered source Artifact as an immutable edit reference.",
            "Do not overwrite or destructively modify the source Artifact file.",
            "Preserve all regions not implicated by the Revision findings.",
            "Return a new Artifact that can be reviewed and explicitly supersede the source only after passing review.",
        ]
    )
    instructions["technical"] = _dedupe([str(value) for value in technical])

    negative = _dedupe(
        [str(value) for value in source_job.get("negative_constraints", [])]
        + [
            "Do not replace the source Artifact in place.",
            "Do not change unrelated composition, content, geometry, or protected regions.",
            "Do not discard the original Theme, Output Contract, or acceptance criteria.",
        ]
    )
    acceptance = _dedupe(
        [str(value) for value in source_job.get("acceptance_criteria", [])]
        + [str(value) for value in plan.get("objectives", [])]
        + [
            "The replacement Artifact must pass deterministic metadata review.",
            "The replacement Artifact must pass semantic visual review before supersession.",
        ]
    )
    approval_id = f"revision-approval:{normalized_id}"
    timestamp = _now()
    job = {
        "schema_version": REVISION_JOB_SCHEMA_VERSION,
        "id": job_id,
        "artifact_kind": source_job.get("artifact_kind"),
        "operation": "edit",
        "executable": False,
        "status": "approval-pending",
        "canvas": dict(source_job.get("canvas", {})),
        "instructions": instructions,
        "negative_constraints": negative,
        "references": [_source_reference(task, source_artifact)],
        "output_contract": dict(source_job.get("output_contract", {})),
        "acceptance_criteria": acceptance,
        "approval_point": {
            "id": approval_id,
            "required": True,
            "question": "Approve this Revision Job before an image-editing Tool receives the source Artifact and edit instructions.",
            "source": "revision",
        },
        "revision": {
            "revision_id": normalized_id,
            "source_job_id": source_job.get("id"),
            "source_artifact_id": source_artifact.get("artifact_id"),
            "finding_ids": list(plan.get("finding_ids", [])),
            "review_id": source_artifact.get("qa", {}).get("review_id"),
        },
        "provenance": {
            "revision_plan": normalized_id,
            "source_artifact_sha256": source_artifact.get("file", {}).get("sha256"),
            "source_prompt_job": source_job.get("id"),
        },
        "artifact_id": None,
        "review_id": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    state = _state(task)
    jobs = state.setdefault("jobs", [])
    approvals = state.setdefault("approvals", {})
    if not isinstance(jobs, list) or not isinstance(approvals, dict):
        raise ValueError("Invalid persisted Revision execution state")
    jobs.append(job)
    approvals[normalized_id] = {
        "revision_id": normalized_id,
        "approval_id": approval_id,
        "status": "pending",
        "decision": None,
        "actor": None,
        "comment": None,
        "decided_at": None,
        "history": [],
    }
    state["updated_at"] = timestamp
    plan["status"] = "approval-pending"
    plan["revision_job_id"] = job_id
    plan["approval_id"] = approval_id
    plan["updated_at"] = timestamp
    task.add_output("revision-job", job, agent="revision")
    task.record("revision", "job-created", f"Constructed Revision Job {job_id} from {normalized_id}.")
    return job


def revision_approval_summary(task: Any, revision_id: str) -> dict[str, Any]:
    state = _state(task)
    approvals = state.get("approvals")
    if not isinstance(approvals, dict) or not isinstance(approvals.get(revision_id), dict):
        raise ValueError(f"Revision Plan has no approval gate: {revision_id}")
    return dict(approvals[revision_id])


def decide_revision_approval(
    task: Any,
    revision_id: str,
    decision: str,
    *,
    actor: str,
    comment: str | None = None,
) -> dict[str, Any]:
    normalized_decision = decision.strip().lower()
    normalized_actor = actor.strip()
    if normalized_decision not in REVISION_APPROVAL_DECISIONS:
        raise ValueError("decision must be approved, rejected, or changes-requested")
    if not normalized_actor:
        raise ValueError("actor must not be empty")
    job = get_revision_job_by_plan(task, revision_id)
    state = _state(task)
    approvals = state.get("approvals")
    history = state.get("history")
    if not isinstance(approvals, dict) or not isinstance(history, list):
        raise ValueError("Invalid persisted Revision approval state")
    approval = approvals.get(revision_id)
    if not isinstance(approval, dict):
        raise ValueError(f"Revision Plan has no approval gate: {revision_id}")
    timestamp = _now()
    record = {
        "revision_id": revision_id,
        "approval_id": approval.get("approval_id"),
        "decision": normalized_decision,
        "actor": normalized_actor,
        "comment": comment.strip() if isinstance(comment, str) and comment.strip() else None,
        "decided_at": timestamp,
    }
    approval.update(record)
    approval["status"] = normalized_decision
    approval.setdefault("history", []).append(dict(record))
    history.append(dict(record))
    executable = normalized_decision == "approved"
    job["executable"] = executable
    job["status"] = "ready" if executable else normalized_decision
    job["updated_at"] = timestamp
    plan = get_revision_plan(task, revision_id)
    plan["status"] = "approved" if executable else normalized_decision
    plan["updated_at"] = timestamp
    state["updated_at"] = timestamp
    task.record("revision-approval", normalized_decision, f"{normalized_actor} set {revision_id} to {normalized_decision}.")
    return dict(approval)


def mark_revision_execution(task: Any, job_id: str, status: str) -> None:
    try:
        job = get_revision_job(task, job_id)
    except ValueError:
        return
    job["status"] = status
    job["updated_at"] = _now()
    plan = get_revision_plan(task, str(job["revision"]["revision_id"]))
    plan["status"] = status
    plan["updated_at"] = job["updated_at"]
    _state(task)["updated_at"] = job["updated_at"]


def link_revision_artifact(task: Any, job_id: str, artifact: dict[str, Any]) -> dict[str, Any] | None:
    try:
        job = get_revision_job(task, job_id)
    except ValueError:
        return None
    revision = dict(job.get("revision", {}))
    artifact["revision"] = revision
    artifact["provenance"]["revision_job_id"] = job_id
    artifact["provenance"]["revision_id"] = revision.get("revision_id")
    artifact["provenance"]["source_artifact_id"] = revision.get("source_artifact_id")
    job["artifact_id"] = artifact.get("artifact_id")
    job["status"] = "review-pending"
    job["updated_at"] = _now()
    plan = get_revision_plan(task, str(revision.get("revision_id")))
    plan["status"] = "review-pending"
    plan["replacement_artifact_id"] = artifact.get("artifact_id")
    plan["updated_at"] = job["updated_at"]
    source = get_artifact(task, str(revision.get("source_artifact_id")))
    candidates = source.setdefault("replacement_candidates", [])
    if isinstance(candidates, list) and artifact.get("artifact_id") not in candidates:
        candidates.append(artifact.get("artifact_id"))
    _state(task)["updated_at"] = job["updated_at"]
    return job


def record_revision_review(task: Any, artifact: dict[str, Any], review: dict[str, Any]) -> dict[str, Any] | None:
    revision = artifact.get("revision")
    if not isinstance(revision, dict) or not revision.get("revision_id"):
        return None
    job = get_revision_job_by_plan(task, str(revision["revision_id"]))
    status = str(review.get("status") or "not-run")
    job["review_id"] = review.get("review_id")
    job["status"] = "passed" if status == "passed" else ("review-pending" if status == "not-run" else status)
    job["updated_at"] = _now()
    plan = get_revision_plan(task, str(revision["revision_id"]))
    plan["review_id"] = review.get("review_id")
    plan["status"] = "resolved" if status == "passed" else job["status"]
    plan["updated_at"] = job["updated_at"]
    _state(task)["updated_at"] = job["updated_at"]
    return job
