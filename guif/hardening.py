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

SOAK_PROFILES = {
    "quick": 10,
    "standard": 100,
    "extended": 1000,
}


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
    """Run bounded repeatability checks over non-mutating production reads."""

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

    @staticmethod
    def _peek_conversation_stage(
        conversation: ConversationWorkflowService,
        project: str,
        conversation_id: str,
    ) -> str:
        session = conversation.store.get(project, conversation_id)
        if session is None:
            raise HardeningError("conversation-record-missing")
        task = None
        task_id = session.get("active_task_id")
        if isinstance(task_id, str):
            try:
                task = conversation.runtime.load_task(project, task_id)
            except FileNotFoundError as exc:
                raise HardeningError("conversation-task-reference-missing") from exc
        stage, _, _ = conversation._stage(session, task)
        if not isinstance(stage, str) or not stage:
            raise HardeningError("conversation-stage-missing")
        return stage

    def soak(
        self,
        project: str,
        *,
        conversation_id: str | None = None,
        backup_path: Path | None = None,
        profile: str = "standard",
        iterations: int | None = None,
        max_p95_ms: float | None = None,
        persist: bool = True,
        report_path: Path | None = None,
    ) -> dict[str, Any]:
        if profile not in SOAK_PROFILES:
            raise ValueError(f"Unknown soak profile: {profile}")
        resolved_iterations = SOAK_PROFILES[profile] if iterations is None else iterations
        selected_profile = profile if iterations is None else "custom"
        if resolved_iterations <= 0 or resolved_iterations > 10_000:
            raise ValueError("iterations must be between 1 and 10000")
        if max_p95_ms is not None and max_p95_ms <= 0:
            raise ValueError("max_p95_ms must be positive")
        conversation = (
            ConversationWorkflowService(
                self.workspace,
                runtime=self.runtime,
                bearer_token=self.bearer_token,
                data_root=self.layout.root,
            )
            if conversation_id
            else None
        )
        samples: list[float] = []
        errors: list[dict[str, Any]] = []
        observed_stages: set[str] = set()
        started = time.perf_counter()
        for index in range(resolved_iterations):
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
                    observed_stages.add(
                        self._peek_conversation_stage(
                            conversation,
                            project,
                            conversation_id,
                        )
                    )
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
        if errors:
            failure_classification = "contract-check"
        elif not threshold_passed:
            failure_classification = "environment-performance-threshold"
        else:
            failure_classification = "none"
        report: dict[str, Any] = {
            "schema_version": 1,
            "status": status,
            "profile": selected_profile,
            "profile_requested": profile,
            "project": project,
            "conversation_checked": conversation_id is not None,
            "observed_stages": sorted(observed_stages),
            "backup_checked": backup_path is not None,
            "iterations": resolved_iterations,
            "successful_iterations": resolved_iterations - len(errors),
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
            "failure_classification": failure_classification,
            "product_correctness_failed": bool(errors),
            "performance_threshold_failed": not threshold_passed,
            "threshold_interpretation": (
                "A performance threshold failure is host/environment evidence requiring investigation; "
                "it is not by itself proof of a GUIF product correctness failure."
            ),
            "errors": errors[:20],
            "error_count_truncated": max(0, len(errors) - 20),
            "mutating_operations_performed": False,
            "production_state_mutated": False,
            "machine_readable": True,
            "completed_at": _now(),
        }
        destination: Path | None = None
        if report_path is not None:
            destination = report_path.resolve()
        elif persist:
            destination = (
                self.layout.hardening_reports
                / project
                / f"soak-{_timestamp()}.json"
            )
        if destination is not None:
            _write_json(destination, report)
            report["report_written"] = True
            report["private_report_written"] = report_path is None
        return report


__all__ = ["HardeningError", "HardeningService", "SOAK_PROFILES"]
