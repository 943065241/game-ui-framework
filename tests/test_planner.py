from __future__ import annotations

import json
from pathlib import Path

from guif.core import init_project
from guif.resource import create_resource_manifest
from guif.runtime import Runtime
from guif.theme import create_theme


def test_structured_planner_uses_theme_resources_and_requirement(tmp_path: Path) -> None:
    root = init_project(tmp_path, "LeekParty")
    theme_path = create_theme(
        tmp_path,
        "LeekParty",
        "Medieval Harbor",
        "Warm sunset medieval harbor art direction.",
    )
    theme = json.loads(theme_path.read_text(encoding="utf-8"))
    theme.update(
        {
            "palette": ["warm gold", "deep sea blue"],
            "materials": ["wood", "aged brass"],
            "lighting": "sunset",
            "must_include": ["harbor view", "gold coins"],
            "avoid": ["pirate skulls", "dirty noise"],
        }
    )
    theme_path.write_text(json.dumps(theme), encoding="utf-8")
    create_resource_manifest(
        tmp_path,
        "LeekParty",
        "currency-icon",
        "icon",
        128,
        128,
        "png",
        target_engine="unity",
    )
    create_resource_manifest(
        tmp_path,
        "LeekParty",
        "purchase-button",
        "button",
        264,
        134,
        "png",
        target_engine="unity",
    )

    task = Runtime(tmp_path).run(
        "LeekParty",
        "制作 1080×2340 竖屏中世纪港口商店页面，复用金币和按钮并导出 Unity",
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
    assert plan["theme"]["avoid"] == ["pirate skulls", "dirty noise"]
    assert {item["id"] for item in plan["reuse_candidates"]} >= {
        "currency-icon",
        "purchase-button",
    }
    assert "shop-background" in {item["suggested_id"] for item in plan["new_resources"]}
    assert task.outputs[0]["type"] == "ui-production-plan"
    assert task.state["agents"]["planner"]["status"] == "completed"
    assert (root / "runs" / task.task_id / "outputs.json").is_file()


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
