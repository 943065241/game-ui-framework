from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from guif.approval import approval_summary, mark_provider_executed
from guif.artifacts import bind_references, register_artifact
from guif.providers.base import ExecutionRequest, ExecutionResult
from guif.runtime.store import TaskStore
from guif.runtime.task import Task
from guif.semantic_qa import build_semantic_qa_report, validate_semantic_qa_report
from guif.tools import (
    HostProfile,
    ToolRegistry,
    ToolRequest,
    ToolResult,
    bind_project_tool,
    build_default_chatgpt_host,
    build_default_tool_registry,
    load_execution_settings,
)


class ToolExecutionError(RuntimeError):
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


def _replace_output(task: Task, output_type: str, value: Any, *, agent: str) -> None:
    for output in reversed(task.outputs):
        if isinstance(output, dict) and output.get("type") == output_type:
            output["value"] = value
            output["agent"] = agent
            return
    task.add_output(output_type, value, agent=agent)


def _refresh_qa(task: Task, *, reason: str) -> None:
    required = ("plan", "direction", "theme_contract", "resource_contracts", "prompt_ir")
    if not all(isinstance(task.state.get(name), dict) for name in required):
        return
    report = build_semantic_qa_report(task)
    errors = validate_semantic_qa_report(report)
    if errors:
        raise ValueError("Tool transition produced invalid Semantic QA report: " + "; ".join(errors))
    task.state["qa_report"] = report
    _replace_output(task, "semantic-qa-report", report, agent="qa")
    task.state.setdefault("agents", {}).setdefault("qa", {}).update(
        {
            "status": "completed",
            "implementation": "semantic-contract-qa",
            "qa_schema_version": report["schema_version"],
            "qa_status": report["status"],
            "check_count": report["summary"]["check_count"],
            "blocking_finding_count": report["summary"]["blocking_finding_count"],
            "artifact_review_status": report["artifact_review"]["status"],
            "export_allowed": report["export_gate"]["allowed"],
        }
    )
    task.record("qa", "refreshed", f"Semantic QA refreshed after {reason} with status {report['status']}.")


def _required_capabilities(job: dict[str, Any]) -> tuple[str, ...]:
    values = ["image-generation"]
    if job.get("operation") == "edit":
        values.extend(("image-editing", "protected-region-editing"))
    output_contract = job.get("output_contract") if isinstance(job.get("output_contract"), dict) else {}
    if output_contract.get("alpha_required") is True:
        values.append("transparent-output")
    return tuple(sorted(set(values)))


def _primary_capability(job: dict[str, Any]) -> str:
    return "image-editing" if job.get("operation") == "edit" else "image-generation"


def _execution_state(task: Task) -> dict[str, Any]:
    state = task.state.get("provider_executions")
    if not isinstance(state, dict):
        state = {
            "schema_version": 2,
            "task_id": task.task_id,
            "project": task.project,
            "attempts": [],
            "latest_by_job": {},
            "updated_at": _now(),
        }
        task.state["provider_executions"] = state
    return state


def _handoff_state(task: Task) -> dict[str, Any]:
    state = task.state.get("tool_handoffs")
    if not isinstance(state, dict):
        state = {
            "schema_version": 1,
            "task_id": task.task_id,
            "project": task.project,
            "records": [],
            "latest_by_job": {},
            "updated_at": _now(),
        }
        task.state["tool_handoffs"] = state
    return state


def _legacy_request(request: ToolRequest) -> ExecutionRequest:
    return ExecutionRequest(
        execution_id=request.execution_id,
        task_id=request.task_id,
        project=request.project,
        job_id=request.job_id,
        provider_id=request.tool_id,
        required_capabilities=request.required_capabilities,
        job=dict(request.job),
        references=request.references,
        approval_snapshot=dict(request.approval_snapshot),
    )


