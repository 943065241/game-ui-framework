from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class CapabilityRequirement:
    """Provider-neutral capability requested by a workflow."""

    capability_id: str
    required_features: tuple[str, ...] = ()
    optional_features: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolAdapter:
    """Provider implementation registered behind one or more capabilities."""

    adapter_id: str
    provider: str
    capabilities: tuple[str, ...]
    features: tuple[str, ...] = ()
    configuration_schema: Mapping[str, Any] = field(default_factory=dict)

    def supports(self, requirement: CapabilityRequirement) -> bool:
        return requirement.capability_id in self.capabilities and set(
            requirement.required_features
        ).issubset(self.features)


@dataclass
class ToolRegistry:
    """Shared registry used by every AIPG domain pack."""

    adapters: dict[str, ToolAdapter] = field(default_factory=dict)

    def register(self, adapter: ToolAdapter) -> None:
        if adapter.adapter_id in self.adapters:
            raise ValueError(f"Tool adapter already registered: {adapter.adapter_id}")
        self.adapters[adapter.adapter_id] = adapter

    def resolve(self, requirement: CapabilityRequirement) -> list[ToolAdapter]:
        return [
            adapter
            for adapter in self.adapters.values()
            if adapter.supports(requirement)
        ]
