from __future__ import annotations

from typing import Any, Callable, Iterable
from uuid import uuid4

from guif.auth import AuthenticatedActor
from guif.operation_ledger import OperationLedger, OperationLedgerError
from guif.runtime.operational import Runtime as OperationalRuntime


class Runtime(OperationalRuntime):
    """GUIF Runtime with a private signed operation ledger."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.operation_ledger = OperationLedger(self.workspace)

    def _ledgered(
        self,
        operation: str,
        *,
        actor: dict[str, Any] | str | None,
        scope: dict[str, Any],
        request: dict[str, Any],
        action: Callable[[], Any],
        summarize: Callable[[Any], dict[str, Any]],
    ) -> Any:
        verification = self.operation_ledger.verify()
        if verification.get("status") == "invalid":
            raise OperationLedgerError(
                "Authenticated operation refused because the private operation ledger is invalid"
            )
        operation_id = "operation-" + uuid4().hex
        self.operation_ledger.append(
            operation,
            "started",
            actor=actor,
            scope=scope,
            details={"request": request},
            operation_id=operation_id + ":started",
        )
        try:
            result = action()
        except Exception as exc:
            self.operation_ledger.append(
                operation,
                "failed",
                actor=actor,
                scope=scope,
                details={
                    "request": request,
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                },
                operation_id=operation_id + ":failed",
            )
            raise
        self.operation_ledger.append(
            operation,
            "completed",
            actor=actor,
            scope=scope,
            details={"request": request, "result": summarize(result)},
            operation_id=operation_id + ":completed",
        )
        return result

    @staticmethod
    def _actor(actor: AuthenticatedActor | dict[str, Any] | str | None) -> dict[str, Any] | str | None:
        return actor.to_dict() if isinstance(actor, AuthenticatedActor) else actor

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
        capability_values = tuple(capabilities)
        role_values = tuple(roles)
        return self._ledgered(
            "host.credential.register",
            actor=created_by,
            scope={"host_id": host_id, "actor_id": actor_id},
            request={
                "capabilities": sorted(set(capability_values)),
                "roles": sorted(set(role_values)),
                "expires_at": expires_at,
            },
            action=lambda: super(Runtime, self).register_host_credential(
                actor_id,
                host_id,
                capability_values,
                roles=role_values,
                created_by=created_by,
                expires_at=expires_at,
            ),
            summarize=lambda value: {
                "credential": value.get("credential"),
                "secret_visible_once": value.get("secret_visible_once"),
            },
        )

    def revoke_host_credential(
        self,
        credential_id: str,
        *,
        actor: str,
        reason: str,
    ) -> dict[str, Any]:
        return self._ledgered(
            "host.credential.revoke",
            actor=actor,
            scope={"credential_id": credential_id},
            request={"reason": reason},
            action=lambda: super(Runtime, self).revoke_host_credential(
                credential_id,
                actor=actor,
                reason=reason,
            ),
            summarize=lambda value: {
                "credential_id": value.get("credential_id"),
                "status": value.get("status"),
                "revoked_at": value.get("revoked_at"),
            },
        )

    def rotate_host_credential(
        self,
        credential_id: str,
        *,
        actor: str,
        reason: str = "credential rotation",
    ) -> dict[str, Any]:
        return self._ledgered(
            "host.credential.rotate",
            actor=actor,
            scope={"credential_id": credential_id},
            request={"reason": reason},
            action=lambda: super(Runtime, self).rotate_host_credential(
                credential_id,
                actor=actor,
                reason=reason,
            ),
            summarize=lambda value: {
                "replacement_credential": value.get("credential"),
                "replaces_credential_id": value.get("replaces_credential_id"),
                "secret_visible_once": value.get("secret_visible_once"),
            },
        )

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
        return self._ledgered(
            "task.lease.acquire",
            actor=actor.to_dict(),
            scope={"project": project, "task_id": task_id},
            request={
                "expected_task_etag": expected_task_etag,
                "ttl_seconds": ttl_seconds,
                "purpose": purpose,
            },
            action=lambda: super(Runtime, self).acquire_task_lease(
                project,
                task_id,
                bearer_token=bearer_token,
                expected_task_etag=expected_task_etag,
                ttl_seconds=ttl_seconds,
                purpose=purpose,
            ),
            summarize=lambda value: {
                "lease": value.get("lease"),
                "secret_visible_once": value.get("secret_visible_once"),
            },
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
        return self._ledgered(
            "task.lease.renew",
            actor=actor.to_dict(),
            scope={"project": project, "task_id": task_id},
            request={"expected_task_etag": expected_task_etag, "ttl_seconds": ttl_seconds},
            action=lambda: super(Runtime, self).renew_task_lease(
                project,
                task_id,
                bearer_token=bearer_token,
                lease_token=lease_token,
                expected_task_etag=expected_task_etag,
                ttl_seconds=ttl_seconds,
            ),
            summarize=lambda value: {
                "lease_id": value.get("lease_id"),
                "status": value.get("status"),
                "expires_at": value.get("expires_at"),
                "renewed_at": value.get("renewed_at"),
            },
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
        return self._ledgered(
            "task.lease.release",
            actor=actor.to_dict(),
            scope={"project": project, "task_id": task_id},
            request={"reason": reason},
            action=lambda: super(Runtime, self).release_task_lease(
                project,
                task_id,
                bearer_token=bearer_token,
                lease_token=lease_token,
                reason=reason,
            ),
            summarize=lambda value: {
                "lease_id": value.get("lease_id"),
                "status": value.get("status"),
                "released_at": value.get("released_at"),
            },
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
        actor = self.authenticate_actor(
            bearer_token,
            required_capabilities=("tool-result:submit",),
        )

        def summarize(task: Any) -> dict[str, Any]:
            callbacks = self.list_host_callbacks(project, task_id)
            callback = callbacks[-1] if callbacks else {}
            return {
                "callback_id": callback.get("callback_id"),
                "artifact_id": callback.get("artifact_id"),
                "task_status": task.status,
                "task_etag": self.get_task_etag(project, task_id),
            }

        return self._ledgered(
            "host.callback.submit",
            actor=actor.to_dict(),
            scope={
                "project": project,
                "task_id": task_id,
                "handoff_id": handoff_id,
            },
            request={
                "expected_task_etag": expected_task_etag,
                "filename": filename,
                "mime_type": mime_type,
                "content_sha256": content_sha256,
                "content_length": len(content),
                "width": width,
                "height": height,
                "model_id": model_id,
                "tool_id": tool_id,
                "request_id": request_id,
            },
            action=lambda: super(Runtime, self).submit_authenticated_tool_result(
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
            ),
            summarize=summarize,
        )

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
        return self._ledgered(
            "approval.decide",
            actor=actor.to_dict(),
            scope={
                "project": project,
                "task_id": task_id,
                "approval_id": approval_id,
            },
            request={"decision": decision, "expected_task_etag": expected_task_etag},
            action=lambda: super(Runtime, self).decide_approval_authenticated(
                project,
                task_id,
                approval_id,
                decision,
                bearer_token=bearer_token,
                lease_token=lease_token,
                expected_task_etag=expected_task_etag,
                comment=comment,
            ),
            summarize=lambda task: {
                "decision": decision,
                "approval_status": task.state.get("approval_state", {}).get("status"),
                "task_etag": self.get_task_etag(project, task_id),
            },
        )

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
        return self._ledgered(
            "export.execute",
            actor=actor.to_dict(),
            scope={"project": project, "task_id": task_id},
            request={
                "expected_task_etag": expected_task_etag,
                "target_engine": target_engine,
            },
            action=lambda: super(Runtime, self).execute_gated_export_authenticated(
                project,
                task_id,
                bearer_token=bearer_token,
                lease_token=lease_token,
                expected_task_etag=expected_task_etag,
                target_engine=target_engine,
            ),
            summarize=lambda value: {
                "export_id": value.get("export_id"),
                "status": value.get("status"),
                "target_engine": value.get("target_engine"),
                "transaction": value.get("transaction"),
            },
        )

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
        return self._ledgered(
            "export.rollback",
            actor=actor.to_dict(),
            scope={"project": project, "task_id": task_id, "export_id": export_id},
            request={
                "expected_task_etag": expected_task_etag,
                "reason": reason,
                "force": force,
            },
            action=lambda: super(Runtime, self).rollback_gated_export_authenticated(
                project,
                task_id,
                export_id,
                bearer_token=bearer_token,
                lease_token=lease_token,
                expected_task_etag=expected_task_etag,
                reason=reason,
                force=force,
            ),
            summarize=lambda value: {
                "export_id": value.get("export_id"),
                "status": value.get("status"),
                "rollback": value.get("rollback"),
            },
        )

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
        return self._ledgered(
            "git.change.prepare",
            actor=actor.to_dict(),
            scope={"project": project, "task_id": task_id, "export_id": export_id},
            request={
                "expected_task_etag": expected_task_etag,
                "branch_name": branch_name,
            },
            action=lambda: super(Runtime, self).prepare_export_git_change(
                project,
                task_id,
                export_id,
                bearer_token=bearer_token,
                expected_task_etag=expected_task_etag,
                branch_name=branch_name,
                message=message,
            ),
            summarize=lambda value: {
                "change_set_id": value.get("change_set_id"),
                "status": value.get("status"),
                "branch": value.get("branch"),
                "base_head": value.get("base_head"),
            },
        )

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
        return self._ledgered(
            "git.change.commit",
            actor=actor.to_dict(),
            scope={
                "project": project,
                "task_id": task_id,
                "change_set_id": change_set_id,
            },
            request={"expected_task_etag": expected_task_etag},
            action=lambda: super(Runtime, self).execute_git_change(
                project,
                task_id,
                change_set_id,
                bearer_token=bearer_token,
                lease_token=lease_token,
                expected_task_etag=expected_task_etag,
            ),
            summarize=lambda value: {
                "change_set_id": value.get("change_set_id"),
                "status": value.get("status"),
                "commit": value.get("commit"),
            },
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
        return self._ledgered(
            "git.change.revert",
            actor=actor.to_dict(),
            scope={
                "project": project,
                "task_id": task_id,
                "change_set_id": change_set_id,
            },
            request={"expected_task_etag": expected_task_etag, "reason": reason},
            action=lambda: super(Runtime, self).revert_git_change(
                project,
                task_id,
                change_set_id,
                bearer_token=bearer_token,
                lease_token=lease_token,
                expected_task_etag=expected_task_etag,
                reason=reason,
            ),
            summarize=lambda value: {
                "change_set_id": value.get("change_set_id"),
                "status": value.get("status"),
                "revert": value.get("revert"),
            },
        )

    def verify_operation_ledger(self) -> dict[str, Any]:
        return self.operation_ledger.verify()

    def operation_ledger_descriptor(self) -> dict[str, Any]:
        return self.operation_ledger.descriptor()

    def list_operation_ledger(
        self,
        *,
        limit: int = 100,
        operations: Iterable[str] = (),
    ) -> tuple[dict[str, Any], ...]:
        return self.operation_ledger.list(limit=limit, operations=operations)

    def operation_summary(self, project: str, task_id: str) -> dict[str, Any]:
        value = super().operation_summary(project, task_id)
        value["operation_ledger"] = self.operation_ledger.descriptor()
        value["operation_ledger_verification"] = self.operation_ledger.verify()
        return value


__all__ = ["Runtime"]
