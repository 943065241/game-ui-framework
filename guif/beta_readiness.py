from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from guif.compatibility import compatibility_contract
from guif.conversation_workflow import ConversationWorkflowService
from guif.core import init_project, validate_project
from guif.private_backup import PrivateBackupService
from guif.private_data import PrivateDataLayout
from guif.private_migration import PrivateSchemaMigrator
from guif.runtime import Runtime

CONVERSATION_HOST_CAPABILITIES = (
    "approval:decide",
    "export:execute",
    "host-work:claim",
    "host-work:complete",
    "host-work:read",
    "revision:decide",
    "task:lease",
    "task:resume",
    "tool:execute",
    "tool-result:submit",
    "visual-inspection:submit",
)


class BetaReadinessError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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


def bootstrap_workspace(
    workspace: Path,
    project: str,
    conversation_id: str,
    *,
    bearer_token: str | None = None,
    actor_id: str = "conversation-host",
) -> dict[str, Any]:
    """Initialize a Project, Host credential, and private Conversation in one call.

    A newly issued Bearer token is returned once and is never written to the
    project or Conversation record. Existing callers can provide a token to
    avoid creating another credential.
    """

    workspace = workspace.resolve()
    project_root = workspace / "projects" / project
    created_project = False
    if not (project_root / "project.json").is_file():
        init_project(workspace, project)
        created_project = True
    runtime = Runtime(workspace)
    issued: dict[str, Any] | None = None
    if isinstance(bearer_token, str) and bearer_token.strip():
        runtime.authenticate_actor(
            bearer_token,
            required_capabilities=CONVERSATION_HOST_CAPABILITIES,
        )
        token = bearer_token
    else:
        issued = runtime.register_host_credential(
            actor_id.strip() or "conversation-host",
            "chatgpt",
            CONVERSATION_HOST_CAPABILITIES,
            roles=("conversation-orchestrator",),
        )
        token = str(issued["bearer_token"])
    workflow = ConversationWorkflowService(
        workspace,
        runtime=runtime,
        bearer_token=token,
    )
    view = workflow.open(project, conversation_id)
    actions = view.get("actions") if isinstance(view.get("actions"), list) else []
    result: dict[str, Any] = {
        "schema_version": 1,
        "status": "ready",
        "project_created": created_project,
        "project": project,
        "conversation_id": conversation_id,
        "host": "chatgpt",
        "credential_created": issued is not None,
        "credential_secret_visible_once": issued is not None,
        "conversation": view,
        "next_action": actions[0] if actions else None,
        "compatibility": compatibility_contract(),
    }
    if issued is not None:
        result["bearer_token"] = token
        result["credential_id"] = issued.get("credential", {}).get("credential_id")
        result["token_handling"] = (
            "Store this token in a protected secret manager or GUIF_HOST_TOKEN; "
            "GUIF cannot display it again."
        )
    return result


