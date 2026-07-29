from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from guif.agents.base import Agent
from guif.direction import build_art_direction_review, validate_art_direction_review

if TYPE_CHECKING:
    from guif.runtime.task import Task


@dataclass(frozen=True)
class StructuredDirectorAgent(Agent):
    name: str = "director"

    def execute(self, task: Task) -> Task:
        review = build_art_direction_review(task)
        errors = validate_art_direction_review(review)
        if errors:
            raise ValueError("Invalid art direction review: " + "; ".join(errors))
        task.state.setdefault("agents", {})[self.name] = {
            "status": "completed",
            "implementation": "structured-rule-director",
            "review_schema_version": review["schema_version"],
            "direction_status": review["status"],
            "conflict_count": len(review["conflicts"]),
            "approval_point_count": len(review["approval_points"]),
        }
        task.state["direction"] = review
        task.add_output("art-direction-review", review, agent=self.name)
        task.record(
            self.name,
            "completed",
            f"Art direction review completed with status {review['status']}.",
        )
        return task
