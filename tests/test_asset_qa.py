import json
from pathlib import Path

from PIL import Image

from guif.asset_qa import validate_asset_against_manifest


def _manifest(path: Path, **overrides) -> Path:
    data = {
        "schema_version": 1,
        "id": "trade-button",
        "type": "button",
        "width": 4,
        "height": 3,
        "format": "png",
        "alpha_required": True,
        "target_engine": "unity",
        "output_name": "trade-button.png",
        "source": None,
    }
    data.update(overrides)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_asset_matches_manifest(tmp_path: Path):
    manifest = _manifest(tmp_path / "trade-button.resource.json")
    asset = tmp_path / "trade-button.png"
    Image.new("RGBA", (4, 3), (1, 2, 3, 0)).save(asset)

    report = validate_asset_against_manifest(manifest, asset)

    assert report.passed
    assert report.errors == ()
    assert report.has_alpha is True


def test_asset_reports_dimensions_alpha_and_name(tmp_path: Path):
    manifest = _manifest(tmp_path / "trade-button.resource.json")
    asset = tmp_path / "wrong-name.png"
    Image.new("RGB", (5, 3), (1, 2, 3)).save(asset)

    report = validate_asset_against_manifest(manifest, asset)

    assert not report.passed
    assert any("dimensions mismatch" in error for error in report.errors)
    assert any("alpha channel required" in error for error in report.errors)
    assert any("filename mismatch" in error for error in report.errors)


def test_jpeg_is_normalized_to_jpg(tmp_path: Path):
    manifest = _manifest(
        tmp_path / "photo.resource.json",
        id="photo",
        type="background",
        format="jpg",
        alpha_required=False,
        output_name="photo.jpg",
    )
    asset = tmp_path / "photo.jpg"
    Image.new("RGB", (4, 3), (1, 2, 3)).save(asset, format="JPEG")

    report = validate_asset_against_manifest(manifest, asset)

    assert report.passed
    assert report.actual_format == "jpg"
