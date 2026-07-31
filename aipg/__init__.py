"""AIPG: AI Production & Governance Framework.

The existing ``guif`` package remains the compatibility API for the GUIF
visual-production domain.
"""

from guif import __version__
from guif.domains import DomainPack, get_domain_pack, list_domain_packs
from guif.layered_workflow import (
    approve_final_composition,
    approve_layer_plan,
    build_export_manifest,
    complete_current_layer,
    create_layered_composition,
    current_layer_contract,
    request_layer_revision,
    validate_layered_composition,
)

__all__ = [
    "DomainPack",
    "__version__",
    "approve_final_composition",
    "approve_layer_plan",
    "build_export_manifest",
    "complete_current_layer",
    "create_layered_composition",
    "current_layer_contract",
    "get_domain_pack",
    "list_domain_packs",
    "request_layer_revision",
    "validate_layered_composition",
]
