from __future__ import annotations

from pathlib import Path

from guif.agents.builtin import build_default_agents
from guif.runtime.context import load_runtime_context
from guif.runtime.pipeline import Pipeline
from guif.runtime.registry import AgentRegistry
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


class Runtime:
    def __init__(
        self,
        workspace: Path,
        *,
        registry: AgentRegistry | None = None,
        pipelines: dict[str, Pipeline] | None = None,
    ) -> None:
        self.workspace = workspace
        self.registry = registry or AgentRegistry(build_default_agents())
        self.pipelines = dict(pipelines or DEFAULT_PIPELINES)

    def run(self, project: str, requirement: str, *, pipeline: str = "ui-production") -> Task:
        if not requirement.strip():
            raise ValueError("Requirement must not be empty")
        try:
            resolved_pipeline = self.pipelines[pipeline]
        except KeyError as exc:
            raise ValueError(f"Unknown pipeline: {pipeline}") from exc

        context = load_runtime_context(self.workspace, project)
        task = Task(
            project=project,
            requirement=requirement.strip(),
            pipeline=resolved_pipeline.name,
            context=context,
        )
        task.record("runtime", "started", f"Loaded project context for {project}")
        task = resolved_pipeline.execute(task, self.registry)
        task.complete()
        task.record("runtime", "completed", f"Pipeline completed: {resolved_pipeline.name}")
        return task
