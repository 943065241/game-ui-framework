from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from guif.agents.base import Agent
from guif.resource_contract import (
    build_resource_contract_bundle,
    validate_resource_contract_bundle,
)

if TYPE_CHECKING:
    from guif.runtime.task import Task


@dataclass(frozen=True)
class StructuredResourceAgent(Agent):
    name: str = "resource"

    def execute(self, task: Task) -> Task:
        bundle = build_resource_contract_bundle(task)
        errors = validate_resource_contract_bundle(bundle)
        if errors:
            raise ValueError("Invalid Resource contract bundle: " + "; ".join(errors))
        task.state.setdefault("agents", {})[self.name] = {
            "status": "completed",
            "implementation": "structured-rule-resource",
            "bundle_schema_version": bundle["schema_version"],
            "resource_status": bundle["status"],
            "approved_existing_count": len(bundle["approved_existing"]),
            "manifest_candidate_count": len(bundle["manifest_candidates"]),
            "unresolved_count": len(bundle["unresolved"]),
        }
        task.state["resource_contracts"] = bundle
        task.add_output("resource-contract-bundle", bundle, agent=self.name)
        task.record(
            self.name,
            "completed",
            f"Resource contract bundle created with status {bundle['status']} and {len(bundle['manifest_candidates'])} manifest candidate(s).",
        )
        return task
