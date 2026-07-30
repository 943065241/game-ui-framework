from __future__ import annotations

from pathlib import Path
from typing import Any

from guif.approval import refresh_approval_gate
from guif.conversation_workflow import ConversationWorkflowService as BaseConversationWorkflowService
from guif.prompt_ir import build_prompt_ir
from guif.source_imports import (
    PrivateSourceImportStore,
    attach_sources_to_task,
    public_source_ref,
    source_reference,
)


class ConversationWorkflowService(BaseConversationWorkflowService):
    """Conversation workflow with explicit external-image registration decisions."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.source_store = PrivateSourceImportStore(
            self.workspace,
            data_root=self.store.layout.root,
        )

    @staticmethod
    def _source_ids(session: dict[str, Any]) -> list[str]:
        values = session.setdefault("source_ids", [])
        if not isinstance(values, list):
            raise ValueError("Invalid conversation source_ids")
        return [str(item) for item in values if isinstance(item, str) and item]

    def _bind_source(self, session: dict[str, Any], source: dict[str, Any]) -> None:
        values = session.setdefault("source_ids", [])
        if not isinstance(values, list):
            raise ValueError("Invalid conversation source_ids")
        source_id = str(source["source_id"])
        if source_id not in values:
            values.append(source_id)
        session["source_registration"] = {
            "status": "registered",
            "source": public_source_ref(source),
        }
        self._record(
            session,
            "source-registered",
            source_id=source_id,
            usages=list(source.get("usages", [])),
        )

    def _theme_source_ids(self, project: str, conversation_id: str) -> list[str]:
        resolution = self.runtime.prepare_conversation_theme(
            conversation_id,
            project=project,
        )
        ref = resolution.get("selected_theme") if isinstance(resolution, dict) else None
        if not isinstance(ref, dict):
            return []
        theme_id = str(ref.get("theme_id") or "")
        version = ref.get("version")
        if not theme_id or not isinstance(version, int):
            return []
        record = self.runtime.get_private_theme(theme_id, version)
        content = record.get("content") if isinstance(record.get("content"), dict) else {}
        values = content.get("visual_sources", [])
        if not isinstance(values, list):
            return []
        return [
            str(item.get("source_id"))
            for item in values
            if isinstance(item, dict) and item.get("source_id")
        ]

    def _available_sources(
        self,
        project: str,
        conversation_id: str,
        session: dict[str, Any],
    ) -> list[dict[str, Any]]:
        ids = self._source_ids(session) + self._theme_source_ids(project, conversation_id)
        records: list[dict[str, Any]] = []
        seen: set[str] = set()
        for source_id in reversed(ids):
            if source_id in seen:
                continue
            seen.add(source_id)
            try:
                records.append(self.source_store.get(project, source_id))
            except ValueError:
                continue
        return records

    @staticmethod
    def _missing_edit_reference(task: Any | None) -> bool:
        if task is None:
            return False
        prompt_ir = task.state.get("prompt_ir")
        blockers = prompt_ir.get("blockers", []) if isinstance(prompt_ir, dict) else []
        return any(
            isinstance(item, dict) and item.get("code") == "missing-edit-reference"
            for item in blockers
        )

    def _repair_task_with_source(
        self,
        task: Any,
        source: dict[str, Any],
    ) -> Any:
        run_dir = self.runtime.store.run_dir(task.project, task.task_id)
        artifact = attach_sources_to_task(task, run_dir, (source,))[0]
        reference = source_reference(source, artifact)
        resource_contracts = task.state.get("resource_contracts")
        if not isinstance(resource_contracts, dict):
            raise ValueError("Source registration requires Resource contracts")
        approved = resource_contracts.setdefault("approved_existing", [])
        if not isinstance(approved, list):
            raise ValueError("Invalid approved_existing Resource contracts")
        source_id = str(source["source_id"])
        if not any(
            isinstance(item, dict) and item.get("resource_id") == source_id
            for item in approved
        ):
            approved.append(
                {
                    "resource_id": source_id,
                    "manifest": dict(reference["manifest"]),
                    "reasons": list(reference["reasons"]),
                }
            )
        task.state["conversation_sources"] = [reference]
        prompt_ir = build_prompt_ir(task)
        for job in prompt_ir.get("jobs", []):
            if not isinstance(job, dict) or job.get("operation") != "edit":
                continue
            values = job.get("references", [])
            if not isinstance(values, list):
                continue
            for index, item in enumerate(values):
                if isinstance(item, dict) and item.get("resource_id") == source_id:
                    values[index] = dict(reference)
        task.state["prompt_ir"] = prompt_ir
        refresh_approval_gate(task)
        task.record(
            "source-import",
            "bound",
            f"Registered private source {source_id} and rebuilt the image-editing contract.",
        )
        self.runtime.store.save(task)
        return task

    def _link_source_to_selected_theme(
        self,
        project: str,
        conversation_id: str,
        source: dict[str, Any],
        *,
        actor: str,
    ) -> None:
        resolution = self.runtime.prepare_conversation_theme(
            conversation_id,
            project=project,
        )
        ref = resolution.get("selected_theme") if isinstance(resolution, dict) else None
        if not isinstance(ref, dict):
            return
        theme_id = str(ref.get("theme_id") or "")
        version = ref.get("version")
        if not theme_id or not isinstance(version, int):
            return
        theme = self.runtime.get_private_theme(theme_id, version)
        content = theme.get("content") if isinstance(theme.get("content"), dict) else {}
        visual_sources = list(content.get("visual_sources", [])) if isinstance(content.get("visual_sources"), list) else []
        public = public_source_ref(source)
        if not any(
            isinstance(item, dict) and item.get("source_id") == public.get("source_id")
            for item in visual_sources
        ):
            visual_sources.append(public)
        self.runtime.derive_private_theme(
            theme_id,
            {"visual_sources": visual_sources},
            from_version=version,
            actor=actor,
            conversation_id=conversation_id,
            name=str(theme.get("name") or "") or None,
        )

    def _stage(self, session: dict[str, Any], task: Any | None) -> tuple[str, str, list[dict[str, Any]]]:
        registration = session.get("source_registration")
        if isinstance(registration, dict) and registration.get("status") == "external-edit-selected":
            return (
                "external-edit-selected",
                "已选择退出 GUIF 正式编辑链。后续普通编辑不会被标记为 GUIF 正式产物；仍可返回并注册源图。",
                [
                    {"action": "import-source-and-continue", "label": "返回并导入源图"},
                    {"action": "submit-request", "label": "提交新的 GUIF 需求"},
                ],
            )
        if self._missing_edit_reference(task):
            return (
                "source-import-required",
                "当前图片尚未注册为 GUIF 源图，不能直接进入受保护编辑流程。请选择导入用途，GUIF 将注册 Source Artifact 后继续。",
                [
                    {"action": "import-source-and-continue", "label": "导入为可编辑源图并继续（推荐）"},
                    {"action": "import-as-theme-reference", "label": "导入并加入 Theme 参考"},
                    {"action": "import-as-master-reference", "label": "导入并设为母版参考"},
                    {"action": "continue-outside-guif", "label": "退出正式链并普通编辑"},
                ],
            )
        return super()._stage(session, task)

    def _public_view(
        self,
        session: dict[str, Any],
        *,
        include_diagnostics: bool = False,
    ) -> dict[str, Any]:
        payload = super()._public_view(session, include_diagnostics=include_diagnostics)
        project = str(session["project"])
        conversation_id = str(session["conversation_id"])
        records = self._available_sources(project, conversation_id, session)
        registration = session.get("source_registration")
        payload["source"] = {
            "status": registration.get("status") if isinstance(registration, dict) else ("registered" if records else "not-configured"),
            "selected": [public_source_ref(item) for item in records],
            "privacy": "private-outside-project-git",
        }
        return payload

    def create_theme(
        self,
        project: str,
        conversation_id: str,
        name: str,
        content: dict[str, Any],
        *,
        actor: str = "conversation-user",
        source_path: Path | None = None,
        source_kind: str = "user-upload",
        source_usage: str = "master-reference",
        source_mime_type: str | None = None,
        source_width: int | None = None,
        source_height: int | None = None,
    ) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        normalized_content = dict(content)
        if source_path is not None:
            source = self.source_store.stage(
                project,
                conversation_id,
                source_path,
                source_kind=source_kind,
                usage=source_usage,
                mime_type=source_mime_type,
                width=source_width,
                height=source_height,
                actor=actor,
            )
            self._bind_source(session, source)
            values = list(normalized_content.get("visual_sources", [])) if isinstance(normalized_content.get("visual_sources"), list) else []
            values.append(public_source_ref(source))
            normalized_content["visual_sources"] = values
            self.store.save(session)
        return super().create_theme(
            project,
            conversation_id,
            name,
            normalized_content,
            actor=actor,
        )

    def derive_theme(
        self,
        project: str,
        conversation_id: str,
        theme_id: str,
        updates: dict[str, Any],
        *,
        from_version: int | None = None,
        name: str | None = None,
        actor: str = "conversation-user",
        source_path: Path | None = None,
        source_kind: str = "user-upload",
        source_usage: str = "theme-reference",
        source_mime_type: str | None = None,
        source_width: int | None = None,
        source_height: int | None = None,
    ) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        normalized_updates = dict(updates)
        if source_path is not None:
            source = self.source_store.stage(
                project,
                conversation_id,
                source_path,
                source_kind=source_kind,
                usage=source_usage,
                mime_type=source_mime_type,
                width=source_width,
                height=source_height,
                actor=actor,
            )
            self._bind_source(session, source)
            base = self.runtime.get_private_theme(theme_id, from_version)
            content = base.get("content") if isinstance(base.get("content"), dict) else {}
            values = list(content.get("visual_sources", [])) if isinstance(content.get("visual_sources"), list) else []
            values.append(public_source_ref(source))
            normalized_updates["visual_sources"] = values
            self.store.save(session)
        return super().derive_theme(
            project,
            conversation_id,
            theme_id,
            normalized_updates,
            from_version=from_version,
            name=name,
            actor=actor,
        )

    def submit(
        self,
        project: str,
        conversation_id: str,
        requirement: str,
        *,
        pipeline: str = "ui-production",
        request_key: str | None = None,
    ) -> dict[str, Any]:
        super().submit(
            project,
            conversation_id,
            requirement,
            pipeline=pipeline,
            request_key=request_key,
        )
        session = self._session(project, conversation_id)
        task = self._load_active_task(session)
        if task is not None and self._missing_edit_reference(task):
            sources = self._available_sources(project, conversation_id, session)
            if sources:
                task = self._repair_task_with_source(task, sources[0])
                session["source_registration"] = {
                    "status": "registered",
                    "source": public_source_ref(sources[0]),
                }
            else:
                session["source_registration"] = {
                    "status": "required",
                    "reason": "missing-edit-reference",
                }
            self.store.save(session)
        return self._public_view(session)

    def import_source(
        self,
        project: str,
        conversation_id: str,
        source_path: Path,
        *,
        source_kind: str = "user-upload",
        usage: str = "editable-source",
        mime_type: str | None = None,
        width: int | None = None,
        height: int | None = None,
        actor: str = "conversation-user",
        continue_after_import: bool = True,
    ) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        source = self.source_store.stage(
            project,
            conversation_id,
            source_path,
            source_kind=source_kind,
            usage=usage,
            mime_type=mime_type,
            width=width,
            height=height,
            actor=actor,
        )
        self._bind_source(session, source)
        if usage in {"theme-reference", "master-reference"}:
            self._link_source_to_selected_theme(
                project,
                conversation_id,
                source,
                actor=actor,
            )
        task = self._load_active_task(session)
        if task is not None and self._missing_edit_reference(task):
            task = self._repair_task_with_source(task, source)
            approval = task.state.get("approval_state")
            approval_status = approval.get("status") if isinstance(approval, dict) else None
            if continue_after_import and approval_status in {"approved", "not-required"}:
                self._execute_next(task)
                self._record(session, "source-import-continued")
        self.store.save(session)
        return self._public_view(session)

    def select_external_edit(
        self,
        project: str,
        conversation_id: str,
    ) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        session["source_registration"] = {
            "status": "external-edit-selected",
            "formal_guif_result": False,
        }
        self._record(session, "external-edit-selected")
        self.store.save(session)
        return self._public_view(session)


__all__ = ["ConversationWorkflowService"]
