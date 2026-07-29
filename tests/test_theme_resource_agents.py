from __future__ import annotations

import json
from pathlib import Path

from guif.core import init_project, record_memory
from guif.resource import create_resource_manifest, validate_resource_data
from guif.runtime import Runtime
from guif.theme import create_theme, validate_theme_data


def _create_medieval_theme(tmp_path: Path) -> None:
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
            "materials": ["weathered wood", "aged brass"],
            "lighting": "sunset",
            "must_include": ["harbor view", "gold coins"],
            "avoid": ["pirate skulls", "dirty noise"],
        }
    )
    theme_path.write_text(json.dumps(theme), encoding="utf-8")


def test_theme_and_resource_agents_create_reviewable_contracts(tmp_path: Path) -> None:
    root = init_project(tmp_path, "LeekParty")
    _create_medieval_theme(tmp_path)
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

    theme_contract = task.state["theme_contract"]
    assert theme_contract["status"] == "ready"
    assert theme_contract["source"] == "project-theme"
    assert theme_contract["approval_required"] is False
    assert theme_contract["manifest"]["name"] == "Medieval Harbor"
    assert not validate_theme_data(theme_contract["manifest"])
    assert any(
        "bottom tab navigation" in value
        for value in theme_contract["manifest"]["avoid"]
    )

    bundle = task.state["resource_contracts"]
    assert bundle["status"] == "review-required"
    assert bundle["target_engine"] == "unity"
    assert bundle["materialization_policy"]["project_mutated"] is False
    assert bundle["approved_existing"][0]["resource_id"] == "purchase-button"
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
        "purchase-button.resource.json"
    ]


def test_theme_agent_infers_reviewable_preset_without_mutating_project(tmp_path: Path) -> None:
    root = init_project(tmp_path, "Demo")

    task = Runtime(tmp_path).run(
        "Demo",
        "制作 1080x2340 竖屏中世纪港口商店页面并导出 Unity",
        pipeline="ui-production",
    )

    contract = task.state["theme_contract"]
    assert contract["status"] == "review-required"
    assert contract["source"] == "inferred-preset"
    assert contract["approval_required"] is True
    assert contract["manifest_id"] == "medieval-harbor"
    assert contract["manifest"]["name"] == "Medieval Harbor"
    assert not validate_theme_data(contract["manifest"])
    assert json.loads((root / "project.json").read_text(encoding="utf-8"))["current_theme"] is None
    assert not list((root / "themes").glob("*.json"))

    bundle = task.state["resource_contracts"]
    assert bundle["status"] == "review-required"
    assert not bundle["blocking_conflicts"]
    assert bundle["manifest_candidates"]


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
