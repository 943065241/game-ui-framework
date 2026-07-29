from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

from guif.paths import project_root
from guif.theme_store import PrivateThemeStore


@dataclass(frozen=True)
class RuntimeContext:
    project_root: str
    project_config: dict[str, Any]
    active_theme: dict[str, Any] | None
    workflows: tuple[dict[str, Any], ...]
    resources: tuple[dict[str, Any], ...]
    memory: tuple[dict[str, Any], ...]
    active_theme_ref: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize Runtime Context without private Theme content."""

        payload = asdict(self)
        payload["active_theme"] = None
        payload["active_theme_ref"] = dict(self.active_theme_ref) if self.active_theme_ref else None
        payload["workflows"] = list(self.workflows)
        payload["resources"] = list(self.resources)
        payload["memory"] = list(self.memory)
        payload["privacy"] = {
            "theme_content_persisted": False,
            "theme_reference_only": self.active_theme_ref is not None,
        }
        return payload

    def with_private_theme(self, theme: dict[str, Any] | None, ref: dict[str, Any] | None) -> "RuntimeContext":
        return replace(self, active_theme=theme, active_theme_ref=ref)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RuntimeContext":
        # Hand-authored/in-memory fixtures may still supply active_theme. TaskStore
        # persistence always calls to_dict(), which redacts it before writing.
        transient_theme = (
            dict(payload["active_theme"])
            if isinstance(payload.get("active_theme"), dict)
            else None
        )
        return cls(
            project_root=str(payload["project_root"]),
            project_config=dict(payload.get("project_config", {})),
            active_theme=transient_theme,
            active_theme_ref=(
                dict(payload["active_theme_ref"])
                if isinstance(payload.get("active_theme_ref"), dict)
                else None
            ),
            workflows=tuple(payload.get("workflows", ())),
            resources=tuple(payload.get("resources", ())),
            memory=tuple(payload.get("memory", ())),
        )


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


def _read_memory_files(directory: Path, *, relative_to: Path) -> tuple[dict[str, Any], ...]:
    if not directory.exists():
        return ()
    records: list[dict[str, Any]] = []
    for path in sorted(directory.rglob("*.md")):
        if not path.is_file():
            continue
        records.append(
            {
                "path": str(path.relative_to(relative_to)),
                "type": path.parent.name,
                "content": path.read_text(encoding="utf-8"),
            }
        )
    return tuple(records)


def load_runtime_context(
    workspace: Path,
    project: str,
    *,
    conversation_id: str | None = None,
    theme_store: PrivateThemeStore | None = None,
) -> RuntimeContext:
    root = project_root(workspace, project)
    config_path = root / "project.json"
    if not config_path.is_file():
        raise FileNotFoundError(f"Unknown project: {project}")

    project_config = _read_json(config_path)
    store = theme_store or PrivateThemeStore(workspace)
    active_theme_record, active_theme_ref = store.resolve(
        project=project,
        conversation_id=conversation_id,
    )
    active_theme = None
    if active_theme_record is not None:
        content = active_theme_record.get("content")
        if not isinstance(content, dict):
            raise ValueError("Private Theme record is missing content")
        active_theme = {
            "schema_version": 1,
            "name": active_theme_record.get("name"),
            **content,
        }

    return RuntimeContext(
        project_root=str(root),
        project_config=project_config,
        active_theme=active_theme,
        active_theme_ref=active_theme_ref,
        workflows=_read_json_files(root / "workflows"),
        resources=_read_json_files(root / "production-assets", "*.resource.json"),
        memory=_read_memory_files(root / "memory", relative_to=root),
    )


__all__ = ["RuntimeContext", "load_runtime_context"]
