"""AIPG: AI Production & Governance Framework.

AIPG owns the domain-neutral production contracts. The existing ``guif``
package remains the compatibility API and visual-production implementation.
"""

from guif import __version__
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
from .domains import (
    BUILTIN_DOMAIN_REGISTRY,
    FRAMEWORK_GOVERNANCE_DOMAIN,
    GUIF_VISUAL_DOMAIN,
    DomainPackDefinition,
    DomainRegistry,
    domain_for_workflow,
    get_domain_pack,
    list_domain_packs,
)
from .runtime import (
    NodeKind,
    WorkflowDefinition,
    WorkflowFrame,
    WorkflowNode,
    WorkflowStack,
    WorkflowStatus,
    validate_workflow_references,
)

DomainPack = DomainPackDefinition

__all__ = [
    "ArtifactRecord",
    "ArtifactRegistry",
    "ArtifactStatus",
    "BUILTIN_DOMAIN_REGISTRY",
    "CapabilityRequirement",
    "ContextMode",
    "DomainPack",
    "DomainPackDefinition",
    "DomainRegistry",
    "FRAMEWORK_GOVERNANCE_DOMAIN",
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
    "domain_for_workflow",
    "get_domain_pack",
    "list_domain_packs",
    "request_layer_revision",
    "validate_layered_composition",
    "validate_workflow_references",
]
