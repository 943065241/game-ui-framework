from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from guif.auth import AuthenticatedActor
from guif.concurrency import ConcurrencyError, TaskLeaseService, task_etag
from guif.paths import project_root
from guif.runtime.store import TaskStore

GIT_CHANGE_SCHEMA_VERSION = 1
GIT_CHANGE_STATE_SCHEMA_VERSION = 1


class GitChangeError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _state(task: Any) -> dict[str, Any]:
    state = task.state.get("git_changes")
    if not isinstance(state, dict):
        state = {
            "schema_version": GIT_CHANGE_STATE_SCHEMA_VERSION,
            "task_id": task.task_id,
            "project": task.project,
            "records": [],
            "latest_by_export": {},
            "updated_at": _now(),
        }
        task.state["git_changes"] = state
    return state


def _replace_output(task: Any, change_set_id: str, record: dict[str, Any]) -> None:
    for output in task.outputs:
        if (
            isinstance(output, dict)
            and output.get("type") == "git-change-set"
            and isinstance(output.get("value"), dict)
            and output["value"].get("change_set_id") == change_set_id
        ):
            output["value"] = record
            return
    task.add_output("git-change-set", record, agent="git")


def _safe_branch(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._/-]+", "-", value.strip()).strip("-./")
    normalized = re.sub(r"/{2,}", "/", normalized)
    if not normalized:
        raise ValueError("Git branch name must not be empty")
    return normalized


