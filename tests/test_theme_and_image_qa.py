from pathlib import Path

from PIL import Image

from guif.core import init_project
from guif.image_qa import compare_protected_pixels
from guif.theme import create_theme, validate_theme_file


def test_create_and_validate_theme(tmp_path: Path) -> None:
    init_project(tmp_path, "Demo")
    theme_path = create_theme(tmp_path, "Demo", "Medieval Harbor", "Warm sunset harbor shop")
    assert theme_path.exists()
    assert validate_theme_file(theme_path) == []


def test_pixel_protection_passes_when_only_masked_area_changes(tmp_path: Path) -> None:
    original = Image.new("RGBA", (2, 1), (10, 10, 10, 255))
    edited = original.copy()
    edited.putpixel((1, 0), (200, 100, 50, 255))
    mask = Image.new("L", (2, 1), 0)
    mask.putpixel((1, 0), 255)

    original_path = tmp_path / "original.png"
    edited_path = tmp_path / "edited.png"
    mask_path = tmp_path / "mask.png"
    original.save(original_path)
    edited.save(edited_path)
    mask.save(mask_path)

    report = compare_protected_pixels(original_path, edited_path, mask_path)
    assert report.passed is True
    assert report.changed_protected_pixels == 0


def test_pixel_protection_fails_when_protected_area_changes(tmp_path: Path) -> None:
    original = Image.new("RGBA", (1, 1), (10, 10, 10, 255))
    edited = Image.new("RGBA", (1, 1), (11, 10, 10, 255))
    mask = Image.new("L", (1, 1), 0)

    original_path = tmp_path / "original.png"
    edited_path = tmp_path / "edited.png"
    mask_path = tmp_path / "mask.png"
    original.save(original_path)
    edited.save(edited_path)
    mask.save(mask_path)

    report = compare_protected_pixels(original_path, edited_path, mask_path)
    assert report.passed is False
    assert report.changed_protected_pixels == 1
