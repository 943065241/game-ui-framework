# AIPG Architecture

## Positioning

AIPG is a local-first AI production workflow and governance framework. GUIF is
the compatible visual-production Domain Pack and the first concrete production
implementation built on AIPG.

This repository evolves by promoting generic responsibilities from GUIF into
AIPG. It does not maintain a second parallel Core.

```text
AIPG
├─ runtime              workflow graph, hierarchical state, stack, recovery
├─ context              project and standalone lifecycle
├─ artifacts            Artifact identity, status, version ancestry, lineage
├─ capabilities         provider-neutral requirements and Tool adapters
├─ review / approval    generic governance contracts
├─ evidence / export    verification and gated delivery
└─ domains
   └─ GUIF Visual Production
```

AIPG understands domain-neutral concepts such as Workflow, Stage, Artifact,
Dependency, Constraint, Approval, Evidence, Revision, Capability, Tool Adapter,
and Export. Buttons, alpha, Theme, masks, visual layers, composition, Figma
mappings, and engine assets belong to GUIF.

## Public module boundary

The initial refactor uses focused modules instead of a monolithic `aipg.core`:

```text
aipg.runtime
aipg.context
aipg.artifacts
aipg.capabilities
aipg.domains
```

The public `aipg` package re-exports stable contracts. Existing `guif` imports,
commands, schemas, storage contracts, and production workflows remain available
while their generic infrastructure is migrated incrementally.

## Routing and context

A request is classified by Domain Pack and workflow before context is resolved.
Theme is a GUIF project-context type, not a mandatory AIPG top-level state.

```text
request
→ domain
→ workflow
→ context mode
→ required context
→ capability resolution
→ governed execution
→ Artifact and lineage
→ review and approval
→ export
```

Two lifecycle modes are shared by all domains:

- `project`: long-lived context, commonly a GUIF Theme;
- `standalone`: finite one-off Artifact production.

## Workflow runtime

Workflow definitions form a behavior-tree-like graph. Runtime execution is a
hierarchical state machine with an explicit finite call stack.

```text
Workflow
→ Subworkflow
→ Control node / Stage
→ Action
→ Tool invocation
```

Parents wait while child workflows execute, then resume with the child result.
Depth, retries, timeouts, and reference validation prevent unbounded execution.
Workflow status and Artifact status are managed independently.

## Capability and Tool routing

Workflows request capabilities rather than providers.

```text
CapabilityRequirement
→ ToolRegistry
→ compatible ToolAdapter
→ provider execution
```

GUIF may register adapters for image generation, editing, segmentation, OCR,
vision, Figma, composition, visual diff, or engine export. AIPG does not
reimplement mature algorithms and does not claim provider availability without
real configuration and evidence.

## GUIF visual domain

GUIF contributes:

- Theme-backed and standalone visual contexts;
- visual workflows such as localized repaint, layering, visual review, Figma
  sync, and resource export;
- image, mask, layer, composite, visual-diff, mapping, and export Artifacts;
- visual constraints, review rules, Tool adapters, and exporters.

Existing GUIF behavior is migrated through a compatibility-preserving strangler
pattern: promote generic contracts first, delegate existing code second, and
remove duplicate infrastructure only after regression validation.