def _legacy_result(result: ToolResult) -> ExecutionResult:
    metadata = dict(result.metadata)
    metadata.setdefault("tool_id", result.tool_id)
    return ExecutionResult(
        provider_id=result.tool_id,
        request_id=result.request_id,
        content=result.content,
        filename=result.filename,
        mime_type=result.mime_type,
        width=result.width,
        height=result.height,
        model_id=result.model_id,
        simulation=result.simulation,
        visual=result.visual,
        metadata=metadata,
    )


class ToolExecutionService:
    def __init__(
        self,
        workspace: Path,
        *,
        store: TaskStore | None = None,
        tools: ToolRegistry | None = None,
        host: HostProfile | None = None,
    ) -> None:
        self.workspace = workspace
        self.store = store or TaskStore(workspace)
        self.tools = tools or build_default_tool_registry()
        self.host = host or build_default_chatgpt_host()

    def list_tools(self) -> tuple[dict[str, Any], ...]:
        return self.tools.describe()

    def tool_health(
        self,
        tool_id: str,
        *,
        project: str | None = None,
        mode: str | None = None,
        explicit: bool = False,
    ) -> dict[str, Any]:
        resolved_mode = mode or (
            load_execution_settings(self.workspace, project).mode if project else "production"
        )
        return self.tools.get(tool_id).health_check(
            self.host,
            mode=resolved_mode,
            explicit=explicit,
        ).to_dict()

    def bind_project_tool(self, project: str, capability: str, tool_id: str) -> Path:
        if self.tools.find(tool_id) is None:
            raise ValueError(f"Cannot bind unregistered Tool: {tool_id}")
        return bind_project_tool(self.workspace, project, capability, tool_id)

    def _load_job(self, task: Task, job_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        if task.status not in {"completed", "waiting-for-tool"}:
            raise ValueError(
                "Tool execution requires a completed Task or a Task waiting for Tool configuration"
            )
        prompt_ir = task.state.get("prompt_ir")
        if not isinstance(prompt_ir, dict):
            raise ValueError("Task does not contain Prompt IR")
        approval_state = approval_summary(task)
        if prompt_ir.get("status") != "ready":
            raise ValueError(f"Prompt IR is not ready for execution: {prompt_ir.get('status')}")
        if approval_state.get("status") not in {"approved", "not-required"}:
            raise ValueError(f"Approval gate is not satisfied: {approval_state.get('status')}")
        jobs = {
            str(item.get("id")): item
            for item in prompt_ir.get("jobs", [])
            if isinstance(item, dict) and item.get("id")
        }
        if job_id not in jobs:
            raise ValueError(f"Unknown Prompt job: {job_id}")
        job = jobs[job_id]
        if job.get("executable") is not True:
            raise ValueError(f"Prompt job is not executable: {job_id}")
        qa_report = task.state.get("qa_report")
        if not isinstance(qa_report, dict) or qa_report.get("status") != "passed":
            raise ValueError("Tool execution requires passing Contract QA")
        return prompt_ir, approval_state, job

    def prepare_or_execute(
        self,
        project: str,
        task_id: str,
        job_id: str,
        *,
        tool_id: str | None = None,
    ) -> Task:
        task = self.store.load(project, task_id)
        prompt_ir, approval_state, job = self._load_job(task, job_id)
        settings = load_execution_settings(
            self.workspace,
            project,
            task_overrides=task.state.get("execution_overrides")
            if isinstance(task.state.get("execution_overrides"), dict)
            else None,
        )
        required = _required_capabilities(job)
        capability = _primary_capability(job)
        resolution = self.tools.resolve(
            capability=capability,
            required_capabilities=required,
            host=self.host,
            mode=settings.mode,
            explicit_tool_id=tool_id,
            task_tools=settings.task_tools,
            project_tools=settings.project_tools,
            workspace_tools=settings.workspace_tools,
        )
        resolution_payload = {
            **resolution.to_dict(),
            "job_id": job_id,
            "settings": settings.to_dict(),
            "updated_at": _now(),
        }
        task.state["tool_resolution"] = resolution_payload
        if resolution.status != "ready" or not resolution.selected_tool_id:
            task.wait_for_tool(resolution.reason)
            self.store.save(task)
            return task

        selected = self.tools.get(resolution.selected_tool_id)
        references = bind_references(
            task,
            [item for item in job.get("references", []) if isinstance(item, dict)],
        )
        if selected.requires_bound_references:
            unbound = [
                str(item.get("resource_id") or "reference")
                for item in references
                if item.get("status") != "bound"
            ]
            if unbound:
                resolution_payload.update(
                    {
                        "status": "waiting-for-tool",
                        "reason": "Tool requires bound reference files: " + ", ".join(unbound),
                        "waiting_state": "waiting-for-configuration",
                    }
                )
                task.wait_for_tool(resolution_payload["reason"])
                self.store.save(task)
                return task

        execution_state = _execution_state(task)
        attempts = execution_state.setdefault("attempts", [])
        latest_by_job = execution_state.setdefault("latest_by_job", {})
        if not isinstance(attempts, list) or not isinstance(latest_by_job, dict):
            raise ValueError("Invalid persisted Tool execution state")
        attempt_number = 1 + sum(
            1
            for item in attempts
            if isinstance(item, dict)
            and item.get("job_id") == job_id
            and item.get("tool_id", item.get("provider_id")) == selected.tool_id
        )
        approval_snapshot = {
            "status": approval_state.get("status"),
            "approved_ids": list(approval_state.get("approved_ids", [])),
            "required_ids": list(approval_state.get("required_ids", [])),
            "prompt_status": prompt_ir.get("status"),
        }
        execution_id = "exec-" + _canonical_hash(
            {
                "task_id": task.task_id,
                "job_id": job_id,
                "tool_id": selected.tool_id,
                "host_id": self.host.host_id,
                "attempt": attempt_number,
                "job": job,
                "approval": approval_snapshot,
            }
        )[:16]
        request = ToolRequest(
            execution_id=execution_id,
            task_id=task.task_id,
            project=task.project,
            job_id=job_id,
            tool_id=selected.tool_id,
            host_id=self.host.host_id,
            mode=settings.mode,
            required_capabilities=required,
            job=dict(job),
            references=references,
            approval_snapshot=approval_snapshot,
        )
        attempt: dict[str, Any] = {
            "schema_version": 2,
            "execution_id": execution_id,
            "job_id": job_id,
            "tool_id": selected.tool_id,
            "provider_id": selected.tool_id,
            "host_id": self.host.host_id,
            "execution_mode": selected.manifest.execution_mode,
            "attempt": attempt_number,
            "status": "preparing",
            "request": request.to_dict(),
            "started_at": _now(),
            "completed_at": None,
            "handoff_id": None,
            "artifact_id": None,
            "error": None,
        }
        attempts.append(attempt)
        latest_by_job[job_id] = execution_id
        execution_state["updated_at"] = _now()

        if selected.manifest.execution_mode == "external-callback":
            try:
                handoff = selected.prepare(request, self.host)
            except Exception as exc:
                attempt["status"] = "failed"
                attempt["completed_at"] = _now()
                attempt["error"] = {"type": type(exc).__name__, "message": str(exc)}
                execution_state["updated_at"] = _now()
                self.store.save(task)
                raise ToolExecutionError(
                    f"Tool {selected.tool_id} failed to prepare handoff for {job_id}: {exc}"
                ) from exc
            state = _handoff_state(task)
            records = state.setdefault("records", [])
            latest = state.setdefault("latest_by_job", {})
            if not isinstance(records, list) or not isinstance(latest, dict):
                raise ValueError("Invalid persisted Tool handoff state")
            handoff_payload = handoff.to_dict()
            records.append(handoff_payload)
            latest[job_id] = handoff.handoff_id
            state["updated_at"] = _now()
            attempt["status"] = "waiting-for-result"
            attempt["handoff_id"] = handoff.handoff_id
            resolution_payload["status"] = "waiting-for-result"
            resolution_payload["handoff_id"] = handoff.handoff_id
            task.wait_for_tool_result(
                f"Prepared {selected.tool_id} handoff {handoff.handoff_id}; waiting for Host result submission."
            )
            task.add_output("tool-handoff", handoff_payload, agent="tool-router")
            self.store.save(task)
            return task

        task.record("tool", "started", f"Executing {job_id} with Tool {selected.tool_id}.")
        self.store.save(task)
        try:
            result = selected.execute(request)
            if result.tool_id != selected.tool_id:
                raise ValueError(
                    f"Tool result identity mismatch: expected {selected.tool_id}, got {result.tool_id}"
                )
            artifact = register_artifact(
                task,
                self.store.run_dir(project, task_id),
                _legacy_request(request),
                _legacy_result(result),
            )
        except Exception as exc:
            attempt["status"] = "failed"
            attempt["completed_at"] = _now()
            attempt["error"] = {"type": type(exc).__name__, "message": str(exc)}
            execution_state["updated_at"] = _now()
            task.record("tool", "failed", f"Tool {selected.tool_id} failed for {job_id}: {exc}")
            self.store.save(task)
            raise ToolExecutionError(
                f"Tool {selected.tool_id} failed for job {job_id}: {exc}"
            ) from exc

        self._complete_attempt(task, attempt, execution_state, artifact, result.metadata_dict())
        task.restore_completed(
            f"Tool {selected.tool_id} registered Artifact {artifact['artifact_id']} for {job_id}."
        )
        _refresh_qa(task, reason="Tool Artifact registration")
        self.store.save(task)
        return task

    @staticmethod
    def _complete_attempt(
        task: Task,
        attempt: dict[str, Any],
        execution_state: dict[str, Any],
        artifact: dict[str, Any],
        result_metadata: dict[str, Any],
    ) -> None:
        tool_id = str(attempt.get("tool_id") or attempt.get("provider_id"))
        attempt["status"] = "completed"
        attempt["completed_at"] = _now()
        attempt["artifact_id"] = artifact["artifact_id"]
        attempt["result"] = result_metadata
        execution_state["updated_at"] = _now()
        mark_provider_executed(task, str(attempt["execution_id"]), tool_id)
        if not any(
            isinstance(output, dict)
            and output.get("type") == "artifact-record"
            and isinstance(output.get("value"), dict)
            and output["value"].get("artifact_id") == artifact["artifact_id"]
            for output in task.outputs
        ):
            task.add_output("artifact-record", artifact, agent=f"tool:{tool_id}")

    def submit_result(
        self,
        project: str,
        task_id: str,
        handoff_id: str,
        *,
        content: bytes,
        filename: str,
        mime_type: str,
        width: int | None = None,
        height: int | None = None,
        model_id: str | None = None,
        tool_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Task:
        if not content:
            raise ValueError("Submitted Tool result file must not be empty")
        task = self.store.load(project, task_id)
        state = task.state.get("tool_handoffs")
        if not isinstance(state, dict):
            raise ValueError("Task does not contain Tool handoffs")
        records = state.get("records", [])
        handoff = next(
            (
                item
                for item in records
                if isinstance(item, dict) and item.get("handoff_id") == handoff_id
            ),
            None,
        )
        if not isinstance(handoff, dict):
            raise ValueError(f"Unknown Tool handoff: {handoff_id}")
        if handoff.get("status") != "waiting-for-result":
            raise ValueError(f"Tool handoff is not waiting for a result: {handoff.get('status')}")
        expected_tool_id = str(handoff.get("tool_id") or "")
        submitted_tool_id = tool_id or expected_tool_id
        if submitted_tool_id != expected_tool_id:
            raise ValueError(
                f"Tool result identity mismatch: expected {expected_tool_id}, got {submitted_tool_id}"
            )
        request_payload = handoff.get("request")
        if not isinstance(request_payload, dict):
            raise ValueError("Persisted Tool handoff request is invalid")
        request = ToolRequest(
            execution_id=str(request_payload["execution_id"]),
            task_id=str(request_payload["task_id"]),
            project=str(request_payload["project"]),
            job_id=str(request_payload["job_id"]),
            tool_id=str(request_payload["tool_id"]),
            host_id=str(request_payload["host_id"]),
            mode=str(request_payload["mode"]),
            required_capabilities=tuple(request_payload.get("required_capabilities", [])),
            job=dict(request_payload.get("job", {})),
            references=tuple(request_payload.get("references", [])),
            approval_snapshot=dict(request_payload.get("approval_snapshot", {})),
        )
        result = ToolResult(
            tool_id=submitted_tool_id,
            request_id=handoff_id,
            content=content,
            filename=filename,
            mime_type=mime_type,
            width=width,
            height=height,
            model_id=model_id,
            simulation=False,
            visual=mime_type.lower().startswith("image/"),
            metadata={
                **dict(metadata or {}),
                "execution_mode": "external-callback",
                "host_id": handoff.get("host_id"),
                "handoff_id": handoff_id,
                "external_result_submitted": True,
            },
        )
        artifact = register_artifact(
            task,
            self.store.run_dir(project, task_id),
            _legacy_request(request),
            _legacy_result(result),
        )
        execution_state = _execution_state(task)
        attempts = execution_state.get("attempts", [])
        attempt = next(
            (
                item
                for item in reversed(attempts)
                if isinstance(item, dict) and item.get("handoff_id") == handoff_id
            ),
            None,
        )
        if not isinstance(attempt, dict):
            raise ValueError("Tool handoff has no matching execution attempt")
        self._complete_attempt(task, attempt, execution_state, artifact, result.metadata_dict())
        handoff["status"] = "completed"
        handoff["completed_at"] = _now()
        handoff["artifact_id"] = artifact["artifact_id"]
        handoff["result"] = result.metadata_dict()
        state["updated_at"] = _now()
        resolution = task.state.get("tool_resolution")
        if isinstance(resolution, dict):
            resolution["status"] = "completed"
            resolution["artifact_id"] = artifact["artifact_id"]
            resolution["updated_at"] = _now()
        task.restore_completed(
            f"Host submitted Artifact {artifact['artifact_id']} for Tool handoff {handoff_id}."
        )
        _refresh_qa(task, reason="external Tool result submission")
        self.store.save(task)
        return task

    def list_handoffs(self, project: str, task_id: str) -> tuple[dict[str, Any], ...]:
        task = self.store.load(project, task_id)
        state = task.state.get("tool_handoffs")
        if not isinstance(state, dict):
            return ()
        return tuple(item for item in state.get("records", []) if isinstance(item, dict))

    def get_resolution(self, project: str, task_id: str) -> dict[str, Any]:
        task = self.store.load(project, task_id)
        state = task.state.get("tool_resolution")
        return dict(state) if isinstance(state, dict) else {
            "schema_version": 1,
            "status": "not-requested",
            "task_id": task_id,
            "project": project,
        }

    def cancel_wait(self, project: str, task_id: str, *, reason: str) -> Task:
        task = self.store.load(project, task_id)
        if task.status not in {"waiting-for-tool", "waiting-for-tool-result"}:
            raise ValueError(f"Task is not waiting for a Tool: {task.status}")
        task.cancel(reason)
        resolution = task.state.get("tool_resolution")
        if isinstance(resolution, dict):
            resolution["status"] = "cancelled"
            resolution["reason"] = reason
            resolution["updated_at"] = _now()
        self.store.save(task)
        return task
