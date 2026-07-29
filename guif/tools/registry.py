from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from guif.tools.base import HostProfile, ToolAdapter, ToolHealthReport
from guif.tools.chatgpt import ChatGPTImageToolAdapter
from guif.tools.dry_run import DryRunToolAdapter

FRAMEWORK_TOOL_DEFAULTS: dict[str, str] = {
    "image-generation": "chatgpt-image",
    "image-editing": "chatgpt-image",
}


@dataclass(frozen=True)
class ToolResolution:
    status: str
    capability: str
    required_capabilities: tuple[str, ...]
    selected_tool_id: str | None
    source: str | None
    host_id: str
    mode: str
    explicit: bool
    health: dict[str, Any] | None
    candidates: tuple[dict[str, Any], ...]
    actions: tuple[str, ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "status": self.status,
            "capability": self.capability,
            "required_capabilities": list(self.required_capabilities),
            "selected_tool_id": self.selected_tool_id,
            "source": self.source,
            "host_id": self.host_id,
            "mode": self.mode,
            "explicit": self.explicit,
            "health": self.health,
            "candidates": [dict(item) for item in self.candidates],
            "actions": list(self.actions),
            "reason": self.reason,
        }


class ToolRegistry:
    def __init__(self, tools: Iterable[ToolAdapter] = ()) -> None:
        self._tools: dict[str, ToolAdapter] = {}
        for tool in tools:
            self.register(tool)

    def register(self, tool: ToolAdapter) -> None:
        tool_id = tool.tool_id.strip()
        if not tool_id:
            raise ValueError("Tool adapter must define a non-empty tool_id")
        if tool_id in self._tools:
            raise ValueError(f"Tool already registered: {tool_id}")
        self._tools[tool_id] = tool

    def get(self, tool_id: str) -> ToolAdapter:
        try:
            return self._tools[tool_id]
        except KeyError as exc:
            raise ValueError(f"Unknown Tool adapter: {tool_id}") from exc

    def find(self, tool_id: str) -> ToolAdapter | None:
        return self._tools.get(tool_id)

    def describe(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._tools[key].describe() for key in sorted(self._tools))

    def candidates(
        self,
        required_capabilities: Iterable[str],
        host: HostProfile,
        *,
        mode: str,
    ) -> tuple[dict[str, Any], ...]:
        required = tuple(sorted(set(required_capabilities)))
        items: list[dict[str, Any]] = []
        for tool_id in sorted(self._tools):
            tool = self._tools[tool_id]
            missing = tool.missing_capabilities(required)
            health = tool.health_check(host, mode=mode, explicit=False)
            if missing:
                continue
            items.append(
                {
                    "tool_id": tool_id,
                    "execution_mode": tool.manifest.execution_mode,
                    "production_allowed": tool.manifest.production_allowed,
                    "health": health.to_dict(),
                }
            )
        return tuple(items)

    def resolve(
        self,
        *,
        capability: str,
        required_capabilities: Iterable[str],
        host: HostProfile,
        mode: str,
        explicit_tool_id: str | None = None,
        task_tools: dict[str, Any] | None = None,
        project_tools: dict[str, Any] | None = None,
        workspace_tools: dict[str, Any] | None = None,
    ) -> ToolResolution:
        required = tuple(sorted(set(required_capabilities)))
        selected: str | None = None
        source: str | None = None
        explicit = explicit_tool_id is not None
        if explicit_tool_id:
            selected = explicit_tool_id
            source = "explicit"
        else:
            for label, mapping in (
                ("task", task_tools or {}),
                ("project", project_tools or {}),
                ("workspace", workspace_tools or {}),
            ):
                value = _primary_tool(mapping.get(capability))
                if value:
                    selected = value
                    source = label
                    break
            if selected is None:
                selected = FRAMEWORK_TOOL_DEFAULTS.get(capability)
                source = "framework-default" if selected else None

        candidates = self.candidates(required, host, mode=mode)
        if not selected:
            return ToolResolution(
                status="waiting-for-tool",
                capability=capability,
                required_capabilities=required,
                selected_tool_id=None,
                source=None,
                host_id=host.host_id,
                mode=mode,
                explicit=False,
                health=None,
                candidates=candidates,
                actions=_resolution_actions(),
                reason=f"No Tool is configured for capability {capability}.",
            )

        tool = self.find(selected)
        if tool is None:
            return ToolResolution(
                status="waiting-for-tool",
                capability=capability,
                required_capabilities=required,
                selected_tool_id=selected,
                source=source,
                host_id=host.host_id,
                mode=mode,
                explicit=explicit,
                health=None,
                candidates=candidates,
                actions=_resolution_actions(),
                reason=f"Configured Tool {selected} is not registered in the current Runtime.",
            )

        missing = tool.missing_capabilities(required)
        health: ToolHealthReport = tool.health_check(host, mode=mode, explicit=explicit)
        if missing or not health.healthy:
            reason_parts: list[str] = []
            if missing:
                reason_parts.append("missing capabilities: " + ", ".join(missing))
            reason_parts.extend(health.reasons)
            return ToolResolution(
                status="waiting-for-tool",
                capability=capability,
                required_capabilities=required,
                selected_tool_id=selected,
                source=source,
                host_id=host.host_id,
                mode=mode,
                explicit=explicit,
                health=health.to_dict(),
                candidates=candidates,
                actions=_resolution_actions(),
                reason=f"Tool {selected} is not ready: " + "; ".join(reason_parts),
            )

        return ToolResolution(
            status="ready",
            capability=capability,
            required_capabilities=required,
            selected_tool_id=selected,
            source=source,
            host_id=host.host_id,
            mode=mode,
            explicit=explicit,
            health=health.to_dict(),
            candidates=candidates,
            actions=(),
            reason=f"Tool {selected} is ready.",
        )


def _primary_tool(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    if isinstance(value, dict):
        primary = value.get("primary")
        if isinstance(primary, str) and primary.strip():
            return primary.strip()
    return None


def _resolution_actions() -> tuple[str, ...]:
    return (
        "Bind an available Tool to the Project.",
        "Connect or install a Tool that provides the missing capability.",
        "Create an Adapter scaffold and implement its contract.",
        "Explicitly choose dry-run for contract testing only.",
        "Cancel the pending execution.",
    )


def build_default_tool_registry() -> ToolRegistry:
    return ToolRegistry((ChatGPTImageToolAdapter(), DryRunToolAdapter()))
