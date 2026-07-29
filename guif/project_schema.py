from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from guif.tools.config import validate_execution_config

REQUIRED_PROJECT_FIELDS = {
    "schema_version": int,
    "name": str,
    "status": str,
    "created_at": str,
}

ALLOWED_STATUSES = {"active", "paused", "archived"}


def validate_project_config(config: object, *, project_root: Path | None = None) -> list[str]:
    """Validate project.json without requiring or exposing private Theme content."""

    errors: list[str] = []
    if not isinstance(config, dict):
        return ["project.json must contain a JSON object"]

    for field, expected_type in REQUIRED_PROJECT_FIELDS.items():
        if field not in config:
            errors.append(f"Missing project field: {field}")
            continue
        if not isinstance(config[field], expected_type):
            errors.append(f"Project field '{field}' must be {expected_type.__name__}")

    schema_version = config.get("schema_version")
    if isinstance(schema_version, int) and schema_version != 1:
        errors.append(f"Unsupported project schema_version: {schema_version}")

    name = config.get("name")
    if isinstance(name, str) and not name.strip():
        errors.append("Project field 'name' must not be empty")

    status = config.get("status")
    if isinstance(status, str) and status not in ALLOWED_STATUSES:
        errors.append(f"Project field 'status' must be one of: {', '.join(sorted(ALLOWED_STATUSES))}")

    created_at = config.get("created_at")
    if isinstance(created_at, str):
        try:
            datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            errors.append("Project field 'created_at' must be an ISO-8601 datetime")

    if config.get("current_theme") is not None or config.get("theme_binding") is not None:
        errors.append(
            "Project Theme content and bindings are private data; migrate them to PrivateThemeStore."
        )

    privacy = config.get("privacy")
    if privacy is not None and not isinstance(privacy, dict):
        errors.append("Project field 'privacy' must be an object when present")

    errors.extend(validate_execution_config(config.get("execution")))
    return errors


def validate_project_config_file(path: Path, *, project_root: Path | None = None) -> list[str]:
    if not path.is_file():
        return [f"Missing project config: {path}"]
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"Invalid project JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}"]
    return validate_project_config(config, project_root=project_root)
