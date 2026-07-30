from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from guif.artifacts import ARTIFACT_REGISTRY_SCHEMA_VERSION, ARTIFACT_SCHEMA_VERSION, validate_artifact_record
from guif.private_data import PrivateDataLayout

SOURCE_IMPORT_SCHEMA_VERSION = 1
SOURCE_KINDS = {
    "conversation-temporary-image",
    "user-upload",
    "external-file",
    "guif-artifact",
}
SOURCE_USAGES = {"editable-source", "theme-reference", "master-reference"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_identity(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized or Path(normalized).name != normalized:
        raise ValueError(f"Invalid {label}: {value}")
    return normalized


def _safe_filename(value: str) -> str:
    name = Path(value).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", name).strip(".-")
    return cleaned or "source-image.bin"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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
        raise ValueError(f"Expected source import object: {path}")
    return value


def public_source_ref(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SOURCE_IMPORT_SCHEMA_VERSION,
        "source_id": record.get("source_id"),
        "status": record.get("status"),
        "source_kind": record.get("source_kind"),
        "usages": list(record.get("usages", [])),
        "mime_type": record.get("mime_type"),
        "width": record.get("width"),
        "height": record.get("height"),
        "privacy": "private",
    }


class PrivateSourceImportStore:
    """Private source-image library outside framework and Project Git."""

    def __init__(self, workspace: Path, *, data_root: Path | None = None) -> None:
        self.workspace = workspace.resolve()
        self.layout = PrivateDataLayout(self.workspace, data_root)

    def _project_root(self, project: str) -> Path:
        return self.layout.source_imports / _safe_identity(project, "project")

    def _source_root(self, project: str, source_id: str) -> Path:
        return self._project_root(project) / _safe_identity(source_id, "source_id")

    def _record_path(self, project: str, source_id: str) -> Path:
        return self._source_root(project, source_id) / "source.json"

    def stage(
        self,
        project: str,
        conversation_id: str,
        source_path: Path,
        *,
        source_kind: str = "user-upload",
        usage: str = "editable-source",
        mime_type: str | None = None,
        width: int | None = None,
        height: int | None = None,
        actor: str = "conversation-user",
    ) -> dict[str, Any]:
        normalized_project = _safe_identity(project, "project")
        normalized_conversation = _safe_identity(conversation_id, "conversation_id")
        normalized_kind = source_kind.strip()
        normalized_usage = usage.strip()
        normalized_actor = actor.strip()
        if normalized_kind not in SOURCE_KINDS:
            raise ValueError("source_kind is unsupported")
        if normalized_usage not in SOURCE_USAGES:
            raise ValueError("usage is unsupported")
        if not normalized_actor:
            raise ValueError("actor must not be empty")

        path = source_path.expanduser().resolve(strict=True)
        if not path.is_file():
            raise ValueError("Source image must be a file")
        content = path.read_bytes()
        if not content:
            raise ValueError("Source image must not be empty")
        resolved_mime = (mime_type or mimetypes.guess_type(path.name)[0] or "").strip().lower()
        if not resolved_mime.startswith("image/"):
            raise ValueError("Source import accepts image files only")
        if width is not None and width <= 0:
            raise ValueError("width must be positive")
        if height is not None and height <= 0:
            raise ValueError("height must be positive")

        sha256 = hashlib.sha256(content).hexdigest()
        source_id = "source-" + sha256[:20]
        root = self._source_root(normalized_project, source_id)
        root.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(root, 0o700)
        except OSError:
            pass
        filename = _safe_filename(path.name)
        stored_path = root / filename
        if stored_path.exists() and stored_path.read_bytes() != content:
            raise ValueError("Private source filename collision")
        stored_path.write_bytes(content)
        try:
            os.chmod(stored_path, 0o600)
        except OSError:
            pass

        record_path = self._record_path(normalized_project, source_id)
        existing = _read_json(record_path) if record_path.is_file() else None
        usages = set(existing.get("usages", [])) if isinstance(existing, dict) else set()
        usages.add(normalized_usage)
        conversations = set(existing.get("conversation_ids", [])) if isinstance(existing, dict) else set()
        conversations.add(normalized_conversation)
        timestamp = _now()
        record = {
            "schema_version": SOURCE_IMPORT_SCHEMA_VERSION,
            "source_id": source_id,
            "project": normalized_project,
            "status": "registered",
            "source_kind": normalized_kind,
            "usages": sorted(usages),
            "conversation_ids": sorted(conversations),
            "filename": filename,
            "mime_type": resolved_mime,
            "size_bytes": len(content),
            "sha256": sha256,
            "width": width,
            "height": height,
            "private_path": str(stored_path),
            "actor": normalized_actor,
            "created_at": existing.get("created_at", timestamp) if isinstance(existing, dict) else timestamp,
            "updated_at": timestamp,
        }
        _write_json(record_path, record)
        return record

    def get(self, project: str, source_id: str) -> dict[str, Any]:
        path = self._record_path(project, source_id)
        if not path.is_file():
            raise ValueError(f"Unknown private source image: {source_id}")
        record = _read_json(path)
        private_path = Path(str(record.get("private_path") or ""))
        if not private_path.is_file():
            raise ValueError(f"Private source image is missing: {source_id}")
        content = private_path.read_bytes()
        if hashlib.sha256(content).hexdigest() != record.get("sha256"):
            raise ValueError(f"Private source image hash mismatch: {source_id}")
        return record

    def list(self, project: str) -> tuple[dict[str, Any], ...]:
        root = self._project_root(project)
        if not root.is_dir():
            return ()
        records: list[dict[str, Any]] = []
        for path in root.glob("*/source.json"):
            try:
                records.append(self.get(project, path.parent.name))
            except (OSError, ValueError, json.JSONDecodeError):
                continue
        records.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
        return tuple(records)


def attach_sources_to_task(
    task: Any,
    run_dir: Path,
    source_records: Iterable[dict[str, Any]],
) -> tuple[dict[str, Any], ...]:
    artifact_dir = run_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    registry = task.state.get("artifact_registry")
    if not isinstance(registry, dict):
        registry = {
            "schema_version": ARTIFACT_REGISTRY_SCHEMA_VERSION,
            "task_id": task.task_id,
            "project": task.project,
            "records": [],
            "updated_at": _now(),
        }
        task.state["artifact_registry"] = registry
    records = registry.setdefault("records", [])
    if not isinstance(records, list):
        raise ValueError("Invalid persisted Artifact registry")

    attached: list[dict[str, Any]] = []
    for source in source_records:
        private_path = Path(str(source.get("private_path") or ""))
        content = private_path.read_bytes()
        sha256 = hashlib.sha256(content).hexdigest()
        if sha256 != source.get("sha256"):
            raise ValueError(f"Private source image hash mismatch: {source.get('source_id')}")
        source_id = str(source.get("source_id") or "")
        artifact_id = "artifact-source-" + hashlib.sha256(
            f"{task.task_id}:{source_id}:{sha256}".encode("utf-8")
        ).hexdigest()[:16]
        filename = _safe_filename(str(source.get("filename") or "source-image.bin"))
        destination = artifact_dir / f"{artifact_id}-{filename}"
        if destination.exists() and destination.read_bytes() != content:
            raise ValueError("Task source Artifact collision")
        destination.write_bytes(content)
        record = {
            "schema_version": ARTIFACT_SCHEMA_VERSION,
            "artifact_id": artifact_id,
            "task_id": task.task_id,
            "project": task.project,
            "job_id": "source-import",
            "artifact_kind": "source-image",
            "operation": "import",
            "status": "registered",
            "provider": {
                "schema_version": 1,
                "provider_id": "user-source-import",
                "request_id": source_id,
                "filename": filename,
                "mime_type": source.get("mime_type"),
                "width": source.get("width"),
                "height": source.get("height"),
                "model_id": None,
                "simulation": False,
                "visual": True,
                "metadata": {"source_kind": source.get("source_kind")},
            },
            "file": {
                "path": str(destination.relative_to(run_dir)),
                "sha256": sha256,
                "mime_type": source.get("mime_type"),
                "size_bytes": len(content),
                "width": source.get("width"),
                "height": source.get("height"),
            },
            "simulation": False,
            "visual": True,
            "output_contract": {
                "source_usage": list(source.get("usages", [])),
                "immutable_source": True,
            },
            "references": [],
            "provenance": {
                "source_id": source_id,
                "source_kind": source.get("source_kind"),
                "conversation_ids": list(source.get("conversation_ids", [])),
                "imported_sha256": sha256,
            },
            "qa": {
                "status": "source-registered",
                "reason": "Imported source registration does not imply semantic visual approval.",
            },
            "created_at": _now(),
        }
        errors = validate_artifact_record(record)
        if errors:
            raise ValueError("Invalid imported source Artifact: " + "; ".join(errors))
        existing = next(
            (item for item in records if isinstance(item, dict) and item.get("artifact_id") == artifact_id),
            None,
        )
        if existing is None:
            records.append(record)
            task.add_output("imported-source-artifact", record, agent="source-import")
        else:
            record = existing
        attached.append(record)
    registry["updated_at"] = _now()
    return tuple(attached)


def source_reference(source: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
    usages = set(str(item) for item in source.get("usages", []))
    if "master-reference" in usages:
        role = "master-reference"
    elif "theme-reference" in usages:
        role = "theme-reference"
    else:
        role = "approved-edit-source"
    file_data = artifact.get("file") if isinstance(artifact.get("file"), dict) else {}
    filename = str(source.get("filename") or "source-image.png")
    return {
        "resource_id": source.get("source_id"),
        "artifact_id": artifact.get("artifact_id"),
        "role": role,
        "storage_scope": "private-run",
        "immutable": True,
        "expected_sha256": file_data.get("sha256"),
        "manifest": {
            "id": source.get("source_id"),
            "type": "source-image",
            "width": source.get("width"),
            "height": source.get("height"),
            "format": Path(filename).suffix.lstrip(".").lower() or "png",
            "source": file_data.get("path"),
            "mime_type": source.get("mime_type"),
        },
        "reasons": ["User approved this registered private image as an editing source."],
    }


__all__ = [
    "PrivateSourceImportStore",
    "SOURCE_IMPORT_SCHEMA_VERSION",
    "SOURCE_KINDS",
    "SOURCE_USAGES",
    "attach_sources_to_task",
    "public_source_ref",
    "source_reference",
]
