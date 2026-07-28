from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from guif.paths import project_root
from guif.project_schema import validate_project_config_file
from guif.resource import validate_resource_file
from guif.theme import validate_theme_file
from guif.workflow import load_workflow, validate_workflow_file

PROJECT_DIRS = (
    "requirements",
    "themes",
    "workflows",
    "effect-images",
    "production-assets",
    "qa",
    "plans",
    "memory/decisions",
    "memory/lessons",
    "memory/mistakes",
    "memory/best-practices",
)


@dataclass(frozen=True)
class Route:
    manager: str
    workflow: str
    reason: str


def route_requirement(requirement: str) -> Route:
    text = requirement.lower()
    if any(word in text for word in ("切ui", "图集", "atlas", "透明通道", "asset", "资源")):
        return Route("Resource Manager", "resource-production", "Production asset terms detected.")
    if any(word in text for word in ("qa", "检查", "像素", "噪点", "偏移", "mask", "遮罩")):
        return Route("QA Manager", "quality-assurance", "Quality or pixel-protection terms detected.")
    if any(word in text for word in ("主题", "风格", "theme", "style", "中世纪", "medieval")):
        return Route("Theme Manager", "theme-direction", "Theme or art-direction terms detected.")
    if any(word in text for word in ("框架", "skill", "规则", "framework", "governance")):
        return Route("Framework Manager", "framework-evolution", "Framework governance terms detected.")
    return Route("UI Director", "effect-image", "Default visual production route.")


def init_project(workspace: Path, project: str) -> Path:
    root = project_root(workspace, project)
    if root.exists():
        raise FileExistsError(f"Project already exists: {root}")
    for relative in PROJECT_DIRS:
        (root / relative).mkdir(parents=True, exist_ok=True)
    config = {
        "schema_version": 1,
        "name": project,
        "status": "active",
        "current_theme": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (root / "project.json").write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return root


def create_plan(workspace: Path, project: str, requirement: str) -> Path:
    root = project_root(workspace, project)
    if not (root / "project.json").exists():
        raise FileNotFoundError(f"Unknown project: {project}")
    route = route_requirement(requirement)
    workflow = load_workflow(workspace, project, route.workflow)
    timestamp = datetime.now(timezone.utc)
    payload = {
        "schema_version": 1,
        "project": project,
        "requirement": requirement,
        "route": asdict(route),
        "workflow": workflow.to_dict(),
        "steps": list(workflow.steps),
        "created_at": timestamp.isoformat(),
    }
    path = root / "plans" / f"{timestamp.strftime('%Y%m%dT%H%M%SZ')}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def validate_project(workspace: Path, project: str) -> list[str]:
    root = project_root(workspace, project)
    errors: list[str] = []
    if not root.exists():
        return [f"Project directory does not exist: {root}"]
    errors.extend(validate_project_config_file(root / "project.json", project_root=root))
    for relative in PROJECT_DIRS:
        if not (root / relative).is_dir():
            errors.append(f"Missing directory: {relative}")
    themes_dir = root / "themes"
    if themes_dir.is_dir():
        for path in sorted(themes_dir.glob("*.json")):
            for error in validate_theme_file(path):
                errors.append(f"{path.relative_to(root)}: {error}")
    workflows_dir = root / "workflows"
    if workflows_dir.is_dir():
        for path in sorted(workflows_dir.glob("*.json")):
            for error in validate_workflow_file(path):
                errors.append(f"{path.relative_to(root)}: {error}")
    resources_dir = root / "production-assets"
    if resources_dir.is_dir():
        for path in sorted(resources_dir.glob("*.resource.json")):
            for error in validate_resource_file(path):
                errors.append(f"{path.relative_to(root)}: {error}")
    return errors


def record_memory(workspace: Path, project: str, memory_type: str, message: str) -> Path:
    allowed = {
        "decision": "decisions",
        "lesson": "lessons",
        "mistake": "mistakes",
        "best-practice": "best-practices",
    }
    if memory_type not in allowed:
        raise ValueError(f"Unsupported memory type: {memory_type}")
    root = project_root(workspace, project)
    if not (root / "project.json").exists():
        raise FileNotFoundError(f"Unknown project: {project}")
    now = datetime.now(timezone.utc)
    path = root / "memory" / allowed[memory_type] / f"{now.strftime('%Y%m%dT%H%M%SZ')}.md"
    path.write_text(
        f"# {memory_type.replace('-', ' ').title()}\n\n"
        f"- Project: {project}\n"
        f"- Recorded: {now.isoformat()}\n\n"
        f"{message.strip()}\n",
        encoding="utf-8",
    )
    return path
