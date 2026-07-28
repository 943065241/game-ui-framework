from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from guif.runtime.task import Task


class Agent(ABC):
    name: str

    @abstractmethod
    def execute(self, task: Task) -> Task:
        raise NotImplementedError


@dataclass(frozen=True)
class ContractAgent(Agent):
    name: str
    responsibility: str

    def execute(self, task: Task) -> Task:
        task.state.setdefault("agents", {})[self.name] = {
            "status": "contract-ready",
            "responsibility": self.responsibility,
        }
        task.record(self.name, "completed", f"Contract executed: {self.responsibility}")
        return task
