from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from guif.resource import ResourceManifest, load_resource_manifest


@dataclass(frozen=True)
class AssetValidationReport:
    manifest: str
    asset: str
    expected_width: int
    expected_height: int
    actual_width: int
    actual_height: int
    expected_format: str
    actual_format: str
    alpha_required: bool
    has_alpha: bool
    expected_output_name: str
    actual_name: str
    errors: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["passed"] = self.passed
        payload["errors"] = list(self.errors)
        return payload


def _image_module():
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Asset validation requires Pillow. Install with: pip install -e .[image]") from exc
    return Image


def _detect_alpha(image) -> bool:
    if image.mode in {"RGBA", "LA"}:
        return True
    if image.mode == "P" and "transparency" in image.info:
        return True
    return "A" in image.getbands()


def validate_asset_against_manifest(manifest_path: Path, asset_path: Path) -> AssetValidationReport:
    manifest: ResourceManifest = load_resource_manifest(manifest_path)
    if not asset_path.is_file():
        raise FileNotFoundError(f"Asset does not exist: {asset_path}")

    Image = _image_module()
    with Image.open(asset_path) as image:
        actual_width, actual_height = image.size
        actual_format = (image.format or asset_path.suffix.lstrip(".")).lower()
        if actual_format == "jpeg":
            actual_format = "jpg"
        has_alpha = _detect_alpha(image)

    errors: list[str] = []
    if (actual_width, actual_height) != (manifest.width, manifest.height):
        errors.append(
            f"dimensions mismatch: expected {manifest.width}x{manifest.height}, got {actual_width}x{actual_height}"
        )
    if actual_format != manifest.file_format:
        errors.append(f"format mismatch: expected {manifest.file_format}, got {actual_format}")
    if manifest.alpha_required and not has_alpha:
        errors.append("alpha channel required but asset has no alpha channel")
    if asset_path.name != manifest.output_name:
        errors.append(f"filename mismatch: expected {manifest.output_name}, got {asset_path.name}")

    return AssetValidationReport(
        manifest=str(manifest_path),
        asset=str(asset_path),
        expected_width=manifest.width,
        expected_height=manifest.height,
        actual_width=actual_width,
        actual_height=actual_height,
        expected_format=manifest.file_format,
        actual_format=actual_format,
        alpha_required=manifest.alpha_required,
        has_alpha=has_alpha,
        expected_output_name=manifest.output_name,
        actual_name=asset_path.name,
        errors=tuple(errors),
    )
