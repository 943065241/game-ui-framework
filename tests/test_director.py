from __future__ import annotations

import json
from pathlib import Path

from guif.core import init_project, record_memory
from guif.resource import create_resource_manifest
from guif.runtime import Runtime
from guif.theme import create_theme


def test_structured_director_reviews_composition_reuse_and_memory(tmp_path: Path) -> None:
    init_project(tmp_path, "LeekParty")
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
    record_memory(
        tmp_path,
        "LeekParty",
        "decision",
        "The shop page must keep the harbor view and must not include bottom tab navigation.",
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
        "Create a 1080x2340 portrait medieval harbor shop page, reuse the purchase button, and export Unity",
        pipeline="ui-production",
    )

    review = task.state["direction"]
    assert review["schema_version"] == 1
    assert review["status"] == "ready"
    assert review["page"]["layout_profile"] == "shop-portrait"
    assert review["composition"]["zones"][0] == "top status and currency area"
    assert review["visual_contract"]["theme_name"] == "Medieval Harbor"
    assert review["visual_contract"]["avoid"] == ["pirate skulls", "dirty noise"]
    assert any(
        "bottom tab navigation" in item["text"]
        for item in review["visual_contract"]["memory_constraints"]
    )
    assert review["resource_review"]["approved_reuse"][0]["resource_id"] == "purchase-button"
    assert task.state["agents"]["director"]["status"] == "completed"
    assert [output["type"] for output in task.outputs[:2]] == [
        "ui-production-plan",
        "art-direction-review",
    ]


def test_structured_director_blocks_missing_theme_and_canvas(tmp_path: Path) -> None:
    init_project(tmp_path, "Demo")

    task = Runtime(tmp_path).run(
        "Demo",
        "Create a generic UI page",
        pipeline="ui-production",
    )
    review = task.state["direction"]

    assert review["status"] == "blocked"
    assert {conflict["code"] for conflict in review["conflicts"]} >= {
        "missing-theme",
        "missing-canvas",
    }
