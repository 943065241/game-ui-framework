from __future__ import annotations

from pathlib import Path

from guif.core import init_project
from guif.resource import create_resource_manifest
from guif.runtime import Runtime


PROJECT = "SampleGame"


def test_structured_planner_uses_theme_resources_and_requirement(tmp_path: Path) -> None:
    init_project(tmp_path, PROJECT)
    runtime = Runtime(tmp_path)
    runtime.create_private_theme(
        "Fictional Geometric Arcade",
        {
            "description": "Synthetic abstract arcade art direction for tests.",
            "palette": ["test blue", "test gray"],
            "materials": ["matte polymer", "brushed alloy"],
            "lighting": "flat studio light",
            "must_include": ["hexagonal navigation", "abstract tokens"],
            "avoid": ["real brands", "photoreal people"],
        },
        project=PROJECT,
        actor="test-host",
    )
    create_resource_manifest(
        tmp_path,
        PROJECT,
        "token-icon",
        "icon",
        128,
        128,
        "png",
        target_engine="unity",
    )
    create_resource_manifest(
        tmp_path,
        PROJECT,
        "action-button",
        "button",
        264,
        134,
        "png",
        target_engine="unity",
    )

    task = runtime.run(
        PROJECT,
        "Create a 1080x2340 portrait fictional geometric arcade shop page, reuse the token and button, and export Unity",
        pipeline="planning",
    )

    plan = task.state["plan"]
    assert plan["schema_version"] == 1
    assert plan["page"] == {
        "type": "shop",
        "orientation": "portrait",
        "width": 1080,
        "height": 2340,
    }
    assert plan["target_engine"] == "unity"
    assert plan["theme"]["status"] == "loaded"
    assert plan["theme"]["avoid"] == ["real brands", "photoreal people"]
    assert {item["id"] for item in plan["reuse_candidates"]} >= {
        "token-icon",
        "action-button",
    }
    assert "shop-background" in {item["suggested_id"] for item in plan["new_resources"]}
    assert task.outputs[0]["type"] == "ui-production-plan"
    assert task.state["agents"]["planner"]["status"] == "completed"
    assert (runtime.store.run_dir(PROJECT, task.task_id) / "outputs.json").is_file()


def test_structured_planner_exposes_missing_decisions(tmp_path: Path) -> None:
    init_project(tmp_path, "Demo")

    task = Runtime(tmp_path).run("Demo", "Create a new UI page", pipeline="planning")
    plan = task.state["plan"]

    assert plan["page"]["type"] == "generic"
    assert plan["theme"]["status"] == "missing"
    assert plan["target_engine"] == "generic"
    assert len(plan["open_questions"]) >= 3
    assert {risk["code"] for risk in plan["risks"]} >= {
        "no-resource-contracts",
        "missing-theme",
    }
