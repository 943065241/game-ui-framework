from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from guif.pillow_compat import flattened_image_data


@dataclass(frozen=True)
class CompositeReport:
    width: int
    height: int
    editable_pixels: int
    protected_pixels: int
    feathered_pixels: int
    output: str

    def to_dict(self) -> dict[str, int | str]:
        return asdict(self)


def _image_module():
    try:
        from PIL import Image, ImageFilter
    except ImportError as exc:
        raise RuntimeError("Image composition requires Pillow. Install with: pip install -e .[image]") from exc
    return Image, ImageFilter


def compose_masked_edit(
    original_path: Path,
    generated_path: Path,
    mask_path: Path,
    output_path: Path,
    *,
    feather_radius: float = 0.0,
    threshold: int = 1,
) -> CompositeReport:
    """Composite a generated edit over the original using an explicit mask.

    Mask contract:
    - 0 is protected and is copied byte-for-byte from the original image.
    - 255 is fully editable and is copied from the generated image.
    - Intermediate values blend the two images.

    Feathering is opt-in. Even when feathering is enabled, pixels whose original
    mask value is 0 remain forced to 0 so protected pixels cannot drift.
    """
    if feather_radius < 0:
        raise ValueError("Feather radius must be non-negative")
    if threshold < 0 or threshold > 255:
        raise ValueError("Threshold must be between 0 and 255")

    Image, ImageFilter = _image_module()
    original = Image.open(original_path).convert("RGBA")
    generated = Image.open(generated_path).convert("RGBA")
    raw_mask = Image.open(mask_path).convert("L")

    if original.size != generated.size or original.size != raw_mask.size:
        raise ValueError(
            f"Image sizes must match: original={original.size}, generated={generated.size}, mask={raw_mask.size}"
        )

    if threshold > 1:
        raw_mask = raw_mask.point(lambda value: 255 if value >= threshold else 0)

    protected_map = raw_mask.point(lambda value: 255 if value == 0 else 0)
    working_mask = raw_mask
    if feather_radius > 0:
        working_mask = raw_mask.filter(ImageFilter.GaussianBlur(radius=feather_radius))
        # Restore all explicitly protected pixels to zero after blur expansion.
        working_mask.paste(0, mask=protected_map)

    output = Image.composite(generated, original, working_mask)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.save(output_path, format="PNG")

    mask_values = list(flattened_image_data(working_mask))
    editable = sum(value == 255 for value in mask_values)
    protected = sum(value == 0 for value in mask_values)
    feathered = len(mask_values) - editable - protected

    return CompositeReport(
        width=original.width,
        height=original.height,
        editable_pixels=editable,
        protected_pixels=protected,
        feathered_pixels=feathered,
        output=str(output_path),
    )
