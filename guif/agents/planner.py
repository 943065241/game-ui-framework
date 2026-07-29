from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from guif.agents.base import Agent
from guif.planning import build_ui_production_plan, validate_ui_production_plan

if TYPE_CHECKING:
    from guif.runtime.task import Task


@dataclass(frozen=True)
class StructuredPlannerAgent(Agent):
    name: str = "planner"

    def execute(self, task: Task) -> Task:
        plan = build_ui_production_plan(task)
        errors = validate_ui_production_plan(plan)
        if errors:
            raise ValueError("Invalid UI production plan: " + "; ".join(errors))
        task.state.setdefault("agents", {})[self.name] = {
            "status": "completed",
            "implementation": "structured-rule-planner",
            "plan_schema_version": plan["schema_version"],
            "open_question_count": len(plan["open_questions"]),
            "risk_count": len(plan["risks"]),
        }
        task.state["plan"] = plan
        task.add_output("ui-production-plan", plan, agent=self.name)
        task.record(
            self.name,
            "completed",
            f"Structured plan created with {len(plan['execution_steps'])} execution steps.",
        )
        return task
