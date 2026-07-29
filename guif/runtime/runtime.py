from __future__ import annotations

from pathlib import Path
from typing import Any

from guif.agents.builtin import build_default_agents
from guif.approval import approval_summary, decide_approval
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


class Runtime:
    def __init__(
        self,
        workspace: Path,
        *,
        registry: AgentRegistry | None = None,
        pipelines: dict[str, Pipeline] | None = None,
        store: TaskStore | None = None,
    ) -> None:
        self.workspace = workspace
        self.registry = registry or AgentRegistry(build_default_agents())
        self.pipelines = dict(pipelines or {})
        self.store = store or TaskStore(workspace)

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
                return
        task.add_output(output_type, value, agent=agent)

    def _refresh_qa_after_approval(self, task: Task) -> None:
        required = ("plan", "direction", "theme_contract", "resource_contracts", "prompt_ir")
        if not all(isinstance(task.state.get(name), dict) for name in required):
            return
        report = build_semantic_qa_report(task)
        errors = validate_semantic_qa_report(report)
        if errors:
            raise ValueError("Approval produced invalid Semantic QA report: " + "; ".join(errors))
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
            f"Semantic QA refreshed after approval change with status {report['status']}.",
        )

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
        self._refresh_qa_after_approval(task)
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

    def load_task(self, project: str, task_id: str) -> Task:
        return self.store.load(project, task_id)

    def list_runs(self, project: str) -> tuple[dict[str, object], ...]:
        return self.store.list(project)
