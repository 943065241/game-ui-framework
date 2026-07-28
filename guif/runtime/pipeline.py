from __future__ import annotations

from dataclasses import dataclass

from guif.runtime.registry import AgentRegistry
from guif.runtime.task import Task


@dataclass(frozen=True)
class Pipeline:
    name: str
    agents: tuple[str, ...]

    def execute(self, task: Task, registry: AgentRegistry) -> Task:
        for agent_name in self.agents:
            task.record(agent_name, "started", f"Executing agent in pipeline {self.name}")
            task = registry.get(agent_name).execute(task)
        return task
