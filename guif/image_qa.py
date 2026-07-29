from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from guif.pillow_compat import flattened_image_data


@dataclass(frozen=True)
class PixelProtectionReport:
    width: int
    height: int
    protected_pixels: int
    changed_protected_pixels: int
    max_channel_delta: int
    passed: bool

    def to_dict(self) -> dict[str, int | bool]:
        return asdict(self)


def _load_image(path: Path):
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Image QA requires Pillow. Install with: pip install -e .[image]") from exc
    return Image.open(path).convert("RGBA")


def compare_protected_pixels(
    original_path: Path,
    edited_path: Path,
    mask_path: Path,
    tolerance: int = 0,
) -> PixelProtectionReport:
    if tolerance < 0 or tolerance > 255:
        raise ValueError("Tolerance must be between 0 and 255")

    original = _load_image(original_path)
    edited = _load_image(edited_path)
    mask = _load_image(mask_path).convert("L")

    if original.size != edited.size or original.size != mask.size:
        raise ValueError(
            f"Image sizes must match: original={original.size}, edited={edited.size}, mask={mask.size}"
        )

    protected = 0
    changed = 0
    max_delta = 0
    pixels = zip(
        flattened_image_data(original),
        flattened_image_data(edited),
        flattened_image_data(mask),
    )
    for source, result, mask_value in pixels:
        # White mask pixels are editable. Black mask pixels are protected.
        if mask_value == 0:
            protected += 1
            delta = max(abs(a - b) for a, b in zip(source, result))
            max_delta = max(max_delta, delta)
            if delta > tolerance:
                changed += 1

    return PixelProtectionReport(
        width=original.width,
        height=original.height,
        protected_pixels=protected,
        changed_protected_pixels=changed,
        max_channel_delta=max_delta,
        passed=changed == 0,
    )
