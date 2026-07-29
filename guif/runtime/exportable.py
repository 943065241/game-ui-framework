from __future__ import annotations

from typing import Any

from guif.gated_export import (
    GatedExportError,
    GatedExportService,
    _now,
    _replace_output,
    _state,
)
from guif.runtime.configurable import Runtime as ConfigurableRuntime


class RuntimeGatedExportService(GatedExportService):
    """Runtime-safe persistence for records already attached to Task state."""

    def _persist(self, task: Any, record: dict[str, Any]) -> dict[str, Any]:
        state = _state(task)
        records = state.setdefault("records", [])
        latest = state.setdefault("latest_by_target", {})
        if not isinstance(records, list) or not isinstance(latest, dict):
            raise ValueError("Invalid persisted gated Export state")
        existing = next(
            (
                item
                for item in records
                if isinstance(item, dict) and item.get("export_id") == record.get("export_id")
            ),
            None,
        )
        if existing is None:
            records.append(record)
            persisted = record
        elif existing is record:
            persisted = existing
        else:
            terminal = existing.get("status") in {"completed", "rolled-back"}
            if terminal and record.get("status") in {"ready", "blocked"}:
                persisted = existing
            else:
                replacement = dict(record)
                existing.clear()
                existing.update(replacement)
                persisted = existing
        latest[str(persisted["target_engine"])] = persisted["export_id"]
        state["updated_at"] = _now()
        _replace_output(task, str(persisted["export_id"]), persisted)
        self.store.save(task)
        return persisted


class Runtime(ConfigurableRuntime):
    """GUIF Runtime with gated production materialization and rollback."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.gated_export = RuntimeGatedExportService(self.workspace, store=self.store)

    def prepare_gated_export(
        self,
        project: str,
        task_id: str,
        *,
        target_engine: str | None = None,
    ) -> dict[str, Any]:
        return self.gated_export.prepare(
            project,
            task_id,
            target_engine=target_engine,
        )

    def execute_gated_export(
        self,
        project: str,
        task_id: str,
        *,
        target_engine: str | None = None,
        actor: str = "host",
    ) -> dict[str, Any]:
        return self.gated_export.execute(
            project,
            task_id,
            target_engine=target_engine,
            actor=actor,
        )

    def list_gated_exports(self, project: str, task_id: str) -> tuple[dict[str, Any], ...]:
        return self.gated_export.list(project, task_id)

    def get_gated_export(self, project: str, task_id: str, export_id: str) -> dict[str, Any]:
        return self.gated_export.get(project, task_id, export_id)

    def rollback_gated_export(
        self,
        project: str,
        task_id: str,
        export_id: str,
        *,
        actor: str,
        reason: str,
        force: bool = False,
    ) -> dict[str, Any]:
        return self.gated_export.rollback(
            project,
            task_id,
            export_id,
            actor=actor,
            reason=reason,
            force=force,
        )


__all__ = ["GatedExportError", "Runtime"]