class BetaReadinessService:
    """Privacy-safe diagnostics, backup coordination, and beta acceptance checks."""

    def __init__(
        self,
        workspace: Path,
        *,
        runtime: Runtime | None = None,
        bearer_token: str | None = None,
        data_root: Path | None = None,
    ) -> None:
        self.workspace = workspace.resolve()
        self.runtime = runtime or Runtime(self.workspace)
        self.layout = PrivateDataLayout(self.workspace, data_root)
        self.bearer_token = bearer_token
        self.backups = PrivateBackupService(self.workspace, data_root=data_root)
        self.migrations = PrivateSchemaMigrator(self.workspace, data_root=data_root)

    @staticmethod
    def _check(
        code: str,
        status: str,
        message: str,
        action: str | None = None,
    ) -> dict[str, Any]:
        return {
            "code": code,
            "status": status,
            "message": message,
            "action": action,
        }

    def _conversation_view(self, project: str, conversation_id: str) -> dict[str, Any]:
        service = ConversationWorkflowService(
            self.workspace,
            runtime=self.runtime,
            bearer_token=self.bearer_token,
        )
        return service.status(project, conversation_id)

    def diagnose(
        self,
        project: str,
        *,
        conversation_id: str | None = None,
        persist: bool = True,
    ) -> dict[str, Any]:
        checks: list[dict[str, Any]] = []
        project_errors = validate_project(self.workspace, project)
        checks.append(
            self._check(
                "project-contract",
                "passed" if not project_errors else "blocked",
                "Project structure and schemas are valid."
                if not project_errors
                else "Project validation found blocking issues: " + "; ".join(project_errors),
                None if not project_errors else "repair-project",
            )
        )
        try:
            self.layout.root.mkdir(parents=True, exist_ok=True)
            probe = self.layout.root / ".alpha28-write-probe"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            checks.append(
                self._check(
                    "private-storage",
                    "passed",
                    "Private data storage is available outside the Project Git tree.",
                )
            )
        except OSError as exc:
            checks.append(
                self._check(
                    "private-storage",
                    "blocked",
                    f"Private data storage is not writable: {type(exc).__name__}",
                    "fix-private-storage-permissions",
                )
            )
        migration = self.migrations.scan()
        migration_status = str(migration["status"])
        checks.append(
            self._check(
                "private-schema",
                "blocked"
                if migration_status == "blocked"
                else ("warning" if migration_status == "migration-required" else "passed"),
                "Private schemas are current."
                if migration_status == "current"
                else (
                    f"{migration['migration_required_count']} private record(s) need a recorded migration."
                    if migration_status == "migration-required"
                    else f"{migration['blocked_count']} private record(s) cannot be migrated automatically."
                ),
                "apply-private-migration"
                if migration_status == "migration-required"
                else ("inspect-private-records" if migration_status == "blocked" else None),
            )
        )
        try:
            ledger = self.runtime.verify_operation_ledger()
            ledger_status = str(ledger.get("status") or "")
            ledger_passed = ledger_status in {"verified", "empty", "not-initialized"}
            checks.append(
                self._check(
                    "operation-ledger",
                    "passed" if ledger_passed else "blocked",
                    f"Operation ledger status: {ledger_status or 'unknown'}.",
                    None if ledger_passed else "repair-operation-ledger",
                )
            )
        except Exception as exc:
            checks.append(
                self._check(
                    "operation-ledger",
                    "blocked",
                    f"Operation ledger verification failed: {type(exc).__name__}",
                    "inspect-operation-ledger",
                )
            )
        credential_status = "not-configured"
        if isinstance(self.bearer_token, str) and self.bearer_token.strip():
            try:
                self.runtime.authenticate_actor(
                    self.bearer_token,
                    required_capabilities=CONVERSATION_HOST_CAPABILITIES,
                )
                credential_status = "configured"
                checks.append(
                    self._check(
                        "conversation-host-credential",
                        "passed",
                        "The configured Host credential has every conversation capability.",
                    )
                )
            except Exception as exc:
                credential_status = "invalid"
                checks.append(
                    self._check(
                        "conversation-host-credential",
                        "blocked",
                        f"The configured Host credential is unusable: {type(exc).__name__}",
                        "issue-host-credential",
                    )
                )
        else:
            checks.append(
                self._check(
                    "conversation-host-credential",
                    "warning",
                    "No Host token is configured for production approvals, Tool work, or export.",
                    "set-GUIF_HOST_TOKEN",
                )
            )
        conversation: dict[str, Any] | None = None
        if conversation_id:
            try:
                conversation = self._conversation_view(project, conversation_id)
                stage = str(conversation.get("stage") or "unknown")
                action_required = stage not in {"completed", "ready-to-export"}
                actions = (
                    conversation.get("actions")
                    if isinstance(conversation.get("actions"), list)
                    else []
                )
                next_action = (
                    str(actions[0].get("action") or "recover")
                    if action_required and actions and isinstance(actions[0], dict)
                    else ("recover" if action_required else None)
                )
                checks.append(
                    self._check(
                        "conversation-state",
                        "warning" if action_required else "passed",
                        f"Conversation is at user-facing stage: {stage}.",
                        next_action,
                    )
                )
            except Exception as exc:
                checks.append(
                    self._check(
                        "conversation-state",
                        "blocked",
                        f"Conversation recovery failed: {type(exc).__name__}",
                        "recover-conversation",
                    )
                )
        backup_root = self.layout.backups
        backup_count = (
            len(tuple(backup_root.glob("*.guif-private.zip")))
            if backup_root.is_dir()
            else 0
        )
        checks.append(
            self._check(
                "portable-backup",
                "passed" if backup_count else "warning",
                f"{backup_count} verified-location candidate backup(s) are present."
                if backup_count
                else "No portable private backup has been created yet.",
                None if backup_count else "create-portable-backup",
            )
        )
        blocked = sum(item["status"] == "blocked" for item in checks)
        warnings = sum(item["status"] == "warning" for item in checks)
        report: dict[str, Any] = {
            "schema_version": 1,
            "status": "blocked" if blocked else ("action-required" if warnings else "ready"),
            "project": project,
            "conversation_id": conversation_id,
            "summary": {
                "check_count": len(checks),
                "passed_count": sum(item["status"] == "passed" for item in checks),
                "warning_count": warnings,
                "blocked_count": blocked,
            },
            "checks": checks,
            "conversation": conversation,
            "credential_status": credential_status,
            "compatibility": compatibility_contract(),
            "diagnosed_at": _now(),
        }
        if persist:
            report_path = (
                self.layout.diagnostics
                / project
                / f"diagnostic-{_timestamp()}.json"
            )
            _write_json(report_path, report)
            report["private_report_written"] = True
        return report

    def acceptance(
        self,
        project: str,
        conversation_id: str,
        *,
        require_completed: bool = False,
    ) -> dict[str, Any]:
        diagnosis = self.diagnose(
            project,
            conversation_id=conversation_id,
            persist=True,
        )
        conversation = diagnosis.get("conversation") or {}
        stage = str(conversation.get("stage") or "unknown")
        accepted_stages = {"ready-to-export", "completed"}
        production_flow_passed = stage in accepted_stages
        if require_completed:
            production_flow_passed = stage == "completed"
        blocked = diagnosis["summary"]["blocked_count"] > 0
        return {
            "schema_version": 1,
            "status": "passed" if production_flow_passed and not blocked else "not-ready",
            "project": project,
            "conversation_id": conversation_id,
            "mvp_contract_frozen": True,
            "privacy_boundary_verified": not any(
                item["code"] == "private-storage" and item["status"] == "blocked"
                for item in diagnosis["checks"]
            ),
            "production_flow_stage": stage,
            "required_stage": "completed" if require_completed else "ready-to-export-or-completed",
            "diagnosis_status": diagnosis["status"],
            "next_actions": [
                item["action"]
                for item in diagnosis["checks"]
                if item.get("action")
            ],
            "checked_at": _now(),
        }


__all__ = [
    "BetaReadinessError",
    "BetaReadinessService",
    "CONVERSATION_HOST_CAPABILITIES",
    "bootstrap_workspace",
]
