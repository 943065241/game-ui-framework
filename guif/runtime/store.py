from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from guif.paths import project_root
from guif.runtime.task import Task


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _write_optional_json(path: Path, payload: Any) -> None:
    if isinstance(payload, dict):
        _write_json(path, payload)
    elif path.exists():
        path.unlink()


class TaskStore:
    def __init__(self, workspace: Path) -> None:
        self.workspace = workspace

    def _runs_dir(self, project: str) -> Path:
        return project_root(self.workspace, project) / "runs"

    def run_dir(self, project: str, task_id: str) -> Path:
        if not task_id or Path(task_id).name != task_id:
            raise ValueError(f"Invalid task id: {task_id}")
        return self._runs_dir(project) / task_id

    def save(self, task: Task) -> Path:
        run_dir = self.run_dir(task.project, task.task_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        payload = task.to_dict()

        _write_json(run_dir / "task.json", payload)
        _write_json(run_dir / "context.json", payload["context"])
        _write_json(run_dir / "outputs.json", payload["outputs"])

        events = "".join(
            json.dumps(event, ensure_ascii=False) + "\n" for event in payload["events"]
        )
        temporary_events = run_dir / "events.jsonl.tmp"
        temporary_events.write_text(events, encoding="utf-8")
        temporary_events.replace(run_dir / "events.jsonl")

        error_path = run_dir / "error.json"
        if payload["error"] is None:
            if error_path.exists():
                error_path.unlink()
        else:
            _write_json(error_path, payload["error"])

        state = payload["state"]
        _write_optional_json(run_dir / "approvals.json", state.get("approval_state"))
        _write_optional_json(run_dir / "artifacts.json", state.get("artifact_registry"))
        _write_optional_json(run_dir / "executions.json", state.get("provider_executions"))
        _write_optional_json(run_dir / "visual-reviews.json", state.get("visual_reviews"))
        _write_optional_json(run_dir / "revision-plans.json", state.get("revision_plans"))
        _write_optional_json(run_dir / "revision-execution.json", state.get("revision_execution"))
        _write_optional_json(run_dir / "tool-resolution.json", state.get("tool_resolution"))
        _write_optional_json(run_dir / "tool-handoffs.json", state.get("tool_handoffs"))

        return run_dir

    def load(self, project: str, task_id: str) -> Task:
        path = self.run_dir(project, task_id) / "task.json"
        if not path.is_file():
            raise FileNotFoundError(f"Unknown task run: {project}/{task_id}")
        return Task.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list(self, project: str) -> tuple[dict[str, Any], ...]:
        runs_dir = self._runs_dir(project)
        if not runs_dir.exists():
            return ()

        summaries: list[dict[str, Any]] = []
        for task_path in sorted(runs_dir.glob("*/task.json")):
            payload = json.loads(task_path.read_text(encoding="utf-8"))
            state = payload.get("state", {})
            approval_state = state.get("approval_state", {}) if isinstance(state, dict) else {}
            artifact_registry = state.get("artifact_registry", {}) if isinstance(state, dict) else {}
            execution_state = state.get("provider_executions", {}) if isinstance(state, dict) else {}
            visual_review_state = state.get("visual_reviews", {}) if isinstance(state, dict) else {}
            revision_state = state.get("revision_plans", {}) if isinstance(state, dict) else {}
            revision_execution = state.get("revision_execution", {}) if isinstance(state, dict) else {}
            qa_report = state.get("qa_report", {}) if isinstance(state, dict) else {}
            tool_resolution = state.get("tool_resolution", {}) if isinstance(state, dict) else {}
            handoff_state = state.get("tool_handoffs", {}) if isinstance(state, dict) else {}
            artifact_records = (
                artifact_registry.get("records", []) if isinstance(artifact_registry, dict) else []
            )
            execution_attempts = (
                execution_state.get("attempts", []) if isinstance(execution_state, dict) else []
            )
            visual_reviews = (
                visual_review_state.get("records", []) if isinstance(visual_review_state, dict) else []
            )
            revision_plans = (
                revision_state.get("records", []) if isinstance(revision_state, dict) else []
            )
            revision_jobs = (
                revision_execution.get("jobs", []) if isinstance(revision_execution, dict) else []
            )
            revision_approvals = (
                revision_execution.get("approvals", {}) if isinstance(revision_execution, dict) else {}
            )
            pending_revision_approvals = [
                item
                for item in revision_approvals.values()
                if isinstance(item, dict) and item.get("status") == "pending"
            ] if isinstance(revision_approvals, dict) else []
            handoffs = handoff_state.get("records", []) if isinstance(handoff_state, dict) else []
            artifact_review = (
                qa_report.get("artifact_review", {}) if isinstance(qa_report, dict) else {}
            )
            summaries.append(
                {
                    **{
                        key: payload.get(key)
                        for key in (
                            "task_id",
                            "project",
                            "requirement",
                            "pipeline",
                            "status",
                            "current_agent",
                            "next_agent_index",
                            "created_at",
                            "updated_at",
                            "completed_at",
                        )
                    },
                    "approval_status": approval_state.get("status")
                    if isinstance(approval_state, dict)
                    else None,
                    "pending_approval_count": len(approval_state.get("pending_ids", []))
                    if isinstance(approval_state, dict)
                    else 0,
                    "artifact_count": len(artifact_records) if isinstance(artifact_records, list) else 0,
                    "provider_execution_count": len(execution_attempts)
                    if isinstance(execution_attempts, list)
                    else 0,
                    "visual_review_count": len(visual_reviews)
                    if isinstance(visual_reviews, list)
                    else 0,
                    "revision_plan_count": len(revision_plans)
                    if isinstance(revision_plans, list)
                    else 0,
                    "revision_job_count": len(revision_jobs)
                    if isinstance(revision_jobs, list)
                    else 0,
                    "pending_revision_approval_count": len(pending_revision_approvals),
                    "artifact_review_status": artifact_review.get("status")
                    if isinstance(artifact_review, dict)
                    else None,
                    "tool_resolution_status": tool_resolution.get("status")
                    if isinstance(tool_resolution, dict)
                    else None,
                    "tool_handoff_count": len(handoffs) if isinstance(handoffs, list) else 0,
                }
            )
        summaries.sort(
            key=lambda item: str(item.get("created_at") or ""),
            reverse=True,
        )
        return tuple(summaries)
