from __future__ import annotations

from pathlib import Path

from guif.adapters.base import AdapterResult, EngineAdapter
from guif.resource import ResourceManifest


class UnityAdapter(EngineAdapter):
    engine = "unity"

    def prepare(self, asset_path: Path, manifest: ResourceManifest) -> AdapterResult:
        hints = {"textureType": "Sprite", "spriteMode": "Single", "mipmapEnabled": False, **manifest.import_settings}
        meta_path = asset_path.with_suffix(asset_path.suffix + ".guif-unity.json")
        written = self.write_json(meta_path, {"schema_version": 1, "engine": self.engine, "asset": asset_path.name, "import_settings": hints})
        return AdapterResult(self.engine, str(asset_path), (written,), hints)
