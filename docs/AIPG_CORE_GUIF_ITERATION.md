# AIPG Runtime and GUIF Domain Refactor

## Decision

This iteration refactors the existing AIPG implementation directly. It does not
create a second framework beside AIPG and does not rebuild GUIF from scratch.

AIPG owns domain-neutral production contracts. GUIF remains the compatible
visual-production implementation and gradually delegates generic behavior to
AIPG.

```text
AIPG
├─ runtime.py          workflow graph, state, stack, validation
├─ artifacts.py        Artifact records, status, lineage
├─ capabilities.py     capability requirements and Tool adapters
├─ context.py          project and standalone lifecycle
└─ domains/
   ├─ model.py         Domain Pack contract
   └─ visual.py        GUIF Visual Production registration

GUIF compatibility layer
├─ existing workflows and CLIs
├─ Theme and visual context
├─ visual Artifact semantics
├─ visual review and exporters
└─ adapters for external visual Tools
```

The former experimental `aipg.core` monolith was removed. Its contracts were
promoted into focused AIPG modules so the repository evolves through its
existing public `aipg` namespace.

## Runtime model

Workflow definitions use a behavior-tree-like graph. Runtime execution uses a
hierarchical state machine and a finite workflow call stack.

```text
Workflow
→ Subworkflow
→ Stage or control node
→ Action
→ Tool invocation
```

A parent enters `waiting-for-child` when it invokes a child workflow. The child
owns a separate frame. Completion pops that frame, binds its outputs, and
resumes the parent. Maximum depth and retry limits prevent unbounded execution.

Supported control contracts include sequence, selector, parallel, condition,
subworkflow, action, approval, and review.

## Context lifecycle

AIPG supports two lifecycle modes shared by every Domain Pack:

- `project`: long-lived context. GUIF normally binds this to Theme, master
  references, approved assets, design tokens, component rules, and exporters.
- `standalone`: finite one-off work such as localized repaint, image editing,
  image layering, or effect-image generation without requiring a Theme.

Figma is a Tool and structured design environment, not another context mode.

## Shared Tool library

Workflows depend on provider-neutral capabilities. Tool adapters bind those
capabilities to real providers.

```text
Workflow requirement
→ CapabilityRequirement
→ ToolRegistry
→ compatible ToolAdapter
→ provider execution
```

GUIF registers visual capabilities such as image generation, image editing,
mask generation, vision analysis, OCR, background removal, composition, visual
diff, Figma design, and engine export. AIPG does not claim these providers are
available until an adapter, credentials, permissions, billing, and data flow are
configured.

## Artifact model

AIPG owns generic Artifact identity, status, parent references, metadata, and
lineage. GUIF contributes visual kinds such as image, mask, layer, composite,
visual-diff report, Figma mapping, and export package.

Workflow state and Artifact state remain independent.

## Compatibility and migration

The migration follows a direct, compatibility-preserving sequence:

1. Keep existing `guif` imports, commands, schemas, records, and workflows.
2. Promote generic contracts into focused `aipg` modules.
3. Export those contracts from the public `aipg` package.
4. Register GUIF as the Visual Production Domain Pack.
5. Move existing GUIF workflow orchestration to `aipg.runtime` incrementally.
6. Move provider routing to `aipg.capabilities` without changing workflow IDs.
7. Connect existing GUIF Artifact persistence to `aipg.artifacts`.
8. Remove duplicate GUIF infrastructure only after regression coverage proves
   compatibility.

This is a strangler-style refactor: existing production remains usable while
framework responsibilities move upward into AIPG.

## Current implementation boundary

Implemented in this iteration:

- focused AIPG runtime, context, capability, Artifact, and Domain Pack contracts;
- finite nested workflow stack and reference validation;
- provider-neutral Tool adapter resolution;
- parent-first Artifact lineage;
- GUIF visual-domain registration;
- public compatibility exports and contract tests.

Not yet claimed:

- a complete scheduler or persistent checkpoint engine;
- automatic migration of every existing GUIF module;
- real external Tool availability;
- semantic visual correctness from metadata-only tests;
- image, segmentation, OCR, or Figma algorithms implemented by AIPG itself.

## Architectural principle

> AIPG is the reusable AI production runtime. GUIF is its first visual Domain
> Pack and compatibility implementation. Generic responsibilities are promoted
> from GUIF into AIPG without replacing the working system all at once.
