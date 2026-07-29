from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from guif.auth import AuthenticatedActor, HostCredentialStore
from guif.concurrency import TaskLeaseService
from guif.git_changes import GitChangeService
from guif.host_api import AuthenticatedHostCallbackService
from guif.runtime.private_theme import Runtime as PrivateThemeRuntime


class Runtime(PrivateThemeRuntime):
    """GUIF Runtime with authenticated actors, Task leases, callbacks, and Git changes."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.host_credentials = HostCredentialStore(self.workspace)
        self.task_leases = TaskLeaseService(self.workspace, store=self.store)
        self.authenticated_callbacks = AuthenticatedHostCallbackService(
            self.workspace,
            runtime=self,
            store=self.store,
            credentials=self.host_credentials,
            leases=self.task_leases,
        )
        self.git_changes = GitChangeService(
            self.workspace,
            store=self.store,
            leases=self.task_leases,
        )

    def register_host_credential(
        self,
        actor_id: str,
        host_id: str,
        capabilities: Iterable[str],
        *,
        roles: Iterable[str] = (),
        created_by: str = "local-admin",
        expires_at: str | None = None,
    ) -> dict[str, Any]:
        return self.host_credentials.register(
            actor_id,
            host_id,
            capabilities,
            roles=roles,
            created_by=created_by,
            expires_at=expires_at,
        )

    def list_host_credentials(self, *, include_revoked: bool = False) -> tuple[dict[str, Any], ...]:
        return self.host_credentials.list(include_revoked=include_revoked)

    def revoke_host_credential(
        self,
        credential_id: str,
        *,
        actor: str,
        reason: str,
    ) -> dict[str, Any]:
        return self.host_credentials.revoke(credential_id, actor=actor, reason=reason)

    def rotate_host_credential(
        self,
        credential_id: str,
        *,
        actor: str,
        reason: str = "credential rotation",
    ) -> dict[str, Any]:
        return self.host_credentials.rotate(credential_id, actor=actor, reason=reason)

    def authenticate_actor(
        self,
        bearer_token: str,
        *,
        required_capabilities: Iterable[str] = (),
        expected_host_id: str | None = None,
    ) -> AuthenticatedActor:
        return self.host_credentials.authenticate(
            bearer_token,
            required_capabilities=required_capabilities,
            expected_host_id=expected_host_id,
        )

    def get_task_etag(self, project: str, task_id: str) -> str:
        return self.task_leases.current_etag(project, task_id)

    def get_task_lease(self, project: str, task_id: str) -> dict[str, Any]:
        return self.task_leases.get(project, task_id)

    def acquire_task_lease(
        self,
        project: str,
        task_id: str,
        *,
        bearer_token: str,
        expected_task_etag: str | None = None,
        ttl_seconds: int = 300,
        purpose: str = "exclusive-task-operation",
    ) -> dict[str, Any]:
        actor = self.authenticate_actor(
            bearer_token,
            required_capabilities=("task:lease",),
        )
        return self.task_leases.acquire(
            project,
            task_id,
            actor,
            expected_task_etag=expected_task_etag,
            ttl_seconds=ttl_seconds,
            purpose=purpose,
        )

    def renew_task_lease(
        self,
        project: str,
        task_id: str,
        *,
        bearer_token: str,
        lease_token: str,
        expected_task_etag: str,
        ttl_seconds: int = 300,
    ) -> dict[str, Any]:
        actor = self.authenticate_actor(
            bearer_token,
            required_capabilities=("task:lease",),
        )
        return self.task_leases.renew(
            project,
            task_id,
            lease_token,
            actor,
            expected_task_etag=expected_task_etag,
            ttl_seconds=ttl_seconds,
        )

    def release_task_lease(
        self,
        project: str,
        task_id: str,
        *,
        bearer_token: str,
        lease_token: str,
        reason: str = "released",
    ) -> dict[str, Any]:
        actor = self.authenticate_actor(
            bearer_token,
            required_capabilities=("task:lease",),
        )
        return self.task_leases.release(
            project,
            task_id,
            lease_token,
            actor,
            reason=reason,
        )

    def submit_authenticated_tool_result(
        self,
        project: str,
        task_id: str,
        handoff_id: str,
        *,
        bearer_token: str,
        lease_token: str,
        expected_task_etag: str,
        content: bytes,
        filename: str,
        mime_type: str,
        content_sha256: str | None = None,
        width: int | None = None,
        height: int | None = None,
        model_id: str | None = None,
        tool_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> Any:
        return self.authenticated_callbacks.submit_result(
            project,
            task_id,
            handoff_id,
            bearer_token=bearer_token,
            lease_token=lease_token,
            expected_task_etag=expected_task_etag,
            content=content,
            filename=filename,
            mime_type=mime_type,
            content_sha256=content_sha256,
            width=width,
            height=height,
            model_id=model_id,
            tool_id=tool_id,
            metadata=metadata,
            request_id=request_id,
        )

    def list_host_callbacks(self, project: str, task_id: str) -> tuple[dict[str, Any], ...]:
        return self.authenticated_callbacks.list(project, task_id)

    def get_host_callback(self, project: str, task_id: str, callback_id: str) -> dict[str, Any]:
        return self.authenticated_callbacks.get(project, task_id, callback_id)

    def decide_approval_authenticated(
        self,
        project: str,
        task_id: str,
        approval_id: str,
        decision: str,
        *,
        bearer_token: str,
        lease_token: str,
        expected_task_etag: str,
        comment: str | None = None,
    ) -> Any:
        actor = self.authenticate_actor(
            bearer_token,
            required_capabilities=("approval:decide",),
        )
        lease = self.task_leases.validate(
            project,
            task_id,
            lease_token,
            actor,
            expected_task_etag=expected_task_etag,
        )
        methods = {
            "approved": self.approve,
            "rejected": self.reject,
            "changes-requested": self.request_changes,
        }
        if decision not in methods:
            raise ValueError("decision must be approved, rejected, or changes-requested")
        task = methods[decision](
            project,
            task_id,
            approval_id,
            actor=actor.actor_id,
            comment=comment,
        )
        state = task.state.get("approval_state")
        if isinstance(state, dict):
            records = state.get("records")
            history = state.get("history")
            if isinstance(records, dict) and isinstance(records.get(approval_id), dict):
                records[approval_id]["authenticated_actor"] = actor.to_dict()
                records[approval_id]["lease_id"] = lease.get("lease_id")
            if isinstance(history, list):
                for item in reversed(history):
                    if isinstance(item, dict) and item.get("approval_id") == approval_id:
                        item["authenticated_actor"] = actor.to_dict()
                        item["lease_id"] = lease.get("lease_id")
                        break
        task.record(
            "host-api",
            decision,
            f"Authenticated actor {actor.actor_id} set Approval {approval_id} to {decision}.",
        )
        self.store.save(task)
        self.task_leases.consume(
            project,
            task_id,
            lease_token,
            actor,
            operation_id=f"approval:{approval_id}:{decision}",
        )
        return task

    def execute_gated_export_authenticated(
        self,
        project: str,
        task_id: str,
        *,
        bearer_token: str,
        lease_token: str,
        expected_task_etag: str,
        target_engine: str | None = None,
    ) -> dict[str, Any]:
        actor = self.authenticate_actor(
            bearer_token,
            required_capabilities=("export:execute",),
        )
        lease = self.task_leases.validate(
            project,
            task_id,
            lease_token,
            actor,
            expected_task_etag=expected_task_etag,
        )
        record = super().execute_gated_export(
            project,
            task_id,
            target_engine=target_engine,
            actor=actor.actor_id,
        )
        task = self.store.load(project, task_id)
        export = next(
            (
                item
                for item in task.state.get("gated_exports", {}).get("records", [])
                if isinstance(item, dict) and item.get("export_id") == record.get("export_id")
            ),
            None,
        )
        if isinstance(export, dict):
            export["authenticated_actor"] = actor.to_dict()
            export["lease_id"] = lease.get("lease_id")
            transaction_value = export.get("transaction")
            if isinstance(transaction_value, str) and transaction_value:
                root = Path(task.context.project_root)
                transaction_path = root / transaction_value
                if transaction_path.is_file():
                    transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
                    if isinstance(transaction, dict):
                        transaction["authenticated_actor"] = actor.to_dict()
                        transaction["lease_id"] = lease.get("lease_id")
                        temporary = transaction_path.with_suffix(transaction_path.suffix + ".tmp")
                        temporary.write_text(
                            json.dumps(transaction, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8",
                        )
                        temporary.replace(transaction_path)
            self.store.save(task)
            record = dict(export)
        self.task_leases.consume(
            project,
            task_id,
            lease_token,
            actor,
            operation_id=f"export:{record['export_id']}",
        )
        return record

    def rollback_gated_export_authenticated(
        self,
        project: str,
        task_id: str,
        export_id: str,
        *,
        bearer_token: str,
        lease_token: str,
        expected_task_etag: str,
        reason: str,
        force: bool = False,
    ) -> dict[str, Any]:
        actor = self.authenticate_actor(
            bearer_token,
            required_capabilities=("export:rollback",),
        )
        lease = self.task_leases.validate(
            project,
            task_id,
            lease_token,
            actor,
            expected_task_etag=expected_task_etag,
        )
        record = super().rollback_gated_export(
            project,
            task_id,
            export_id,
            actor=actor.actor_id,
            reason=reason,
            force=force,
        )
        task = self.store.load(project, task_id)
        export = next(
            (
                item
                for item in task.state.get("gated_exports", {}).get("records", [])
                if isinstance(item, dict) and item.get("export_id") == export_id
            ),
            None,
        )
        if isinstance(export, dict) and isinstance(export.get("rollback"), dict):
            export["rollback"]["authenticated_actor"] = actor.to_dict()
            export["rollback"]["lease_id"] = lease.get("lease_id")
            self.store.save(task)
            record = dict(export)
        self.task_leases.consume(
            project,
            task_id,
            lease_token,
            actor,
            operation_id=f"export-rollback:{export_id}",
        )
        return record

    def prepare_export_git_change(
        self,
        project: str,
        task_id: str,
        export_id: str,
        *,
        bearer_token: str,
        expected_task_etag: str,
        branch_name: str | None = None,
        message: str | None = None,
    ) -> dict[str, Any]:
        actor = self.authenticate_actor(
            bearer_token,
            required_capabilities=("git:prepare",),
        )
        return self.git_changes.prepare_export_change(
            project,
            task_id,
            export_id,
            actor,
            expected_task_etag=expected_task_etag,
            branch_name=branch_name,
            message=message,
        )

    def list_git_changes(self, project: str, task_id: str) -> tuple[dict[str, Any], ...]:
        return self.git_changes.list(project, task_id)

    def get_git_change(self, project: str, task_id: str, change_set_id: str) -> dict[str, Any]:
        return self.git_changes.get(project, task_id, change_set_id)

    def diff_git_change(self, project: str, task_id: str, change_set_id: str) -> dict[str, Any]:
        return self.git_changes.diff(project, task_id, change_set_id)

    def execute_git_change(
        self,
        project: str,
        task_id: str,
        change_set_id: str,
        *,
        bearer_token: str,
        lease_token: str,
        expected_task_etag: str,
    ) -> dict[str, Any]:
        actor = self.authenticate_actor(
            bearer_token,
            required_capabilities=("git:commit",),
        )
        return self.git_changes.execute(
            project,
            task_id,
            change_set_id,
            actor,
            lease_token=lease_token,
            expected_task_etag=expected_task_etag,
        )

    def revert_git_change(
        self,
        project: str,
        task_id: str,
        change_set_id: str,
        *,
        bearer_token: str,
        lease_token: str,
        expected_task_etag: str,
        reason: str,
    ) -> dict[str, Any]:
        actor = self.authenticate_actor(
            bearer_token,
            required_capabilities=("git:revert",),
        )
        return self.git_changes.revert(
            project,
            task_id,
            change_set_id,
            actor,
            lease_token=lease_token,
            expected_task_etag=expected_task_etag,
            reason=reason,
        )

    def operation_summary(self, project: str, task_id: str) -> dict[str, Any]:
        task = self.store.load(project, task_id)
        return {
            "schema_version": 1,
            "project": project,
            "task_id": task_id,
            "status": task.status,
            "task_etag": self.get_task_etag(project, task_id),
            "lease": self.get_task_lease(project, task_id),
            "host_callback_count": len(self.list_host_callbacks(project, task_id)),
            "git_change_count": len(self.list_git_changes(project, task_id)),
            "latest_tool_resolution": task.state.get("tool_resolution"),
            "latest_export_status": (
                task.state.get("gated_exports", {}).get("records", [])[-1].get("status")
                if isinstance(task.state.get("gated_exports"), dict)
                and task.state["gated_exports"].get("records")
                else None
            ),
        }


__all__ = ["Runtime"]
