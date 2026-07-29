from __future__ import annotations

import hashlib
import json
from abc import ABC
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

TOOL_MANIFEST_SCHEMA_VERSION = 1
TOOL_REQUEST_SCHEMA_VERSION = 1
TOOL_HANDOFF_SCHEMA_VERSION = 1
TOOL_RESULT_SCHEMA_VERSION = 1
HOST_PROFILE_SCHEMA_VERSION = 1
TOOL_HEALTH_SCHEMA_VERSION = 1


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class HostProfile:
    host_id: str
    capabilities: frozenset[str]
    available_tools: frozenset[str] = frozenset()
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = HOST_PROFILE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "host_id": self.host_id,
            "capabilities": sorted(self.capabilities),
            "available_tools": sorted(self.available_tools),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ToolManifest:
    tool_id: str
    name: str
    version: str
    capabilities: frozenset[str]
    execution_mode: str
    input_contract: str = "prompt-ir-job-v1"
    output_contract: str = "artifact-submission-v1"
    environments: tuple[str, ...] = ("production", "development", "ci")
    production_allowed: bool = True
    requires_host_support: bool = False
    supported_hosts: tuple[str, ...] = ()
    requires_credentials: bool = False
    external_call: bool = False
    billable: bool | None = None
    description: str = ""
    schema_version: int = TOOL_MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.tool_id.strip():
            raise ValueError("Tool manifest requires a non-empty tool_id")
        if not self.name.strip():
            raise ValueError("Tool manifest requires a non-empty name")
        if not self.version.strip():
            raise ValueError("Tool manifest requires a non-empty version")
        if not self.capabilities:
            raise ValueError("Tool manifest requires at least one capability")
        if self.execution_mode not in {"direct", "external-callback"}:
            raise ValueError("Tool execution_mode must be direct or external-callback")
        if not self.environments:
            raise ValueError("Tool manifest requires at least one environment")

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["capabilities"] = sorted(self.capabilities)
        payload["environments"] = list(self.environments)
        payload["supported_hosts"] = list(self.supported_hosts)
        return payload


@dataclass(frozen=True)
class ToolHealthReport:
    tool_id: str
    host_id: str
    mode: str
    status: str
    reasons: tuple[str, ...] = ()
    checked_at: str = field(default_factory=_now)
    schema_version: int = TOOL_HEALTH_SCHEMA_VERSION

    @property
    def healthy(self) -> bool:
        return self.status == "healthy"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reasons"] = list(self.reasons)
        payload["healthy"] = self.healthy
        return payload


@dataclass(frozen=True)
class ToolRequest:
    execution_id: str
    task_id: str
    project: str
    job_id: str
    tool_id: str
    host_id: str
    mode: str
    required_capabilities: tuple[str, ...]
    job: dict[str, Any]
    references: tuple[dict[str, Any], ...]
    approval_snapshot: dict[str, Any]
    schema_version: int = TOOL_REQUEST_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["required_capabilities"] = list(self.required_capabilities)
        payload["references"] = [dict(item) for item in self.references]
        return payload


@dataclass(frozen=True)
class ToolHandoff:
    handoff_id: str
    execution_id: str
    task_id: str
    project: str
    job_id: str
    tool_id: str
    host_id: str
    status: str
    request: dict[str, Any]
    instructions: dict[str, Any]
    expected_result: dict[str, Any]
    created_at: str = field(default_factory=_now)
    schema_version: int = TOOL_HANDOFF_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        request: ToolRequest,
        *,
        instructions: dict[str, Any],
        expected_result: dict[str, Any],
    ) -> "ToolHandoff":
        identity = {
            "execution_id": request.execution_id,
            "tool_id": request.tool_id,
            "host_id": request.host_id,
            "job_id": request.job_id,
            "request": request.to_dict(),
        }
        return cls(
            handoff_id="handoff-" + _canonical_hash(identity)[:16],
            execution_id=request.execution_id,
            task_id=request.task_id,
            project=request.project,
            job_id=request.job_id,
            tool_id=request.tool_id,
            host_id=request.host_id,
            status="waiting-for-result",
            request=request.to_dict(),
            instructions=instructions,
            expected_result=expected_result,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ToolResult:
    tool_id: str
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
    schema_version: int = TOOL_RESULT_SCHEMA_VERSION

    def metadata_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tool_id": self.tool_id,
            "provider_id": self.tool_id,
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


class ToolAdapter(ABC):
    manifest: ToolManifest
    requires_bound_references: bool = True

    @property
    def tool_id(self) -> str:
        return self.manifest.tool_id

    @property
    def capabilities(self) -> frozenset[str]:
        return self.manifest.capabilities

    def describe(self) -> dict[str, Any]:
        return {
            **self.manifest.to_dict(),
            "requires_bound_references": self.requires_bound_references,
        }

    def missing_capabilities(self, required: Iterable[str]) -> tuple[str, ...]:
        return tuple(sorted(set(required) - set(self.capabilities)))

    def health_check(
        self,
        host: HostProfile,
        *,
        mode: str,
        explicit: bool = False,
    ) -> ToolHealthReport:
        reasons: list[str] = []
        if mode not in self.manifest.environments:
            reasons.append(f"Tool is not available in {mode} mode.")
        if mode == "production" and not self.manifest.production_allowed and not explicit:
            reasons.append("Tool is not allowed as an automatic production selection.")
        if self.manifest.requires_host_support:
            if self.manifest.supported_hosts and host.host_id not in self.manifest.supported_hosts:
                reasons.append(f"Host {host.host_id} is not supported by this Tool.")
            missing_host = sorted(self.capabilities - host.capabilities)
            if missing_host:
                reasons.append(
                    "Host does not advertise required Tool capabilities: "
                    + ", ".join(missing_host)
                )
        status = "healthy" if not reasons else "unavailable"
        return ToolHealthReport(
            tool_id=self.tool_id,
            host_id=host.host_id,
            mode=mode,
            status=status,
            reasons=tuple(reasons),
        )

    def prepare(self, request: ToolRequest, host: HostProfile) -> ToolHandoff:
        raise ValueError(f"Tool {self.tool_id} does not support external handoff preparation")

    def execute(self, request: ToolRequest) -> ToolResult:
        raise ValueError(f"Tool {self.tool_id} does not support direct execution")
