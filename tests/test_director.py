from __future__ import annotations

from pathlib import Path

from guif.core import init_project, record_memory
from guif.resource import create_resource_manifest
from guif.runtime import Runtime


PROJECT = "SampleGame"


def test_structured_director_reviews_composition_reuse_and_memory(tmp_path: Path) -> None:
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
    record_memory(
        tmp_path,
        PROJECT,
        "decision",
        "The fictional shop page must keep the hexagonal navigation and must not include bottom tab navigation.",
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
        "Create a 1080x2340 portrait fictional geometric arcade shop page, reuse the action button, and export Unity",
        pipeline="ui-production",
    )

    review = task.state["direction"]
    assert review["schema_version"] == 1
    assert review["status"] == "ready"
    assert review["page"]["layout_profile"] == "shop-portrait"
    assert review["composition"]["zones"][0] == "top status and currency area"
    assert review["visual_contract"]["theme_name"] == "Fictional Geometric Arcade"
    assert review["visual_contract"]["avoid"] == ["real brands", "photoreal people"]
    assert any(
        "bottom tab navigation" in item["text"]
        for item in review["visual_contract"]["memory_constraints"]
    )
    assert review["resource_review"]["approved_reuse"][0]["resource_id"] == "action-button"
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
