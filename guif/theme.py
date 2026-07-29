from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from guif.paths import project_root
from guif.theme_store import PrivateThemeStore

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
    for field in ("name", "description", "lighting"):
        if field in data and not isinstance(data[field], str):
            errors.append(f"Theme {field} must be a string")
    for field in ("palette", "materials", "must_include", "avoid"):
        if field in data and (
            not isinstance(data[field], list)
            or any(not isinstance(item, str) for item in data[field])
        ):
            errors.append(f"Theme {field} must be a list of strings")
    return errors


def create_theme_record(
    workspace: Path,
    name: str,
    description: str,
    *,
    project: str | None = None,
    conversation_id: str | None = None,
    actor: str = "host",
) -> dict[str, Any]:
    """Create a private Theme and optionally bind it to a project/conversation.

    Theme content is written only to GUIF's private data store. Project Git receives
    no Theme name, description, palette, or other personal design content.
    """

    if project is not None:
        root = project_root(workspace, project)
        if not (root / "project.json").is_file():
            raise FileNotFoundError(f"Unknown project: {project}")
    store = PrivateThemeStore(workspace)
    record = store.create(
        name,
        {
            "description": description.strip(),
            "palette": [],
            "materials": [],
            "lighting": "",
            "must_include": [],
            "avoid": [],
        },
        actor=actor,
        source_conversation_id=conversation_id,
    )
    if project is not None:
        store.bind_project(project, str(record["theme_id"]), version=int(record["version"]), actor=actor)
    if conversation_id is not None:
        store.bind_conversation(
            conversation_id,
            str(record["theme_id"]),
            version=int(record["version"]),
            actor=actor,
        )
    return record


def create_theme(workspace: Path, project: str, name: str, description: str) -> Path:
    """Backward-compatible private Theme creation helper.

    The returned path is outside the framework/project repository.
    """

    record = create_theme_record(workspace, name, description, project=project)
    store = PrivateThemeStore(workspace)
    return store._version_path(str(record["theme_id"]), int(record["version"]))


def validate_theme_file(path: Path) -> list[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Invalid theme file {path}: {exc}"]
    if not isinstance(data, dict):
        return [f"Theme root must be an object: {path}"]
    if isinstance(data.get("content"), dict):
        content = {"name": data.get("name"), **data["content"]}
        return validate_theme_data(content)
    return validate_theme_data(data)


__all__ = ["create_theme", "create_theme_record", "validate_theme_data", "validate_theme_file"]
