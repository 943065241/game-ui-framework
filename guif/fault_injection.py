from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Iterable


class FaultInjectionDisabled(RuntimeError):
    pass


class InjectedFault(RuntimeError):
    def __init__(self, point: str) -> None:
        super().__init__(f"Injected fault at {point}")
        self.point = point


def _normalized(values: Iterable[str]) -> frozenset[str]:
    return frozenset(str(value).strip() for value in values if str(value).strip())


@dataclass
class FaultInjector:
    """Explicit test/development-only failure injection.

    Production code receives a disabled injector by default. Environment-driven
    injection requires both GUIF_ALLOW_FAULT_INJECTION=1 and one or more named
    GUIF_FAULT_POINTS. This prevents a forgotten fault-point variable from
    silently affecting production execution.
    """

    enabled: bool = False
    points: frozenset[str] = field(default_factory=frozenset)
    triggered: list[str] = field(default_factory=list)

    @classmethod
    def disabled(cls) -> "FaultInjector":
        return cls(enabled=False, points=frozenset())

    @classmethod
    def explicit(cls, *points: str) -> "FaultInjector":
        normalized = _normalized(points)
        if not normalized:
            raise ValueError("At least one fault point is required")
        return cls(enabled=True, points=normalized)

    @classmethod
    def from_env(cls) -> "FaultInjector":
        requested = _normalized(os.environ.get("GUIF_FAULT_POINTS", "").split(","))
        if not requested:
            return cls.disabled()
        if os.environ.get("GUIF_ALLOW_FAULT_INJECTION") != "1":
            raise FaultInjectionDisabled(
                "GUIF_FAULT_POINTS is set but GUIF_ALLOW_FAULT_INJECTION=1 is not enabled"
            )
        return cls(enabled=True, points=requested)

    def hit(self, point: str) -> None:
        normalized = point.strip()
        if not normalized:
            raise ValueError("Fault point must not be empty")
        if self.enabled and normalized in self.points:
            self.triggered.append(normalized)
            raise InjectedFault(normalized)


__all__ = [
    "FaultInjectionDisabled",
    "FaultInjector",
    "InjectedFault",
]
