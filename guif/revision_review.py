from __future__ import annotations

from pathlib import Path
from typing import Any

from guif.artifacts import get_artifact
from guif.revision import get_revision_job, record_revision_review
from guif.runtime.store import TaskStore
from guif.visual_review import VisualInspectorRegistry, VisualReviewService, _aggregate_into_qa


class RevisionReviewService:
    """Review replacement Artifacts and supersede their source only after a pass."""

    def __init__(
        self,
        workspace: Path,
        *,
        store: TaskStore | None = None,
        inspectors: VisualInspectorRegistry | None = None,
    ) -> None:
        self.workspace = workspace
        self.store = store or TaskStore(workspace)
        self.base = VisualReviewService(workspace, store=self.store, inspectors=inspectors)

    def list_inspectors(self) -> tuple[dict[str, Any], ...]:
        return self.base.list_inspectors()

    def review(
        self,
        project: str,
        task_id: str,
        artifact_id: str,
        *,
        inspector_id: str | None = None,
    ) -> Any:
        task = self.store.load(project, task_id)
        artifact = get_artifact(task, artifact_id)
        revision = artifact.get("revision")
        if not isinstance(revision, dict):
            return self.base.review(project, task_id, artifact_id, inspector_id=inspector_id)

        job_id = str(artifact.get("job_id") or "")
        revision_job = get_revision_job(task, job_id)
        prompt_ir = task.state.get("prompt_ir")
        if not isinstance(prompt_ir, dict) or not isinstance(prompt_ir.get("jobs"), list):
            raise ValueError("Revision review requires the source Prompt IR")
        jobs = prompt_ir["jobs"]
        injected = not any(isinstance(item, dict) and item.get("id") == job_id for item in jobs)
        if injected:
            jobs.append(revision_job)
            self.store.save(task)
        try:
            task = self.base.review(project, task_id, artifact_id, inspector_id=inspector_id)
        finally:
            cleanup = self.store.load(project, task_id)
            cleanup_prompt = cleanup.state.get("prompt_ir")
            if injected and isinstance(cleanup_prompt, dict) and isinstance(cleanup_prompt.get("jobs"), list):
                cleanup_prompt["jobs"] = [
                    item
                    for item in cleanup_prompt["jobs"]
                    if not (isinstance(item, dict) and item.get("id") == job_id)
                ]
                self.store.save(cleanup)

        task = self.store.load(project, task_id)
        artifact = get_artifact(task, artifact_id)
        review_state = task.state.get("visual_reviews")
        latest = review_state.get("latest_by_artifact", {}) if isinstance(review_state, dict) else {}
        review_id = latest.get(artifact_id) if isinstance(latest, dict) else None
        review = next(
            (
                item
                for item in reversed(review_state.get("records", []))
                if isinstance(item, dict) and item.get("review_id") == review_id
            ),
            None,
        ) if isinstance(review_state, dict) else None
        if not isinstance(review, dict):
            raise ValueError("Revision Artifact review was not persisted")
        record_revision_review(task, artifact, review)

        if review.get("status") == "passed":
            source_id = str(revision.get("source_artifact_id") or "")
            source = get_artifact(task, source_id)
            source["status"] = "stale"
            source["superseded_by"] = artifact_id
            source["stale_at"] = review.get("created_at")
            supersedes = artifact.setdefault("supersedes", [])
            if not isinstance(supersedes, list):
                raise ValueError("Invalid replacement Artifact supersession metadata")
            if source_id not in supersedes:
                supersedes.append(source_id)
            artifact["status"] = "registered"
            artifact["revision"]["supersession_status"] = "completed"
            task.record(
                "revision",
                "superseded",
                f"Passing replacement Artifact {artifact_id} superseded source Artifact {source_id}.",
            )
        else:
            artifact["revision"]["supersession_status"] = "waiting-for-passing-review"

        _aggregate_into_qa(task)
        self.store.save(task)
        return task

    def list_reviews(self, project: str, task_id: str) -> tuple[dict[str, Any], ...]:
        return self.base.list_reviews(project, task_id)

    def list_revision_plans(self, project: str, task_id: str) -> tuple[dict[str, Any], ...]:
        return self.base.list_revision_plans(project, task_id)

    def supersede(
        self,
        project: str,
        task_id: str,
        old_artifact_id: str,
        new_artifact_id: str,
    ) -> Any:
        return self.base.supersede(project, task_id, old_artifact_id, new_artifact_id)
