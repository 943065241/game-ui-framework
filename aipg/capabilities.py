from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping


ToolExecutionHandler = Callable[[Mapping[str, Any]], Mapping[str, Any] | None]


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
    priority: int = 100
    execute_handler: ToolExecutionHandler | None = field(
        default=None, repr=False, compare=False
    )

    def supports(self, requirement: CapabilityRequirement) -> bool:
        return requirement.capability_id in self.capabilities and set(
            requirement.required_features
        ).issubset(self.features)

    def execute(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        if self.execute_handler is None:
            raise RuntimeError(f"Tool adapter has no execution handler: {self.adapter_id}")
        return dict(self.execute_handler(dict(arguments)) or {})


@dataclass
class ToolRegistry:
    """Shared registry used by every AIPG domain pack."""

    adapters: dict[str, ToolAdapter] = field(default_factory=dict)

    def register(self, adapter: ToolAdapter) -> None:
        if adapter.adapter_id in self.adapters:
            raise ValueError(f"Tool adapter already registered: {adapter.adapter_id}")
        self.adapters[adapter.adapter_id] = adapter

    def resolve(self, requirement: CapabilityRequirement) -> list[ToolAdapter]:
        return sorted(
            (
                adapter
                for adapter in self.adapters.values()
                if adapter.supports(requirement)
            ),
            key=lambda adapter: (adapter.priority, adapter.adapter_id),
        )

    def select(self, requirement: CapabilityRequirement) -> ToolAdapter:
        matches = self.resolve(requirement)
        if not matches:
            raise LookupError(
                f"No tool adapter satisfies capability: {requirement.capability_id}"
            )
        return matches[0]

    def execute(
        self,
        requirement: CapabilityRequirement,
        arguments: Mapping[str, Any] | None = None,
    ) -> tuple[ToolAdapter, dict[str, Any]]:
        adapter = self.select(requirement)
        return adapter, adapter.execute(dict(arguments or {}))
