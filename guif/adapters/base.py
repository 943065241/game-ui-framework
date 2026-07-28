from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from guif.resource import ResourceManifest


@dataclass(frozen=True)
class AdapterResult:
    engine: str
    asset_path: str
    metadata_paths: tuple[str, ...]
    import_hints: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "engine": self.engine,
            "asset_path": self.asset_path,
            "metadata_paths": list(self.metadata_paths),
            "import_hints": self.import_hints,
        }


class EngineAdapter(ABC):
    engine: str

    @abstractmethod
    def prepare(self, asset_path: Path, manifest: ResourceManifest) -> AdapterResult:
        """Create engine-specific sidecar metadata for an exported asset."""

    @staticmethod
    def write_json(path: Path, payload: dict[str, Any]) -> str:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return str(path)
