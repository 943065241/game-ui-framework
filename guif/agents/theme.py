from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from guif.agents.base import Agent
from guif.theme_contract import build_theme_contract, validate_theme_contract

if TYPE_CHECKING:
    from guif.runtime.task import Task


@dataclass(frozen=True)
class StructuredThemeAgent(Agent):
    name: str = "theme"

    def execute(self, task: Task) -> Task:
        contract = build_theme_contract(task)
        errors = validate_theme_contract(contract)
        if errors:
            raise ValueError("Invalid Theme contract: " + "; ".join(errors))
        task.state.setdefault("agents", {})[self.name] = {
            "status": "completed",
            "implementation": "structured-rule-theme",
            "contract_schema_version": contract["schema_version"],
            "theme_status": contract["status"],
            "approval_required": contract["approval_required"],
            "conflict_count": len(contract["conflicts"]),
        }
        task.state["theme_contract"] = contract
        task.add_output("resolved-theme-contract", contract, agent=self.name)
        task.record(
            self.name,
            "completed",
            f"Theme contract resolved with status {contract['status']} from {contract['source']}.",
        )
        return task
