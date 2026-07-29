from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from guif.agents.base import Agent
from guif.semantic_qa import build_semantic_qa_report, validate_semantic_qa_report

if TYPE_CHECKING:
    from guif.runtime.task import Task


@dataclass(frozen=True)
class StructuredSemanticQAAgent(Agent):
    name: str = "qa"

    def execute(self, task: Task) -> Task:
        report = build_semantic_qa_report(task)
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
