from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DomainPackDefinition:
    """Capabilities and domain semantics registered with the AIPG runtime."""

    domain_id: str
    name: str
    description: str
    context_types: tuple[str, ...]
    artifact_kinds: tuple[str, ...]
    workflow_ids: tuple[str, ...]
    capability_ids: tuple[str, ...] = ()
    legacy_names: tuple[str, ...] = ()

    @property
    def workflows(self) -> tuple[str, ...]:
        """Compatibility alias used by the original GUIF domain API."""

        return self.workflow_ids

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 2,
            "id": self.domain_id,
            "name": self.name,
            "description": self.description,
            "workflows": list(self.workflow_ids),
            "context_types": list(self.context_types),
            "artifact_kinds": list(self.artifact_kinds),
            "capability_ids": list(self.capability_ids),
            "legacy_names": list(self.legacy_names),
        }
