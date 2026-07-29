from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from guif.agents.builtin import build_default_agents
from guif.approval import approval_summary, decide_approval, mark_provider_executed
from guif.artifacts import bind_references, get_artifact, list_artifacts, register_artifact
from guif.providers import ExecutionRequest, ProviderRegistry, build_default_provider_registry
from guif.retrieval import select_relevant_context
from guif.runtime.context import load_runtime_context
from guif.runtime.pipeline import Pipeline
from guif.runtime.registry import AgentRegistry
from guif.runtime.store import TaskStore
from guif.runtime.task import Task
from guif.semantic_qa import build_semantic_qa_report, validate_semantic_qa_report
from guif.workflow import load_workflow


class RuntimeExecutionError(RuntimeError):
    pass


class ProviderExecutionError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class Runtime:
    def __init__(
        self,
        workspace: Path,
        *,
        registry: AgentRegistry | None = None,
        pipelines: dict[str, Pipeline] | None = None,
        store: TaskStore | None = None,
        providers: ProviderRegistry | None = None,
    ) -> None:
        self.workspace = workspace
        self.registry = registry or AgentRegistry(build_default_agents())
        self.pipelines = dict(pipelines or {})
        self.store = store or TaskStore(workspace)
        self.providers = providers or build_default_provider_registry()

    def _resolve_pipeline(self, project: str, name: str) -> Pipeline:
        configured = self.pipelines.get(name)
        if configured is not None:
            return configured
        try:
            workflow = load_workflow(self.workspace, project, name)
        except FileNotFoundError as exc:
            raise ValueError(f"Unknown pipeline: {name}") from exc
        return Pipeline.from_workflow(workflow)

    def _execute(self, task: Task, pipeline: Pipeline, *, start_index: int) -> Task:
        task.start()
        self.store.save(task)
        try:
            task = pipeline.execute(
                task,
                self.registry,
                start_index=start_index,
                checkpoint=self.store.save,
            )
        except Exception as exc:
            failed_agent = task.current_agent or "runtime"
            task.fail(failed_agent, exc)
            self.store.save(task)
            raise RuntimeExecutionError(f"Agent {failed_agent} failed: {exc}") from exc

        task.complete()
        task.record("runtime", "completed", f"Pipeline completed: {pipeline.name}")
        self.store.save(task)
        return task

    @staticmethod
    def _replace_output(task: Task, output_type: str, value: Any, *, agent: str) -> None:
        for output in reversed(task.outputs):
            if isinstance(output, dict) and output.get("type") == output_type:
                output["value"] = value
                output["agent"] = agent
                return
        task.add_output(output_type, value, agent=agent)

    def _refresh_qa(self, task: Task, *, reason: str) -> None:
        required = ("plan", "direction", "theme_contract", "resource_contracts", "prompt_ir")
        if not all(isinstance(task.state.get(name), dict) for name in required):
            return
        report = build_semantic_qa_report(task)
        errors = validate_semantic_qa_report(report)
        if errors:
            raise ValueError("State transition produced invalid Semantic QA report: " + "; ".join(errors))
        task.state["qa_report"] = report
        self._replace_output(task, "semantic-qa-report", report, agent="qa")
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
        task.record(
            "qa",
            "refreshed",
            f"Semantic QA refreshed after {reason} with status {report['status']}.",
        )

    @staticmethod
    def _execution_state(task: Task) -> dict[str, Any]:
        state = task.state.get("provider_executions")
        if not isinstance(state, dict):
            state = {
                "schema_version": 1,
                "task_id": task.task_id,
                "project": task.project,
                "attempts": [],
                "latest_by_job": {},
                "updated_at": _now(),
            }
            task.state["provider_executions"] = state
        return state

    @staticmethod
    def _required_capabilities(job: dict[str, Any]) -> tuple[str, ...]:
        values = ["image-generation"]
        if job.get("operation") == "edit":
            values.extend(("image-editing", "protected-region-editing"))
        output_contract = job.get("output_contract") if isinstance(job.get("output_contract"), dict) else {}
        if output_contract.get("alpha_required") is True:
            values.append("transparent-output")
        return tuple(sorted(set(values)))

    def run(self, project: str, requirement: str, *, pipeline: str = "ui-production") -> Task:
        normalized_requirement = requirement.strip()
        if not normalized_requirement:
            raise ValueError("Requirement must not be empty")
        resolved_pipeline = self._resolve_pipeline(project, pipeline)
        context = load_runtime_context(self.workspace, project)
        context_selection = select_relevant_context(context, normalized_requirement)
        task = Task(
            project=project,
            requirement=normalized_requirement,
            pipeline=resolved_pipeline.name,
            context=context,
        )
        task.state["pipeline"] = resolved_pipeline.to_dict()
        task.state["context_selection"] = context_selection
        selected_counts = {
            key: len(context_selection[key])
            for key in ("memory", "resources", "workflows")
        }
        task.record(
            "runtime",
            "started",
            f"Loaded project context, selected {selected_counts}, and resolved workflow {resolved_pipeline.name} for {project}",
        )
        return self._execute(task, resolved_pipeline, start_index=0)

    def resume(self, project: str, task_id: str) -> Task:
        task = self.store.load(project, task_id)
        if task.status == "completed":
            raise ValueError(f"Task is already completed: {task_id}")
        resolved_pipeline = self._resolve_pipeline(project, task.pipeline)
        stored_agents = tuple(task.state.get("pipeline", {}).get("agents", ()))
        if stored_agents and stored_agents != resolved_pipeline.agents:
            raise ValueError(
                "Workflow agents changed after the task was created; resume is unsafe. "
                f"stored={stored_agents}, current={resolved_pipeline.agents}"
            )
        task.state["pipeline"] = resolved_pipeline.to_dict()
        task.record(
            "runtime",
            "resumed",
            f"Resuming pipeline at agent index {task.next_agent_index} with the persisted Context selection",
        )
        return self._execute(task, resolved_pipeline, start_index=task.next_agent_index)

    def get_approvals(self, project: str, task_id: str) -> dict[str, Any]:
        task = self.store.load(project, task_id)
        summary = approval_summary(task)
        self.store.save(task)
        return summary

    def decide_approval(
        self,
        project: str,
        task_id: str,
        approval_id: str,
        decision: str,
        *,
        actor: str,
        comment: str | None = None,
    ) -> Task:
        task = self.store.load(project, task_id)
        decide_approval(
            task,
            approval_id,
            decision,
            actor=actor,
            comment=comment,
        )
        self._refresh_qa(task, reason="approval change")
        self.store.save(task)
        return task

    def approve(
        self,
        project: str,
        task_id: str,
        approval_id: str,
        *,
        actor: str,
        comment: str | None = None,
    ) -> Task:
        return self.decide_approval(
            project,
            task_id,
            approval_id,
            "approved",
            actor=actor,
            comment=comment,
        )

    def reject(
        self,
        project: str,
        task_id: str,
        approval_id: str,
        *,
        actor: str,
        comment: str | None = None,
    ) -> Task:
        return self.decide_approval(
            project,
            task_id,
            approval_id,
            "rejected",
            actor=actor,
            comment=comment,
        )

    def request_changes(
        self,
        project: str,
        task_id: str,
        approval_id: str,
        *,
        actor: str,
        comment: str | None = None,
    ) -> Task:
        return self.decide_approval(
            project,
            task_id,
            approval_id,
            "changes-requested",
            actor=actor,
            comment=comment,
        )

    def list_providers(self) -> tuple[dict[str, object], ...]:
        return self.providers.describe()

    def execute_job(
        self,
        project: str,
        task_id: str,
        job_id: str,
        *,
        provider_id: str = "dry-run",
    ) -> Task:
        task = self.store.load(project, task_id)
        if task.status != "completed":
            raise ValueError("Provider execution requires a completed Runtime Task")
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
            raise ValueError("Provider execution requires passing Contract QA")

        provider = self.providers.get(provider_id)
        required_capabilities = self._required_capabilities(job)
        missing = provider.missing_capabilities(required_capabilities)
        if missing:
            raise ValueError(
                f"Provider {provider_id} lacks required capabilities: {', '.join(missing)}"
            )
        references = bind_references(
            task,
            [item for item in job.get("references", []) if isinstance(item, dict)],
        )
        if provider.requires_bound_references:
            unbound = [
                str(item.get("resource_id") or "reference")
                for item in references
                if item.get("status") != "bound"
            ]
            if unbound:
                raise ValueError(
                    "Provider requires bound reference files: " + ", ".join(unbound)
                )

        execution_state = self._execution_state(task)
        attempts = execution_state.setdefault("attempts", [])
        latest_by_job = execution_state.setdefault("latest_by_job", {})
        if not isinstance(attempts, list) or not isinstance(latest_by_job, dict):
            raise ValueError("Invalid persisted Provider execution state")
        attempt_number = 1 + sum(
            1
            for item in attempts
            if isinstance(item, dict)
            and item.get("job_id") == job_id
            and item.get("provider_id") == provider_id
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
                "provider_id": provider_id,
                "attempt": attempt_number,
                "job": job,
                "approval": approval_snapshot,
            }
        )[:16]
        request = ExecutionRequest(
            execution_id=execution_id,
            task_id=task.task_id,
            project=task.project,
            job_id=job_id,
            provider_id=provider_id,
            required_capabilities=required_capabilities,
            job=dict(job),
            references=references,
            approval_snapshot=approval_snapshot,
        )
        attempt: dict[str, Any] = {
            "schema_version": 1,
            "execution_id": execution_id,
            "job_id": job_id,
            "provider_id": provider_id,
            "attempt": attempt_number,
            "status": "running",
            "request": request.to_dict(),
            "started_at": _now(),
            "completed_at": None,
            "artifact_id": None,
            "error": None,
        }
        attempts.append(attempt)
        latest_by_job[job_id] = execution_id
        execution_state["updated_at"] = _now()
        task.record("provider", "started", f"Executing {job_id} with Provider {provider_id}.")
        self.store.save(task)

        try:
            result = provider.execute(request)
            if result.provider_id != provider_id:
                raise ValueError(
                    f"Provider result identity mismatch: expected {provider_id}, got {result.provider_id}"
                )
            artifact = register_artifact(
                task,
                self.store.run_dir(project, task_id),
                request,
                result,
            )
        except Exception as exc:
            attempt["status"] = "failed"
            attempt["completed_at"] = _now()
            attempt["error"] = {"type": type(exc).__name__, "message": str(exc)}
            execution_state["updated_at"] = _now()
            task.record("provider", "failed", f"Provider {provider_id} failed for {job_id}: {exc}")
            self.store.save(task)
            raise ProviderExecutionError(
                f"Provider {provider_id} failed for job {job_id}: {exc}"
            ) from exc

        attempt["status"] = "completed"
        attempt["completed_at"] = _now()
        attempt["artifact_id"] = artifact["artifact_id"]
        attempt["result"] = result.metadata_dict()
        execution_state["updated_at"] = _now()
        mark_provider_executed(task, execution_id, provider_id)
        if not any(
            isinstance(output, dict)
            and output.get("type") == "artifact-record"
            and isinstance(output.get("value"), dict)
            and output["value"].get("artifact_id") == artifact["artifact_id"]
            for output in task.outputs
        ):
            task.add_output("artifact-record", artifact, agent=f"provider:{provider_id}")
        task.record(
            "provider",
            "completed",
            f"Provider {provider_id} registered Artifact {artifact['artifact_id']} for {job_id}.",
        )
        self._refresh_qa(task, reason="Artifact registration")
        self.store.save(task)
        return task

    def list_artifacts(self, project: str, task_id: str) -> tuple[dict[str, Any], ...]:
        return list_artifacts(self.store.load(project, task_id))

    def get_artifact(self, project: str, task_id: str, artifact_id: str) -> dict[str, Any]:
        return get_artifact(self.store.load(project, task_id), artifact_id)

    def load_task(self, project: str, task_id: str) -> Task:
        return self.store.load(project, task_id)

    def list_runs(self, project: str) -> tuple[dict[str, object], ...]:
        return self.store.list(project)
