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
    """Validate the semantic contract of a GUIF project.json payload."""
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

    current_theme = config.get("current_theme")
    if current_theme is not None and not isinstance(current_theme, str):
        errors.append("Project field 'current_theme' must be a string or null")
    elif isinstance(current_theme, str):
        if not current_theme.strip():
            errors.append("Project field 'current_theme' must not be empty")
        elif project_root is not None and not (project_root / "themes" / f"{current_theme}.json").is_file():
            errors.append(f"Current theme file does not exist: themes/{current_theme}.json")

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
