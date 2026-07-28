from __future__ import annotations

import json

from guif.core import init_project, validate_project
from guif.resource import create_resource_manifest, load_resource_manifest, validate_resource_data


def test_create_and_load_resource_manifest(tmp_path):
    init_project(tmp_path, "LeekParty")
    path = create_resource_manifest(
        tmp_path,
        "LeekParty",
        "trade-button-long",
        "button",
        264,
        134,
        "png",
        target_engine="unity",
    )
    manifest = load_resource_manifest(path)
    assert manifest.resource_id == "trade-button-long"
    assert manifest.width == 264
    assert manifest.height == 134
    assert manifest.alpha_required is True
    assert manifest.output_name == "trade-button-long.png"
    assert validate_project(tmp_path, "LeekParty") == []


def test_rejects_jpg_with_required_alpha():
    errors = validate_resource_data(
        {
            "schema_version": 1,
            "id": "shop-background",
            "type": "background",
            "width": 2340,
            "height": 1080,
            "format": "jpg",
            "alpha_required": True,
            "target_engine": "generic",
            "output_name": "shop-background.jpg",
        }
    )
    assert "jpg cannot satisfy alpha_required=true" in errors


def test_project_validation_reports_invalid_resource(tmp_path):
    root = init_project(tmp_path, "LeekParty")
    path = root / "production-assets" / "bad.resource.json"
    path.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
    errors = validate_project(tmp_path, "LeekParty")
    assert any("bad.resource.json" in error for error in errors)