class GitChangeService:
    """Plan, commit, inspect, and revert Task-bound Project Git changes."""

    def __init__(
        self,
        workspace: Path,
        *,
        store: TaskStore | None = None,
        leases: TaskLeaseService | None = None,
    ) -> None:
        self.workspace = workspace
        self.store = store or TaskStore(workspace)
        self.leases = leases or TaskLeaseService(workspace, store=self.store)

    @staticmethod
    def _run(
        repo_root: Path,
        args: Iterable[str],
        *,
        allowed: tuple[int, ...] = (0,),
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if result.returncode not in allowed:
            message = result.stderr.strip() or result.stdout.strip() or "unknown Git error"
            raise GitChangeError(f"git {' '.join(args)} failed: {message}")
        return result

    def _repo_root(self, project: str) -> tuple[Path, Path]:
        root = project_root(self.workspace, project).resolve()
        result = self._run(root, ("rev-parse", "--show-toplevel"))
        repo = Path(result.stdout.strip()).resolve()
        try:
            root.relative_to(repo)
        except ValueError as exc:
            raise GitChangeError("Project root is outside the resolved Git repository") from exc
        return repo, root

    @staticmethod
    def _safe_project_path(root: Path, value: str) -> Path:
        candidate = (root / value).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise GitChangeError(f"Git Change Set path escapes Project root: {value}") from exc
        return candidate

    @staticmethod
    def _export_record(task: Any, export_id: str) -> dict[str, Any]:
        state = task.state.get("gated_exports")
        if not isinstance(state, dict):
            raise GitChangeError("Task does not contain Gated Export records")
        record = next(
            (
                item
                for item in state.get("records", [])
                if isinstance(item, dict) and item.get("export_id") == export_id
            ),
            None,
        )
        if not isinstance(record, dict):
            raise GitChangeError(f"Unknown Gated Export: {export_id}")
        return record

    def _persist(self, task: Any, record: dict[str, Any]) -> dict[str, Any]:
        state = _state(task)
        records = state.setdefault("records", [])
        latest = state.setdefault("latest_by_export", {})
        if not isinstance(records, list) or not isinstance(latest, dict):
            raise ValueError("Invalid persisted Git Change Set state")
        existing = next(
            (
                item
                for item in records
                if isinstance(item, dict) and item.get("change_set_id") == record.get("change_set_id")
            ),
            None,
        )
        if existing is None:
            records.append(record)
            persisted = record
        elif existing is record:
            persisted = existing
        else:
            replacement = dict(record)
            existing.clear()
            existing.update(replacement)
            persisted = existing
        latest[str(record["export_id"])] = record["change_set_id"]
        state["updated_at"] = _now()
        _replace_output(task, str(record["change_set_id"]), persisted)
        self.store.save(task)
        return persisted

    def prepare_export_change(
        self,
        project: str,
        task_id: str,
        export_id: str,
        actor: AuthenticatedActor,
        *,
        expected_task_etag: str,
        branch_name: str | None = None,
        message: str | None = None,
    ) -> dict[str, Any]:
        task = self.store.load(project, task_id)
        current_etag = task_etag(task)
        if current_etag != expected_task_etag:
            raise ConcurrencyError(
                f"Task etag mismatch: expected {expected_task_etag}, current {current_etag}"
            )
        export = self._export_record(task, export_id)
        if export.get("status") != "completed":
            raise GitChangeError(
                f"Only completed Gated Exports can create Git Change Sets: {export.get('status')}"
            )
        repo, root = self._repo_root(project)
        transaction_value = str(export.get("transaction") or "")
        transaction_path = self._safe_project_path(root, transaction_value)
        if not transaction_path.is_file():
            raise GitChangeError("Gated Export transaction record is missing")
        transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
        if not isinstance(transaction, dict):
            raise GitChangeError("Gated Export transaction is invalid")

        project_paths: set[Path] = {transaction_path}
        for mutation in transaction.get("mutations", []):
            if isinstance(mutation, dict) and isinstance(mutation.get("path"), str):
                project_paths.add(self._safe_project_path(root, mutation["path"]))
        output_value = str(export.get("engine_output_dir") or "")
        if output_value:
            output_dir = self._safe_project_path(root, output_value)
            if output_dir.exists():
                project_paths.update(path for path in output_dir.rglob("*") if path.is_file())
        if not project_paths:
            raise GitChangeError("Gated Export did not produce any Git-manageable paths")

        paths = sorted(str(path.relative_to(repo)) for path in project_paths)
        base_head = self._run(repo, ("rev-parse", "HEAD")).stdout.strip()
        current_branch = self._run(repo, ("branch", "--show-current")).stdout.strip() or None
        resolved_branch = _safe_branch(branch_name or f"guif/{project}/{export_id}")
        self._run(repo, ("check-ref-format", "--branch", resolved_branch))
        status_lines = self._run(
            repo,
            ("status", "--porcelain", "--untracked-files=all", "--", *paths),
        ).stdout.splitlines()
        identity = {
            "task_id": task_id,
            "export_id": export_id,
            "base_head": base_head,
            "paths": paths,
            "branch": resolved_branch,
        }
        change_set_id = "change-" + _canonical_hash(identity)[:16]
        record = {
            "schema_version": GIT_CHANGE_SCHEMA_VERSION,
            "change_set_id": change_set_id,
            "task_id": task_id,
            "project": project,
            "export_id": export_id,
            "status": "ready" if status_lines else "no-changes",
            "actor": actor.to_dict(),
            "repository_root": str(repo),
            "project_root": str(root.relative_to(repo)),
            "base_head": base_head,
            "base_branch": current_branch,
            "branch": resolved_branch,
            "message": (message or f"chore({project}): commit GUIF Export {export_id}").strip(),
            "paths": paths,
            "working_tree_status": status_lines,
            "transaction": transaction_value,
            "transaction_sha256": hashlib.sha256(transaction_path.read_bytes()).hexdigest(),
            "prepared_from_task_etag": expected_task_etag,
            "prepared_at": _now(),
            "updated_at": _now(),
            "commit": None,
            "revert": None,
            "error": None,
        }
        task.record(
            "git",
            record["status"],
            f"Prepared Git Change Set {change_set_id} for Export {export_id} with {len(paths)} path(s).",
        )
        return dict(self._persist(task, record))

    def list(self, project: str, task_id: str) -> tuple[dict[str, Any], ...]:
        task = self.store.load(project, task_id)
        state = task.state.get("git_changes")
        if not isinstance(state, dict):
            return ()
        return tuple(item for item in state.get("records", []) if isinstance(item, dict))

    def get(self, project: str, task_id: str, change_set_id: str) -> dict[str, Any]:
        for record in self.list(project, task_id):
            if record.get("change_set_id") == change_set_id:
                return record
        raise GitChangeError(f"Unknown Git Change Set: {change_set_id}")

    def diff(self, project: str, task_id: str, change_set_id: str) -> dict[str, Any]:
        record = self.get(project, task_id, change_set_id)
        repo = Path(str(record["repository_root"])).resolve()
        paths = tuple(str(item) for item in record.get("paths", []))
        if not paths:
            raise GitChangeError("Git Change Set contains no paths")
        tracked = self._run(repo, ("diff", "--no-ext-diff", "--", *paths)).stdout
        status_lines = self._run(
            repo,
            ("status", "--porcelain", "--untracked-files=all", "--", *paths),
        ).stdout.splitlines()
        untracked_diffs: list[str] = []
        for line in status_lines:
            if not line.startswith("?? "):
                continue
            relative = line[3:]
            candidate = (repo / relative).resolve()
            try:
                candidate.relative_to(repo)
            except ValueError:
                continue
            if candidate.is_file():
                result = self._run(
                    repo,
                    ("diff", "--no-index", "--", "/dev/null", relative),
                    allowed=(0, 1),
                )
                untracked_diffs.append(result.stdout)
        combined = tracked + "".join(untracked_diffs)
        return {
            "schema_version": 1,
            "change_set_id": change_set_id,
            "status": record.get("status"),
            "base_head": record.get("base_head"),
            "paths": list(paths),
            "working_tree_status": status_lines,
            "diff": combined,
            "diff_sha256": hashlib.sha256(combined.encode("utf-8")).hexdigest(),
        }

    def execute(
        self,
        project: str,
        task_id: str,
        change_set_id: str,
        actor: AuthenticatedActor,
        *,
        lease_token: str,
        expected_task_etag: str,
    ) -> dict[str, Any]:
        self.leases.validate(
            project,
            task_id,
            lease_token,
            actor,
            expected_task_etag=expected_task_etag,
        )
        task = self.store.load(project, task_id)
        state = _state(task)
        record = next(
            (
                item
                for item in state.get("records", [])
                if isinstance(item, dict) and item.get("change_set_id") == change_set_id
            ),
            None,
        )
        if not isinstance(record, dict):
            raise GitChangeError(f"Unknown Git Change Set: {change_set_id}")
        if record.get("status") == "committed":
            return dict(record)
        if record.get("status") != "ready":
            raise GitChangeError(f"Git Change Set is not ready: {record.get('status')}")

        repo = Path(str(record["repository_root"])).resolve()
        paths = tuple(str(item) for item in record.get("paths", []))
        current_head = self._run(repo, ("rev-parse", "HEAD")).stdout.strip()
        if current_head != record.get("base_head"):
            raise ConcurrencyError(
                f"Git HEAD changed after planning: expected {record.get('base_head')}, current {current_head}"
            )
        branch = str(record["branch"])
        exists = self._run(
            repo,
            ("show-ref", "--verify", "--quiet", f"refs/heads/{branch}"),
            allowed=(0, 1),
        ).returncode == 0
        if exists:
            raise GitChangeError(f"Git branch already exists: {branch}")
        original_branch = self._run(repo, ("branch", "--show-current")).stdout.strip()
        if not original_branch:
            raise GitChangeError("Git Change Set execution requires a named current branch")

        try:
            self._run(repo, ("switch", "-c", branch))
            self._run(repo, ("add", "--", *paths))
            staged = self._run(repo, ("diff", "--cached", "--name-only", "--", *paths)).stdout.splitlines()
            if not staged:
                raise GitChangeError("Git Change Set produced no staged changes")
            staged_diff = self._run(repo, ("diff", "--cached", "--no-ext-diff", "--", *paths)).stdout
            self._run(repo, ("commit", "-m", str(record["message"]), "--", *paths))
            commit_sha = self._run(repo, ("rev-parse", "HEAD")).stdout.strip()
        except Exception as exc:
            try:
                self._run(repo, ("reset", "--", *paths), allowed=(0, 1))
                self._run(repo, ("switch", original_branch), allowed=(0, 1))
                self._run(repo, ("branch", "-D", branch), allowed=(0, 1))
            except Exception:
                pass
            record["status"] = "failed"
            record["error"] = {"type": type(exc).__name__, "message": str(exc)}
            record["updated_at"] = _now()
            task.record("git", "failed", f"Git Change Set {change_set_id} failed: {exc}")
            self._persist(task, record)
            raise GitChangeError(f"Git Change Set execution failed: {exc}") from exc

        completed_at = _now()
        record["status"] = "committed"
        record["actor"] = actor.to_dict()
        record["commit"] = {
            "sha": commit_sha,
            "parent": current_head,
            "branch": branch,
            "message": record["message"],
            "paths": staged,
            "diff_sha256": hashlib.sha256(staged_diff.encode("utf-8")).hexdigest(),
            "committed_at": completed_at,
        }
        record["updated_at"] = completed_at
        export = self._export_record(task, str(record["export_id"]))
        export["git_change_set_id"] = change_set_id
        export["git_commit"] = commit_sha
        export["updated_at"] = completed_at
        task.record("git", "committed", f"Git Change Set {change_set_id} created commit {commit_sha}.")
        persisted = dict(self._persist(task, record))
        self.leases.consume(
            project,
            task_id,
            lease_token,
            actor,
            operation_id=change_set_id,
        )
        return persisted

    def revert(
        self,
        project: str,
        task_id: str,
        change_set_id: str,
        actor: AuthenticatedActor,
        *,
        lease_token: str,
        expected_task_etag: str,
        reason: str,
    ) -> dict[str, Any]:
        normalized_reason = reason.strip()
        if not normalized_reason:
            raise ValueError("reason must not be empty")
        self.leases.validate(
            project,
            task_id,
            lease_token,
            actor,
            expected_task_etag=expected_task_etag,
        )
        task = self.store.load(project, task_id)
        state = _state(task)
        record = next(
            (
                item
                for item in state.get("records", [])
                if isinstance(item, dict) and item.get("change_set_id") == change_set_id
            ),
            None,
        )
        if not isinstance(record, dict):
            raise GitChangeError(f"Unknown Git Change Set: {change_set_id}")
        if record.get("status") == "reverted":
            return dict(record)
        if record.get("status") != "committed" or not isinstance(record.get("commit"), dict):
            raise GitChangeError("Only a committed Git Change Set can be reverted")

        repo = Path(str(record["repository_root"])).resolve()
        paths = tuple(str(item) for item in record.get("paths", []))
        dirty = self._run(
            repo,
            ("status", "--porcelain", "--untracked-files=all", "--", *paths),
        ).stdout.splitlines()
        if dirty:
            raise GitChangeError(
                "Git revert would overwrite selected path changes: " + ", ".join(dirty)
            )
        branch = str(record["commit"]["branch"])
        current_branch = self._run(repo, ("branch", "--show-current")).stdout.strip()
        if current_branch != branch:
            self._run(repo, ("switch", branch))
        commit_sha = str(record["commit"]["sha"])
        self._run(repo, ("revert", "--no-edit", commit_sha))
        revert_sha = self._run(repo, ("rev-parse", "HEAD")).stdout.strip()
        completed_at = _now()
        record["status"] = "reverted"
        record["revert"] = {
            "sha": revert_sha,
            "reverted_commit": commit_sha,
            "actor": actor.to_dict(),
            "reason": normalized_reason,
            "completed_at": completed_at,
        }
        record["updated_at"] = completed_at
        export = self._export_record(task, str(record["export_id"]))
        export["git_revert_commit"] = revert_sha
        export["updated_at"] = completed_at
        task.record("git", "reverted", f"Git Change Set {change_set_id} was reverted by {actor.actor_id}.")
        persisted = dict(self._persist(task, record))
        self.leases.consume(
            project,
            task_id,
            lease_token,
            actor,
            operation_id=f"revert:{change_set_id}",
        )
        return persisted


__all__ = [
    "GIT_CHANGE_SCHEMA_VERSION",
    "GitChangeError",
    "GitChangeService",
]
