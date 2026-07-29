from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from guif.privacy import audit_workspace_privacy
from guif.retrieval import select_relevant_context
from guif.runtime.context import load_runtime_context
from guif.runtime.exportable import Runtime as ExportableRuntime
from guif.runtime.task import Task
from guif.theme_store import PrivateThemeStore, public_theme_ref


class ThemeResolutionRequired(RuntimeError):
    def __init__(self, resolution: dict[str, Any]) -> None:
        self.resolution = resolution
        super().__init__(
            "Conversation Theme confirmation is required before this Task can start. "
            "Select a historical Theme, create a new Theme, derive a version, or explicitly continue unbound."
        )


class Runtime(ExportableRuntime):
    """GUIF Runtime with private Theme Library and conversation bindings."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.theme_store = getattr(self.store, "theme_store", None) or PrivateThemeStore(self.workspace)

    def list_private_themes(self, *, include_archived: bool = False) -> tuple[dict[str, Any], ...]:
        return self.theme_store.list(include_archived=include_archived)

    def get_private_theme(self, theme_id: str, version: int | None = None) -> dict[str, Any]:
        return self.theme_store.get(theme_id, version)

    def prepare_conversation_theme(
        self,
        conversation_id: str,
        *,
        project: str | None = None,
    ) -> dict[str, Any]:
        return self.theme_store.prepare_conversation(conversation_id, project=project)

    def create_private_theme(
        self,
        name: str,
        content: dict[str, Any],
        *,
        actor: str = "host",
        conversation_id: str | None = None,
        project: str | None = None,
        status: str = "published",
    ) -> dict[str, Any]:
        record = self.theme_store.create(
            name,
            content,
            actor=actor,
            source_conversation_id=conversation_id,
            status=status,
        )
        if conversation_id:
            self.theme_store.bind_conversation(
                conversation_id,
                str(record["theme_id"]),
                version=int(record["version"]),
                actor=actor,
            )
        if project:
            self.theme_store.bind_project(
                project,
                str(record["theme_id"]),
                version=int(record["version"]),
                actor=actor,
            )
        return record

    def derive_private_theme(
        self,
        theme_id: str,
        updates: dict[str, Any],
        *,
        from_version: int | None = None,
        actor: str = "host",
        conversation_id: str | None = None,
        project: str | None = None,
        name: str | None = None,
        status: str = "published",
    ) -> dict[str, Any]:
        record = self.theme_store.derive(
            theme_id,
            updates,
            from_version=from_version,
            actor=actor,
            source_conversation_id=conversation_id,
            name=name,
            status=status,
        )
        if conversation_id:
            self.theme_store.bind_conversation(
                conversation_id,
                theme_id,
                version=int(record["version"]),
                actor=actor,
            )
        if project:
            self.theme_store.bind_project(
                project,
                theme_id,
                version=int(record["version"]),
                actor=actor,
            )
        return record

    def bind_conversation_theme(
        self,
        conversation_id: str,
        theme_id: str,
        *,
        version: int | None = None,
        actor: str = "host",
    ) -> dict[str, Any]:
        return self.theme_store.bind_conversation(
            conversation_id,
            theme_id,
            version=version,
            actor=actor,
        )

    def bind_project_theme(
        self,
        project: str,
        theme_id: str,
        *,
        version: int | None = None,
        actor: str = "host",
    ) -> dict[str, Any]:
        return self.theme_store.bind_project(project, theme_id, version=version, actor=actor)

    def migrate_legacy_project_themes(
        self,
        project: str,
        *,
        actor: str = "migration",
    ) -> dict[str, Any]:
        root = Path(self.workspace) / "projects" / project
        if not (root / "project.json").is_file():
            raise FileNotFoundError(f"Unknown project: {project}")
        return self.theme_store.migrate_legacy_project(root, project, actor=actor)

    def audit_privacy(
        self,
        *,
        sensitive_terms: Iterable[str] = (),
        persist: bool = True,
    ) -> dict[str, Any]:
        return audit_workspace_privacy(
            self.workspace,
            sensitive_terms=sensitive_terms,
            persist=persist,
        )

    def run(
        self,
        project: str,
        requirement: str,
        *,
        pipeline: str = "ui-production",
        conversation_id: str | None = None,
        continue_unbound: bool = False,
    ) -> Task:
        normalized_requirement = requirement.strip()
        if not normalized_requirement:
            raise ValueError("Requirement must not be empty")
        if conversation_id:
            resolution = self.prepare_conversation_theme(conversation_id, project=project)
            if resolution["status"] == "confirmation-required" and not continue_unbound:
                raise ThemeResolutionRequired(resolution)
        resolved_pipeline = self._resolve_pipeline(project, pipeline)
        context = load_runtime_context(
            self.workspace,
            project,
            conversation_id=conversation_id,
            theme_store=self.theme_store,
        )
        context_selection = select_relevant_context(context, normalized_requirement)
        task = Task(
            project=project,
            requirement=normalized_requirement,
            pipeline=resolved_pipeline.name,
            context=context,
        )
        task.state["pipeline"] = resolved_pipeline.to_dict()
        task.state["context_selection"] = context_selection
        task.state["conversation_theme"] = {
            "conversation_id": conversation_id,
            "theme_ref": dict(context.active_theme_ref) if context.active_theme_ref else None,
            "content_persisted_in_project_git": False,
            "private_data_root": str(self.theme_store.root),
        }
        selected_counts = {
            key: len(context_selection[key])
            for key in ("memory", "resources", "workflows")
        }
        task.record(
            "runtime",
            "started",
            f"Loaded project context, selected {selected_counts}, and resolved workflow {resolved_pipeline.name} for {project}",
        )
        return self._execute(task, resolved_pipeline, start_index=0)


__all__ = ["Runtime", "ThemeResolutionRequired", "public_theme_ref"]
