from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from guif.private_data import PrivateDataLayout

THEME_RECORD_SCHEMA_VERSION = 1
THEME_BINDING_SCHEMA_VERSION = 1
THEME_CONTENT_FIELDS = (
    "description",
    "palette",
    "materials",
    "lighting",
    "must_include",
    "avoid",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalize_content(content: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(content)
    normalized.setdefault("description", "")
    normalized.setdefault("palette", [])
    normalized.setdefault("materials", [])
    normalized.setdefault("lighting", "")
    normalized.setdefault("must_include", [])
    normalized.setdefault("avoid", [])
    errors: list[str] = []
    for field in ("description", "lighting"):
        if not isinstance(normalized.get(field), str):
            errors.append(f"Theme {field} must be a string")
    for field in ("palette", "materials", "must_include", "avoid"):
        value = normalized.get(field)
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            errors.append(f"Theme {field} must be a list of strings")
    if errors:
        raise ValueError("Invalid Theme content: " + "; ".join(errors))
    return normalized


def public_theme_ref(record: dict[str, Any]) -> dict[str, Any]:
    """Return an opaque reference safe to persist outside the private Theme Library."""

    return {
        "schema_version": THEME_BINDING_SCHEMA_VERSION,
        "theme_id": record["theme_id"],
        "version": record["version"],
        "snapshot_hash": record["snapshot_hash"],
        "privacy": "private",
    }


class PrivateThemeStore:
    """File-backed private Theme Library outside the framework/project Git tree."""

    def __init__(self, workspace: Path, *, data_root: Path | None = None) -> None:
        self.workspace = workspace
        self.layout = PrivateDataLayout(workspace, data_root)

    @property
    def root(self) -> Path:
        return self.layout.root

    def _theme_dir(self, theme_id: str) -> Path:
        if not theme_id or Path(theme_id).name != theme_id:
            raise ValueError(f"Invalid theme_id: {theme_id}")
        return self.layout.themes / theme_id

    def _version_path(self, theme_id: str, version: int) -> Path:
        if not isinstance(version, int) or isinstance(version, bool) or version <= 0:
            raise ValueError("Theme version must be a positive integer")
        return self._theme_dir(theme_id) / "versions" / f"{version}.json"

    def _index_path(self, theme_id: str) -> Path:
        return self._theme_dir(theme_id) / "index.json"

    def list(self, *, include_archived: bool = False) -> tuple[dict[str, Any], ...]:
        if not self.layout.themes.exists():
            return ()
        records: list[dict[str, Any]] = []
        for path in sorted(self.layout.themes.glob("*/index.json")):
            try:
                item = _read_json(path)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if include_archived or item.get("status") != "archived":
                records.append(item)
        records.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
        return tuple(records)

    def create(
        self,
        name: str,
        content: dict[str, Any],
        *,
        actor: str = "host",
        source_conversation_id: str | None = None,
        status: str = "published",
    ) -> dict[str, Any]:
        normalized_name = name.strip()
        normalized_actor = actor.strip()
        if not normalized_name or not normalized_actor:
            raise ValueError("Theme name and actor must not be empty")
        if status not in {"draft", "published", "archived"}:
            raise ValueError("Theme status must be draft, published, or archived")
        normalized_content = _normalize_content(content)
        theme_id = "theme-" + uuid4().hex[:16]
        created_at = _now()
        record = {
            "schema_version": THEME_RECORD_SCHEMA_VERSION,
            "theme_id": theme_id,
            "version": 1,
            "parent_version": None,
            "name": normalized_name,
            "status": status,
            "privacy": "private",
            "content": normalized_content,
            "sources": [
                {
                    "type": "conversation" if source_conversation_id else "host",
                    "conversation_id": source_conversation_id,
                    "actor": normalized_actor,
                    "recorded_at": created_at,
                }
            ],
            "created_at": created_at,
            "updated_at": created_at,
        }
        record["snapshot_hash"] = _canonical_hash(
            {"theme_id": theme_id, "version": 1, "name": normalized_name, "content": normalized_content}
        )
        _write_json(self._version_path(theme_id, 1), record)
        index = {
            "schema_version": THEME_RECORD_SCHEMA_VERSION,
            "theme_id": theme_id,
            "name": normalized_name,
            "status": status,
            "privacy": "private",
            "latest_version": 1,
            "latest_snapshot_hash": record["snapshot_hash"],
            "created_at": created_at,
            "updated_at": created_at,
        }
        _write_json(self._index_path(theme_id), index)
        return record

    def get(self, theme_id: str, version: int | None = None) -> dict[str, Any]:
        index_path = self._index_path(theme_id)
        if not index_path.is_file():
            raise ValueError(f"Unknown private Theme: {theme_id}")
        index = _read_json(index_path)
        resolved_version = version if version is not None else int(index["latest_version"])
        path = self._version_path(theme_id, resolved_version)
        if not path.is_file():
            raise ValueError(f"Unknown private Theme version: {theme_id}@{resolved_version}")
        record = _read_json(path)
        expected = str(record.get("snapshot_hash") or "")
        actual = _canonical_hash(
            {
                "theme_id": record.get("theme_id"),
                "version": record.get("version"),
                "name": record.get("name"),
                "content": record.get("content"),
            }
        )
        if not expected or expected != actual:
            raise ValueError(f"Private Theme snapshot hash mismatch: {theme_id}@{resolved_version}")
        return record

    def derive(
        self,
        theme_id: str,
        updates: dict[str, Any],
        *,
        from_version: int | None = None,
        actor: str = "host",
        source_conversation_id: str | None = None,
        name: str | None = None,
        status: str = "published",
    ) -> dict[str, Any]:
        base = self.get(theme_id, from_version)
        index = _read_json(self._index_path(theme_id))
        next_version = int(index["latest_version"]) + 1
        content = dict(base["content"])
        content.update(updates)
        normalized_content = _normalize_content(content)
        normalized_name = name.strip() if isinstance(name, str) and name.strip() else str(base["name"])
        normalized_actor = actor.strip()
        if not normalized_actor:
            raise ValueError("actor must not be empty")
        if status not in {"draft", "published", "archived"}:
            raise ValueError("Theme status must be draft, published, or archived")
        timestamp = _now()
        record = {
            "schema_version": THEME_RECORD_SCHEMA_VERSION,
            "theme_id": theme_id,
            "version": next_version,
            "parent_version": int(base["version"]),
            "name": normalized_name,
            "status": status,
            "privacy": "private",
            "content": normalized_content,
            "sources": list(base.get("sources", []))
            + [
                {
                    "type": "conversation-update" if source_conversation_id else "host-update",
                    "conversation_id": source_conversation_id,
                    "actor": normalized_actor,
                    "recorded_at": timestamp,
                    "updated_fields": sorted(str(key) for key in updates),
                }
            ],
            "created_at": str(base.get("created_at") or timestamp),
            "updated_at": timestamp,
        }
        record["snapshot_hash"] = _canonical_hash(
            {
                "theme_id": theme_id,
                "version": next_version,
                "name": normalized_name,
                "content": normalized_content,
            }
        )
        _write_json(self._version_path(theme_id, next_version), record)
        index.update(
            {
                "name": normalized_name,
                "status": status,
                "latest_version": next_version,
                "latest_snapshot_hash": record["snapshot_hash"],
                "updated_at": timestamp,
            }
        )
        _write_json(self._index_path(theme_id), index)
        return record

    def _binding_path(self, kind: str, identity: str) -> Path:
        if not identity or Path(identity).name != identity:
            raise ValueError(f"Invalid {kind} identity: {identity}")
        root = self.layout.conversations if kind == "conversation" else self.layout.project_bindings
        return root / f"{identity}.json"

    def bind_conversation(
        self,
        conversation_id: str,
        theme_id: str,
        *,
        version: int | None = None,
        actor: str = "host",
    ) -> dict[str, Any]:
        return self._bind("conversation", conversation_id, theme_id, version=version, actor=actor)

    def bind_project(
        self,
        project: str,
        theme_id: str,
        *,
        version: int | None = None,
        actor: str = "host",
    ) -> dict[str, Any]:
        return self._bind("project", project, theme_id, version=version, actor=actor)

    def _bind(
        self,
        kind: str,
        identity: str,
        theme_id: str,
        *,
        version: int | None,
        actor: str,
    ) -> dict[str, Any]:
        record = self.get(theme_id, version)
        normalized_actor = actor.strip()
        if not normalized_actor:
            raise ValueError("actor must not be empty")
        binding = {
            "schema_version": THEME_BINDING_SCHEMA_VERSION,
            "binding_kind": kind,
            "binding_id": identity,
            "theme_ref": public_theme_ref(record),
            "actor": normalized_actor,
            "bound_at": _now(),
        }
        _write_json(self._binding_path(kind, identity), binding)
        return binding

    def get_binding(self, kind: str, identity: str) -> dict[str, Any] | None:
        path = self._binding_path(kind, identity)
        return _read_json(path) if path.is_file() else None

    def resolve(
        self,
        *,
        project: str | None = None,
        conversation_id: str | None = None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        binding = None
        if conversation_id:
            binding = self.get_binding("conversation", conversation_id)
        if binding is None and project:
            binding = self.get_binding("project", project)
        if not isinstance(binding, dict):
            return None, None
        ref = binding.get("theme_ref") if isinstance(binding.get("theme_ref"), dict) else {}
        theme_id = str(ref.get("theme_id") or "")
        version = ref.get("version")
        if not theme_id or not isinstance(version, int):
            raise ValueError("Invalid private Theme binding")
        record = self.get(theme_id, version)
        if record.get("snapshot_hash") != ref.get("snapshot_hash"):
            raise ValueError("Private Theme binding snapshot hash mismatch")
        return record, dict(ref)

    def prepare_conversation(self, conversation_id: str, *, project: str | None = None) -> dict[str, Any]:
        conversation_binding = self.get_binding("conversation", conversation_id)
        if conversation_binding is not None:
            record, ref = self.resolve(conversation_id=conversation_id)
            return {
                "schema_version": 1,
                "conversation_id": conversation_id,
                "project": project,
                "status": "selected",
                "selected_theme": ref,
                "selected_name": record.get("name") if record else None,
                "candidates": [],
                "next_actions": ["continue-with-selected-theme", "choose-another-theme", "derive-theme"],
            }
        candidates = [
            {
                "theme_id": item.get("theme_id"),
                "name": item.get("name"),
                "latest_version": item.get("latest_version"),
                "updated_at": item.get("updated_at"),
            }
            for item in self.list()
        ]
        return {
            "schema_version": 1,
            "conversation_id": conversation_id,
            "project": project,
            "status": "confirmation-required",
            "selected_theme": None,
            "candidates": candidates,
            "next_actions": ["select-history", "create-theme", "derive-theme", "continue-unbound"],
        }

    def migrate_legacy_project(self, project_root: Path, project: str, *, actor: str = "migration") -> dict[str, Any]:
        themes_dir = project_root / "themes"
        config_path = project_root / "project.json"
        config = _read_json(config_path)
        current = config.get("current_theme")
        imported: list[dict[str, Any]] = []
        selected: dict[str, Any] | None = None
        if themes_dir.is_dir():
            for path in sorted(themes_dir.glob("*.json")):
                legacy = _read_json(path)
                name = str(legacy.get("name") or path.stem)
                content = {field: legacy.get(field) for field in THEME_CONTENT_FIELDS}
                record = self.create(name, content, actor=actor, status="published")
                archive = self.layout.migrations / project / "legacy-themes" / path.name
                _write_json(archive, legacy)
                imported.append({"legacy_path": str(path), "theme_ref": public_theme_ref(record)})
                if current == path.stem:
                    selected = record
                path.unlink()
            try:
                themes_dir.rmdir()
            except OSError:
                pass
        config.pop("current_theme", None)
        config.pop("theme_binding", None)
        _write_json(config_path, config)
        if selected is not None:
            self.bind_project(project, str(selected["theme_id"]), version=int(selected["version"]), actor=actor)
        report = {
            "schema_version": 1,
            "project": project,
            "imported": imported,
            "selected_theme": public_theme_ref(selected) if selected else None,
            "legacy_project_theme_removed": True,
            "private_archive_root": str(self.layout.migrations / project / "legacy-themes"),
            "completed_at": _now(),
        }
        _write_json(self.layout.migrations / project / "migration-report.json", report)
        return report


__all__ = [
    "PrivateThemeStore",
    "THEME_BINDING_SCHEMA_VERSION",
    "THEME_RECORD_SCHEMA_VERSION",
    "public_theme_ref",
]
