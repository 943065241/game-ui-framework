from __future__ import annotations

from typing import Any, Iterable


def flattened_image_data(image: Any) -> Iterable[Any]:
    """Return flattened Pillow pixel data across supported Pillow releases.

    Pillow 14 replaces ``Image.getdata()`` with ``Image.get_flattened_data()``.
    Prefer the new API when available and retain the old API only as an
    explicit compatibility path for supported older Pillow versions.
    """

    modern = getattr(image, "get_flattened_data", None)
    if callable(modern):
        return modern()
    legacy = getattr(image, "getdata", None)
    if callable(legacy):
        return legacy()
    raise TypeError("Image object exposes neither flattened pixel-data API")


__all__ = ["flattened_image_data"]
