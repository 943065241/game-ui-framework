"""AIPG: AI Production & Governance Framework.

AIPG owns the domain-neutral production contracts. The existing ``guif``
package remains the compatibility API and visual-production implementation.
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

from .artifacts import ArtifactRecord, ArtifactRegistry, ArtifactStatus
from .capabilities import CapabilityRequirement, ToolAdapter, ToolRegistry
from .context import ContextMode, ProductionRequest
from .domains import GUIF_VISUAL_DOMAIN
from .domains.model import DomainPackDefinition
from .runtime import (
    NodeKind,
    WorkflowDefinition,
    WorkflowFrame,
    WorkflowNode,
    WorkflowStack,
    WorkflowStatus,
    validate_workflow_references,
)

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
