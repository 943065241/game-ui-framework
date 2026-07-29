from __future__ import annotations

import json
from pathlib import Path

from guif.core import init_project, record_memory
from guif.resource import create_resource_manifest, validate_resource_data
from guif.runtime import Runtime
from guif.theme import validate_theme_data

PROJECT = "SampleGame"


def _create_private_fixture_theme(tmp_path: Path) -> None:
    Runtime(tmp_path).create_private_theme(
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


def test_theme_and_resource_agents_create_reviewable_contracts(tmp_path: Path) -> None:
    root = init_project(tmp_path, PROJECT)
    _create_private_fixture_theme(tmp_path)
    record_memory(
        tmp_path,
        PROJECT,
        "decision",
        "The fictional shop page must keep hexagonal navigation and must not include bottom tab navigation.",
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

    task = Runtime(tmp_path).run(
        PROJECT,
        "Create a 1080x2340 portrait fictional geometric arcade shop page, reuse the action button, and export Unity",
        pipeline="ui-production",
    )

    theme_contract = task.state["theme_contract"]
    assert theme_contract["status"] == "ready"
    assert theme_contract["source"] == "private-theme"
    assert theme_contract["approval_required"] is False
    assert theme_contract["manifest"]["name"] == "Fictional Geometric Arcade"
    assert theme_contract["provenance"]["private_theme_ref"]["privacy"] == "private"
    assert not validate_theme_data(theme_contract["manifest"])
    assert any(
        "bottom tab navigation" in value
        for value in theme_contract["manifest"]["avoid"]
    )

    bundle = task.state["resource_contracts"]
    assert bundle["status"] == "review-required"
    assert bundle["target_engine"] == "unity"
    assert bundle["materialization_policy"]["project_mutated"] is False
    assert bundle["approved_existing"][0]["resource_id"] == "action-button"
    candidates = {
        item["resource_id"]: item
        for item in bundle["manifest_candidates"]
    }
    assert candidates["shop-background"]["manifest"]["width"] == 1080
    assert candidates["shop-background"]["manifest"]["height"] == 2340
    assert candidates["currency-icon"]["manifest"]["width"] == 128
    assert candidates["currency-icon"]["manifest"]["height"] == 128
    assert candidates["shop-main-panel"]["dimension_source"] == "layout-proposal"
    for item in candidates.values():
        assert not validate_resource_data(item["manifest"])

    assert [output["type"] for output in task.outputs[:4]] == [
        "ui-production-plan",
        "art-direction-review",
        "resolved-theme-contract",
        "resource-contract-bundle",
    ]
    assert sorted(path.name for path in (root / "production-assets").glob("*.resource.json")) == [
        "action-button.resource.json"
    ]


def test_theme_agent_does_not_silently_infer_or_write_theme(tmp_path: Path) -> None:
    root = init_project(tmp_path, "Demo")

    task = Runtime(tmp_path).run(
        "Demo",
        "Create a 1080x2340 portrait fictional illustrated shop page and export Unity",
        pipeline="ui-production",
    )

    contract = task.state["theme_contract"]
    assert contract["status"] == "blocked"
    assert contract["source"] == "unresolved"
    assert contract["approval_required"] is True
    assert contract["manifest_id"] == "unresolved-theme"
    assert contract["manifest"]["name"] == "Unresolved Theme"
    assert not validate_theme_data(contract["manifest"])
    project_config = json.loads((root / "project.json").read_text(encoding="utf-8"))
    assert "current_theme" not in project_config
    assert "theme_binding" not in project_config
    assert not (root / "themes").exists()

    bundle = task.state["resource_contracts"]
    assert bundle["status"] == "blocked"
    assert any(item["code"] == "theme-contract-blocked" for item in bundle["blocking_conflicts"])


def test_theme_and_resource_agents_preserve_blocking_unknowns(tmp_path: Path) -> None:
    init_project(tmp_path, "Demo")

    task = Runtime(tmp_path).run(
        "Demo",
        "Create a generic UI page",
        pipeline="ui-production",
    )

    assert task.state["theme_contract"]["status"] == "blocked"
    bundle = task.state["resource_contracts"]
    assert bundle["status"] == "blocked"
    assert {item["code"] for item in bundle["unresolved"]} == {"dimension-unresolved"}
    assert {item["code"] for item in bundle["blocking_conflicts"]} >= {
        "missing-theme",
        "missing-canvas",
        "theme-contract-blocked",
    }
