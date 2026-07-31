from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping


class ArtifactStatus(str, Enum):
    REGISTERED = "registered"
    DRAFT = "draft"
    GENERATED = "generated"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    EXPORTED = "exported"


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_id: str
    domain_id: str
    kind: str
    status: ArtifactStatus
    parent_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass
class ArtifactRegistry:
    """Domain-neutral Artifact registration, version ancestry, and lineage."""

    records: dict[str, ArtifactRecord] = field(default_factory=dict)

    def register(self, artifact: ArtifactRecord) -> None:
        if artifact.artifact_id in self.records:
            raise ValueError(f"Artifact already registered: {artifact.artifact_id}")
        missing = [parent for parent in artifact.parent_ids if parent not in self.records]
        if missing:
            raise ValueError(f"Unknown parent artifacts: {', '.join(missing)}")
        self.records[artifact.artifact_id] = artifact

    def lineage(self, artifact_id: str) -> list[ArtifactRecord]:
        if artifact_id not in self.records:
            raise ValueError(f"Unknown artifact: {artifact_id}")
        ordered: list[ArtifactRecord] = []
        visited: set[str] = set()

        def visit(current_id: str) -> None:
            if current_id in visited:
                return
            visited.add(current_id)
            current = self.records[current_id]
            for parent_id in current.parent_ids:
                visit(parent_id)
            ordered.append(current)

        visit(artifact_id)
        return ordered
