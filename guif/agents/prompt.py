from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from guif.agents.base import Agent
from guif.approval import initialize_approvals
from guif.prompt_ir import build_prompt_ir, validate_prompt_ir

if TYPE_CHECKING:
    from guif.runtime.task import Task


@dataclass(frozen=True)
class StructuredPromptAgent(Agent):
    name: str = "prompt"

    def execute(self, task: Task) -> Task:
        prompt_ir = build_prompt_ir(task)
        errors = validate_prompt_ir(prompt_ir)
        if errors:
            raise ValueError("Invalid Prompt IR: " + "; ".join(errors))
        task.state["prompt_ir"] = prompt_ir
        task.add_output("model-neutral-prompt-ir", prompt_ir, agent=self.name)
        approval_state = initialize_approvals(task)
        task.state.setdefault("agents", {})[self.name] = {
            "status": "completed",
            "implementation": "model-neutral-prompt-ir",
            "prompt_ir_schema_version": prompt_ir["schema_version"],
            "prompt_status": prompt_ir["status"],
            "job_count": len(prompt_ir["jobs"]),
            "blocker_count": len(prompt_ir["blockers"]),
            "approval_point_count": len(prompt_ir["approval_points"]),
            "required_approval_count": len(approval_state["required_ids"]),
        }
        task.record(
            self.name,
            "completed",
            f"Prompt IR created with {len(prompt_ir['jobs'])} job(s), status {prompt_ir['status']}, and {len(approval_state['required_ids'])} required approval(s).",
        )
        return task
