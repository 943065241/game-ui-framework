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
from .capabilities import (
    CapabilityRequirement,
    ToolAdapter,
    ToolAuthenticationError,
    ToolConfigurationError,
    ToolError,
    ToolExecutionHandler,
    ToolExecutionPolicy,
    ToolExecutionResult,
    ToolHealth,
    ToolHealthHandler,
    ToolRegistry,
    ToolRetryableError,
    ToolTimeoutError,
    ToolUnavailableError,
)
from .checkpoints import CheckpointStore, InMemoryCheckpointStore
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
from .engine import ActionHandler, ConditionHandler, WorkflowEngine, WorkflowRun
from .events import EventBus, EventHandler, RuntimeEvent
from .recovery import RecoverableWorkflowEngine
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
    "ActionHandler", "ArtifactRecord", "ArtifactRegistry", "ArtifactStatus",
    "BUILTIN_DOMAIN_REGISTRY", "CapabilityRequirement", "CheckpointStore",
    "ConditionHandler", "ContextMode", "DomainPack", "DomainPackDefinition",
    "DomainRegistry", "EventBus", "EventHandler", "FRAMEWORK_GOVERNANCE_DOMAIN",
    "GUIF_VISUAL_DOMAIN", "InMemoryCheckpointStore", "NodeKind",
    "ProductionRequest", "RecoverableWorkflowEngine", "RuntimeEvent",
    "ToolAdapter", "ToolAuthenticationError", "ToolConfigurationError",
    "ToolError", "ToolExecutionHandler", "ToolExecutionPolicy",
    "ToolExecutionResult", "ToolHealth", "ToolHealthHandler", "ToolRegistry",
    "ToolRetryableError", "ToolTimeoutError", "ToolUnavailableError",
    "WorkflowDefinition", "WorkflowEngine", "WorkflowFrame", "WorkflowNode",
    "WorkflowRun", "WorkflowStack", "WorkflowStatus", "__version__",
    "approve_final_composition", "approve_layer_plan", "build_export_manifest",
    "complete_current_layer", "create_layered_composition",
    "current_layer_contract", "domain_for_workflow", "get_domain_pack",
    "list_domain_packs", "request_layer_revision",
    "validate_layered_composition", "validate_workflow_references",
]
