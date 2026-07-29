from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from guif.auth import HostCredentialStore
from guif.concurrency import TaskLeaseService
from guif.runtime.store import TaskStore

HOST_CALLBACK_SCHEMA_VERSION = 1
HOST_CALLBACK_STATE_SCHEMA_VERSION = 1
HOST_RESULT_CAPABILITY = "tool-result:submit"


class HostCallbackError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _state(task: Any) -> dict[str, Any]:
    state = task.state.get("host_callbacks")
    if not isinstance(state, dict):
        state = {
            "schema_version": HOST_CALLBACK_STATE_SCHEMA_VERSION,
            "task_id": task.task_id,
            "project": task.project,
            "records": [],
            "latest_by_handoff": {},
            "updated_at": _now(),
        }
        task.state["host_callbacks"] = state
    return state


def _handoff(task: Any, handoff_id: str) -> dict[str, Any]:
    state = task.state.get("tool_handoffs")
    if not isinstance(state, dict):
        raise HostCallbackError("Task does not contain Tool handoffs")
    record = next(
        (
            item
            for item in state.get("records", [])
            if isinstance(item, dict) and item.get("handoff_id") == handoff_id
        ),
        None,
    )
    if not isinstance(record, dict):
        raise HostCallbackError(f"Unknown Tool handoff: {handoff_id}")
    return record


