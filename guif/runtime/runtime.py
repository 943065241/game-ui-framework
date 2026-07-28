from __future__ import annotations

from pathlib import Path

from guif.agents.builtin import build_default_agents
from guif.runtime.context import load_runtime_context
from guif.runtime.pipeline import Pipeline
from guif.runtime.registry import AgentRegistry
from guif.runtime.store import TaskStore
from guif.runtime.task import Task


DEFAULT_PIPELINES = {
    "ui-production": Pipeline(
        "ui-production",
        ("planner", "director", "theme", "resource", "prompt", "qa", "export"),
    ),
    "planning": Pipeline("planning", ("planner",)),
    "resource-production": Pipeline(
        "resource-production",
        ("director", "theme", "resource", "prompt", "qa", "export"),
    ),
}


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
        self.pipelines = dict(pipelines or DEFAULT_PIPELINES)
        self.store = store or TaskStore(workspace)

    def _resolve_pipeline(self, name: str) -> Pipeline:
        try:
            return self.pipelines[name]
        except KeyError as exc:
            raise ValueError(f"Unknown pipeline: {name}") from exc

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

    def run(self, project: str, requirement: str, *, pipeline: str = "ui-production") -> Task:
        if not requirement.strip():
            raise ValueError("Requirement must not be empty")
        resolved_pipeline = self._resolve_pipeline(pipeline)
        context = load_runtime_context(self.workspace, project)
        task = Task(
            project=project,
            requirement=requirement.strip(),
            pipeline=resolved_pipeline.name,
            context=context,
        )
        task.record("runtime", "started", f"Loaded project context for {project}")
        return self._execute(task, resolved_pipeline, start_index=0)

    def resume(self, project: str, task_id: str) -> Task:
        task = self.store.load(project, task_id)
        if task.status == "completed":
            raise ValueError(f"Task is already completed: {task_id}")
        resolved_pipeline = self._resolve_pipeline(task.pipeline)
        task.record(
            "runtime",
            "resumed",
            f"Resuming pipeline at agent index {task.next_agent_index}",
        )
        return self._execute(task, resolved_pipeline, start_index=task.next_agent_index)

    def load_task(self, project: str, task_id: str) -> Task:
        return self.store.load(project, task_id)

    def list_runs(self, project: str) -> tuple[dict[str, object], ...]:
        return self.store.list(project)
