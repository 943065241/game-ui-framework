"""AIPG: AI Production & Governance Framework.

The existing ``guif`` package remains the compatibility API for the GUIF
visual-production domain. New domain-neutral integrations should prefer the
contracts exported from :mod:`aipg.core`.
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

from aipg.core import (
    ArtifactRecord,
    ArtifactRegistry,
    ArtifactStatus,
    CapabilityRequirement,
    ContextMode,
    DomainPackDefinition,
    NodeKind,
    ProductionRequest,
    ToolAdapter,
    ToolRegistry,
    WorkflowDefinition,
    WorkflowFrame,
    WorkflowNode,
    WorkflowStack,
    WorkflowStatus,
    validate_workflow_references,
)
from aipg.domains import GUIF_VISUAL_DOMAIN

__all__ = [
    "ArtifactRecord",
    "ArtifactRegistry",
    "ArtifactStatus",
    "CapabilityRequirement",
    "ContextMode",
    "DomainPack",
    "DomainPackDefinition",
    "GUIF_VISUAL_DOMAIN",
    "NodeKind",
    "ProductionRequest",
    "ToolAdapter",
    "ToolRegistry",
    "WorkflowDefinition",
    "WorkflowFrame",
    "WorkflowNode",
    "WorkflowStack",
    "WorkflowStatus",
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
    "validate_workflow_references",
]
