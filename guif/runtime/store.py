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

        approval_path = run_dir / "approvals.json"
        approval_state = payload["state"].get("approval_state")
        if isinstance(approval_state, dict):
            _write_json(approval_path, approval_state)
        elif approval_path.exists():
            approval_path.unlink()

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
            approval_state = payload.get("state", {}).get("approval_state", {})
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
                }
            )
        summaries.sort(
            key=lambda item: str(item.get("created_at") or ""),
            reverse=True,
        )
        return tuple(summaries)
