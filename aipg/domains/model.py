from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DomainPackDefinition:
    """Capabilities and domain semantics registered with the AIPG runtime."""

    domain_id: str
    name: str
    context_types: tuple[str, ...]
    artifact_kinds: tuple[str, ...]
    workflow_ids: tuple[str, ...]
    capability_ids: tuple[str, ...]
