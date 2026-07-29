from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from guif.agents.base import Agent
from guif.semantic_qa import (
    SEMANTIC_QA_SCHEMA_VERSION,
    build_semantic_qa_report,
    validate_semantic_qa_report,
)

if TYPE_CHECKING:
    from guif.runtime.task import Task


_REQUIRED_STATE = ("plan", "direction", "theme_contract", "resource_contracts", "prompt_ir")


def _missing_prerequisite_report(task: Any, missing: list[str]) -> dict[str, Any]:
    findings = [
        {
            "severity": "blocking",
            "code": "missing-qa-prerequisite",
            "message": f"Semantic QA cannot perform the full contract review because task.state['{name}'] is unavailable in this Pipeline.",
            "source": "qa",
            "evidence": {"state_key": name},
        }
        for name in missing
    ]
    return {
        "schema_version": SEMANTIC_QA_SCHEMA_VERSION,
        "task_id": task.task_id,
        "project": task.project,
        "status": "blocked",
        "scope": "prerequisite-only",
        "summary": {
            "check_count": 1,
            "passed_check_count": 0,
            "failed_check_count": 1,
            "finding_count": len(findings),
            "blocking_finding_count": len(findings),
            "review_finding_count": 0,
        },
        "checks": [
            {
                "id": "qa-prerequisite-chain",
                "category": "provenance",
                "status": "failed",
                "message": "The current Pipeline does not provide every state required for full Semantic Contract QA.",
                "evidence": {"missing_state_keys": missing},
            }
        ],
        "findings": findings,
        "artifact_review": {
            "status": "not-run",
            "artifact_count": 0,
            "reason": "Semantic QA prerequisites are incomplete; no Artifact review was attempted.",
            "checks": [],
        },
        "export_gate": {
            "allowed": False,
            "reasons": ["Semantic QA prerequisites are incomplete."],
        },
        "revision_request": {
            "required": True,
            "finding_codes": ["missing-qa-prerequisite"],
            "next_step": "Use a Pipeline that provides the required upstream contracts, or remove Semantic QA from this partial Workflow.",
        },
        "provenance": {
            "plan_output": "ui-production-plan",
            "director_output": "art-direction-review",
            "theme_output": "resolved-theme-contract",
            "resource_output": "resource-contract-bundle",
            "prompt_output": "model-neutral-prompt-ir",
        },
        "handoff": {
            "approval": "No approval can resolve missing upstream Pipeline stages.",
            "generation": "Do not execute Provider jobs from an incomplete QA chain.",
            "artifact_qa": "Run full Semantic QA after all required contracts exist.",
            "export": "Export remains blocked.",
        },
    }


@dataclass(frozen=True)
class StructuredSemanticQAAgent(Agent):
    name: str = "qa"

    def execute(self, task: Task) -> Task:
        missing = [name for name in _REQUIRED_STATE if not isinstance(task.state.get(name), dict)]
        report = _missing_prerequisite_report(task, missing) if missing else build_semantic_qa_report(task)
        errors = validate_semantic_qa_report(report)
        if errors:
            raise ValueError("Invalid Semantic QA report: " + "; ".join(errors))
        task.state.setdefault("agents", {})[self.name] = {
            "status": "completed",
            "implementation": "semantic-contract-qa",
            "qa_schema_version": report["schema_version"],
            "qa_status": report["status"],
            "check_count": report["summary"]["check_count"],
            "blocking_finding_count": report["summary"]["blocking_finding_count"],
            "artifact_review_status": report["artifact_review"]["status"],
            "export_allowed": report["export_gate"]["allowed"],
        }
        task.state["qa_report"] = report
        task.add_output("semantic-qa-report", report, agent=self.name)
        task.record(
            self.name,
            "completed",
            f"Semantic QA completed with status {report['status']} and {report['summary']['finding_count']} finding(s).",
        )
        return task
