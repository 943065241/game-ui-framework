from __future__ import annotations

from pathlib import Path
from typing import Any

from guif.providers import ProviderRegistry
from guif.revision import (
    create_revision_job,
    decide_revision_approval,
    get_revision_job_by_plan,
    list_revision_jobs,
    revision_approval_summary,
)
from guif.revision_execution import RevisionAwareToolExecutionService
from guif.runtime.pipeline import Pipeline
from guif.runtime.registry import AgentRegistry
from guif.runtime.runtime import Runtime as LegacyProviderRuntime
from guif.runtime.store import TaskStore
from guif.runtime.task import Task
from guif.tool_execution import ToolExecutionError
from guif.tools import HostProfile, ToolRegistry, create_tool_scaffold


class Runtime(LegacyProviderRuntime):
    """GUIF Runtime with configurable Host, Tool, and Revision routing."""

    def __init__(
        self,
        workspace: Path,
        *,
        registry: AgentRegistry | None = None,
        pipelines: dict[str, Pipeline] | None = None,
        store: TaskStore | None = None,
        providers: ProviderRegistry | None = None,
        tools: ToolRegistry | None = None,
        host: HostProfile | None = None,
    ) -> None:
        super().__init__(
            workspace,
            registry=registry,
            pipelines=pipelines,
            store=store,
            providers=providers,
        )
        self.tool_execution = RevisionAwareToolExecutionService(
            workspace,
            store=self.store,
            tools=tools,
            host=host,
        )

    def execute_job(
        self,
        project: str,
        task_id: str,
        job_id: str,
        *,
        tool_id: str | None = None,
        provider_id: str | None = None,
    ) -> Task:
        if tool_id is not None and provider_id is not None:
            raise ValueError("Specify either tool_id or provider_id, not both")
        if provider_id is not None:
            return super().execute_job(
                project,
                task_id,
                job_id,
                provider_id=provider_id,
            )
        return self.tool_execution.prepare_or_execute(
            project,
            task_id,
            job_id,
            tool_id=tool_id,
        )

    def resume(self, project: str, task_id: str) -> Task:
        task = self.store.load(project, task_id)
        if task.status == "waiting-for-tool":
            raise ValueError(
                "Task is waiting for Tool configuration; bind or explicitly select a Tool, then execute the pending job again"
            )
        if task.status == "waiting-for-tool-result":
            raise ValueError(
                "Task is waiting for an external Tool result; submit the persisted handoff result instead of resuming the Pipeline"
            )
        if task.status == "cancelled":
            raise ValueError(f"Task is cancelled: {task_id}")
        return super().resume(project, task_id)

    def get_host_profile(self) -> dict[str, Any]:
        return self.tool_execution.host.to_dict()

    def list_tools(self) -> tuple[dict[str, Any], ...]:
        return self.tool_execution.list_tools()

    def tool_health(
        self,
        tool_id: str,
        *,
        project: str | None = None,
        mode: str | None = None,
        explicit: bool = False,
    ) -> dict[str, Any]:
        return self.tool_execution.tool_health(
            tool_id,
            project=project,
            mode=mode,
            explicit=explicit,
        )

    def bind_project_tool(self, project: str, capability: str, tool_id: str) -> Path:
        return self.tool_execution.bind_project_tool(project, capability, tool_id)

    def submit_tool_result(
        self,
        project: str,
        task_id: str,
        handoff_id: str,
        *,
        content: bytes,
        filename: str,
        mime_type: str,
        width: int | None = None,
        height: int | None = None,
        model_id: str | None = None,
        tool_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Task:
        return self.tool_execution.submit_result(
            project,
            task_id,
            handoff_id,
            content=content,
            filename=filename,
            mime_type=mime_type,
            width=width,
            height=height,
            model_id=model_id,
            tool_id=tool_id,
            metadata=metadata,
        )

    def list_tool_handoffs(self, project: str, task_id: str) -> tuple[dict[str, Any], ...]:
        return self.tool_execution.list_handoffs(project, task_id)

    def get_tool_resolution(self, project: str, task_id: str) -> dict[str, Any]:
        return self.tool_execution.get_resolution(project, task_id)

    def cancel_tool_wait(self, project: str, task_id: str, *, reason: str) -> Task:
        return self.tool_execution.cancel_wait(project, task_id, reason=reason)

    def scaffold_tool(
        self,
        tool_id: str,
        capabilities: tuple[str, ...],
        *,
        execution_mode: str = "external-callback",
    ) -> Path:
        return create_tool_scaffold(
            self.workspace,
            tool_id,
            capabilities,
            execution_mode=execution_mode,
        )

    def create_revision_job(self, project: str, task_id: str, revision_id: str) -> Task:
        task = self.store.load(project, task_id)
        create_revision_job(task, revision_id)
        self.store.save(task)
        return task

    def list_revision_jobs(self, project: str, task_id: str) -> tuple[dict[str, Any], ...]:
        return list_revision_jobs(self.store.load(project, task_id))

    def get_revision_approval(self, project: str, task_id: str, revision_id: str) -> dict[str, Any]:
        return revision_approval_summary(self.store.load(project, task_id), revision_id)

    def decide_revision(
        self,
        project: str,
        task_id: str,
        revision_id: str,
        decision: str,
        *,
        actor: str,
        comment: str | None = None,
    ) -> Task:
        task = self.store.load(project, task_id)
        decide_revision_approval(
            task,
            revision_id,
            decision,
            actor=actor,
            comment=comment,
        )
        self.store.save(task)
        return task

    def approve_revision(
        self,
        project: str,
        task_id: str,
        revision_id: str,
        *,
        actor: str,
        comment: str | None = None,
    ) -> Task:
        return self.decide_revision(
            project,
            task_id,
            revision_id,
            "approved",
            actor=actor,
            comment=comment,
        )

    def reject_revision(
        self,
        project: str,
        task_id: str,
        revision_id: str,
        *,
        actor: str,
        comment: str | None = None,
    ) -> Task:
        return self.decide_revision(
            project,
            task_id,
            revision_id,
            "rejected",
            actor=actor,
            comment=comment,
        )

    def request_revision_changes(
        self,
        project: str,
        task_id: str,
        revision_id: str,
        *,
        actor: str,
        comment: str | None = None,
    ) -> Task:
        return self.decide_revision(
            project,
            task_id,
            revision_id,
            "changes-requested",
            actor=actor,
            comment=comment,
        )

    def execute_revision(
        self,
        project: str,
        task_id: str,
        revision_id: str,
        *,
        tool_id: str | None = None,
    ) -> Task:
        task = self.store.load(project, task_id)
        job = get_revision_job_by_plan(task, revision_id)
        return self.execute_job(
            project,
            task_id,
            str(job["id"]),
            tool_id=tool_id,
        )


__all__ = ["Runtime", "ToolExecutionError"]
