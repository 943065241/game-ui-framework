from __future__ import annotations

import json

from guif.core import create_plan, init_project
from guif.runtime import Runtime
from guif.workflow import list_workflows, load_workflow, validate_workflow_data, validate_workflow_file


def test_builtin_workflows_are_valid_and_executable(tmp_path):
    items = list_workflows(tmp_path)
    assert {item["id"] for item in items} == {
        "effect-image",
        "framework-evolution",
        "planning",
        "quality-assurance",
        "resource-production",
        "theme-direction",
        "ui-production",
    }
    manifest = load_workflow(tmp_path, "unused", "effect-image")
    assert manifest.schema_version == 2
    assert manifest.manager == "UI Director"
    assert manifest.steps
    assert manifest.agents == ("planner", "director", "theme", "prompt", "qa")
    assert manifest.source == "builtin"


def test_project_workflow_overrides_builtin_and_drives_plan(tmp_path):
    init_project(tmp_path, "Demo")
    path = tmp_path / "projects" / "Demo" / "workflows" / "theme-direction.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "id": "theme-direction",
                "name": "Project Theme Review",
                "manager": "Theme Manager",
                "steps": ["Load the project theme", "Run the custom review"],
            }
        ),
        encoding="utf-8",
    )

    manifest = load_workflow(tmp_path, "Demo", "theme-direction")
    assert manifest.source == str(path)
    assert manifest.steps[-1] == "Run the custom review"
    assert manifest.agents == ("planner", "director", "theme", "qa")

    plan_path = create_plan(tmp_path, "Demo", "Create a medieval theme")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert plan["workflow"]["source"] == str(path)
    assert plan["steps"] == ["Load the project theme", "Run the custom review"]


def test_runtime_builds_pipeline_from_project_workflow(tmp_path):
    init_project(tmp_path, "Demo")
    path = tmp_path / "projects" / "Demo" / "workflows" / "planning.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "id": "planning",
                "name": "Project Planning",
                "manager": "UI Director",
                "steps": ["Create the project plan", "Review the plan contract"],
                "agents": ["planner", "qa"],
            }
        ),
        encoding="utf-8",
    )

    task = Runtime(tmp_path).run("Demo", "Create a shop page", pipeline="planning")

    assert task.state["pipeline"]["source"] == str(path)
    assert task.state["pipeline"]["agents"] == ["planner", "qa"]
    assert tuple(task.state["agents"]) == ("planner", "qa")


def test_workflow_validation_rejects_empty_steps_and_schema2_without_agents(tmp_path):
    data = {
        "schema_version": 1,
        "id": "bad",
        "name": "Bad Workflow",
        "manager": "QA Manager",
        "steps": [],
    }
    assert "steps must be a non-empty list" in validate_workflow_data(data)

    schema2 = {
        "schema_version": 2,
        "id": "bad-v2",
        "name": "Bad Workflow V2",
        "manager": "QA Manager",
        "steps": ["Inspect"],
    }
    assert "agents must be a non-empty list" in validate_workflow_data(schema2)

    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert validate_workflow_file(path)
