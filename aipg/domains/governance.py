from __future__ import annotations

from .model import DomainPackDefinition


FRAMEWORK_GOVERNANCE_DOMAIN = DomainPackDefinition(
    domain_id="framework-governance",
    name="AIPG Framework Governance",
    description=(
        "Framework evolution, evidence, adoption, publication, and regression."
    ),
    context_types=("improvement-case", "candidate-evidence"),
    artifact_kinds=("candidate-result", "regression-report"),
    workflow_ids=("framework-evolution",),
)
