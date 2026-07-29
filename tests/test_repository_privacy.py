from pathlib import Path

from guif.privacy import audit_workspace_privacy


def test_framework_tree_contains_no_private_data_paths() -> None:
    root = Path(__file__).resolve().parents[1]

    report = audit_workspace_privacy(root, persist=False)

    assert report["status"] == "passed", report["findings"]


def test_sensitive_term_scanning_uses_only_fictional_markers(tmp_path: Path) -> None:
    marker = "fictional-private-marker-for-test"
    sample = tmp_path / "sample.txt"
    sample.write_text(f"contains {marker}", encoding="utf-8")

    report = audit_workspace_privacy(
        tmp_path,
        sensitive_terms=(marker,),
        persist=False,
    )

    assert report["status"] == "blocked"
    assert report["findings"][0]["code"] == "sensitive-term-in-working-tree"
    assert report["findings"][0]["path"] == "sample.txt"
