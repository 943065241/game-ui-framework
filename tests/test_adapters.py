from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from guif.adapters import get_adapter, supported_engines
from guif.core import init_project
from guif.exporter import export_project_assets
from guif.resource import create_resource_manifest


def _png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (16, 12), (1, 2, 3, 128)).save(path)


def test_adapter_registry() -> None:
    assert supported_engines() == ("generic", "godot", "unity", "unreal")
    assert get_adapter("unity").engine == "unity"
    with pytest.raises(ValueError, match="Unsupported target engine"):
        get_adapter("unknown")


def test_unity_export_writes_import_metadata(tmp_path: Path) -> None:
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
        import_settings={"spriteMode": "Multiple", "pixelsPerUnit": 100},
    )
    _png(root / "source" / "trade-button.png")

    report = export_project_assets(tmp_path, "demo", target_engine="unity")

    assert report.passed
    metadata = root / "exports" / "unity" / "trade-button.png.guif-unity.json"
    assert metadata.is_file()
    payload = json.loads(metadata.read_text(encoding="utf-8"))
    assert payload["import_settings"]["textureType"] == "Sprite"
    assert payload["import_settings"]["spriteMode"] == "Multiple"
    assert report.exported[0].adapter["metadata_paths"] == [str(metadata)]


def test_generic_export_creates_no_sidecar(tmp_path: Path) -> None:
    root = init_project(tmp_path, "demo")
    create_resource_manifest(tmp_path, "demo", "icon", "icon", 16, 12, "png", source="source/icon.png")
    _png(root / "source" / "icon.png")

    report = export_project_assets(tmp_path, "demo", target_engine="generic")

    assert report.passed
    assert report.exported[0].adapter["metadata_paths"] == []
