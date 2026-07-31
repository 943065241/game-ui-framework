from __future__ import annotations

from aipg import get_domain_pack, list_domain_packs


def test_aipg_registers_guif_as_visual_domain_pack() -> None:
    domains = list_domain_packs()
    assert {item["id"] for item in domains} == {
        "framework-governance",
        "visual-production",
    }

    visual = get_domain_pack("visual-production")
    assert visual.name == "GUIF Visual Production"
    assert "master-guided-layer-creation" in visual.workflows
    assert "GUIF" in visual.legacy_names
    assert "layer-artifact" in visual.artifact_kinds