class AuthenticatedHostCallbackService:
    """Stable Host result protocol with authentication, lease, etag, and hash checks."""

    def __init__(
        self,
        workspace: Path,
        *,
        runtime: Any,
        store: TaskStore | None = None,
        credentials: HostCredentialStore | None = None,
        leases: TaskLeaseService | None = None,
    ) -> None:
        self.workspace = workspace
        self.runtime = runtime
        self.store = store or TaskStore(workspace)
        self.credentials = credentials or HostCredentialStore(workspace)
        self.leases = leases or TaskLeaseService(workspace, store=self.store)

    def submit_result(
        self,
        project: str,
        task_id: str,
        handoff_id: str,
        *,
        bearer_token: str,
        lease_token: str,
        expected_task_etag: str,
        content: bytes,
        filename: str,
        mime_type: str,
        content_sha256: str | None = None,
        width: int | None = None,
        height: int | None = None,
        model_id: str | None = None,
        tool_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> Any:
        if not content:
            raise ValueError("Submitted Host result content must not be empty")
        normalized_filename = Path(filename).name
        if not normalized_filename or normalized_filename in {".", ".."}:
            raise ValueError("Submitted Host result filename is invalid")
        normalized_mime = mime_type.strip().lower()
        if not normalized_mime:
            raise ValueError("mime_type must not be empty")

        task = self.store.load(project, task_id)
        handoff = _handoff(task, handoff_id)
        expected_host_id = str(handoff.get("host_id") or "")
        actor = self.credentials.authenticate(
            bearer_token,
            required_capabilities=(HOST_RESULT_CAPABILITY,),
            expected_host_id=expected_host_id,
        )
        actual_sha256 = hashlib.sha256(content).hexdigest()
        if content_sha256 is not None and content_sha256 != actual_sha256:
            raise HostCallbackError(
                f"Host result content SHA-256 mismatch: expected {content_sha256}, actual {actual_sha256}"
            )
        expected_tool_id = str(handoff.get("tool_id") or "")
        submitted_tool_id = tool_id or expected_tool_id
        if submitted_tool_id != expected_tool_id:
            raise HostCallbackError(
                f"Host result Tool mismatch: expected {expected_tool_id}, got {submitted_tool_id}"
            )
        execution_id = str(handoff.get("execution_id") or "")
        normalized_request_id = request_id or execution_id or handoff_id
        identity = {
            "project": project,
            "task_id": task_id,
            "handoff_id": handoff_id,
            "execution_id": execution_id,
            "tool_id": submitted_tool_id,
            "request_id": normalized_request_id,
            "actor_credential_id": actor.credential_id,
            "content_sha256": actual_sha256,
            "filename": normalized_filename,
            "mime_type": normalized_mime,
        }
        callback_id = "callback-" + _canonical_hash(identity)[:16]

        callback_state = _state(task)
        existing = next(
            (
                item
                for item in callback_state.get("records", [])
                if isinstance(item, dict) and item.get("callback_id") == callback_id
            ),
            None,
        )
        if isinstance(existing, dict) and existing.get("status") == "completed":
            return task
        if handoff.get("status") != "waiting-for-result":
            raise HostCallbackError(
                f"Tool handoff is not waiting for a result: {handoff.get('status')}"
            )

        lease = self.leases.validate(
            project,
            task_id,
            lease_token,
            actor,
            expected_task_etag=expected_task_etag,
        )
        envelope = {
            "schema_version": HOST_CALLBACK_SCHEMA_VERSION,
            "callback_id": callback_id,
            "project": project,
            "task_id": task_id,
            "handoff_id": handoff_id,
            "execution_id": execution_id,
            "tool_id": submitted_tool_id,
            "host_id": expected_host_id,
            "request_id": normalized_request_id,
            "content_sha256": actual_sha256,
            "filename": normalized_filename,
            "mime_type": normalized_mime,
            "width": width,
            "height": height,
            "model_id": model_id,
            "expected_task_etag": expected_task_etag,
            "lease_id": lease.get("lease_id"),
            "metadata": dict(metadata or {}),
            "submitted_at": _now(),
        }

        try:
            updated = self.runtime.submit_tool_result(
                project,
                task_id,
                handoff_id,
                content=content,
                filename=normalized_filename,
                mime_type=normalized_mime,
                width=width,
                height=height,
                model_id=model_id,
                tool_id=submitted_tool_id,
                metadata={
                    **dict(metadata or {}),
                    "authenticated_actor": actor.to_dict(),
                    "host_callback_id": callback_id,
                    "content_sha256": actual_sha256,
                },
            )
        except Exception as exc:
            raise HostCallbackError(f"Authenticated Host callback failed: {exc}") from exc

        persisted_state = _state(updated)
        records = persisted_state.setdefault("records", [])
        latest = persisted_state.setdefault("latest_by_handoff", {})
        if not isinstance(records, list) or not isinstance(latest, dict):
            raise ValueError("Invalid persisted Host callback state")
        completed_handoff = _handoff(updated, handoff_id)
        record = {
            "schema_version": HOST_CALLBACK_SCHEMA_VERSION,
            "callback_id": callback_id,
            "status": "completed",
            "actor": actor.to_dict(),
            "lease": lease,
            "envelope": envelope,
            "artifact_id": completed_handoff.get("artifact_id"),
            "completed_at": _now(),
            "error": None,
        }
        records.append(record)
        latest[handoff_id] = callback_id
        persisted_state["updated_at"] = record["completed_at"]
        updated.record(
            "host-api",
            "completed",
            f"Authenticated Host callback {callback_id} registered Artifact {record['artifact_id']}.",
        )
        self.store.save(updated)
        self.leases.consume(
            project,
            task_id,
            lease_token,
            actor,
            operation_id=callback_id,
        )
        return updated

    def list(self, project: str, task_id: str) -> tuple[dict[str, Any], ...]:
        task = self.store.load(project, task_id)
        state = task.state.get("host_callbacks")
        if not isinstance(state, dict):
            return ()
        return tuple(item for item in state.get("records", []) if isinstance(item, dict))

    def get(self, project: str, task_id: str, callback_id: str) -> dict[str, Any]:
        for record in self.list(project, task_id):
            if record.get("callback_id") == callback_id:
                return dict(record)
        raise ValueError(f"Unknown Host callback: {callback_id}")


__all__ = [
    "AuthenticatedHostCallbackService",
    "HOST_CALLBACK_SCHEMA_VERSION",
    "HOST_RESULT_CAPABILITY",
    "HostCallbackError",
]
