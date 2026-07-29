from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from guif.paths import project_root
from guif.tools.base import HostProfile, ToolAdapter
from guif.tools.config import bind_project_tool, load_execution_settings
from guif.tools.registry import ToolRegistry

TOOL_CATALOG_SCHEMA_VERSION = 1
HOST_DISCOVERY_SCHEMA_VERSION = 1
TOOL_DISCOVERY_SCHEMA_VERSION = 1
TOOL_CONNECTION_SCHEMA_VERSION = 1
TOOL_CONTRACT_TEST_SCHEMA_VERSION = 1
CONNECTION_DECISIONS = {"approved", "rejected"}


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


def _cost_label(value: bool | None) -> str:
    if value is True:
        return "billable"
    if value is False:
        return "no-charge"
    return "unknown"


@dataclass(frozen=True)
class ToolCatalogEntry:
    tool_id: str
    name: str
    version: str
    capabilities: frozenset[str]
    install_method: str
    source: str
    permissions: tuple[str, ...] = ()
    data_scopes: tuple[str, ...] = ()
    requires_credentials: bool = False
    credential_kind: str | None = None
    external_call: bool = False
    billable: bool | None = None
    supported_hosts: tuple[str, ...] = ()
    description: str = ""
    schema_version: int = TOOL_CATALOG_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.tool_id.strip():
            raise ValueError("Catalog Tool requires a non-empty tool_id")
        if not self.name.strip() or not self.version.strip():
            raise ValueError("Catalog Tool requires name and version")
        if not self.capabilities:
            raise ValueError("Catalog Tool requires at least one capability")
        if not self.install_method.strip() or not self.source.strip():
            raise ValueError("Catalog Tool requires install_method and source")
        if self.requires_credentials and not self.credential_kind:
            raise ValueError("Credential-requiring Catalog Tool must declare credential_kind")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ToolCatalogEntry":
        return cls(
            tool_id=str(value.get("tool_id") or value.get("id") or ""),
            name=str(value.get("name") or ""),
            version=str(value.get("version") or ""),
            capabilities=frozenset(str(item) for item in value.get("capabilities", [])),
            install_method=str(value.get("install_method") or "manual"),
            source=str(value.get("source") or "workspace-catalog"),
            permissions=tuple(str(item) for item in value.get("permissions", [])),
            data_scopes=tuple(str(item) for item in value.get("data_scopes", [])),
            requires_credentials=value.get("requires_credentials") is True,
            credential_kind=(
                str(value.get("credential_kind"))
                if value.get("credential_kind") is not None
                else None
            ),
            external_call=value.get("external_call") is True,
            billable=value.get("billable") if isinstance(value.get("billable"), bool) else None,
            supported_hosts=tuple(str(item) for item in value.get("supported_hosts", [])),
            description=str(value.get("description") or ""),
            schema_version=int(value.get("schema_version", TOOL_CATALOG_SCHEMA_VERSION)),
        )

    def disclosure(self) -> dict[str, Any]:
        return {
            "permissions": list(self.permissions),
            "data_scopes": list(self.data_scopes),
            "external_call": self.external_call,
            "cost": _cost_label(self.billable),
            "billable": self.billable,
            "requires_credentials": self.requires_credentials,
            "credential_kind": self.credential_kind,
            "supported_hosts": list(self.supported_hosts),
            "install_method": self.install_method,
            "source": self.source,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["capabilities"] = sorted(self.capabilities)
        payload["permissions"] = list(self.permissions)
        payload["data_scopes"] = list(self.data_scopes)
        payload["supported_hosts"] = list(self.supported_hosts)
        payload["disclosure"] = self.disclosure()
        return payload


def load_tool_catalog(workspace: Path) -> tuple[ToolCatalogEntry, ...]:
    path = workspace / ".guif" / "tool-catalog.json"
    if not path.is_file():
        return ()
    payload = json.loads(path.read_text(encoding="utf-8"))
    values = payload.get("tools", []) if isinstance(payload, dict) else payload
    if not isinstance(values, list):
        raise ValueError("Tool catalog must be a list or an object containing tools")
    entries = tuple(ToolCatalogEntry.from_dict(item) for item in values if isinstance(item, dict))
    seen: set[str] = set()
    for entry in entries:
        if entry.tool_id in seen:
            raise ValueError(f"Duplicate Tool catalog entry: {entry.tool_id}")
        seen.add(entry.tool_id)
    return entries


class ToolDiscoveryService:
    def __init__(
        self,
        workspace: Path,
        *,
        tools: ToolRegistry,
        host: HostProfile,
        catalog: Iterable[ToolCatalogEntry] | None = None,
    ) -> None:
        self.workspace = workspace
        self.tools = tools
        self.host = host
        self.catalog = tuple(catalog) if catalog is not None else load_tool_catalog(workspace)

    def discover_host(self) -> dict[str, Any]:
        return {
            "schema_version": HOST_DISCOVERY_SCHEMA_VERSION,
            "protocol": "guif-host-capability-discovery-v1",
            "host": self.host.to_dict(),
            "available_tool_ids": sorted(self.host.available_tools),
            "capability_count": len(self.host.capabilities),
            "discovered_at": _now(),
        }

    def _state_path(self, project: str) -> Path:
        return project_root(self.workspace, project) / "tool-connections.json"

    def _load_state(self, project: str) -> dict[str, Any]:
        path = self._state_path(project)
        if not path.is_file():
            return {
                "schema_version": TOOL_CONNECTION_SCHEMA_VERSION,
                "project": project,
                "requests": [],
                "health_checks": [],
                "updated_at": _now(),
            }
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Tool connection state must be an object")
        payload.setdefault("requests", [])
        payload.setdefault("health_checks", [])
        return payload

    def _save_state(self, project: str, state: dict[str, Any]) -> Path:
        path = self._state_path(project)
        path.parent.mkdir(parents=True, exist_ok=True)
        state["schema_version"] = TOOL_CONNECTION_SCHEMA_VERSION
        state["project"] = project
        state["updated_at"] = _now()
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
        return path

    def _catalog_by_id(self) -> dict[str, ToolCatalogEntry]:
        return {entry.tool_id: entry for entry in self.catalog}

    def discover_tools(
        self,
        *,
        project: str | None = None,
        mode: str | None = None,
    ) -> tuple[dict[str, Any], ...]:
        resolved_mode = mode or (
            load_execution_settings(self.workspace, project).mode if project else "production"
        )
        catalog = self._catalog_by_id()
        registered = {item["tool_id"]: item for item in self.tools.describe()}
        ids = sorted(set(registered) | set(catalog) | set(self.host.available_tools))
        connection_state = self._load_state(project) if project else {"requests": []}
        requests = connection_state.get("requests", [])
        results: list[dict[str, Any]] = []
        for tool_id in ids:
            adapter = self.tools.find(tool_id)
            catalog_entry = catalog.get(tool_id)
            states: list[str] = []
            if adapter is not None:
                states.append("registered")
            if tool_id in self.host.available_tools or (
                adapter is not None and not adapter.manifest.requires_host_support
            ):
                states.append("available")
            if catalog_entry is not None:
                states.append("installable")
            health = (
                adapter.health_check(self.host, mode=resolved_mode, explicit=False).to_dict()
                if adapter is not None
                else None
            )
            if adapter is not None:
                disclosure = adapter.manifest.disclosure()
                manifest = adapter.describe()
            elif catalog_entry is not None:
                disclosure = catalog_entry.disclosure()
                manifest = catalog_entry.to_dict()
            else:
                disclosure = {
                    "permissions": [],
                    "data_scopes": [],
                    "external_call": None,
                    "cost": "unknown",
                    "billable": None,
                    "requires_credentials": None,
                    "credential_kind": None,
                    "supported_hosts": [],
                }
                manifest = None
            ready = bool(adapter is not None and health and health.get("healthy") is True)
            if ready:
                status = "available"
            elif adapter is not None:
                status = "registered"
            elif catalog_entry is not None:
                status = "installable"
            else:
                status = "available-unregistered"
            related = [
                item
                for item in requests
                if isinstance(item, dict) and item.get("tool_id") == tool_id
            ]
            latest_connection = related[-1] if related else None
            results.append(
                {
                    "schema_version": TOOL_DISCOVERY_SCHEMA_VERSION,
                    "tool_id": tool_id,
                    "status": status,
                    "states": states,
                    "ready": ready,
                    "registered": adapter is not None,
                    "available": "available" in states,
                    "installable": catalog_entry is not None,
                    "host_id": self.host.host_id,
                    "mode": resolved_mode,
                    "manifest": manifest,
                    "disclosure": disclosure,
                    "health": health,
                    "connection_status": latest_connection.get("status")
                    if isinstance(latest_connection, dict)
                    else None,
                }
            )
        return tuple(results)

    def _descriptor(self, project: str, tool_id: str) -> dict[str, Any] | None:
        return next(
            (item for item in self.discover_tools(project=project) if item["tool_id"] == tool_id),
            None,
        )

    def create_connection_request(
        self,
        project: str,
        capability: str,
        tool_id: str | None,
        *,
        requested_by: str = "host",
        reason: str | None = None,
        required_capabilities: Iterable[str] = (),
    ) -> dict[str, Any]:
        normalized_capability = capability.strip()
        normalized_tool_id = tool_id.strip() if isinstance(tool_id, str) and tool_id.strip() else None
        normalized_actor = requested_by.strip()
        if not normalized_capability or not normalized_actor:
            raise ValueError("Capability and requested_by must not be empty")
        state = self._load_state(project)
        requests = state.setdefault("requests", [])
        if not isinstance(requests, list):
            raise ValueError("Invalid Tool connection request state")
        unresolved = {
            "pending",
            "tool-selection-required",
            "installation-required",
            "waiting-for-credentials",
            "waiting-for-host-support",
            "health-check-failed",
        }
        existing = next(
            (
                item
                for item in reversed(requests)
                if isinstance(item, dict)
                and item.get("capability") == normalized_capability
                and item.get("tool_id") == normalized_tool_id
                and item.get("status") in unresolved
            ),
            None,
        )
        if isinstance(existing, dict):
            return dict(existing)
        descriptor = self._descriptor(project, normalized_tool_id) if normalized_tool_id else None
        sequence = len(requests) + 1
        identity = {
            "project": project,
            "capability": normalized_capability,
            "tool_id": normalized_tool_id,
            "sequence": sequence,
        }
        request_id = "tool-connection-" + _canonical_hash(identity)[:16]
        disclosure = descriptor.get("disclosure") if isinstance(descriptor, dict) else {
            "permissions": [],
            "data_scopes": [],
            "external_call": None,
            "cost": "unknown",
            "billable": None,
            "requires_credentials": None,
            "credential_kind": None,
            "supported_hosts": [],
        }
        timestamp = _now()
        request = {
            "schema_version": TOOL_CONNECTION_SCHEMA_VERSION,
            "request_id": request_id,
            "project": project,
            "capability": normalized_capability,
            "required_capabilities": sorted(set(str(item) for item in required_capabilities)),
            "tool_id": normalized_tool_id,
            "status": "pending" if normalized_tool_id else "tool-selection-required",
            "requested_by": normalized_actor,
            "reason": reason or "A Tool connection is required before execution can continue.",
            "tool_states": list(descriptor.get("states", [])) if isinstance(descriptor, dict) else [],
            "disclosure": disclosure,
            "approval": None,
            "credential": {
                "required": disclosure.get("requires_credentials") is True,
                "kind": disclosure.get("credential_kind"),
                "reference": None,
                "secret_stored_by_guif": False,
            },
            "health": descriptor.get("health") if isinstance(descriptor, dict) else None,
            "next_actions": [
                "Review permissions, data scope, external-call, cost, and credential disclosures.",
                "Approve or reject the connection request.",
                "Install or register the Tool when status is installable only.",
                "Provide an opaque credential reference when credentials are required.",
                "Retry health after Host, Tool, or credential configuration changes.",
            ],
            "history": [],
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        requests.append(request)
        self._save_state(project, state)
        return dict(request)

    def list_connection_requests(self, project: str) -> tuple[dict[str, Any], ...]:
        state = self._load_state(project)
        return tuple(item for item in state.get("requests", []) if isinstance(item, dict))

    @staticmethod
    def _find_request(state: dict[str, Any], request_id: str) -> dict[str, Any]:
        for item in state.get("requests", []):
            if isinstance(item, dict) and item.get("request_id") == request_id:
                return item
        raise ValueError(f"Unknown Tool connection request: {request_id}")

    def _finalize_approved_request(
        self,
        project: str,
        request: dict[str, Any],
        *,
        credential_ref: str | None,
    ) -> None:
        tool_id = request.get("tool_id")
        if not isinstance(tool_id, str) or not tool_id:
            request["status"] = "tool-selection-required"
            return
        descriptor = self._descriptor(project, tool_id)
        if descriptor is None:
            request["status"] = "unsupported"
            return
        adapter = self.tools.find(tool_id)
        if adapter is None:
            request["status"] = "installation-required" if descriptor.get("installable") else "unsupported"
            return
        credential = request.get("credential") if isinstance(request.get("credential"), dict) else {}
        if credential.get("required") is True:
            normalized_ref = credential_ref.strip() if isinstance(credential_ref, str) else ""
            if normalized_ref:
                credential["reference"] = normalized_ref
            if not credential.get("reference"):
                request["status"] = "waiting-for-credentials"
                request["credential"] = credential
                return
        health = adapter.health_check(self.host, mode=load_execution_settings(self.workspace, project).mode)
        request["health"] = health.to_dict()
        if not health.healthy:
            request["status"] = (
                "waiting-for-host-support"
                if any("Host" in reason for reason in health.reasons)
                else "health-check-failed"
            )
            return
        bind_project_tool(self.workspace, project, str(request["capability"]), tool_id)
        request["status"] = "connected"
        request["connected_at"] = _now()

    def decide_connection(
        self,
        project: str,
        request_id: str,
        decision: str,
        *,
        actor: str,
        comment: str | None = None,
        credential_ref: str | None = None,
    ) -> dict[str, Any]:
        normalized_decision = decision.strip().lower()
        normalized_actor = actor.strip()
        if normalized_decision not in CONNECTION_DECISIONS:
            raise ValueError("decision must be approved or rejected")
        if not normalized_actor:
            raise ValueError("actor must not be empty")
        state = self._load_state(project)
        request = self._find_request(state, request_id)
        timestamp = _now()
        record = {
            "decision": normalized_decision,
            "actor": normalized_actor,
            "comment": comment.strip() if isinstance(comment, str) and comment.strip() else None,
            "decided_at": timestamp,
        }
        request["approval"] = dict(record)
        history = request.setdefault("history", [])
        if not isinstance(history, list):
            raise ValueError("Invalid Tool connection request history")
        history.append(dict(record))
        if normalized_decision == "rejected":
            request["status"] = "rejected"
        else:
            self._finalize_approved_request(project, request, credential_ref=credential_ref)
        request["updated_at"] = timestamp
        self._save_state(project, state)
        return dict(request)

    def retry_health(self, project: str, tool_id: str) -> dict[str, Any]:
        adapter = self.tools.get(tool_id)
        mode = load_execution_settings(self.workspace, project).mode
        health = adapter.health_check(self.host, mode=mode, explicit=False).to_dict()
        state = self._load_state(project)
        checks = state.setdefault("health_checks", [])
        if not isinstance(checks, list):
            raise ValueError("Invalid Tool health check history")
        record = {
            "schema_version": 1,
            "attempt": 1 + sum(
                1 for item in checks if isinstance(item, dict) and item.get("tool_id") == tool_id
            ),
            "tool_id": tool_id,
            "project": project,
            "host_id": self.host.host_id,
            "mode": mode,
            "health": health,
            "checked_at": _now(),
        }
        checks.append(record)
        for request in state.get("requests", []):
            if not isinstance(request, dict) or request.get("tool_id") != tool_id:
                continue
            approval = request.get("approval")
            if isinstance(approval, dict) and approval.get("decision") == "approved" and request.get("status") != "connected":
                credential = request.get("credential") if isinstance(request.get("credential"), dict) else {}
                self._finalize_approved_request(
                    project,
                    request,
                    credential_ref=credential.get("reference"),
                )
                request["updated_at"] = _now()
        self._save_state(project, state)
        return record

    def run_contract_tests(self, tool_id: str, *, mode: str = "production") -> dict[str, Any]:
        tool = self.tools.get(tool_id)
        checks: list[dict[str, Any]] = []

        def check(check_id: str, passed: bool, message: str) -> None:
            checks.append({"id": check_id, "status": "passed" if passed else "failed", "message": message})

        manifest = tool.manifest
        check("manifest-schema", manifest.schema_version == 1, "Tool Manifest schema is supported.")
        check("identity", tool.tool_id == manifest.tool_id and bool(tool.tool_id.strip()), "Adapter and Manifest identity match.")
        check("capabilities", bool(manifest.capabilities), "At least one capability is declared.")
        check("input-contract", bool(manifest.input_contract.strip()), "Input contract is declared.")
        check("output-contract", bool(manifest.output_contract.strip()), "Output contract is declared.")
        check(
            "execution-method",
            (
                type(tool).prepare is not ToolAdapter.prepare
                if manifest.execution_mode == "external-callback"
                else type(tool).execute is not ToolAdapter.execute
            ),
            "Adapter implements the method required by its execution mode.",
        )
        disclosure = manifest.disclosure()
        check("permission-disclosure", isinstance(disclosure.get("permissions"), list), "Permissions are explicitly disclosed.")
        check("data-scope-disclosure", isinstance(disclosure.get("data_scopes"), list), "Data scopes are explicitly disclosed.")
        check("cost-disclosure", disclosure.get("cost") in {"billable", "no-charge", "unknown"}, "Cost behavior is explicitly disclosed.")
        check(
            "credential-disclosure",
            not manifest.requires_credentials or bool(manifest.credential_kind),
            "Credential requirements include an opaque credential kind.",
        )
        health = tool.health_check(self.host, mode=mode, explicit=False)
        check(
            "health-contract",
            health.tool_id == tool_id and health.host_id == self.host.host_id and health.status in {"healthy", "unavailable"},
            "Health Check returns a valid identity and status.",
        )
        failed = [item for item in checks if item["status"] == "failed"]
        return {
            "schema_version": TOOL_CONTRACT_TEST_SCHEMA_VERSION,
            "tool_id": tool_id,
            "host_id": self.host.host_id,
            "mode": mode,
            "status": "failed" if failed else "passed",
            "summary": {
                "check_count": len(checks),
                "failed_count": len(failed),
                "external_call_performed": False,
            },
            "checks": checks,
            "manifest": tool.describe(),
            "health": health.to_dict(),
            "tested_at": _now(),
        }
