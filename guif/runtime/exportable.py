from __future__ import annotations

from typing import Any

from guif.gated_export import GatedExportError, GatedExportService
from guif.runtime.configurable import Runtime as ConfigurableRuntime


class Runtime(ConfigurableRuntime):
    """GUIF Runtime with gated production materialization and rollback."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.gated_export = GatedExportService(self.workspace, store=self.store)

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
