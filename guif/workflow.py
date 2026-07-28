from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

REQUIRED_FIELDS = ("schema_version", "id", "name", "manager", "steps")

BUILTIN_WORKFLOWS: dict[str, dict[str, object]] = {
    "effect-image": {
        "schema_version": 1,
        "id": "effect-image",
        "name": "Effect Image Production",
        "manager": "UI Director",
        "steps": [
            "Load project context, active theme, and confirmed decisions",
            "Define composition, hierarchy, interaction intent, and visual constraints",
            "Produce or revise the effect image",
            "Run visual consistency and target-specific QA",
            "Record approved outcome and reusable lessons",
        ],
    },
    "theme-direction": {
        "schema_version": 1,
        "id": "theme-direction",
        "name": "Theme Direction",
        "manager": "Theme Manager",
        "steps": [
            "Load project context and existing themes",
            "Define palette, lighting, materials, motifs, required elements, and exclusions",
            "Create or update the theme definition",
            "Validate the theme manifest",
            "Record the approved art-direction decision",
        ],
    },
    "resource-production": {
        "schema_version": 1,
        "id": "resource-production",
        "name": "Production Resource Export",
        "manager": "Resource Manager",
        "steps": [
            "Confirm target engine, dimensions, naming, and transparency requirements",
            "Separate effect-image references from production assets",
            "Extract, clean, or compose production-ready resources",
            "Validate dimensions, alpha channel, edges, and naming",
            "Export assets and record reusable production rules",
        ],
    },
    "quality-assurance": {
        "schema_version": 1,
        "id": "quality-assurance",
        "name": "Quality Assurance",
        "manager": "QA Manager",
        "steps": [
            "Identify protected regions and acceptance criteria",
            "Run structural, visual, and pixel-protection checks",
            "Report failures with measurable evidence",
            "Re-run checks after correction",
            "Record recurring defects and prevention rules",
        ],
    },
    "framework-evolution": {
        "schema_version": 1,
        "id": "framework-evolution",
        "name": "Framework Evolution",
        "manager": "Framework Manager",
        "steps": [
            "Collect the triggering project experience and evidence",
            "Classify it as memory, rule, skill, schema, or workflow change",
            "Implement the smallest backward-compatible framework improvement",
            "Add tests and validate existing contracts",
            "Record the change in framework history",
        ],
    },
}


@dataclass(frozen=True)
class WorkflowManifest:
    workflow_id: str
    name: str
    manager: str
    steps: tuple[str, ...]
    source: str

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.workflow_id,
            "name": self.name,
            "manager": self.manager,
            "steps": list(self.steps),
            "source": self.source,
        }


def validate_workflow_data(data: object) -> list[str]:
    if not isinstance(data, dict):
        return ["Workflow must be a JSON object"]
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"Missing field: {field}")
    if data.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    for field in ("id", "name", "manager"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} must be a non-empty string")
    steps = data.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append("steps must be a non-empty list")
    elif any(not isinstance(step, str) or not step.strip() for step in steps):
        errors.append("every step must be a non-empty string")
    return errors


def validate_workflow_file(path: Path) -> list[str]:
    if not path.is_file():
        return [f"Workflow file does not exist: {path}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"Invalid JSON: {exc}"]
    return validate_workflow_data(data)


def _to_manifest(data: dict[str, object], source: str) -> WorkflowManifest:
    errors = validate_workflow_data(data)
    if errors:
        raise ValueError("Invalid workflow manifest: " + "; ".join(errors))
    return WorkflowManifest(
        workflow_id=str(data["id"]),
        name=str(data["name"]),
        manager=str(data["manager"]),
        steps=tuple(str(step) for step in data["steps"]),
        source=source,
    )


def load_workflow(workspace: Path, project: str, workflow_id: str) -> WorkflowManifest:
    project_path = workspace / "projects" / project / "workflows" / f"{workflow_id}.json"
    if project_path.is_file():
        data = json.loads(project_path.read_text(encoding="utf-8"))
        return _to_manifest(data, str(project_path))
    try:
        data = BUILTIN_WORKFLOWS[workflow_id]
    except KeyError as exc:
        raise FileNotFoundError(f"Unknown workflow: {workflow_id}") from exc
    return _to_manifest(data, "builtin")


def list_workflows(workspace: Path, project: str | None = None) -> list[dict[str, str]]:
    items = [
        {"id": workflow_id, "name": str(data["name"]), "manager": str(data["manager"]), "source": "builtin"}
        for workflow_id, data in sorted(BUILTIN_WORKFLOWS.items())
    ]
    if project:
        workflows_dir = workspace / "projects" / project / "workflows"
        if workflows_dir.is_dir():
            by_id = {item["id"]: item for item in items}
            for path in sorted(workflows_dir.glob("*.json")):
                data = json.loads(path.read_text(encoding="utf-8"))
                errors = validate_workflow_data(data)
                if not errors:
                    workflow_id = str(data["id"])
                    by_id[workflow_id] = {
                        "id": workflow_id,
                        "name": str(data["name"]),
                        "manager": str(data["manager"]),
                        "source": str(path),
                    }
            items = sorted(by_id.values(), key=lambda item: item["id"])
    return items
