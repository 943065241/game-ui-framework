from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol


class CheckpointStore(Protocol):
    """Persistence boundary for workflow checkpoints."""

    def save(self, run_id: str, checkpoint: Mapping[str, Any]) -> None:
        ...

    def latest(self, run_id: str) -> dict[str, Any] | None:
        ...

    def list(self, run_id: str) -> list[dict[str, Any]]:
        ...


@dataclass
class InMemoryCheckpointStore:
    """Default checkpoint store used by tests and embedded runtimes."""

    _records: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def save(self, run_id: str, checkpoint: Mapping[str, Any]) -> None:
        self._records.setdefault(run_id, []).append(deepcopy(dict(checkpoint)))

    def latest(self, run_id: str) -> dict[str, Any] | None:
        records = self._records.get(run_id, ())
        return deepcopy(records[-1]) if records else None

    def list(self, run_id: str) -> list[dict[str, Any]]:
        return deepcopy(self._records.get(run_id, []))
