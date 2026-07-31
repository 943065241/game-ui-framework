from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .governance import FRAMEWORK_GOVERNANCE_DOMAIN
from .model import DomainPackDefinition
from .visual import GUIF_VISUAL_DOMAIN


@dataclass
class DomainRegistry:
    """Authoritative registry for AIPG production domains."""

    domains: dict[str, DomainPackDefinition] = field(default_factory=dict)

    def register(self, domain: DomainPackDefinition) -> None:
        if domain.domain_id in self.domains:
            raise ValueError(f"Domain already registered: {domain.domain_id}")
        self.domains[domain.domain_id] = domain

    def get(self, domain_id: str) -> DomainPackDefinition:
        try:
            return self.domains[domain_id]
        except KeyError as exc:
            raise ValueError(f"Unknown production domain: {domain_id}") from exc

    def list(self) -> list[DomainPackDefinition]:
        return [self.domains[key] for key in sorted(self.domains)]

    def domain_for_workflow(self, workflow_id: str) -> str:
        matches = [
            domain.domain_id
            for domain in self.domains.values()
            if workflow_id in domain.workflow_ids
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Workflow must belong to exactly one registered domain: {workflow_id}"
            )
        return matches[0]

    @classmethod
    def from_domains(cls, domains: Iterable[DomainPackDefinition]) -> "DomainRegistry":
        registry = cls()
        for domain in domains:
            registry.register(domain)
        return registry


BUILTIN_DOMAIN_REGISTRY = DomainRegistry.from_domains(
    (FRAMEWORK_GOVERNANCE_DOMAIN, GUIF_VISUAL_DOMAIN)
)


def get_domain_pack(domain_id: str) -> DomainPackDefinition:
    return BUILTIN_DOMAIN_REGISTRY.get(domain_id)


def list_domain_packs() -> list[dict[str, object]]:
    return [domain.to_dict() for domain in BUILTIN_DOMAIN_REGISTRY.list()]


def domain_for_workflow(workflow_id: str) -> str:
    return BUILTIN_DOMAIN_REGISTRY.domain_for_workflow(workflow_id)
