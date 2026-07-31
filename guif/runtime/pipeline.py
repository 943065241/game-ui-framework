from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from guif.runtime.registry import AgentRegistry
from guif.runtime.task import Task

if TYPE_CHECKING:
    from guif.workflow import WorkflowManifest

Checkpoint = Callable[[Task], None]


@dataclass(frozen=True)
class Pipeline:
    name: str
    agents: tuple[str, ...]
    source: str = "runtime"
    manager: str | None = None
    steps: tuple[str, ...] = ()
    domain: str = "visual-production"
    requires: tuple[str, ...] = ()
    stages: tuple[str, ...] = ()

    @classmethod
    def from_workflow(cls, workflow: WorkflowManifest) -> "Pipeline":
        return cls(
            name=workflow.workflow_id,
            agents=workflow.agents,
            source=workflow.source,
            manager=workflow.manager,
            steps=workflow.steps,
            domain=workflow.domain,
            requires=workflow.requires,
            stages=workflow.stages,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.name,
            "agents": list(self.agents),
            "source": self.source,
            "manager": self.manager,
            "steps": list(self.steps),
            "domain": self.domain,
            "requires": list(self.requires),
            "stages": list(self.stages),
        }

    def execute(
        self,
        task: Task,
        registry: AgentRegistry,
        *,
        start_index: int = 0,
        checkpoint: Checkpoint | None = None,
    ) -> Task:
        if start_index < 0 or start_index > len(self.agents):
            raise ValueError(f"Invalid pipeline start index: {start_index}")
        for index in range(start_index, len(self.agents)):
            agent_name = self.agents[index]
            task.begin_agent(agent_name, index)
            if checkpoint:
                checkpoint(task)
            task = registry.get(agent_name).execute(task)
            task.finish_agent(index)
            if checkpoint:
                checkpoint(task)
        return task
