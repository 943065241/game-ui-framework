from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = ("schema_version", "id", "name", "manager", "steps")
SUPPORTED_SCHEMA_VERSIONS = {1, 2, 3}

LEGACY_MANAGER_AGENTS: dict[str, tuple[str, ...]] = {
    "UI Director": ("planner", "director", "theme", "prompt", "qa"),
    "Theme Manager": ("planner", "director", "theme", "qa"),
    "Resource Manager": ("planner", "director", "theme", "resource", "prompt", "qa", "export"),
    "QA Manager": ("planner", "qa"),
    "Framework Manager": ("planner", "director", "qa"),
}

BUILTIN_WORKFLOWS: dict[str, dict[str, object]] = {
    "master-guided-layer-creation": {
        "schema_version": 3,
        "id": "master-guided-layer-creation",
        "name": "Master-Guided Layer Creation",
        "domain": "visual-production",
        "manager": "UI Director",
        "agents": ["planner", "director", "theme", "resource", "prompt", "qa", "export"],
        "requires": ["theme", "master-reference"],
        "creation_direction": "bottom-to-top",
        "stages": [
            "master-approval",
            "layer-analysis",
            "layer-plan-approval",
            "progressive-layer-creation",
            "recomposition-review",
            "final-approval",
            "engine-export",
        ],
        "constraint_policy": {
            "master_role": "style-and-layout-guidance",
            "pixel_matching": False,
            "creative_freedom": "adaptive",
            "hard_constraints": [
                "functional role",
                "layout anchors",
                "asset boundary",
                "output contract",
            ],
            "soft_guidance": [
                "shape details",
                "materials",
                "texture",
                "lighting",
                "decorative interpretation",
            ],
        },
        "steps": [
            "Confirm the Theme and master effect image as style and layout guidance",
            "Analyze a coarse semantic layer plan and assign adaptive creative freedom",
            "Approve the layer plan without requiring pixel matching",
            "Create layers from bottom to top using the master and current composite",
            "Recompose and perform semantic visual review after each layer",
            "Revise only the affected layer and its downstream composites",
            "Approve and export independent assets plus the composition manifest",
        ],
    },
    "ui-production": {
        "schema_version": 2,
        "id": "ui-production",
        "name": "Complete UI Production",
        "manager": "UI Director",
        "agents": ["planner", "director", "theme", "resource", "prompt", "qa", "export"],
        "steps": [
            "Create a structured UI production plan",
            "Review art direction and resource reuse",
            "Resolve theme constraints",
            "Resolve production resource contracts",
            "Build model-neutral generation instructions",
            "Run semantic and technical QA",
            "Export validated production assets",
        ],
    },
    "planning": {
        "schema_version": 2,
        "id": "planning",
        "name": "Structured UI Planning",
        "manager": "UI Director",
        "agents": ["planner"],
        "steps": ["Convert the requirement and project context into a structured production plan"],
    },
    "effect-image": {
        "schema_version": 2,
        "id": "effect-image",
        "name": "Effect Image Production",
        "manager": "UI Director",
        "agents": ["planner", "director", "theme", "prompt", "qa"],
        "steps": [
            "Load project context, active theme, and confirmed decisions",
            "Define composition, hierarchy, interaction intent, and visual constraints",
            "Produce or revise the effect image",
            "Run visual consistency and target-specific QA",
            "Record approved outcome and reusable lessons",
        ],
    },
    "theme-direction": {
        "schema_version": 2,
        "id": "theme-direction",
        "name": "Theme Direction",
        "manager": "Theme Manager",
        "agents": ["planner", "director", "theme", "qa"],
        "steps": [
            "Load project context and existing themes",
            "Define palette, lighting, materials, motifs, required elements, and exclusions",
            "Create or update the theme definition",
            "Validate the theme manifest",
            "Record the approved art-direction decision",
        ],
    },
    "resource-production": {
        "schema_version": 2,
        "id": "resource-production",
        "name": "Production Resource Export",
        "manager": "Resource Manager",
        "agents": ["planner", "director", "theme", "resource", "prompt", "qa", "export"],
        "steps": [
            "Confirm target engine, dimensions, naming, and transparency requirements",
            "Separate effect-image references from production assets",
            "Extract, clean, or compose production-ready resources",
            "Validate dimensions, alpha channel, edges, and naming",
            "Export assets and record reusable production rules",
        ],
    },
    "quality-assurance": {
        "schema_version": 2,
        "id": "quality-assurance",
        "name": "Quality Assurance",
        "manager": "QA Manager",
        "agents": ["planner", "qa"],
        "steps": [
            "Identify protected regions and acceptance criteria",
            "Run structural, visual, and pixel-protection checks",
            "Report failures with measurable evidence",
            "Re-run checks after correction",
            "Record recurring defects and prevention rules",
        ],
    },
    "framework-evolution": {
        "schema_version": 2,
        "id": "framework-evolution",
        "name": "Framework Evolution",
        "manager": "Framework Manager",
        "agents": ["planner", "director", "qa"],
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
    schema_version: int
    workflow_id: str
    name: str
    manager: str
    steps: tuple[str, ...]
    agents: tuple[str, ...]
    source: str
    domain: str = "visual-production"
    requires: tuple[str, ...] = ()
    stages: tuple[str, ...] = ()
    creation_direction: str | None = None
    constraint_policy: dict[str, object] | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "id": self.workflow_id,
            "name": self.name,
            "manager": self.manager,
            "steps": list(self.steps),
            "agents": list(self.agents),
            "source": self.source,
            "domain": self.domain,
            "requires": list(self.requires),
            "stages": list(self.stages),
            "creation_direction": self.creation_direction,
            "constraint_policy": dict(self.constraint_policy or {}),
        }


def _validate_string_list(
    data: dict[str, Any],
    field: str,
    *,
    required: bool,
    unique: bool = False,
) -> list[str]:
    value = data.get(field)
    if value is None and not required:
        return []
    if not isinstance(value, list) or not value:
        return [f"{field} must be a non-empty list"]
    if any(not isinstance(item, str) or not item.strip() for item in value):
        return [f"every {field[:-1] if field.endswith('s') else field} must be a non-empty string"]
    if unique and len(set(value)) != len(value):
        return [f"{field} must not contain duplicates"]
    return []


def validate_workflow_data(data: object) -> list[str]:
    if not isinstance(data, dict):
        return ["Workflow must be a JSON object"]
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"Missing field: {field}")
    schema_version = data.get("schema_version")
    if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append("schema_version must be 1, 2, or 3")
    for field in ("id", "name", "manager"):
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} must be a non-empty string")
    errors.extend(_validate_string_list(data, "steps", required=True))
    errors.extend(_validate_string_list(data, "agents", required=schema_version == 2, unique=True))
    if schema_version == 3:
        errors.extend(_validate_string_list(data, "agents", required=True, unique=True))
        errors.extend(_validate_string_list(data, "requires", required=True, unique=True))
        errors.extend(_validate_string_list(data, "stages", required=True, unique=True))
        if not isinstance(data.get("domain"), str) or not str(data.get("domain")).strip():
            errors.append("domain must be a non-empty string")
        if data.get("creation_direction") not in {"bottom-to-top", "top-to-bottom", "unordered"}:
            errors.append(
                "creation_direction must be bottom-to-top, top-to-bottom, or unordered"
            )
        if not isinstance(data.get("constraint_policy"), dict):
            errors.append("constraint_policy must be an object")
    return errors


