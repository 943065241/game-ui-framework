from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable
from uuid import uuid4

from guif.chatgpt_host_loop import ChatGPTHostLoop
from guif.private_data import PrivateDataLayout
from guif.runtime import Runtime, ThemeResolutionRequired

CONVERSATION_WORKFLOW_SCHEMA_VERSION = 1
CONVERSATION_VIEW_SCHEMA_VERSION = 1


class ConversationWorkflowError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _safe_identity(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized or Path(normalized).name != normalized:
        raise ValueError(f"Invalid {label}: {value}")
    return normalized


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


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ConversationWorkflowError(f"Expected Conversation Workflow object: {path}")
    return value


class ConversationWorkflowStore:
    """Private persisted conversation state. Low-level Task identities never enter Project Git."""

    def __init__(self, workspace: Path, *, data_root: Path | None = None) -> None:
        self.workspace = workspace.resolve()
        self.layout = PrivateDataLayout(self.workspace, data_root)

    def _project_dir(self, project: str) -> Path:
        return self.layout.conversation_workflows / _safe_identity(project, "project")

    def _path(self, project: str, conversation_id: str) -> Path:
        normalized = _safe_identity(conversation_id, "conversation_id")
        digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
        return self._project_dir(project) / f"conversation-{digest}.json"

    def get(self, project: str, conversation_id: str) -> dict[str, Any] | None:
        path = self._path(project, conversation_id)
        return _read_json(path) if path.is_file() else None

    def save(self, record: dict[str, Any]) -> dict[str, Any]:
        project = str(record.get("project") or "")
        conversation_id = str(record.get("conversation_id") or "")
        record["schema_version"] = CONVERSATION_WORKFLOW_SCHEMA_VERSION
        record["updated_at"] = _now()
        _write_json(self._path(project, conversation_id), record)
        return record

    def create(self, project: str, conversation_id: str) -> dict[str, Any]:
        normalized_project = _safe_identity(project, "project")
        normalized_conversation = _safe_identity(conversation_id, "conversation_id")
        existing = self.get(normalized_project, normalized_conversation)
        if existing is not None:
            return existing
        timestamp = _now()
        return self.save(
            {
                "schema_version": CONVERSATION_WORKFLOW_SCHEMA_VERSION,
                "conversation_id": normalized_conversation,
                "project": normalized_project,
                "status": "active",
                "continue_unbound": False,
                "active_task_id": None,
                "request_records": {},
                "checkpoint": None,
                "history": [
                    {
                        "event": "conversation-opened",
                        "recorded_at": timestamp,
                    }
                ],
                "created_at": timestamp,
                "updated_at": timestamp,
            }
        )

    def list(self, project: str) -> tuple[dict[str, Any], ...]:
        root = self._project_dir(project)
        if not root.is_dir():
            return ()
        records: list[dict[str, Any]] = []
        for path in sorted(root.glob("conversation-*.json")):
            try:
                records.append(_read_json(path))
            except (OSError, ValueError, json.JSONDecodeError):
                continue
        records.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
        return tuple(records)


class ConversationWorkflowService:
    """Conversation-first facade that hides Task IDs, etags, leases, claims, and callbacks."""

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
        self.store = ConversationWorkflowStore(self.workspace, data_root=data_root)
        self.bearer_token = bearer_token

    def _session(self, project: str, conversation_id: str) -> dict[str, Any]:
        return self.store.create(project, conversation_id)

    def _require_token(self, capabilities: Iterable[str]) -> str:
        if not isinstance(self.bearer_token, str) or not self.bearer_token.strip():
            raise ConversationWorkflowError(
                "This production conversation action requires a configured GUIF Host bearer token"
            )
        self.runtime.authenticate_actor(
            self.bearer_token,
            required_capabilities=tuple(capabilities),
        )
        return self.bearer_token

    @staticmethod
    def _record(session: dict[str, Any], event: str, **details: Any) -> None:
        history = session.setdefault("history", [])
        if not isinstance(history, list):
            raise ConversationWorkflowError("Invalid Conversation Workflow history")
        history.append(
            {
                "event": event,
                "recorded_at": _now(),
                **details,
            }
        )
        if len(history) > 500:
            del history[:-500]

    def _find_recovery_task(self, project: str, conversation_id: str) -> str | None:
        matches: list[tuple[str, str]] = []
        for summary in self.runtime.list_tasks(project):
            task_id = summary.get("task_id")
            if not isinstance(task_id, str):
                continue
            try:
                task = self.runtime.load_task(project, task_id)
            except (FileNotFoundError, ValueError):
                continue
            binding = task.state.get("conversation_theme")
            workflow = task.state.get("conversation_workflow")
            bound_conversation = (
                binding.get("conversation_id") if isinstance(binding, dict) else None
            )
            workflow_conversation = (
                workflow.get("conversation_id") if isinstance(workflow, dict) else None
            )
            if conversation_id not in {bound_conversation, workflow_conversation}:
                continue
            matches.append((str(task.created_at or ""), task_id))
        matches.sort(reverse=True)
        return matches[0][1] if matches else None

    def _load_active_task(self, session: dict[str, Any]) -> Any | None:
        project = str(session["project"])
        conversation_id = str(session["conversation_id"])
        task_id = session.get("active_task_id")
        if isinstance(task_id, str):
            try:
                return self.runtime.load_task(project, task_id)
            except FileNotFoundError:
                pass
        recovered = self._find_recovery_task(project, conversation_id)
        if recovered is None:
            session["active_task_id"] = None
            return None
        if recovered != task_id:
            session["active_task_id"] = recovered
            self._record(session, "task-reference-recovered")
        return self.runtime.load_task(project, recovered)

    def _theme_view(self, project: str, conversation_id: str, session: dict[str, Any]) -> dict[str, Any]:
        resolution = self.runtime.prepare_conversation_theme(
            conversation_id,
            project=project,
        )
        if resolution.get("status") == "selected":
            return {
                "status": "selected",
                "name": resolution.get("selected_name"),
                "version": (resolution.get("selected_theme") or {}).get("version"),
                "privacy": "private",
            }
        if session.get("continue_unbound") is True:
            return {
                "status": "unbound",
                "name": None,
                "version": None,
                "privacy": "private",
            }
        return {
            "status": "confirmation-required",
            "name": None,
            "version": None,
            "privacy": "private",
            "candidates": [
                {
                    "choice_id": str(item.get("theme_id") or ""),
                    "name": item.get("name"),
                    "version": item.get("latest_version"),
                    "updated_at": item.get("updated_at"),
                }
                for item in resolution.get("candidates", [])
                if isinstance(item, dict)
            ],
        }

    @staticmethod
    def _attempts(task: Any) -> list[dict[str, Any]]:
        state = task.state.get("provider_executions")
        return [
            item
            for item in (state.get("attempts", []) if isinstance(state, dict) else [])
            if isinstance(item, dict)
        ]

    @staticmethod
    def _revision_jobs(task: Any) -> list[dict[str, Any]]:
        state = task.state.get("revision_execution")
        return [
            item
            for item in (state.get("jobs", []) if isinstance(state, dict) else [])
            if isinstance(item, dict)
        ]

    def _task_work(self, task: Any) -> list[dict[str, Any]]:
        return [
            item
            for item in self.runtime.list_host_work(
                task.project,
                statuses=("available", "claimed", "completed"),
                limit=1000,
            )
            if item.get("task_id") == task.task_id
        ]

    @staticmethod
    def _pending_initial_approvals(task: Any) -> list[str]:
        state = task.state.get("approval_state")
        if not isinstance(state, dict):
            return []
        return [str(item) for item in state.get("pending_ids", [])]

    @staticmethod
    def _pending_revision(task: Any) -> dict[str, Any] | None:
        state = task.state.get("revision_execution")
        approvals = state.get("approvals", {}) if isinstance(state, dict) else {}
        if not isinstance(approvals, dict):
            return None
        for revision_id, approval in approvals.items():
            if isinstance(approval, dict) and approval.get("status") in {
                "pending",
                "changes-requested",
                "rejected",
            }:
                return {"revision_id": str(revision_id), **approval}
        return None

    @staticmethod
    def _completed_export(task: Any) -> dict[str, Any] | None:
        state = task.state.get("gated_exports")
        records = state.get("records", []) if isinstance(state, dict) else []
        for item in reversed(records):
            if isinstance(item, dict) and item.get("status") == "completed":
                return item
        return None

    def _stage(self, session: dict[str, Any], task: Any | None) -> tuple[str, str, list[dict[str, Any]]]:
        project = str(session["project"])
        conversation_id = str(session["conversation_id"])
        theme = self._theme_view(project, conversation_id, session)
        if theme["status"] == "confirmation-required":
            return (
                "theme-confirmation",
                "请先从历史主题中选择、创建新主题，或明确本次不绑定主题。",
                [
                    {"action": "select-theme", "label": "选择历史主题"},
                    {"action": "create-theme", "label": "创建新主题"},
                    {"action": "continue-unbound", "label": "本次不绑定主题"},
                ],
            )
        if task is None:
            return (
                "ready-for-request",
                "主题已确认，可以直接描述需要设计或修改的界面。",
                [{"action": "submit-request", "label": "提交设计需求"}],
            )
        if task.status == "failed":
            return (
                "recoverable-error",
                "上一次处理在流水线中断，已保留检查点，可以从失败位置恢复。",
                [{"action": "retry", "label": "从检查点重试"}],
            )
        if task.status == "cancelled":
            return (
                "cancelled",
                "当前任务已取消，可以在同一对话中提交新的需求。",
                [{"action": "submit-request", "label": "提交新需求"}],
            )

        approval = task.state.get("approval_state")
        approval_status = approval.get("status") if isinstance(approval, dict) else None
        if approval_status == "pending":
            return (
                "approval-required",
                "方案与生成契约已经准备好，需要确认后才会调用图片工具。",
                [
                    {"action": "approve", "label": "批准并继续生成"},
                    {"action": "request-changes", "label": "要求修改方案"},
                    {"action": "reject", "label": "拒绝本次方案"},
                ],
            )
        if approval_status in {"rejected", "changes-requested"}:
            return (
                "changes-required",
                "当前方案未获批准，需要调整需求或提交新的设计请求。",
                [{"action": "submit-request", "label": "提交调整后的需求"}],
            )

        pending_revision = self._pending_revision(task)
        if pending_revision is not None:
            status = pending_revision.get("status")
            if status == "pending":
                return (
                    "revision-approval-required",
                    "视觉检查提出了返修建议，需要单独批准后才会修改原图。",
                    [
                        {"action": "approve", "label": "批准返修并继续"},
                        {"action": "request-changes", "label": "调整返修要求"},
                        {"action": "reject", "label": "拒绝返修"},
                    ],
                )
            return (
                "revision-changes-required",
                "返修方案尚未获准，原图仍保持有效。",
                [{"action": "submit-request", "label": "补充修改要求"}],
            )

        ready_revision = next(
            (item for item in self._revision_jobs(task) if item.get("status") == "ready"),
            None,
        )
        if ready_revision is not None:
            return (
                "revision-ready",
                "返修已经批准，可以调用图片编辑工具。",
                [{"action": "continue", "label": "开始返修"}],
            )

        work = self._task_work(task)
        active_work = [item for item in work if item.get("status") in {"available", "claimed"}]
        if any(item.get("kind") == "visual-inspection" for item in active_work):
            return (
                "visual-review",
                "图片已经生成，正在等待语义视觉检查。",
                [{"action": "run-host", "label": "执行视觉检查"}],
            )
        if any(item.get("kind") in {"image-generation", "image-editing"} for item in active_work):
            return (
                "image-production",
                "已准备图片生成或修图任务，正在等待 Host 调用真实图片工具。",
                [{"action": "run-host", "label": "执行图片工具"}],
            )
        if task.status == "waiting-for-tool":
            return (
                "tool-configuration-required",
                "当前缺少可用工具或必要参考文件，配置完成后可以从这里继续。",
                [{"action": "retry", "label": "配置后重试"}],
            )
        if task.status == "waiting-for-tool-result":
            return (
                "image-production",
                "图片工具任务已发出，正在等待真实结果回传。",
                [{"action": "run-host", "label": "继续 Host 执行"}],
            )

        report = task.state.get("qa_report")
        export_gate = report.get("export_gate", {}) if isinstance(report, dict) else {}
        if self._completed_export(task) is not None:
            return (
                "completed",
                "图片已经通过检查并完成受控导出。",
                [{"action": "submit-request", "label": "继续新的设计需求"}],
            )
        if export_gate.get("allowed") is True:
            return (
                "ready-to-export",
                "图片已经通过契约与视觉检查，可以确认导出到项目。",
                [{"action": "export", "label": "确认并导出"}],
            )

        attempts = self._attempts(task)
        prompt_ir = task.state.get("prompt_ir")
        prompt_jobs = [
            item
            for item in (prompt_ir.get("jobs", []) if isinstance(prompt_ir, dict) else [])
            if isinstance(item, dict) and item.get("id")
        ]
        attempted_job_ids = {
            str(item.get("job_id"))
            for item in attempts
            if item.get("status") in {"completed", "waiting-for-result", "preparing"}
        }
        if approval_status in {"approved", "not-required"} and any(
            str(item["id"]) not in attempted_job_ids for item in prompt_jobs
        ):
            return (
                "ready-to-produce",
                "方案已批准，可以开始调用图片生成工具。",
                [{"action": "continue", "label": "开始生成"}],
            )

        return (
            "attention-required",
            "当前状态需要 Host 刷新或人工检查，所有已完成步骤和文件都已保留。",
            [{"action": "recover", "label": "重新同步状态"}],
        )

    def _public_view(
        self,
        session: dict[str, Any],
        *,
        include_diagnostics: bool = False,
    ) -> dict[str, Any]:
        task = self._load_active_task(session)
        stage, message, actions = self._stage(session, task)
        theme = self._theme_view(
            str(session["project"]),
            str(session["conversation_id"]),
            session,
        )
        artifact_records: list[dict[str, Any]] = []
        if task is not None:
            registry = task.state.get("artifact_registry")
            records = registry.get("records", []) if isinstance(registry, dict) else []
            for item in records:
                if not isinstance(item, dict):
                    continue
                file_data = item.get("file") if isinstance(item.get("file"), dict) else {}
                qa = item.get("qa") if isinstance(item.get("qa"), dict) else {}
                artifact_records.append(
                    {
                        "kind": item.get("artifact_kind"),
                        "operation": item.get("operation"),
                        "status": item.get("status"),
                        "review_status": qa.get("status"),
                        "mime_type": file_data.get("mime_type"),
                        "width": file_data.get("width"),
                        "height": file_data.get("height"),
                    }
                )
        checkpoint = {
            "stage": stage,
            "task_status": task.status if task is not None else None,
            "task_etag": self.runtime.get_task_etag(task.project, task.task_id)
            if task is not None
            else None,
            "artifact_count": len(artifact_records),
            "recorded_at": _now(),
        }
        session["checkpoint"] = checkpoint
        self.store.save(session)
        payload: dict[str, Any] = {
            "schema_version": CONVERSATION_VIEW_SCHEMA_VERSION,
            "conversation_id": session["conversation_id"],
            "project": session["project"],
            "status": "ready",
            "stage": stage,
            "message": message,
            "theme": theme,
            "actions": actions,
            "artifacts": artifact_records,
            "recovery": {
                "checkpoint_available": task is not None,
                "last_checkpoint_at": checkpoint["recorded_at"],
                "automatic_reconciliation": True,
            },
            "updated_at": session["updated_at"],
        }
        if include_diagnostics:
            payload["diagnostics"] = {
                "task_id": task.task_id if task is not None else None,
                "task_etag": checkpoint["task_etag"],
                "private_storage_root": str(self.store.layout.root),
            }
        return payload

    def open(
        self,
        project: str,
        conversation_id: str,
        *,
        include_diagnostics: bool = False,
    ) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        self._load_active_task(session)
        return self._public_view(session, include_diagnostics=include_diagnostics)

    def select_theme(
        self,
        project: str,
        conversation_id: str,
        theme_id: str,
        *,
        version: int | None = None,
        actor: str = "conversation-user",
    ) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        self.runtime.bind_conversation_theme(
            conversation_id,
            theme_id,
            version=version,
            actor=actor,
        )
        session["continue_unbound"] = False
        self._record(session, "theme-selected", version=version)
        self.store.save(session)
        return self._public_view(session)

    def create_theme(
        self,
        project: str,
        conversation_id: str,
        name: str,
        content: dict[str, Any],
        *,
        actor: str = "conversation-user",
    ) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        record = self.runtime.create_private_theme(
            name,
            content,
            actor=actor,
            conversation_id=conversation_id,
        )
        session["continue_unbound"] = False
        self._record(session, "theme-created", version=record.get("version"))
        self.store.save(session)
        return self._public_view(session)

    def derive_theme(
        self,
        project: str,
        conversation_id: str,
        theme_id: str,
        updates: dict[str, Any],
        *,
        from_version: int | None = None,
        name: str | None = None,
        actor: str = "conversation-user",
    ) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        record = self.runtime.derive_private_theme(
            theme_id,
            updates,
            from_version=from_version,
            actor=actor,
            conversation_id=conversation_id,
            name=name,
        )
        session["continue_unbound"] = False
        self._record(session, "theme-derived", version=record.get("version"))
        self.store.save(session)
        return self._public_view(session)

    def continue_unbound(self, project: str, conversation_id: str) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        session["continue_unbound"] = True
        self._record(session, "theme-unbound-confirmed")
        self.store.save(session)
        return self._public_view(session)

    def submit(
        self,
        project: str,
        conversation_id: str,
        requirement: str,
        *,
        pipeline: str = "ui-production",
        request_key: str | None = None,
    ) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        normalized_requirement = requirement.strip()
        if not normalized_requirement:
            raise ValueError("Requirement must not be empty")
        theme = self._theme_view(project, conversation_id, session)
        if theme["status"] == "confirmation-required":
            return self._public_view(session)
        normalized_key = request_key.strip() if isinstance(request_key, str) else ""
        if not normalized_key:
            normalized_key = "request-" + uuid4().hex
        if len(normalized_key) > 128:
            raise ValueError("request_key must be at most 128 characters")
        request_hash = _canonical_hash(
            {
                "project": project,
                "conversation_id": conversation_id,
                "requirement": normalized_requirement,
                "pipeline": pipeline,
            }
        )
        request_records = session.setdefault("request_records", {})
        if not isinstance(request_records, dict):
            raise ConversationWorkflowError("Invalid Conversation Workflow request records")
        existing = request_records.get(normalized_key)
        if isinstance(existing, dict):
            if existing.get("request_hash") != request_hash:
                raise ConversationWorkflowError(
                    "request_key was already used for a different conversation request"
                )
            task_id = existing.get("task_id")
            if isinstance(task_id, str):
                session["active_task_id"] = task_id
            self._record(session, "request-replayed", request_key=normalized_key)
            self.store.save(session)
            return self._public_view(session)

        try:
            task = self.runtime.run(
                project,
                normalized_requirement,
                pipeline=pipeline,
                conversation_id=conversation_id,
                continue_unbound=session.get("continue_unbound") is True,
            )
        except ThemeResolutionRequired:
            return self._public_view(session)
        task.state["conversation_workflow"] = {
            "schema_version": CONVERSATION_WORKFLOW_SCHEMA_VERSION,
            "conversation_id": conversation_id,
            "request_key": normalized_key,
            "request_hash": request_hash,
            "private_record": True,
        }
        self.runtime.store.save(task)
        request_records[normalized_key] = {
            "request_hash": request_hash,
            "task_id": task.task_id,
            "created_at": _now(),
        }
        session["active_task_id"] = task.task_id
        self._record(session, "request-submitted", request_key=normalized_key)
        self.store.save(session)
        return self._public_view(session)

    def _leased_action(
        self,
        task: Any,
        *,
        capabilities: tuple[str, ...],
        purpose: str,
        operation: str,
        request: dict[str, Any],
        action: Callable[[dict[str, Any]], Any],
        summarize: Callable[[Any], dict[str, Any]],
    ) -> Any:
        token = self._require_token(("task:lease", *capabilities))
        actor = self.runtime.authenticate_actor(token, required_capabilities=capabilities)
        etag = self.runtime.get_task_etag(task.project, task.task_id)
        issued = self.runtime.acquire_task_lease(
            task.project,
            task.task_id,
            bearer_token=token,
            expected_task_etag=etag,
            purpose=purpose,
        )
        lease_token = str(issued["lease_token"])
        lease = dict(issued["lease"])

        def execute() -> Any:
            result = action(
                {
                    "actor": actor,
                    "etag": etag,
                    "lease": lease,
                    "lease_token": lease_token,
                    "bearer_token": token,
                }
            )
            current = self.runtime.get_task_lease(task.project, task.task_id)
            if current.get("status") == "active":
                self.runtime.task_leases.consume(
                    task.project,
                    task.task_id,
                    lease_token,
                    actor,
                    operation_id=purpose,
                )
            return result

        try:
            ledgered = getattr(self.runtime, "_ledgered", None)
            if callable(ledgered):
                return ledgered(
                    operation,
                    actor=actor.to_dict(),
                    scope={"project": task.project, "task_id": task.task_id},
                    request=request,
                    action=execute,
                    summarize=summarize,
                )
            return execute()
        except Exception:
            current = self.runtime.get_task_lease(task.project, task.task_id)
            if current.get("status") == "active":
                self.runtime.release_task_lease(
                    task.project,
                    task.task_id,
                    bearer_token=token,
                    lease_token=lease_token,
                    reason=f"{purpose} failed",
                )
            raise

    def _execute_next(self, task: Any) -> Any:
        ready_revision = next(
            (item for item in self._revision_jobs(task) if item.get("status") == "ready"),
            None,
        )
        if ready_revision is not None:
            revision_id = str(ready_revision.get("revision", {}).get("revision_id") or "")
            return self._leased_action(
                task,
                capabilities=("tool:execute",),
                purpose=f"conversation-revision-execute:{revision_id}",
                operation="conversation.revision.execute",
                request={"revision_id": revision_id},
                action=lambda context: self.runtime.execute_revision(
                    task.project,
                    task.task_id,
                    revision_id,
                ),
                summarize=lambda value: {
                    "task_status": value.status,
                    "tool_resolution_status": (
                        value.state.get("tool_resolution", {}).get("status")
                        if isinstance(value.state.get("tool_resolution"), dict)
                        else None
                    ),
                },
            )

        prompt_ir = task.state.get("prompt_ir")
        jobs = [
            item
            for item in (prompt_ir.get("jobs", []) if isinstance(prompt_ir, dict) else [])
            if isinstance(item, dict) and item.get("id")
        ]
        attempts = self._attempts(task)
        attempted = {
            str(item.get("job_id"))
            for item in attempts
            if item.get("status") in {"completed", "waiting-for-result", "preparing"}
        }
        job = next((item for item in jobs if str(item["id"]) not in attempted), None)
        if not isinstance(job, dict):
            raise ConversationWorkflowError("No approved Prompt Job is ready for execution")
        job_id = str(job["id"])
        return self._leased_action(
            task,
            capabilities=("tool:execute",),
            purpose=f"conversation-tool-execute:{job_id}",
            operation="conversation.tool.execute",
            request={"job_id": job_id},
            action=lambda context: self.runtime.execute_job(
                task.project,
                task.task_id,
                job_id,
            ),
            summarize=lambda value: {
                "task_status": value.status,
                "tool_resolution_status": (
                    value.state.get("tool_resolution", {}).get("status")
                    if isinstance(value.state.get("tool_resolution"), dict)
                    else None
                ),
            },
        )

    def _decide_revision(
        self,
        task: Any,
        revision_id: str,
        decision: str,
        comment: str | None,
    ) -> Any:
        def action(context: dict[str, Any]) -> Any:
            actor = context["actor"]
            result = self.runtime.decide_revision(
                task.project,
                task.task_id,
                revision_id,
                decision,
                actor=actor.actor_id,
                comment=comment,
            )
            state = result.state.get("revision_execution")
            approvals = state.get("approvals", {}) if isinstance(state, dict) else {}
            approval = approvals.get(revision_id) if isinstance(approvals, dict) else None
            if isinstance(approval, dict):
                approval["authenticated_actor"] = actor.to_dict()
                approval["lease_id"] = context["lease"].get("lease_id")
            self.runtime.store.save(result)
            return result

        return self._leased_action(
            task,
            capabilities=("revision:decide",),
            purpose=f"conversation-revision-decision:{revision_id}:{decision}",
            operation="conversation.revision.decide",
            request={"revision_id": revision_id, "decision": decision},
            action=action,
            summarize=lambda value: {
                "task_status": value.status,
                "decision": decision,
            },
        )

    def decide(
        self,
        project: str,
        conversation_id: str,
        decision: str,
        *,
        comment: str | None = None,
    ) -> dict[str, Any]:
        normalized = decision.strip().lower()
        if normalized not in {"approved", "rejected", "changes-requested"}:
            raise ValueError("decision must be approved, rejected, or changes-requested")
        session = self._session(project, conversation_id)
        task = self._load_active_task(session)
        if task is None:
            raise ConversationWorkflowError("Conversation has no active production task")
        pending_revision = self._pending_revision(task)
        if pending_revision is not None and pending_revision.get("status") == "pending":
            revision_id = str(pending_revision["revision_id"])
            task = self._decide_revision(task, revision_id, normalized, comment)
            self._record(session, "revision-decision", decision=normalized)
            if normalized == "approved":
                task = self._execute_next(task)
        else:
            pending = self._pending_initial_approvals(task)
            if not pending:
                raise ConversationWorkflowError("Conversation has no pending approval")
            for approval_id in pending:
                current = self.runtime.load_task(project, task.task_id)
                token = self._require_token(("task:lease", "approval:decide"))
                etag = self.runtime.get_task_etag(project, task.task_id)
                issued = self.runtime.acquire_task_lease(
                    project,
                    task.task_id,
                    bearer_token=token,
                    expected_task_etag=etag,
                    purpose=f"conversation-approval:{approval_id}:{normalized}",
                )
                task = self.runtime.decide_approval_authenticated(
                    project,
                    task.task_id,
                    approval_id,
                    normalized,
                    bearer_token=token,
                    lease_token=str(issued["lease_token"]),
                    expected_task_etag=etag,
                    comment=comment,
                )
            self._record(session, "initial-decision", decision=normalized)
            if normalized == "approved":
                task = self._execute_next(task)
        self.store.save(session)
        return self._public_view(session)

    def approve(
        self,
        project: str,
        conversation_id: str,
        *,
        comment: str | None = None,
    ) -> dict[str, Any]:
        return self.decide(project, conversation_id, "approved", comment=comment)

    def request_changes(
        self,
        project: str,
        conversation_id: str,
        *,
        comment: str | None = None,
    ) -> dict[str, Any]:
        return self.decide(project, conversation_id, "changes-requested", comment=comment)

    def reject(
        self,
        project: str,
        conversation_id: str,
        *,
        comment: str | None = None,
    ) -> dict[str, Any]:
        return self.decide(project, conversation_id, "rejected", comment=comment)

    def continue_work(self, project: str, conversation_id: str) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        task = self._load_active_task(session)
        if task is None:
            raise ConversationWorkflowError("Conversation has no active production task")
        self._execute_next(task)
        self._record(session, "production-continued")
        self.store.save(session)
        return self._public_view(session)

    def run_host_until_blocked(
        self,
        project: str,
        conversation_id: str,
        *,
        image_executor: Callable[[dict[str, Any], tuple[dict[str, Any], ...]], dict[str, Any]]
        | None = None,
        visual_inspector: Callable[[dict[str, Any], tuple[dict[str, Any], ...]], dict[str, Any]]
        | None = None,
        max_steps: int = 10,
    ) -> dict[str, Any]:
        if max_steps < 1 or max_steps > 100:
            raise ValueError("max_steps must be between 1 and 100")
        token = self._require_token(
            (
                "host-work:read",
                "host-work:claim",
                "host-work:complete",
                "task:lease",
            )
        )
        session = self._session(project, conversation_id)
        task = self._load_active_task(session)
        if task is None:
            raise ConversationWorkflowError("Conversation has no active production task")
        loop = ChatGPTHostLoop(self.runtime, bearer_token=token)
        completed = 0
        receipts: list[dict[str, Any]] = []
        for _ in range(max_steps):
            receipt = loop.run_once(
                project,
                task_id=task.task_id,
                image_executor=image_executor,
                visual_inspector=visual_inspector,
            )
            if receipt is None:
                break
            receipts.append(receipt)
            completed += 1
            refreshed = self.runtime.load_task(project, task.task_id)
            stage, _, _ = self._stage(session, refreshed)
            if stage in {
                "approval-required",
                "revision-approval-required",
                "tool-configuration-required",
                "ready-to-export",
                "completed",
                "recoverable-error",
            }:
                break
        self._record(session, "host-loop-run", completed_steps=completed)
        session["last_host_receipts"] = [
            {
                "status": item.get("status"),
                "kind": item.get("kind"),
                "artifact_created": bool(item.get("artifact_id")),
                "revision_created": bool(item.get("revision_id")),
            }
            for item in receipts[-10:]
        ]
        self.store.save(session)
        return self._public_view(session)

    def export(
        self,
        project: str,
        conversation_id: str,
        *,
        target_engine: str | None = None,
    ) -> dict[str, Any]:
        token = self._require_token(("task:lease", "export:execute"))
        session = self._session(project, conversation_id)
        task = self._load_active_task(session)
        if task is None:
            raise ConversationWorkflowError("Conversation has no active production task")
        view = self._public_view(session)
        if view["stage"] != "ready-to-export":
            raise ConversationWorkflowError("Conversation is not ready for export")
        etag = self.runtime.get_task_etag(project, task.task_id)
        issued = self.runtime.acquire_task_lease(
            project,
            task.task_id,
            bearer_token=token,
            expected_task_etag=etag,
            purpose="conversation-gated-export",
        )
        record = self.runtime.execute_gated_export_authenticated(
            project,
            task.task_id,
            bearer_token=token,
            lease_token=str(issued["lease_token"]),
            expected_task_etag=etag,
            target_engine=target_engine,
        )
        self._record(
            session,
            "export-completed",
            target_engine=record.get("target_engine"),
        )
        self.store.save(session)
        return self._public_view(session)

    def recover(self, project: str, conversation_id: str) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        previous = session.get("active_task_id")
        task = self._load_active_task(session)
        self._record(
            session,
            "conversation-reconciled",
            task_recovered=task is not None and task.task_id != previous,
        )
        self.store.save(session)
        return self._public_view(session)

    def retry(self, project: str, conversation_id: str) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        task = self._load_active_task(session)
        if task is None:
            raise ConversationWorkflowError("Conversation has no active production task")
        if task.status == "failed":
            task = self._leased_action(
                task,
                capabilities=("task:resume",),
                purpose="conversation-task-resume",
                operation="conversation.task.resume",
                request={"resume_from": task.next_agent_index},
                action=lambda context: self.runtime.resume(project, task.task_id),
                summarize=lambda value: {
                    "task_status": value.status,
                    "next_agent_index": value.next_agent_index,
                },
            )
        elif task.status == "waiting-for-tool":
            task = self._execute_next(task)
        else:
            raise ConversationWorkflowError(
                f"Conversation task is not in a retryable state: {task.status}"
            )
        self._record(session, "conversation-retried")
        self.store.save(session)
        return self._public_view(session)

    def status(
        self,
        project: str,
        conversation_id: str,
        *,
        include_diagnostics: bool = False,
    ) -> dict[str, Any]:
        session = self._session(project, conversation_id)
        return self._public_view(session, include_diagnostics=include_diagnostics)


__all__ = [
    "CONVERSATION_VIEW_SCHEMA_VERSION",
    "CONVERSATION_WORKFLOW_SCHEMA_VERSION",
    "ConversationWorkflowError",
    "ConversationWorkflowService",
    "ConversationWorkflowStore",
]
