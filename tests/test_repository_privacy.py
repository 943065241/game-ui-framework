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
    details = "\n".join(
        f"{item.get('path')}: {', '.join(item.get('matched_terms', []))}"
        for item in report["findings"]
    )

    assert report["status"] == "passed", details
