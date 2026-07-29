from __future__ import annotations

from guif.retrieval import select_relevant_context, selected_records, tokenize


def test_tokenize_supports_english_and_chinese_terms() -> None:
    tokens = tokenize("Geometric 抽象商店 UI")

    assert "geometric" in tokens
    assert "抽象" in tokens
    assert "商店" in tokens


def test_retrieval_ranks_relevant_memory_and_respects_budget() -> None:
    context = {
        "active_theme": None,
        "memory": (
            {
                "path": "memory/decisions/shop.md",
                "type": "decisions",
                "content": "The fictional shop page must keep hexagonal navigation and must not use bottom tabs.",
            },
            {
                "path": "memory/lessons/dashboard.md",
                "type": "lessons",
                "content": "The dashboard data grid needs stronger contrast.",
            },
            {
                "path": "memory/mistakes/login.md",
                "type": "mistakes",
                "content": "The login logo was too small.",
            },
        ),
        "resources": (),
        "workflows": (),
    }

    selection = select_relevant_context(
        context,
        "Create the geometric arcade shop page without bottom tabs",
        memory_limit=1,
    )

    assert len(selection["memory"]) == 1
    assert selection["memory"][0]["record"]["path"].endswith("shop.md")
    assert selection["memory"][0]["score"] > 0
    assert selection["omitted"]["memory"] >= 0
    assert selected_records(selection, "memory")[0]["type"] == "decisions"


def test_retrieval_selects_matching_resource_and_workflow() -> None:
    context = {
        "active_theme": None,
        "memory": (),
        "resources": (
            {"id": "action-button", "type": "button", "output_name": "action-button.png"},
            {"id": "data-chart", "type": "panel", "output_name": "data-chart.png"},
        ),
        "workflows": (
            {"id": "shop-production", "name": "Shop Production", "steps": ["Build shop UI"]},
            {"id": "dashboard-production", "name": "Dashboard Production", "steps": ["Build dashboard UI"]},
        ),
    }

    selection = select_relevant_context(context, "Create a shop action button")

    assert selected_records(selection, "resources")[0]["id"] == "action-button"
    assert selected_records(selection, "workflows")[0]["id"] == "shop-production"
