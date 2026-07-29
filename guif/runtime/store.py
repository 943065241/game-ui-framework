from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from guif.paths import project_root
from guif.private_data import PrivateDataLayout
from guif.runtime.context import RuntimeContext
from guif.runtime.task import Task
from guif.theme_store import PrivateThemeStore


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
    """Persist Task Runs in private data storage, not in the framework/project Git tree."""

    def __init__(
        self,
        workspace: Path,
        *,
        data_root: Path | None = None,
        theme_store: PrivateThemeStore | None = None,
    ) -> None:
        self.workspace = workspace
        self.layout = PrivateDataLayout(workspace, data_root)
        self.theme_store = theme_store or PrivateThemeStore(workspace, data_root=data_root)

    def _runs_dir(self, project: str) -> Path:
        return self.layout.runs(project)

    def _legacy_runs_dir(self, project: str) -> Path:
        return project_root(self.workspace, project) / "runs"

    def run_dir(self, project: str, task_id: str) -> Path:
        if not task_id or Path(task_id).name != task_id:
            raise ValueError(f"Invalid task id: {task_id}")
        return self._runs_dir(project) / task_id

    def private_root(self) -> Path:
        return self.layout.root

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
            error_path.unlink(missing_ok=True)
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
        _write_optional_json(run_dir / "host-callbacks.json", state.get("host_callbacks"))
        _write_optional_json(run_dir / "gated-exports.json", state.get("gated_exports"))
        _write_optional_json(run_dir / "git-changes.json", state.get("git_changes"))
        return run_dir

    def _task_path(self, project: str, task_id: str) -> Path:
        private = self.run_dir(project, task_id) / "task.json"
        if private.is_file():
            return private
        legacy = self._legacy_runs_dir(project) / task_id / "task.json"
        if legacy.is_file():
            return legacy
        return private

    def _rehydrate_theme(self, task: Task) -> Task:
        context = task.context
        if not isinstance(context, RuntimeContext):
            return task
        ref = context.active_theme_ref
        if not isinstance(ref, dict):
            return task
        theme_id = ref.get("theme_id")
        version = ref.get("version")
        if not isinstance(theme_id, str) or not isinstance(version, int):
            raise ValueError("Invalid persisted private Theme reference")
        record = self.theme_store.get(theme_id, version)
        if record.get("snapshot_hash") != ref.get("snapshot_hash"):
            raise ValueError("Persisted Task Theme reference no longer matches private Theme data")
        content = record.get("content")
        if not isinstance(content, dict):
            raise ValueError("Private Theme record is missing content")
        task.context = context.with_private_theme(
            {"schema_version": 1, "name": record.get("name"), **content},
            ref,
        )
        return task

    def load(self, project: str, task_id: str) -> Task:
        path = self._task_path(project, task_id)
        if not path.is_file():
            raise FileNotFoundError(f"Unknown task run: {project}/{task_id}")
        task = Task.from_dict(json.loads(path.read_text(encoding="utf-8")))
        return self._rehydrate_theme(task)

    def _task_paths(self, project: str) -> tuple[Path, ...]:
        paths: dict[str, Path] = {}
        for root in (self._legacy_runs_dir(project), self._runs_dir(project)):
            if not root.exists():
                continue
            for path in root.glob("*/task.json"):
                paths[path.parent.name] = path
        return tuple(paths[key] for key in sorted(paths))

    def list(self, project: str) -> tuple[dict[str, Any], ...]:
        summaries: list[dict[str, Any]] = []
        for task_path in self._task_paths(project):
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
            callback_state = state.get("host_callbacks", {}) if isinstance(state, dict) else {}
            gated_export_state = state.get("gated_exports", {}) if isinstance(state, dict) else {}
            git_change_state = state.get("git_changes", {}) if isinstance(state, dict) else {}
            artifact_records = artifact_registry.get("records", []) if isinstance(artifact_registry, dict) else []
            execution_attempts = execution_state.get("attempts", []) if isinstance(execution_state, dict) else []
            visual_reviews = visual_review_state.get("records", []) if isinstance(visual_review_state, dict) else []
            revision_plans = revision_state.get("records", []) if isinstance(revision_state, dict) else []
            revision_jobs = revision_execution.get("jobs", []) if isinstance(revision_execution, dict) else []
            revision_approvals = revision_execution.get("approvals", {}) if isinstance(revision_execution, dict) else {}
            pending_revision_approvals = [
                item for item in revision_approvals.values()
                if isinstance(item, dict) and item.get("status") == "pending"
            ] if isinstance(revision_approvals, dict) else []
            handoffs = handoff_state.get("records", []) if isinstance(handoff_state, dict) else []
            callbacks = callback_state.get("records", []) if isinstance(callback_state, dict) else []
            gated_exports = gated_export_state.get("records", []) if isinstance(gated_export_state, dict) else []
            git_changes = git_change_state.get("records", []) if isinstance(git_change_state, dict) else []
            completed_exports = [
                item for item in gated_exports
                if isinstance(item, dict) and item.get("status") == "completed"
            ] if isinstance(gated_exports, list) else []
            committed_changes = [
                item for item in git_changes
                if isinstance(item, dict) and item.get("status") == "committed"
            ] if isinstance(git_changes, list) else []
            latest_export = gated_exports[-1] if isinstance(gated_exports, list) and gated_exports else {}
            latest_git_change = git_changes[-1] if isinstance(git_changes, list) and git_changes else {}
            artifact_review = qa_report.get("artifact_review", {}) if isinstance(qa_report, dict) else {}
            context = payload.get("context", {}) if isinstance(payload.get("context"), dict) else {}
            lease_path = task_path.parent / "task-lease.json"
            lease = {}
            if lease_path.is_file():
                try:
                    lease = json.loads(lease_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    lease = {"status": "invalid"}
            summaries.append(
                {
                    **{
                        key: payload.get(key)
                        for key in (
                            "task_id", "project", "requirement", "pipeline", "status",
                            "current_agent", "next_agent_index", "created_at", "updated_at", "completed_at",
                        )
                    },
                    "private_storage": str(task_path).startswith(str(self.layout.root)),
                    "theme_ref": context.get("active_theme_ref"),
                    "approval_status": approval_state.get("status") if isinstance(approval_state, dict) else None,
                    "pending_approval_count": len(approval_state.get("pending_ids", [])) if isinstance(approval_state, dict) else 0,
                    "artifact_count": len(artifact_records) if isinstance(artifact_records, list) else 0,
                    "provider_execution_count": len(execution_attempts) if isinstance(execution_attempts, list) else 0,
                    "visual_review_count": len(visual_reviews) if isinstance(visual_reviews, list) else 0,
                    "revision_plan_count": len(revision_plans) if isinstance(revision_plans, list) else 0,
                    "revision_job_count": len(revision_jobs) if isinstance(revision_jobs, list) else 0,
                    "pending_revision_approval_count": len(pending_revision_approvals),
                    "artifact_review_status": artifact_review.get("status") if isinstance(artifact_review, dict) else None,
                    "tool_resolution_status": tool_resolution.get("status") if isinstance(tool_resolution, dict) else None,
                    "tool_handoff_count": len(handoffs) if isinstance(handoffs, list) else 0,
                    "authenticated_callback_count": len(callbacks) if isinstance(callbacks, list) else 0,
                    "task_lease_status": lease.get("status") if isinstance(lease, dict) else None,
                    "gated_export_count": len(gated_exports) if isinstance(gated_exports, list) else 0,
                    "completed_export_count": len(completed_exports),
                    "latest_export_status": latest_export.get("status") if isinstance(latest_export, dict) else None,
                    "git_change_count": len(git_changes) if isinstance(git_changes, list) else 0,
                    "committed_git_change_count": len(committed_changes),
                    "latest_git_change_status": latest_git_change.get("status") if isinstance(latest_git_change, dict) else None,
                }
            )
        summaries.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return tuple(summaries)


__all__ = ["TaskStore"]
