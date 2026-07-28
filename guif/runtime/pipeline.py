from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from guif.runtime.registry import AgentRegistry
from guif.runtime.task import Task

Checkpoint = Callable[[Task], None]


@dataclass(frozen=True)
class Pipeline:
    name: str
    agents: tuple[str, ...]

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
