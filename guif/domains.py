from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DomainPack:
    """A production domain registered with the AIPG governance core."""

    domain_id: str
    name: str
    description: str
    workflows: tuple[str, ...]
    context_types: tuple[str, ...]
    artifact_kinds: tuple[str, ...]
    legacy_names: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "id": self.domain_id,
            "name": self.name,
            "description": self.description,
            "workflows": list(self.workflows),
            "context_types": list(self.context_types),
            "artifact_kinds": list(self.artifact_kinds),
            "legacy_names": list(self.legacy_names),
        }


BUILTIN_DOMAIN_PACKS: dict[str, DomainPack] = {
    "visual-production": DomainPack(
        domain_id="visual-production",
        name="GUIF Visual Production",
        description=(
            "Game UI and visual asset production governed by AIPG. "
            "GUIF remains the compatible visual-domain name."
        ),
        workflows=(
            "effect-image",
            "master-guided-layer-creation",
            "planning",
            "quality-assurance",
            "resource-production",
            "theme-direction",
            "ui-production",
        ),
        context_types=("theme", "master-reference", "editable-source"),
        artifact_kinds=(
            "effect-image",
            "production-asset",
            "layer-artifact",
            "composition-preview",
            "layer-manifest",
        ),
        legacy_names=("GUIF", "Game UI Framework"),
    ),
    "framework-governance": DomainPack(
        domain_id="framework-governance",
        name="AIPG Framework Governance",
        description="Framework evolution, evidence, adoption, publication, and regression.",
        workflows=("framework-evolution",),
        context_types=("improvement-case", "candidate-evidence"),
        artifact_kinds=("candidate-result", "regression-report"),
    ),
}


def get_domain_pack(domain_id: str) -> DomainPack:
    try:
        return BUILTIN_DOMAIN_PACKS[domain_id]
    except KeyError as exc:
        raise ValueError(f"Unknown production domain: {domain_id}") from exc


def list_domain_packs() -> list[dict[str, object]]:
    return [
        BUILTIN_DOMAIN_PACKS[domain_id].to_dict()
        for domain_id in sorted(BUILTIN_DOMAIN_PACKS)
    ]


def domain_for_workflow(workflow_id: str) -> str:
    matches = [
        domain_id
        for domain_id, domain in BUILTIN_DOMAIN_PACKS.items()
        if workflow_id in domain.workflows
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Workflow must belong to exactly one built-in domain: {workflow_id}"
        )
    return matches[0]
