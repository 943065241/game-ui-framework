from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from guif.paths import project_root

RESOURCE_TYPES = {"sprite", "panel", "button", "icon", "background", "atlas", "font", "other"}
TARGET_ENGINES = {"generic", "unity", "godot", "unreal"}
FILE_FORMATS = {"png", "webp", "jpg", "svg", "json"}
NAME_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class ResourceManifest:
    resource_id: str
    resource_type: str
    width: int
    height: int
    file_format: str
    alpha_required: bool
    target_engine: str
    output_name: str
    source: str | None = None
    import_settings: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["import_settings"] = dict(self.import_settings or {})
        return payload


def validate_resource_data(data: object) -> list[str]:
    if not isinstance(data, dict):
        return ["Resource manifest must be a JSON object"]
    errors: list[str] = []
    required = ("schema_version", "id", "type", "width", "height", "format", "alpha_required", "target_engine", "output_name")
    for field in required:
        if field not in data:
            errors.append(f"Missing field: {field}")
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    resource_id = data.get("id")
    if not isinstance(resource_id, str) or not NAME_PATTERN.fullmatch(resource_id):
        errors.append("id must use lowercase kebab-case")
    if data.get("type") not in RESOURCE_TYPES:
        errors.append(f"type must be one of: {', '.join(sorted(RESOURCE_TYPES))}")
    for field in ("width", "height"):
        value = data.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            errors.append(f"{field} must be a positive integer")
    file_format = data.get("format")
    if file_format not in FILE_FORMATS:
        errors.append(f"format must be one of: {', '.join(sorted(FILE_FORMATS))}")
    if not isinstance(data.get("alpha_required"), bool):
        errors.append("alpha_required must be a boolean")
    elif data.get("alpha_required") and file_format == "jpg":
        errors.append("jpg cannot satisfy alpha_required=true")
    if data.get("target_engine") not in TARGET_ENGINES:
        errors.append(f"target_engine must be one of: {', '.join(sorted(TARGET_ENGINES))}")
    output_name = data.get("output_name")
    if not isinstance(output_name, str) or not output_name.strip():
        errors.append("output_name must be a non-empty string")
    elif isinstance(file_format, str) and not output_name.lower().endswith(f".{file_format}"):
        errors.append(f"output_name must end with .{file_format}")
    source = data.get("source")
    if source is not None and (not isinstance(source, str) or not source.strip()):
        errors.append("source must be null or a non-empty string")
    import_settings = data.get("import_settings", {})
    if not isinstance(import_settings, dict):
        errors.append("import_settings must be an object")
    elif any(not isinstance(key, str) or not key.strip() for key in import_settings):
        errors.append("import_settings keys must be non-empty strings")
    return errors


def validate_resource_file(path: Path) -> list[str]:
    if not path.is_file():
        return [f"Resource manifest does not exist: {path}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Invalid resource manifest {path}: {exc}"]
    return validate_resource_data(data)


def create_resource_manifest(workspace: Path, project: str, resource_id: str, resource_type: str, width: int, height: int, file_format: str, *, alpha_required: bool = True, target_engine: str = "generic", output_name: str | None = None, source: str | None = None, import_settings: dict[str, object] | None = None) -> Path:
    root = project_root(workspace, project)
    if not (root / "project.json").is_file():
        raise FileNotFoundError(f"Unknown project: {project}")
    normalized_format = file_format.lower()
    payload: dict[str, Any] = {
        "schema_version": 1,
        "id": resource_id,
        "type": resource_type,
        "width": width,
        "height": height,
        "format": normalized_format,
        "alpha_required": alpha_required,
        "target_engine": target_engine,
        "output_name": output_name or f"{resource_id}.{normalized_format}",
        "source": source,
        "import_settings": dict(import_settings or {}),
    }
    errors = validate_resource_data(payload)
    if errors:
        raise ValueError("Invalid resource manifest: " + "; ".join(errors))
    path = root / "production-assets" / f"{resource_id}.resource.json"
    if path.exists():
        raise FileExistsError(f"Resource manifest already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_resource_manifest(path: Path) -> ResourceManifest:
    errors = validate_resource_file(path)
    if errors:
        raise ValueError("Invalid resource manifest: " + "; ".join(errors))
    data = json.loads(path.read_text(encoding="utf-8"))
    return ResourceManifest(resource_id=data["id"], resource_type=data["type"], width=data["width"], height=data["height"], file_format=data["format"], alpha_required=data["alpha_required"], target_engine=data["target_engine"], output_name=data["output_name"], source=data.get("source"), import_settings=dict(data.get("import_settings", {})))
