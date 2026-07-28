from __future__ import annotations

from pathlib import Path

from guif.adapters.base import AdapterResult, EngineAdapter
from guif.resource import ResourceManifest


class GenericAdapter(EngineAdapter):
    engine = "generic"

    def prepare(self, asset_path: Path, manifest: ResourceManifest) -> AdapterResult:
        return AdapterResult(
            engine=self.engine,
            asset_path=str(asset_path),
            metadata_paths=(),
            import_hints=dict(manifest.import_settings),
        )
