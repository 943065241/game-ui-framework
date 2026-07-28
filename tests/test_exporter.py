from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from guif.core import init_project
from guif.exporter import export_project_assets
from guif.resource import create_resource_manifest


def _create_png(path: Path, size: tuple[int, int] = (16, 12)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", size, (20, 40, 60, 128)).save(path)


def test_export_project_assets_copies_valid_asset_and_writes_report(tmp_path: Path) -> None:
    root = init_project(tmp_path, "demo")
    create_resource_manifest(
        tmp_path,
        "demo",
        "trade-button",
        "button",
        16,
        12,
        "png",
        target_engine="unity",
        source="source/trade-button.png",
    )
    _create_png(root / "source" / "trade-button.png")

    report = export_project_assets(tmp_path, "demo", target_engine="unity")

    assert report.passed
    assert len(report.exported) == 1
    exported = root / "exports" / "unity" / "trade-button.png"
    assert exported.is_file()
    payload = json.loads((root / "exports" / "unity" / "export-report.json").read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert payload["exported"][0]["resource_id"] == "trade-button"


def test_export_filters_resources_for_other_engines(tmp_path: Path) -> None:
    root = init_project(tmp_path, "demo")
    create_resource_manifest(
        tmp_path,
        "demo",
        "unreal-panel",
        "panel",
        16,
        12,
        "png",
        target_engine="unreal",
        source="source/unreal-panel.png",
    )
    _create_png(root / "source" / "unreal-panel.png")

    report = export_project_assets(tmp_path, "demo", target_engine="unity")

    assert report.passed
    assert report.exported == ()
    assert not (root / "exports" / "unity" / "unreal-panel.png").exists()


def test_export_reports_invalid_asset_without_copying(tmp_path: Path) -> None:
    root = init_project(tmp_path, "demo")
    create_resource_manifest(
        tmp_path,
        "demo",
        "bad-icon",
        "icon",
        16,
        12,
        "png",
        source="source/bad-icon.png",
    )
    _create_png(root / "source" / "bad-icon.png", size=(8, 8))

    report = export_project_assets(tmp_path, "demo", target_engine="generic")

    assert not report.passed
    assert any("dimensions mismatch" in error for error in report.errors)
    assert not (root / "exports" / "generic" / "bad-icon.png").exists()


def test_clean_export_removes_stale_files(tmp_path: Path) -> None:
    root = init_project(tmp_path, "demo")
    stale = root / "exports" / "generic" / "stale.png"
    stale.parent.mkdir(parents=True)
    stale.write_bytes(b"stale")

    report = export_project_assets(tmp_path, "demo", target_engine="generic", clean=True)

    assert report.passed
    assert not stale.exists()
    assert (root / "exports" / "generic" / "export-report.json").is_file()
