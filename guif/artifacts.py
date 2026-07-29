from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from guif.providers.base import ExecutionRequest, ExecutionResult

ARTIFACT_SCHEMA_VERSION = 1
ARTIFACT_REGISTRY_SCHEMA_VERSION = 1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _project_root(task: Any) -> Path:
    value = getattr(task.context, "project_root", None)
    if not value:
        raise ValueError("Artifact reference binding requires RuntimeContext.project_root")
    return Path(str(value))


def bind_references(task: Any, references: list[dict[str, Any]]) -> tuple[dict[str, Any], ...]:
    project_root = _project_root(task)
    bound: list[dict[str, Any]] = []
    for reference in references:
        manifest = reference.get("manifest") if isinstance(reference.get("manifest"), dict) else {}
        source_value = manifest.get("source")
        item: dict[str, Any] = {
            "resource_id": reference.get("resource_id"),
            "role": reference.get("role"),
            "source": source_value,
            "status": "unbound",
            "path": None,
            "sha256": None,
            "size_bytes": None,
        }
        if isinstance(source_value, str) and source_value.strip():
            source_path = Path(source_value)
            resolved = source_path if source_path.is_absolute() else project_root / source_path
            try:
                resolved = resolved.resolve(strict=True)
                resolved.relative_to(project_root.resolve())
            except (FileNotFoundError, ValueError):
                item["status"] = "missing-or-outside-project"
            else:
                if resolved.is_file():
                    content = resolved.read_bytes()
                    item.update(
                        {
                            "status": "bound",
                            "path": str(resolved.relative_to(project_root.resolve())),
                            "sha256": _sha256_bytes(content),
                            "size_bytes": len(content),
                        }
                    )
        bound.append(item)
    return tuple(bound)


def validate_artifact_record(record: object) -> list[str]:
    if not isinstance(record, dict):
        return ["Artifact record must be an object"]
    errors: list[str] = []
    required = (
        "schema_version",
        "artifact_id",
        "task_id",
        "project",
        "job_id",
        "artifact_kind",
        "status",
        "provider",
        "file",
        "simulation",
        "visual",
        "output_contract",
        "references",
        "provenance",
        "qa",
        "created_at",
    )
    for field in required:
        if field not in record:
            errors.append(f"Missing Artifact field: {field}")
    if record.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
        errors.append(f"schema_version must be {ARTIFACT_SCHEMA_VERSION}")
    if record.get("status") not in {"registered", "stale", "failed"}:
        errors.append("status must be registered, stale, or failed")
    for field in ("provider", "file", "output_contract", "provenance", "qa"):
        if field in record and not isinstance(record[field], dict):
            errors.append(f"{field} must be an object")
    if "references" in record and not isinstance(record["references"], list):
        errors.append("references must be a list")
    if not isinstance(record.get("simulation"), bool):
        errors.append("simulation must be a boolean")
    if not isinstance(record.get("visual"), bool):
        errors.append("visual must be a boolean")
    file_data = record.get("file")
    if isinstance(file_data, dict):
        for field in ("path", "sha256", "mime_type", "size_bytes"):
            if field not in file_data:
                errors.append(f"file missing field: {field}")
    return errors


def register_artifact(
    task: Any,
    run_dir: Path,
    request: ExecutionRequest,
    result: ExecutionResult,
) -> dict[str, Any]:
    filename = Path(result.filename).name
    if not filename or filename in {".", ".."}:
        raise ValueError("Provider returned an invalid Artifact filename")
    artifact_dir = run_dir / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    content_sha = _sha256_bytes(result.content)
    artifact_id = "artifact-" + hashlib.sha256(
        f"{task.task_id}:{request.job_id}:{result.provider_id}:{content_sha}".encode("utf-8")
    ).hexdigest()[:16]
    path = artifact_dir / f"{artifact_id}-{filename}"
    if path.exists() and path.read_bytes() != result.content:
        raise ValueError(f"Artifact path collision: {path.name}")
    path.write_bytes(result.content)

    output_contract = (
        request.job.get("output_contract")
        if isinstance(request.job.get("output_contract"), dict)
        else {}
    )
    record = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "artifact_id": artifact_id,
        "task_id": task.task_id,
        "project": task.project,
        "job_id": request.job_id,
        "artifact_kind": request.job.get("artifact_kind"),
        "operation": request.job.get("operation"),
        "status": "registered",
        "provider": result.metadata_dict(),
        "file": {
            "path": str(path.relative_to(run_dir)),
            "sha256": content_sha,
            "mime_type": result.mime_type,
            "size_bytes": len(result.content),
            "width": result.width,
            "height": result.height,
        },
        "simulation": result.simulation,
        "visual": result.visual,
        "output_contract": dict(output_contract),
        "references": list(request.references),
        "provenance": {
            "execution_id": request.execution_id,
            "prompt_output": "model-neutral-prompt-ir",
            "prompt_ir_schema_version": task.state.get("prompt_ir", {}).get("schema_version"),
            "approval_snapshot": dict(request.approval_snapshot),
        },
        "qa": {
            "status": "not-run",
            "reason": "Artifact registration does not imply visual or semantic QA approval.",
        },
        "created_at": _now(),
    }
    errors = validate_artifact_record(record)
    if errors:
        raise ValueError("Invalid Artifact record: " + "; ".join(errors))

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
    existing = next(
        (
            item
            for item in records
            if isinstance(item, dict) and item.get("artifact_id") == artifact_id
        ),
        None,
    )
    if existing is None:
        records.append(record)
    else:
        record = existing
    registry["updated_at"] = _now()

    if not any(
        isinstance(output, dict)
        and output.get("type") == "generated-artifact"
        and isinstance(output.get("value"), dict)
        and output["value"].get("artifact_id") == artifact_id
        for output in task.outputs
    ):
        task.add_output("generated-artifact", record, agent=f"provider:{result.provider_id}")
    return record


def list_artifacts(task: Any) -> tuple[dict[str, Any], ...]:
    registry = task.state.get("artifact_registry")
    if not isinstance(registry, dict):
        return ()
    return tuple(item for item in registry.get("records", []) if isinstance(item, dict))


def get_artifact(task: Any, artifact_id: str) -> dict[str, Any]:
    for record in list_artifacts(task):
        if record.get("artifact_id") == artifact_id:
            return record
    raise ValueError(f"Unknown Artifact: {artifact_id}")
