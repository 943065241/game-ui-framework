from __future__ import annotations

from pathlib import Path
from typing import Any

from guif.artifacts import list_artifacts
from guif.revision import (
    get_revision_job,
    link_revision_artifact,
    mark_revision_execution,
    revision_approval_summary,
)
from guif.runtime.task import Task
from guif.tool_execution import ToolExecutionService
from guif.visual_review import VisualReviewService


class RevisionAwareToolExecutionService(ToolExecutionService):
    """Tool execution that recognizes separately approved Revision Jobs."""

    def _load_job(self, task: Task, job_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        try:
            job = get_revision_job(task, job_id)
        except ValueError:
            return super()._load_job(task, job_id)

        if task.status not in {"completed", "waiting-for-tool"}:
            raise ValueError(
                "Revision Tool execution requires a completed Task or a Task waiting for Tool configuration"
            )
        revision = job.get("revision") if isinstance(job.get("revision"), dict) else {}
        revision_id = str(revision.get("revision_id") or "")
        approval = revision_approval_summary(task, revision_id)
        if approval.get("status") != "approved":
            raise ValueError(f"Revision approval gate is not satisfied: {approval.get('status')}")
        if job.get("executable") is not True or job.get("status") not in {
            "ready",
            "waiting-for-tool",
            "waiting-for-result",
        }:
            raise ValueError(f"Revision job is not executable: {job_id}")
        qa_report = task.state.get("qa_report")
        if not isinstance(qa_report, dict) or qa_report.get("status") != "passed":
            raise ValueError("Revision Tool execution requires passing Contract QA")
        prompt_ir = task.state.get("prompt_ir")
        if not isinstance(prompt_ir, dict):
            raise ValueError("Revision Tool execution requires the source Prompt IR")
        approval_id = approval.get("approval_id")
        approval_snapshot = {
            "status": "approved",
            "approved_ids": [approval_id] if approval_id else [],
            "required_ids": [approval_id] if approval_id else [],
            "prompt_status": "ready",
            "revision_id": revision_id,
            "revision_approval": dict(approval),
        }
        return prompt_ir, approval_snapshot, job

    def _finalize_revision_artifact(self, task: Task, job_id: str) -> Task:
        try:
            job = get_revision_job(task, job_id)
        except ValueError:
            return task
        artifact = next(
            (
                item
                for item in reversed(list_artifacts(task))
                if item.get("job_id") == job_id and not isinstance(item.get("revision"), dict)
            ),
            None,
        )
        if not isinstance(artifact, dict):
            return task
        link_revision_artifact(task, job_id, artifact)
        self.store.save(task)
        if artifact.get("visual") is True and artifact.get("simulation") is not True:
            return VisualReviewService(self.workspace, store=self.store).review(
                task.project,
                task.task_id,
                str(artifact["artifact_id"]),
            )
        return VisualReviewService(self.workspace, store=self.store).review(
            task.project,
            task.task_id,
            str(artifact["artifact_id"]),
        )

    def prepare_or_execute(
        self,
        project: str,
        task_id: str,
        job_id: str,
        *,
        tool_id: str | None = None,
    ) -> Task:
        task = super().prepare_or_execute(project, task_id, job_id, tool_id=tool_id)
        try:
            get_revision_job(task, job_id)
        except ValueError:
            return task
        if task.status == "waiting-for-tool":
            mark_revision_execution(task, job_id, "waiting-for-tool")
            self.store.save(task)
            return task
        if task.status == "waiting-for-tool-result":
            mark_revision_execution(task, job_id, "waiting-for-result")
            self.store.save(task)
            return task
        return self._finalize_revision_artifact(task, job_id)

    def submit_result(
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
        task = super().submit_result(
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
        handoffs = task.state.get("tool_handoffs")
        records = handoffs.get("records", []) if isinstance(handoffs, dict) else []
        handoff = next(
            (
                item
                for item in records
                if isinstance(item, dict) and item.get("handoff_id") == handoff_id
            ),
            None,
        )
        job_id = str(handoff.get("job_id") or "") if isinstance(handoff, dict) else ""
        if not job_id:
            return task
        return self._finalize_revision_artifact(task, job_id)
