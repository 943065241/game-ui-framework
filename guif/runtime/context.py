from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from guif.paths import project_root


@dataclass(frozen=True)
class RuntimeContext:
    project_root: str
    project_config: dict[str, Any]
    active_theme: dict[str, Any] | None
    workflows: tuple[dict[str, Any], ...]
    resources: tuple[dict[str, Any], ...]
    memory: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["workflows"] = list(self.workflows)
        payload["resources"] = list(self.resources)
        payload["memory"] = list(self.memory)
        return payload


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_json_files(
    directory: Path,
    pattern: str = "*.json",
    *,
    recursive: bool = False,
) -> tuple[dict[str, Any], ...]:
    if not directory.exists():
        return ()
    paths = directory.rglob(pattern) if recursive else directory.glob(pattern)
    return tuple(_read_json(path) for path in sorted(paths) if path.is_file())


def load_runtime_context(workspace: Path, project: str) -> RuntimeContext:
    root = project_root(workspace, project)
    config_path = root / "project.json"
    if not config_path.is_file():
        raise FileNotFoundError(f"Unknown project: {project}")

    project_config = _read_json(config_path)
    active_theme = None
    theme_name = project_config.get("current_theme")
    if theme_name:
        theme_path = root / "themes" / f"{theme_name}.json"
        if theme_path.is_file():
            active_theme = _read_json(theme_path)

    return RuntimeContext(
        project_root=str(root),
        project_config=project_config,
        active_theme=active_theme,
        workflows=_read_json_files(root / "workflows"),
        resources=_read_json_files(root / "production-assets", "*.resource.json"),
        memory=_read_json_files(root / "memory", recursive=True),
    )
