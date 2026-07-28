from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from guif.paths import project_root

REQUIRED_THEME_FIELDS = (
    "name",
    "description",
    "palette",
    "materials",
    "lighting",
    "must_include",
    "avoid",
)


def validate_theme_data(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_THEME_FIELDS:
        if field not in data:
            errors.append(f"Missing theme field: {field}")
    if "palette" in data and not isinstance(data["palette"], list):
        errors.append("Theme palette must be a list")
    for field in ("materials", "must_include", "avoid"):
        if field in data and not isinstance(data[field], list):
            errors.append(f"Theme {field} must be a list")
    return errors


def create_theme(workspace: Path, project: str, name: str, description: str) -> Path:
    root = project_root(workspace, project)
    config_path = root / "project.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Unknown project: {project}")

    slug = "-".join(name.strip().lower().split())
    if not slug:
        raise ValueError("Theme name cannot be empty")
    path = root / "themes" / f"{slug}.json"
    if path.exists():
        raise FileExistsError(f"Theme already exists: {path}")

    payload = {
        "schema_version": 1,
        "name": name.strip(),
        "description": description.strip(),
        "palette": [],
        "materials": [],
        "lighting": "",
        "must_include": [],
        "avoid": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    project_config = json.loads(config_path.read_text(encoding="utf-8"))
    project_config["current_theme"] = slug
    config_path.write_text(json.dumps(project_config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def validate_theme_file(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Invalid theme file {path}: {exc}"]
    if not isinstance(data, dict):
        return [f"Theme root must be an object: {path}"]
    return validate_theme_data(data)
