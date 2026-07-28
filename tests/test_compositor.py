from pathlib import Path

from PIL import Image

from guif.compositor import compose_masked_edit
from guif.image_qa import compare_protected_pixels


def test_compose_edit_preserves_black_mask_pixels(tmp_path: Path) -> None:
    original_path = tmp_path / "original.png"
    generated_path = tmp_path / "generated.png"
    mask_path = tmp_path / "mask.png"
    output_path = tmp_path / "output.png"

    Image.new("RGBA", (3, 1), (10, 20, 30, 255)).save(original_path)
    Image.new("RGBA", (3, 1), (200, 100, 50, 255)).save(generated_path)
    mask = Image.new("L", (3, 1), 0)
    mask.putpixel((1, 0), 255)
    mask.save(mask_path)

    report = compose_masked_edit(original_path, generated_path, mask_path, output_path)
    output = Image.open(output_path).convert("RGBA")

    assert output.getpixel((0, 0)) == (10, 20, 30, 255)
    assert output.getpixel((1, 0)) == (200, 100, 50, 255)
    assert output.getpixel((2, 0)) == (10, 20, 30, 255)
    assert report.editable_pixels == 1
    assert report.protected_pixels == 2
    assert compare_protected_pixels(original_path, output_path, mask_path).passed


def test_feather_does_not_expand_into_explicitly_protected_pixels(tmp_path: Path) -> None:
    original_path = tmp_path / "original.png"
    generated_path = tmp_path / "generated.png"
    mask_path = tmp_path / "mask.png"
    output_path = tmp_path / "output.png"

    Image.new("RGBA", (5, 1), (0, 0, 0, 255)).save(original_path)
    Image.new("RGBA", (5, 1), (255, 255, 255, 255)).save(generated_path)
    mask = Image.new("L", (5, 1), 0)
    mask.putpixel((2, 0), 255)
    mask.save(mask_path)

    compose_masked_edit(original_path, generated_path, mask_path, output_path, feather_radius=2)

    assert compare_protected_pixels(original_path, output_path, mask_path, tolerance=0).passed
