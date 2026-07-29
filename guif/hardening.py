from __future__ import annotations

import json
import os
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from guif.conversation_workflow import ConversationWorkflowService
from guif.core import validate_project
from guif.private_backup import PrivateBackupService
from guif.private_data import PrivateDataLayout
from guif.private_migration import PrivateSchemaMigrator
from guif.runtime import Runtime


class HardeningError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * percentile))
    return ordered[max(0, min(index, len(ordered) - 1))]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    try:
        os.chmod(temporary, 0o600)
    except OSError:
        pass
    temporary.replace(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


class HardeningService:
    """Run bounded repeatability checks over read-only production contracts."""

    def __init__(
        self,
        workspace: Path,
        *,
        bearer_token: str | None = None,
        data_root: Path | None = None,
    ) -> None:
        self.workspace = workspace.resolve()
        self.layout = PrivateDataLayout(self.workspace, data_root)
        self.runtime = Runtime(self.workspace)
        self.bearer_token = bearer_token
        self.migrator = PrivateSchemaMigrator(self.workspace, data_root=data_root)
        self.backups = PrivateBackupService(self.workspace, data_root=data_root)

    def soak(
        self,
        project: str,
        *,
        conversation_id: str | None = None,
        backup_path: Path | None = None,
        iterations: int = 100,
        max_p95_ms: float | None = None,
        persist: bool = True,
    ) -> dict[str, Any]:
        if iterations <= 0 or iterations > 10_000:
            raise ValueError("iterations must be between 1 and 10000")
        if max_p95_ms is not None and max_p95_ms <= 0:
            raise ValueError("max_p95_ms must be positive")
        conversation = (
            ConversationWorkflowService(
                self.workspace,
                runtime=self.runtime,
                bearer_token=self.bearer_token,
            )
            if conversation_id
            else None
        )
        samples: list[float] = []
        errors: list[dict[str, Any]] = []
        started = time.perf_counter()
        for index in range(iterations):
            iteration_started = time.perf_counter()
            try:
                project_errors = validate_project(self.workspace, project)
                if project_errors:
                    raise HardeningError("project-contract-invalid")
                migration = self.migrator.scan()
                if migration["status"] == "blocked":
                    raise HardeningError("private-schema-blocked")
                ledger = self.runtime.verify_operation_ledger()
                if str(ledger.get("status") or "") not in {
                    "verified",
                    "empty",
                    "not-initialized",
                }:
                    raise HardeningError("operation-ledger-invalid")
                if conversation is not None and conversation_id is not None:
                    view = conversation.status(project, conversation_id)
                    if not isinstance(view.get("stage"), str):
                        raise HardeningError("conversation-stage-missing")
                if backup_path is not None:
                    verification = self.backups.verify(backup_path)
                    if verification.get("status") != "verified":
                        raise HardeningError("backup-verification-failed")
            except Exception as exc:
                errors.append(
                    {
                        "iteration": index + 1,
                        "error_type": type(exc).__name__,
                        "error_code": str(exc)
                        if isinstance(exc, HardeningError)
                        else "unexpected-error",
                    }
                )
            samples.append((time.perf_counter() - iteration_started) * 1000.0)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        p50 = _percentile(samples, 0.50)
        p95 = _percentile(samples, 0.95)
        threshold_passed = max_p95_ms is None or p95 <= max_p95_ms
        status = "passed" if not errors and threshold_passed else "failed"
        report: dict[str, Any] = {
            "schema_version": 1,
            "status": status,
            "project": project,
            "conversation_checked": conversation_id is not None,
            "backup_checked": backup_path is not None,
            "iterations": iterations,
            "successful_iterations": iterations - len(errors),
            "failed_iterations": len(errors),
            "timing_ms": {
                "total": round(elapsed_ms, 3),
                "mean": round(statistics.fmean(samples), 3),
                "p50": round(p50, 3),
                "p95": round(p95, 3),
                "max": round(max(samples), 3),
                "threshold": max_p95_ms,
                "threshold_passed": threshold_passed,
            },
            "errors": errors[:20],
            "error_count_truncated": max(0, len(errors) - 20),
            "mutating_operations_performed": False,
            "completed_at": _now(),
        }
        if persist:
            report_path = (
                self.layout.hardening_reports
                / project
                / f"soak-{_timestamp()}.json"
            )
            _write_json(report_path, report)
            report["private_report_written"] = True
        return report


__all__ = ["HardeningError", "HardeningService"]
