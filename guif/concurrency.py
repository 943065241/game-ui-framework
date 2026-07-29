from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from guif.auth import AuthenticatedActor
from guif.runtime.store import TaskStore

TASK_LEASE_SCHEMA_VERSION = 1
LEASE_TOKEN_PREFIX = "guifl1"
MIN_LEASE_SECONDS = 15
MAX_LEASE_SECONDS = 3600


class ConcurrencyError(RuntimeError):
    pass


class LeaseError(ConcurrencyError):
    pass


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _now() -> str:
    return _now_dt().isoformat()


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def task_etag(task: Any) -> str:
    payload = task.to_dict() if hasattr(task, "to_dict") else task
    return "task-sha256:" + _canonical_hash(payload)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def _parse_time(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        raise LeaseError("Task lease timestamp is invalid")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise LeaseError("Task lease timestamp is invalid") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


class TaskLeaseService:
    """Exclusive, expiring Task leases guarded by optimistic Task etags."""

    def __init__(self, workspace: Path, *, store: TaskStore | None = None) -> None:
        self.workspace = workspace
        self.store = store or TaskStore(workspace)

    def _path(self, project: str, task_id: str) -> Path:
        return self.store.run_dir(project, task_id) / "task-lease.json"

    def current_etag(self, project: str, task_id: str) -> str:
        return task_etag(self.store.load(project, task_id))

    def get(self, project: str, task_id: str) -> dict[str, Any]:
        path = self._path(project, task_id)
        if not path.is_file():
            return {
                "schema_version": TASK_LEASE_SCHEMA_VERSION,
                "project": project,
                "task_id": task_id,
                "status": "unleased",
            }
        record = _read_json(path)
        if record.get("status") == "active" and _parse_time(record.get("expires_at")) <= _now_dt():
            record["status"] = "expired"
            record["expired_at"] = _now()
            _write_json(path, record)
        return record

    def acquire(
        self,
        project: str,
        task_id: str,
        actor: AuthenticatedActor,
        *,
        expected_task_etag: str | None = None,
        ttl_seconds: int = 300,
        purpose: str = "exclusive-task-operation",
    ) -> dict[str, Any]:
        if not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool):
            raise ValueError("ttl_seconds must be an integer")
        if ttl_seconds < MIN_LEASE_SECONDS or ttl_seconds > MAX_LEASE_SECONDS:
            raise ValueError(
                f"ttl_seconds must be between {MIN_LEASE_SECONDS} and {MAX_LEASE_SECONDS}"
            )
        normalized_purpose = purpose.strip()
        if not normalized_purpose:
            raise ValueError("purpose must not be empty")

        current_etag = self.current_etag(project, task_id)
        if expected_task_etag is not None and expected_task_etag != current_etag:
            raise ConcurrencyError(
                f"Task etag mismatch: expected {expected_task_etag}, current {current_etag}"
            )
        existing = self.get(project, task_id)
        if existing.get("status") == "active":
            raise LeaseError(
                f"Task already has an active lease {existing.get('lease_id')} owned by "
                f"{existing.get('actor', {}).get('actor_id')} until {existing.get('expires_at')}"
            )

        lease_id = "lease-" + uuid4().hex[:16]
        secret = secrets.token_urlsafe(32)
        acquired_at = _now_dt()
        record = {
            "schema_version": TASK_LEASE_SCHEMA_VERSION,
            "lease_id": lease_id,
            "project": project,
            "task_id": task_id,
            "status": "active",
            "purpose": normalized_purpose,
            "actor": actor.to_dict(),
            "base_task_etag": current_etag,
            "token_hash": hashlib.sha256(secret.encode("utf-8")).hexdigest(),
            "acquired_at": acquired_at.isoformat(),
            "expires_at": (acquired_at + timedelta(seconds=ttl_seconds)).isoformat(),
            "ttl_seconds": ttl_seconds,
            "renewed_at": None,
            "released_at": None,
            "consumed_at": None,
        }
        _write_json(self._path(project, task_id), record)
        return {
            "lease": {key: value for key, value in record.items() if key != "token_hash"},
            "lease_token": f"{LEASE_TOKEN_PREFIX}.{lease_id}.{secret}",
            "secret_visible_once": True,
        }

    def _verify_token(
        self,
        record: dict[str, Any],
        lease_token: str,
        actor: AuthenticatedActor,
        *,
        require_active: bool = True,
    ) -> None:
        parts = lease_token.strip().split(".", 2)
        if len(parts) != 3 or parts[0] != LEASE_TOKEN_PREFIX:
            raise LeaseError("Invalid Task lease token format")
        _, lease_id, secret = parts
        if lease_id != record.get("lease_id"):
            raise LeaseError("Task lease identity mismatch")
        actual = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(str(record.get("token_hash") or ""), actual):
            raise LeaseError("Task lease token verification failed")
        recorded_actor = record.get("actor") if isinstance(record.get("actor"), dict) else {}
        if (
            recorded_actor.get("actor_id") != actor.actor_id
            or recorded_actor.get("credential_id") != actor.credential_id
        ):
            raise LeaseError("Task lease belongs to a different authenticated actor")
        if require_active and record.get("status") != "active":
            raise LeaseError(f"Task lease is not active: {record.get('status')}")
        if require_active and _parse_time(record.get("expires_at")) <= _now_dt():
            record["status"] = "expired"
            record["expired_at"] = _now()
            raise LeaseError("Task lease has expired")

    def validate(
        self,
        project: str,
        task_id: str,
        lease_token: str,
        actor: AuthenticatedActor,
        *,
        expected_task_etag: str,
    ) -> dict[str, Any]:
        path = self._path(project, task_id)
        if not path.is_file():
            raise LeaseError("Task does not have a lease")
        record = _read_json(path)
        try:
            self._verify_token(record, lease_token, actor)
        except LeaseError:
            _write_json(path, record)
            raise
        current_etag = self.current_etag(project, task_id)
        if expected_task_etag != record.get("base_task_etag"):
            raise ConcurrencyError("Operation etag does not match the Task lease base etag")
        if current_etag != expected_task_etag:
            raise ConcurrencyError(
                f"Task changed after lease acquisition: expected {expected_task_etag}, current {current_etag}"
            )
        return {key: value for key, value in record.items() if key != "token_hash"}

    def renew(
        self,
        project: str,
        task_id: str,
        lease_token: str,
        actor: AuthenticatedActor,
        *,
        expected_task_etag: str,
        ttl_seconds: int = 300,
    ) -> dict[str, Any]:
        if ttl_seconds < MIN_LEASE_SECONDS or ttl_seconds > MAX_LEASE_SECONDS:
            raise ValueError(
                f"ttl_seconds must be between {MIN_LEASE_SECONDS} and {MAX_LEASE_SECONDS}"
            )
        self.validate(
            project,
            task_id,
            lease_token,
            actor,
            expected_task_etag=expected_task_etag,
        )
        path = self._path(project, task_id)
        record = _read_json(path)
        timestamp = _now_dt()
        record["ttl_seconds"] = ttl_seconds
        record["renewed_at"] = timestamp.isoformat()
        record["expires_at"] = (timestamp + timedelta(seconds=ttl_seconds)).isoformat()
        _write_json(path, record)
        return {key: value for key, value in record.items() if key != "token_hash"}

    def release(
        self,
        project: str,
        task_id: str,
        lease_token: str,
        actor: AuthenticatedActor,
        *,
        reason: str = "released",
    ) -> dict[str, Any]:
        path = self._path(project, task_id)
        if not path.is_file():
            raise LeaseError("Task does not have a lease")
        record = _read_json(path)
        self._verify_token(record, lease_token, actor, require_active=False)
        if record.get("status") in {"released", "consumed"}:
            return {key: value for key, value in record.items() if key != "token_hash"}
        record["status"] = "released"
        record["released_at"] = _now()
        record["release_reason"] = reason.strip() or "released"
        _write_json(path, record)
        return {key: value for key, value in record.items() if key != "token_hash"}

    def consume(
        self,
        project: str,
        task_id: str,
        lease_token: str,
        actor: AuthenticatedActor,
        *,
        operation_id: str,
    ) -> dict[str, Any]:
        path = self._path(project, task_id)
        if not path.is_file():
            raise LeaseError("Task does not have a lease")
        record = _read_json(path)
        self._verify_token(record, lease_token, actor)
        record["status"] = "consumed"
        record["consumed_at"] = _now()
        record["operation_id"] = operation_id
        _write_json(path, record)
        return {key: value for key, value in record.items() if key != "token_hash"}


__all__ = [
    "ConcurrencyError",
    "LeaseError",
    "TASK_LEASE_SCHEMA_VERSION",
    "TaskLeaseService",
    "task_etag",
]
