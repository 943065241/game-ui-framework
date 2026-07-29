from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from guif.compatibility import SUPPORTED_PRIVATE_SCHEMAS
from guif.private_data import PrivateDataLayout

PRIVATE_MIGRATION_SCHEMA_VERSION = 1
_FORBIDDEN_SECRET_KEYS = {
    "bearer_token",
    "lease_token",
    "claim_token",
    "raw_secret",
    "plaintext_secret",
}


class PrivateMigrationError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
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


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PrivateMigrationError(f"Invalid private JSON record: {path}") from exc
    if not isinstance(value, dict):
        raise PrivateMigrationError(f"Private JSON record must be an object: {path}")
    return value


def _secret_paths(value: Any, prefix: str = "") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if str(key).casefold() in _FORBIDDEN_SECRET_KEYS:
                paths.append(path)
            paths.extend(_secret_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            paths.extend(_secret_paths(child, f"{prefix}[{index}]"))
    return paths


class PrivateSchemaMigrator:
    """Detect and repair supported private records without silent upgrades.

    Alpha.28 keeps Conversation Workflow schema version 1 compatible. The
    migration fills fields introduced by the frozen MVP facade and records the
    operation. Unknown future schemas and raw secret fields are blocked rather
    than rewritten.
    """

    def __init__(self, workspace: Path, *, data_root: Path | None = None) -> None:
        self.workspace = workspace.resolve()
        self.layout = PrivateDataLayout(self.workspace, data_root)

    def _conversation_records(self) -> tuple[Path, ...]:
        root = self.layout.conversation_workflows
        if not root.is_dir():
            return ()
        return tuple(sorted(root.glob("*/conversation-*.json")))

    @staticmethod
    def _repair_conversation(record: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
        repaired = dict(record)
        changes: list[str] = []
        defaults: tuple[tuple[str, Any], ...] = (
            ("schema_version", 1),
            ("status", "active"),
            ("continue_unbound", False),
            ("active_task_id", None),
            ("request_records", {}),
            ("checkpoint", None),
            ("history", []),
        )
        for key, default in defaults:
            if key not in repaired:
                repaired[key] = default
                changes.append(f"add:{key}")
        privacy = repaired.get("privacy")
        expected_privacy = {
            "storage": "private-data-store",
            "framework_git_mutated": False,
            "project_git_mutated": False,
            "raw_secrets_persisted": False,
        }
        if not isinstance(privacy, dict):
            repaired["privacy"] = expected_privacy
            changes.append("add:privacy")
        else:
            merged = dict(privacy)
            for key, value in expected_privacy.items():
                if key not in merged:
                    merged[key] = value
                    changes.append(f"add:privacy.{key}")
            repaired["privacy"] = merged
        compatibility = repaired.get("compatibility")
        expected_compatibility = {
            "public_api_version": 1,
            "conversation_schema": 1,
            "migrated_by": "alpha.28-private-schema-migrator",
        }
        if not isinstance(compatibility, dict):
            repaired["compatibility"] = expected_compatibility
            changes.append("add:compatibility")
        else:
            merged = dict(compatibility)
            for key, value in expected_compatibility.items():
                if key not in merged:
                    merged[key] = value
                    changes.append(f"add:compatibility.{key}")
            repaired["compatibility"] = merged
        return repaired, changes

    def scan(self) -> dict[str, Any]:
        records: list[dict[str, Any]] = []
        blocked = 0
        pending = 0
        supported = set(SUPPORTED_PRIVATE_SCHEMAS["conversation-workflow"])
        for path in self._conversation_records():
            relative = path.relative_to(self.layout.root).as_posix()
            try:
                record = _read_object(path)
            except PrivateMigrationError as exc:
                blocked += 1
                records.append(
                    {
                        "path": relative,
                        "kind": "conversation-workflow",
                        "status": "blocked",
                        "reason": str(exc),
                        "changes": [],
                    }
                )
                continue
            secrets = _secret_paths(record)
            version = record.get("schema_version", 1)
            if not isinstance(version, int) or isinstance(version, bool) or version not in supported:
                blocked += 1
                records.append(
                    {
                        "path": relative,
                        "kind": "conversation-workflow",
                        "status": "blocked",
                        "reason": f"unsupported schema_version: {version}",
                        "changes": [],
                    }
                )
                continue
            if secrets:
                blocked += 1
                records.append(
                    {
                        "path": relative,
                        "kind": "conversation-workflow",
                        "status": "blocked",
                        "reason": "raw secret-like fields require manual removal",
                        "secret_fields": secrets,
                        "changes": [],
                    }
                )
                continue
            _, changes = self._repair_conversation(record)
            status = "migration-required" if changes else "current"
            if changes:
                pending += 1
            records.append(
                {
                    "path": relative,
                    "kind": "conversation-workflow",
                    "status": status,
                    "schema_version": version,
                    "changes": changes,
                }
            )
        return {
            "schema_version": PRIVATE_MIGRATION_SCHEMA_VERSION,
            "status": "blocked" if blocked else ("migration-required" if pending else "current"),
            "private_root": str(self.layout.root),
            "record_count": len(records),
            "migration_required_count": pending,
            "blocked_count": blocked,
            "records": records,
            "apply_required": pending > 0,
            "scanned_at": _now(),
        }

    def apply(self, *, actor: str = "private-schema-migrator") -> dict[str, Any]:
        normalized_actor = actor.strip()
        if not normalized_actor:
            raise ValueError("actor must not be empty")
        scan = self.scan()
        if scan["blocked_count"]:
            raise PrivateMigrationError(
                "Private schema migration is blocked; resolve unsupported or secret-bearing records first"
            )
        applied: list[dict[str, Any]] = []
        for item in scan["records"]:
            if item["status"] != "migration-required":
                continue
            path = self.layout.root / str(item["path"])
            original = _read_object(path)
            repaired, changes = self._repair_conversation(original)
            history = repaired.setdefault("migration_history", [])
            if not isinstance(history, list):
                raise PrivateMigrationError(f"Invalid migration_history: {path}")
            history.append(
                {
                    "migration": "alpha.28-conversation-v1-repair",
                    "actor": normalized_actor,
                    "changes": changes,
                    "applied_at": _now(),
                }
            )
            _write_json(path, repaired)
            applied.append(
                {
                    "path": item["path"],
                    "changes": changes,
                    "schema_version": repaired["schema_version"],
                }
            )
        report = {
            "schema_version": PRIVATE_MIGRATION_SCHEMA_VERSION,
            "status": "applied",
            "actor": normalized_actor,
            "applied_count": len(applied),
            "applied": applied,
            "compatibility_preserved": True,
            "completed_at": _now(),
        }
        report_path = (
            self.layout.migrations
            / "private-schema"
            / f"migration-{_timestamp()}.json"
        )
        _write_json(report_path, report)
        return {**report, "report": str(report_path)}


__all__ = [
    "PRIVATE_MIGRATION_SCHEMA_VERSION",
    "PrivateMigrationError",
    "PrivateSchemaMigrator",
]
