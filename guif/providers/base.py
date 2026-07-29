from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any


EXECUTION_REQUEST_SCHEMA_VERSION = 1
EXECUTION_RESULT_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ExecutionRequest:
    execution_id: str
    task_id: str
    project: str
    job_id: str
    provider_id: str
    required_capabilities: tuple[str, ...]
    job: dict[str, Any]
    references: tuple[dict[str, Any], ...]
    approval_snapshot: dict[str, Any]
    schema_version: int = EXECUTION_REQUEST_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["required_capabilities"] = list(self.required_capabilities)
        payload["references"] = list(self.references)
        return payload


@dataclass(frozen=True)
class ExecutionResult:
    provider_id: str
    request_id: str
    content: bytes
    filename: str
    mime_type: str
    width: int | None = None
    height: int | None = None
    model_id: str | None = None
    simulation: bool = False
    visual: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = EXECUTION_RESULT_SCHEMA_VERSION

    def metadata_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "provider_id": self.provider_id,
            "request_id": self.request_id,
            "filename": self.filename,
            "mime_type": self.mime_type,
            "width": self.width,
            "height": self.height,
            "model_id": self.model_id,
            "simulation": self.simulation,
            "visual": self.visual,
            "metadata": dict(self.metadata),
        }


class ProviderAdapter(ABC):
    provider_id: str
    capabilities: frozenset[str]
    requires_bound_references: bool = True

    def describe(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "capabilities": sorted(self.capabilities),
            "requires_bound_references": self.requires_bound_references,
        }

    def missing_capabilities(self, required: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(sorted(set(required) - set(self.capabilities)))

    @abstractmethod
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        raise NotImplementedError