def validate_workflow_file(path: Path) -> list[str]:
    if not path.is_file():
        return [f"Workflow file does not exist: {path}"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"Invalid JSON: {exc}"]
    return validate_workflow_data(data)


def _resolve_agents(data: dict[str, object]) -> tuple[str, ...]:
    configured = data.get("agents")
    if isinstance(configured, list) and configured:
        return tuple(str(agent) for agent in configured)
    manager = str(data.get("manager") or "")
    return LEGACY_MANAGER_AGENTS.get(manager, ("planner", "director", "qa"))


def _to_manifest(data: dict[str, object], source: str) -> WorkflowManifest:
    errors = validate_workflow_data(data)
    if errors:
        raise ValueError("Invalid workflow manifest: " + "; ".join(errors))
    workflow_id = str(data["id"])
    domain = data.get("domain")
    if not isinstance(domain, str) or not domain:
        from guif.domains import domain_for_workflow

        domain = domain_for_workflow(workflow_id)
    return WorkflowManifest(
        schema_version=int(data["schema_version"]),
        workflow_id=workflow_id,
        name=str(data["name"]),
        manager=str(data["manager"]),
        steps=tuple(str(step) for step in data["steps"]),
        agents=_resolve_agents(data),
        source=source,
        domain=domain,
        requires=tuple(str(item) for item in data.get("requires", [])),
        stages=tuple(str(item) for item in data.get("stages", [])),
        creation_direction=(
            str(data["creation_direction"])
            if data.get("creation_direction") is not None
            else None
        ),
        constraint_policy=(
            dict(data["constraint_policy"])
            if isinstance(data.get("constraint_policy"), dict)
            else None
        ),
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


def list_workflows(workspace: Path, project: str | None = None) -> list[dict[str, object]]:
    items: list[dict[str, object]] = [
        {
            "id": workflow_id,
            "name": str(data["name"]),
            "manager": str(data["manager"]),
            "schema_version": int(data["schema_version"]),
            "agents": list(_resolve_agents(data)),
            "source": "builtin",
            "domain": _to_manifest(data, "builtin").domain,
        }
        for workflow_id, data in sorted(BUILTIN_WORKFLOWS.items())
    ]
    if project:
        workflows_dir = workspace / "projects" / project / "workflows"
        if workflows_dir.is_dir():
            by_id = {str(item["id"]): item for item in items}
            for path in sorted(workflows_dir.glob("*.json")):
                data = json.loads(path.read_text(encoding="utf-8"))
                errors = validate_workflow_data(data)
                if not errors:
                    manifest = _to_manifest(data, str(path))
                    by_id[manifest.workflow_id] = {
                        "id": manifest.workflow_id,
                        "name": manifest.name,
                        "manager": manifest.manager,
                        "schema_version": manifest.schema_version,
                        "agents": list(manifest.agents),
                        "source": manifest.source,
                        "domain": manifest.domain,
                    }
            items = sorted(by_id.values(), key=lambda item: str(item["id"]))
    return items
