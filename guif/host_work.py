from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from guif.artifacts import get_artifact, list_artifacts
from guif.auth import AuthenticatedActor
from guif.paths import project_root
from guif.private_data import PrivateDataLayout
from guif.revision_review import RevisionReviewService
from guif.runtime.store import TaskStore
from guif.visual_review import (
    VisualInspectionAdapter,
    VisualInspectionRequest,
    VisualInspectionResult,
    VisualInspectorRegistry,
)

HOST_WORK_SCHEMA_VERSION = 1
HOST_WORK_CLAIM_TOKEN_PREFIX = "guifw1"
DEFAULT_VISUAL_INSPECTOR_ID = "chatgpt-vision"
MIN_CLAIM_SECONDS = 30
MAX_CLAIM_SECONDS = 1800
SUPPORTED_WORK_KINDS = frozenset(
    {"image-generation", "image-editing", "visual-inspection"}
)


class HostWorkError(RuntimeError):
    pass


class HostWorkClaimError(HostWorkError):
    pass


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _now() -> str:
    return _now_dt().isoformat()


def _parse_time(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        raise HostWorkClaimError("Host work claim timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise HostWorkClaimError("Host work claim timestamp is invalid") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    try:
        os.chmod(temporary, 0o600)
    except OSError:
        pass
    temporary.replace(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise HostWorkError(f"Expected Host work JSON object: {path}")
    return value


def _safe_name(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized or Path(normalized).name != normalized:
        raise ValueError(f"Invalid {label}: {value}")
    return normalized


def _public(record: dict[str, Any]) -> dict[str, Any]:
    copy = json.loads(json.dumps(record, ensure_ascii=False))
    claim = copy.get("claim")
    if isinstance(claim, dict):
        claim.pop("token_hash", None)
    return copy


def _work_kind(handoff: dict[str, Any]) -> str:
    request = handoff.get("request") if isinstance(handoff.get("request"), dict) else {}
    job = request.get("job") if isinstance(request.get("job"), dict) else {}
    return "image-editing" if job.get("operation") == "edit" else "image-generation"


def _mime_from_path(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(suffix, "application/octet-stream")


@dataclass(frozen=True)
class HostWorkAttachment:
    attachment_id: str
    label: str
    storage_scope: str
    path: str
    sha256: str
    size_bytes: int
    mime_type: str
    role: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "attachment_id": self.attachment_id,
            "label": self.label,
            "storage_scope": self.storage_scope,
            "path": self.path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "mime_type": self.mime_type,
            "role": self.role,
        }


class SubmittedVisualInspector(VisualInspectionAdapter):
    def __init__(
        self,
        inspector_id: str,
        result: VisualInspectionResult,
        capabilities: Iterable[str],
    ) -> None:
        self.inspector_id = inspector_id
        self.result = result
        self.capabilities = frozenset(str(item) for item in capabilities)

    def inspect(
        self,
        request: VisualInspectionRequest,
        artifact_path: Path,
    ) -> VisualInspectionResult:
        if self.result.inspector_id != self.inspector_id:
            raise ValueError("Submitted Visual Inspector identity mismatch")
        return self.result


class HostWorkService:
    """Private, claimable Host work for image execution and semantic review."""

    def __init__(
        self,
        workspace: Path,
        *,
        store: TaskStore | None = None,
        runtime: Any | None = None,
    ) -> None:
        self.workspace = workspace.resolve()
        self.layout = PrivateDataLayout(self.workspace)
        self.store = store or TaskStore(self.workspace)
        self.runtime = runtime

    def _project_dir(self, project: str) -> Path:
        return self.layout.host_work / _safe_name(project, "project")

    def _path(self, project: str, work_id: str) -> Path:
        return self._project_dir(project) / f"{_safe_name(work_id, 'work_id')}.json"

    def _save(self, record: dict[str, Any]) -> dict[str, Any]:
        _write_json(self._path(str(record["project"]), str(record["work_id"])), record)
        return _public(record)

    def _refresh(self, record: dict[str, Any]) -> dict[str, Any]:
        claim = record.get("claim") if isinstance(record.get("claim"), dict) else None
        if record.get("status") == "claimed" and claim is not None:
            try:
                expired = _parse_time(claim.get("expires_at")) <= _now_dt()
            except HostWorkClaimError:
                expired = True
            if expired:
                record["status"] = "available"
                record["claim"] = None
                record["updated_at"] = _now()
                self._save(record)
        return record

    def _load(self, project: str, work_id: str) -> dict[str, Any]:
        path = self._path(project, work_id)
        if not path.is_file():
            raise HostWorkError(f"Unknown Host work item: {project}/{work_id}")
        return self._refresh(_read_json(path))

    def _all(self, project: str) -> list[dict[str, Any]]:
        directory = self._project_dir(project)
        if not directory.exists():
            return []
        records: list[dict[str, Any]] = []
        for path in sorted(directory.glob("work-*.json")):
            try:
                records.append(self._refresh(_read_json(path)))
            except (OSError, ValueError, json.JSONDecodeError, HostWorkError):
                continue
        return records

    def _attachment(
        self,
        *,
        task: Any,
        label: str,
        path: Path,
        root: Path,
        storage_scope: str,
        role: str | None,
        expected_sha256: str | None = None,
    ) -> HostWorkAttachment | None:
        try:
            resolved = path.resolve(strict=True)
            relative = resolved.relative_to(root.resolve())
        except (FileNotFoundError, ValueError):
            return None
        if not resolved.is_file():
            return None
        content = resolved.read_bytes()
        actual = hashlib.sha256(content).hexdigest()
        if expected_sha256 and expected_sha256 != actual:
            return None
        attachment_id = "attachment-" + _canonical_hash(
            {
                "task_id": task.task_id,
                "scope": storage_scope,
                "path": str(relative),
                "sha256": actual,
            }
        )[:16]
        return HostWorkAttachment(
            attachment_id=attachment_id,
            label=label,
            storage_scope=storage_scope,
            path=str(relative),
            sha256=actual,
            size_bytes=len(content),
            mime_type=_mime_from_path(resolved),
            role=role,
        )

    def _handoff_attachments(self, task: Any, handoff: dict[str, Any]) -> list[dict[str, Any]]:
        request = handoff.get("request") if isinstance(handoff.get("request"), dict) else {}
        references = request.get("references") if isinstance(request.get("references"), list) else []
        run_root = self.store.run_dir(task.project, task.task_id).resolve()
        project_base = project_root(self.workspace, task.project).resolve()
        attachments: list[dict[str, Any]] = []
        for index, reference in enumerate(references):
            if not isinstance(reference, dict) or reference.get("status") != "bound":
                continue
            path_value = reference.get("path")
            if not isinstance(path_value, str) or not path_value:
                continue
            scope = "private-run" if reference.get("storage_scope") == "private-run" else "project"
            root = run_root if scope == "private-run" else project_base
            attachment = self._attachment(
                task=task,
                label=str(reference.get("resource_id") or reference.get("artifact_id") or f"reference-{index + 1}"),
                path=root / path_value,
                root=root,
                storage_scope=scope,
                role=str(reference.get("role")) if reference.get("role") is not None else None,
                expected_sha256=str(reference.get("sha256") or reference.get("expected_sha256") or "") or None,
            )
            if attachment is not None:
                attachments.append(attachment.to_dict())
        return attachments

    def _sync_handoffs(self, project: str) -> None:
        for summary in self.store.list(project):
            task_id = summary.get("task_id")
            if not isinstance(task_id, str):
                continue
            try:
                task = self.store.load(project, task_id)
            except (FileNotFoundError, ValueError):
                continue
            handoff_state = task.state.get("tool_handoffs")
            handoffs = handoff_state.get("records", []) if isinstance(handoff_state, dict) else []
            for handoff in handoffs:
                if not isinstance(handoff, dict) or not handoff.get("handoff_id"):
                    continue
                work_id = "work-image-" + _canonical_hash(
                    {"task_id": task.task_id, "handoff_id": handoff["handoff_id"]}
                )[:16]
                path = self._path(project, work_id)
                existing = _read_json(path) if path.is_file() else None
                if handoff.get("status") == "completed":
                    if isinstance(existing, dict) and existing.get("status") != "completed":
                        existing["status"] = "completed"
                        existing["result"] = {
                            "artifact_id": handoff.get("artifact_id"),
                            "completed_at": handoff.get("completed_at"),
                        }
                        existing["updated_at"] = _now()
                        self._save(existing)
                    continue
                if handoff.get("status") != "waiting-for-result":
                    continue
                if isinstance(existing, dict):
                    self._refresh(existing)
                    continue
                request = handoff.get("request") if isinstance(handoff.get("request"), dict) else {}
                kind = _work_kind(handoff)
                record = {
                    "schema_version": HOST_WORK_SCHEMA_VERSION,
                    "work_id": work_id,
                    "project": project,
                    "task_id": task.task_id,
                    "kind": kind,
                    "capability": kind,
                    "status": "available",
                    "host_id": handoff.get("host_id"),
                    "tool_id": handoff.get("tool_id"),
                    "handoff_id": handoff.get("handoff_id"),
                    "artifact_id": None,
                    "request": request,
                    "attachments": self._handoff_attachments(task, handoff),
                    "submission_contract": handoff.get("submission_contract"),
                    "claim": None,
                    "result": None,
                    "created_at": _now(),
                    "updated_at": _now(),
                }
                self._save(record)

    def prepare_visual_inspection(
        self,
        project: str,
        task_id: str,
        artifact_id: str,
    ) -> dict[str, Any] | None:
        task = self.store.load(project, task_id)
        artifact = get_artifact(task, artifact_id)
        if artifact.get("visual") is not True or artifact.get("simulation") is True:
            return None
        service = RevisionReviewService(self.workspace, store=self.store)
        service.review(project, task_id, artifact_id, inspector_id=None)
        task = self.store.load(project, task_id)
        artifact = get_artifact(task, artifact_id)
        qa = artifact.get("qa") if isinstance(artifact.get("qa"), dict) else {}
        if qa.get("status") != "not-run" or qa.get("metadata_status") != "passed":
            return None
        review_state = task.state.get("visual_reviews")
        records = review_state.get("records", []) if isinstance(review_state, dict) else []
        review = next(
            (
                item
                for item in reversed(records)
                if isinstance(item, dict)
                and item.get("artifact_id") == artifact_id
                and item.get("status") == "not-run"
            ),
            None,
        )
        if not isinstance(review, dict) or not isinstance(review.get("request"), dict):
            raise HostWorkError("Visual inspection preparation did not persist a review request")
        work_id = "work-visual-" + _canonical_hash(
            {
                "task_id": task_id,
                "artifact_id": artifact_id,
                "sha256": artifact.get("file", {}).get("sha256"),
            }
        )[:16]
        path = self._path(project, work_id)
        if path.is_file():
            return _public(self._refresh(_read_json(path)))
        file_data = artifact.get("file") if isinstance(artifact.get("file"), dict) else {}
        run_root = self.store.run_dir(project, task_id).resolve()
        attachment = self._attachment(
            task=task,
            label=str(file_data.get("path") or artifact_id),
            path=run_root / str(file_data.get("path") or ""),
            root=run_root,
            storage_scope="private-run",
            role="visual-inspection-target",
            expected_sha256=str(file_data.get("sha256") or "") or None,
        )
        if attachment is None:
            raise HostWorkError("Visual Artifact attachment is missing or has changed")
        record = {
            "schema_version": HOST_WORK_SCHEMA_VERSION,
            "work_id": work_id,
            "project": project,
            "task_id": task_id,
            "kind": "visual-inspection",
            "capability": "visual-inspection",
            "status": "available",
            "host_id": "chatgpt",
            "tool_id": DEFAULT_VISUAL_INSPECTOR_ID,
            "handoff_id": None,
            "artifact_id": artifact_id,
            "request": review["request"],
            "source_review_id": review.get("review_id"),
            "attachments": [attachment.to_dict()],
            "submission_contract": {
                "schema_version": 1,
                "statuses": ["passed", "review-required", "blocked"],
                "finding_severities": ["blocking", "review", "warning", "info"],
                "default_inspector_id": DEFAULT_VISUAL_INSPECTOR_ID,
            },
            "claim": None,
            "result": None,
            "created_at": _now(),
            "updated_at": _now(),
        }
        return self._save(record)

    def prepare_latest_visual_inspection(
        self,
        project: str,
        task_id: str,
    ) -> dict[str, Any] | None:
        task = self.store.load(project, task_id)
        artifact = next(
            (
                item
                for item in reversed(list_artifacts(task))
                if item.get("status") == "registered"
                and item.get("visual") is True
                and item.get("simulation") is not True
            ),
            None,
        )
        if not isinstance(artifact, dict):
            return None
        return self.prepare_visual_inspection(project, task_id, str(artifact["artifact_id"]))

    def list(
        self,
        project: str,
        *,
        capabilities: Iterable[str] = (),
        statuses: Iterable[str] = ("available", "claimed"),
        limit: int = 100,
    ) -> tuple[dict[str, Any], ...]:
        if limit < 1 or limit > 1000:
            raise ValueError("limit must be between 1 and 1000")
        self._sync_handoffs(project)
        selected_capabilities = {str(item) for item in capabilities if str(item)}
        selected_statuses = {str(item) for item in statuses if str(item)}
        records = []
        for record in self._all(project):
            if selected_capabilities and str(record.get("capability")) not in selected_capabilities:
                continue
            if selected_statuses and str(record.get("status")) not in selected_statuses:
                continue
            records.append(_public(record))
        records.sort(key=lambda item: (str(item.get("created_at") or ""), str(item.get("work_id"))))
        return tuple(records[:limit])

    def get(self, project: str, work_id: str) -> dict[str, Any]:
        self._sync_handoffs(project)
        return _public(self._load(project, work_id))

    def claim(
        self,
        project: str,
        work_id: str,
        actor: AuthenticatedActor,
        *,
        ttl_seconds: int = 300,
    ) -> dict[str, Any]:
        if not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool):
            raise ValueError("ttl_seconds must be an integer")
        if ttl_seconds < MIN_CLAIM_SECONDS or ttl_seconds > MAX_CLAIM_SECONDS:
            raise ValueError(
                f"ttl_seconds must be between {MIN_CLAIM_SECONDS} and {MAX_CLAIM_SECONDS}"
            )
        record = self._load(project, work_id)
        if record.get("status") != "available":
            raise HostWorkClaimError(f"Host work is not available: {record.get('status')}")
        secret = secrets.token_urlsafe(32)
        claimed_at = _now_dt()
        record["status"] = "claimed"
        record["claim"] = {
            "actor": actor.to_dict(),
            "token_hash": hashlib.sha256(secret.encode("utf-8")).hexdigest(),
            "claimed_at": claimed_at.isoformat(),
            "expires_at": (claimed_at + timedelta(seconds=ttl_seconds)).isoformat(),
            "ttl_seconds": ttl_seconds,
        }
        record["updated_at"] = claimed_at.isoformat()
        self._save(record)
        return {
            "work": _public(record),
            "claim_token": f"{HOST_WORK_CLAIM_TOKEN_PREFIX}.{work_id}.{secret}",
            "secret_visible_once": True,
        }

    def validate_claim(
        self,
        project: str,
        work_id: str,
        actor: AuthenticatedActor,
        claim_token: str,
    ) -> dict[str, Any]:
        record = self._load(project, work_id)
        if record.get("status") != "claimed":
            raise HostWorkClaimError(f"Host work claim is not active: {record.get('status')}")
        claim = record.get("claim") if isinstance(record.get("claim"), dict) else {}
        parts = claim_token.strip().split(".", 2)
        if len(parts) != 3 or parts[0] != HOST_WORK_CLAIM_TOKEN_PREFIX:
            raise HostWorkClaimError("Invalid Host work claim token format")
        _, token_work_id, secret = parts
        if token_work_id != work_id:
            raise HostWorkClaimError("Host work claim identity mismatch")
        actual = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(str(claim.get("token_hash") or ""), actual):
            raise HostWorkClaimError("Host work claim token verification failed")
        recorded_actor = claim.get("actor") if isinstance(claim.get("actor"), dict) else {}
        if (
            recorded_actor.get("actor_id") != actor.actor_id
            or recorded_actor.get("credential_id") != actor.credential_id
        ):
            raise HostWorkClaimError("Host work claim belongs to another authenticated actor")
        if _parse_time(claim.get("expires_at")) <= _now_dt():
            record["status"] = "available"
            record["claim"] = None
            record["updated_at"] = _now()
            self._save(record)
            raise HostWorkClaimError("Host work claim has expired")
        return _public(record)

    def attachment(
        self,
        project: str,
        work_id: str,
        actor: AuthenticatedActor,
        claim_token: str,
        attachment_id: str,
    ) -> tuple[dict[str, Any], bytes]:
        record = self.validate_claim(project, work_id, actor, claim_token)
        descriptor = next(
            (
                item
                for item in record.get("attachments", [])
                if isinstance(item, dict) and item.get("attachment_id") == attachment_id
            ),
            None,
        )
        if not isinstance(descriptor, dict):
            raise HostWorkError(f"Unknown Host work attachment: {attachment_id}")
        scope = descriptor.get("storage_scope")
        root = (
            self.store.run_dir(project, str(record["task_id"])).resolve()
            if scope == "private-run"
            else project_root(self.workspace, project).resolve()
        )
        candidate = (root / str(descriptor.get("path") or "")).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise HostWorkError("Host work attachment escapes its allowed root") from exc
        if not candidate.is_file():
            raise HostWorkError("Host work attachment no longer exists")
        content = candidate.read_bytes()
        actual = hashlib.sha256(content).hexdigest()
        if actual != descriptor.get("sha256"):
            raise HostWorkError("Host work attachment SHA-256 has changed")
        return descriptor, content

    def mark_completed(
        self,
        project: str,
        work_id: str,
        *,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        record = self._load(project, work_id)
        record["status"] = "completed"
        record["result"] = dict(result)
        record["claim"] = None
        record["completed_at"] = _now()
        record["updated_at"] = record["completed_at"]
        return self._save(record)

    def complete_visual(
        self,
        project: str,
        work_id: str,
        *,
        inspector_id: str,
        status: str,
        findings: Iterable[dict[str, Any]],
        summary: str,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[Any, dict[str, Any]]:
        record = self._load(project, work_id)
        if record.get("kind") != "visual-inspection":
            raise HostWorkError("Host work item is not a Visual Inspection")
        if status not in {"passed", "review-required", "blocked"}:
            raise ValueError("Visual inspection status must be passed, review-required, or blocked")
        request_payload = record.get("request") if isinstance(record.get("request"), dict) else {}
        dimensions = tuple(str(item) for item in request_payload.get("review_dimensions", []))
        result = VisualInspectionResult(
            inspector_id=inspector_id,
            status=status,
            findings=tuple(dict(item) for item in findings if isinstance(item, dict)),
            summary=summary,
            metadata=dict(metadata or {}),
        )
        adapter = SubmittedVisualInspector(inspector_id, result, dimensions)
        registry = VisualInspectorRegistry((adapter,))
        task = RevisionReviewService(
            self.workspace,
            store=self.store,
            inspectors=registry,
        ).review(
            project,
            str(record["task_id"]),
            str(record["artifact_id"]),
            inspector_id=inspector_id,
        )
        artifact = get_artifact(task, str(record["artifact_id"]))
        qa = artifact.get("qa") if isinstance(artifact.get("qa"), dict) else {}
        receipt = {
            "status": qa.get("status"),
            "review_id": qa.get("review_id"),
            "revision_id": qa.get("revision_id"),
            "artifact_id": artifact.get("artifact_id"),
            "task_id": task.task_id,
        }
        self.mark_completed(project, work_id, result=receipt)
        revision_id = qa.get("revision_id")
        if revision_id and self.runtime is not None:
            self.runtime.create_revision_job(project, task.task_id, str(revision_id))
            task = self.store.load(project, task.task_id)
            receipt["revision_job_created"] = True
        else:
            receipt["revision_job_created"] = False
        return task, receipt


__all__ = [
    "DEFAULT_VISUAL_INSPECTOR_ID",
    "HOST_WORK_CLAIM_TOKEN_PREFIX",
    "HOST_WORK_SCHEMA_VERSION",
    "HostWorkAttachment",
    "HostWorkClaimError",
    "HostWorkError",
    "HostWorkService",
    "SubmittedVisualInspector",
]
