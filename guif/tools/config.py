from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from guif.paths import project_root

EXECUTION_CONFIG_SCHEMA_VERSION = 1
DEFAULT_EXECUTION_CONFIG: dict[str, Any] = {
    "schema_version": EXECUTION_CONFIG_SCHEMA_VERSION,
    "mode": "production",
    "default_host": "chatgpt",
    "tools": {
        "image-generation": {"primary": "chatgpt-image", "fallback": []},
        "image-editing": {"primary": "chatgpt-image", "fallback": []},
    },
}


@dataclass(frozen=True)
class ExecutionSettings:
    mode: str
    default_host: str
    task_tools: dict[str, Any]
    project_tools: dict[str, Any]
    workspace_tools: dict[str, Any]
    sources: dict[str, str | None]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": EXECUTION_CONFIG_SCHEMA_VERSION,
            "mode": self.mode,
            "default_host": self.default_host,
            "task_tools": dict(self.task_tools),
            "project_tools": dict(self.project_tools),
            "workspace_tools": dict(self.workspace_tools),
            "sources": dict(self.sources),
        }


def validate_execution_config(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, dict):
        return ["execution must be an object"]
    errors: list[str] = []
    schema_version = value.get("schema_version", EXECUTION_CONFIG_SCHEMA_VERSION)
    if schema_version != EXECUTION_CONFIG_SCHEMA_VERSION:
        errors.append(f"execution.schema_version must be {EXECUTION_CONFIG_SCHEMA_VERSION}")
    mode = value.get("mode", "production")
    if mode not in {"production", "development", "ci"}:
        errors.append("execution.mode must be production, development, or ci")
    default_host = value.get("default_host", "chatgpt")
    if not isinstance(default_host, str) or not default_host.strip():
        errors.append("execution.default_host must be a non-empty string")
    tools = value.get("tools", {})
    if not isinstance(tools, dict):
        errors.append("execution.tools must be an object")
    else:
        for capability, config in tools.items():
            if not isinstance(capability, str) or not capability.strip():
                errors.append("execution.tools capability keys must be non-empty strings")
                continue
            if isinstance(config, str):
                if not config.strip():
                    errors.append(f"execution.tools.{capability} must not be empty")
                continue
            if not isinstance(config, dict):
                errors.append(f"execution.tools.{capability} must be a string or object")
                continue
            primary = config.get("primary")
            if primary is not None and (not isinstance(primary, str) or not primary.strip()):
                errors.append(f"execution.tools.{capability}.primary must be a non-empty string")
            fallback = config.get("fallback", [])
            if not isinstance(fallback, list) or any(
                not isinstance(item, str) or not item.strip() for item in fallback
            ):
                errors.append(f"execution.tools.{capability}.fallback must be a list of tool IDs")
    return errors


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Configuration must contain an object: {path}")
    return payload


def _execution(value: dict[str, Any]) -> dict[str, Any]:
    execution = value.get("execution")
    return dict(execution) if isinstance(execution, dict) else {}


def load_execution_settings(
    workspace: Path,
    project: str,
    *,
    task_overrides: dict[str, Any] | None = None,
) -> ExecutionSettings:
    project_path = project_root(workspace, project) / "project.json"
    project_config = _read_json(project_path)
    workspace_path = workspace / ".guif" / "config.json"
    workspace_config = _read_json(workspace_path)
    project_execution = _execution(project_config)
    workspace_execution = _execution(workspace_config)
    task_execution = task_overrides if isinstance(task_overrides, dict) else {}

    mode = str(
        task_execution.get("mode")
        or project_execution.get("mode")
        or workspace_execution.get("mode")
        or DEFAULT_EXECUTION_CONFIG["mode"]
    )
    default_host = str(
        task_execution.get("default_host")
        or project_execution.get("default_host")
        or workspace_execution.get("default_host")
        or DEFAULT_EXECUTION_CONFIG["default_host"]
    )
    return ExecutionSettings(
        mode=mode,
        default_host=default_host,
        task_tools=dict(task_execution.get("tools", {}))
        if isinstance(task_execution.get("tools"), dict)
        else {},
        project_tools=dict(project_execution.get("tools", {}))
        if isinstance(project_execution.get("tools"), dict)
        else {},
        workspace_tools=dict(workspace_execution.get("tools", {}))
        if isinstance(workspace_execution.get("tools"), dict)
        else {},
        sources={
            "task": "task.state.execution_overrides" if task_execution else None,
            "project": str(project_path) if project_execution else None,
            "workspace": str(workspace_path) if workspace_execution else None,
            "framework": "guif.tools.config.DEFAULT_EXECUTION_CONFIG",
        },
    )


def bind_project_tool(
    workspace: Path,
    project: str,
    capability: str,
    tool_id: str,
) -> Path:
    if not capability.strip() or not tool_id.strip():
        raise ValueError("Capability and Tool ID must not be empty")
    path = project_root(workspace, project) / "project.json"
    payload = _read_json(path)
    if not payload:
        raise FileNotFoundError(f"Unknown project: {project}")
    execution = payload.setdefault("execution", {})
    if not isinstance(execution, dict):
        raise ValueError("project.json execution field must be an object")
    execution.setdefault("schema_version", EXECUTION_CONFIG_SCHEMA_VERSION)
    execution.setdefault("mode", "production")
    execution.setdefault("default_host", "chatgpt")
    tools = execution.setdefault("tools", {})
    if not isinstance(tools, dict):
        raise ValueError("project.json execution.tools must be an object")
    tools[capability] = {"primary": tool_id, "fallback": []}
    errors = validate_execution_config(execution)
    if errors:
        raise ValueError("Invalid execution configuration: " + "; ".join(errors))
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
