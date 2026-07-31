from __future__ import annotations

import pytest

from aipg import get_domain_pack, list_domain_packs
from aipg.domains import DomainPackDefinition, DomainRegistry, domain_for_workflow
from guif.domains import DomainPack as LegacyDomainPack


def test_aipg_registers_guif_as_visual_domain_pack() -> None:
    domains = list_domain_packs()
    assert [item["id"] for item in domains] == [
        "framework-governance",
        "visual-production",
    ]

    visual = get_domain_pack("visual-production")
    assert visual.name == "GUIF Visual Production"
    assert "master-guided-layer-creation" in visual.workflows
    assert "GUIF" in visual.legacy_names
    assert "layer-artifact" in visual.artifact_kinds
    assert domain_for_workflow("framework-evolution") == "framework-governance"


def test_domain_pack_serialization_keeps_legacy_shape() -> None:
    serialized = get_domain_pack("visual-production").to_dict()

    assert serialized["schema_version"] == 2
    assert serialized["id"] == "visual-production"
    assert serialized["workflows"] == list(
        get_domain_pack("visual-production").workflow_ids
    )


def test_guif_domain_pack_is_aipg_compatibility_alias() -> None:
    assert LegacyDomainPack is DomainPackDefinition


def test_registry_rejects_duplicate_domain() -> None:
    domain = DomainPackDefinition(
        domain_id="example",
        name="Example",
        description="Example domain",
        context_types=(),
        artifact_kinds=(),
        workflow_ids=("example-workflow",),
    )
    registry = DomainRegistry.from_domains((domain,))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(domain)


def test_registry_rejects_ambiguous_workflow_ownership() -> None:
    first = DomainPackDefinition(
        domain_id="first",
        name="First",
        description="First",
        context_types=(),
        artifact_kinds=(),
        workflow_ids=("shared",),
    )
    second = DomainPackDefinition(
        domain_id="second",
        name="Second",
        description="Second",
        context_types=(),
        artifact_kinds=(),
        workflow_ids=("shared",),
    )
    registry = DomainRegistry.from_domains((first, second))

    with pytest.raises(ValueError, match="exactly one registered domain"):
        registry.domain_for_workflow("shared")
