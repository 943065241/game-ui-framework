from pathlib import Path

from guif.privacy import audit_workspace_privacy


def test_framework_tree_contains_no_user_theme_identifiers() -> None:
    root = Path(__file__).resolve().parents[1]
    sensitive_terms = (
        "Leek" + "Party",
        "Medieval " + "Harbor",
        "pirate " + "skulls",
        "warm " + "sunset medieval",
        "韭菜" + "派对",
        "中世纪" + "港口",
    )

    report = audit_workspace_privacy(
        root,
        sensitive_terms=sensitive_terms,
        persist=False,
    )

    assert report["status"] == "passed", report["findings"]
