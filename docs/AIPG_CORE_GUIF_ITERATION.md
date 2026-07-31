# AIPG Core and GUIF Domain Iteration

## Decision

AIPG is the domain-neutral AI production runtime. GUIF is its visual-production
Domain Pack.

GUIF does not own the generic runtime, Artifact lineage, approval mechanism,
capability routing, or nested workflow execution. It contributes visual
workflows, visual context, visual Artifact kinds, Tool adapters, review rules,
and exporters.

```text
AIPG Core
├─ hierarchical workflow graph and runtime
├─ finite workflow call stack
├─ context lifecycle
├─ capability and Tool adapter registry
├─ Artifact registry and lineage
├─ review and approval contracts
├─ checkpoints, recovery, and events
└─ gated export

Domain Packs
└─ GUIF Visual Production
   ├─ Theme-backed and standalone production
   ├─ image generation and editing workflows
   ├─ localized repaint and image layering
   ├─ visual review and visual diff
   ├─ Figma integration
   └─ engine and asset export
```

## Two context modes

A workflow runs in one of two lifecycle modes.

### Project context

Project context is used when the result belongs to a long-lived visual system.
GUIF commonly binds this mode to a Theme, master references, approved assets,
design tokens, component rules, and export targets.

### Standalone context

Standalone context is used for finite one-off work such as localized repaint,
single-image editing, image layering, or a disposable effect-image task. It
uses the same workflow and Tool libraries as project production, but does not
require a Theme and may terminate after the requested Artifact is delivered.

A standalone Artifact may later be promoted into project context. A project
workflow may also create a one-off result without updating its Theme.

## Nested workflows

Workflow definitions form a behavior-tree-like graph. Runtime execution is a
hierarchical finite state machine with an explicit, finite call stack.

```text
visual-production-task
└─ localized-repaint
   ├─ identify-edit-region
   │  └─ mask-generation
   │     └─ semantic-segmentation action
   ├─ image-edit-execution
   ├─ protected-region-diff
   └─ semantic-review
```

When a parent invokes a child workflow, the parent enters
`waiting-for-child`. The child owns a separate stack frame. Completion pops the
child frame, binds its declared outputs, and resumes the parent node. Failure
can select retry, revision, fallback, cancellation, or propagation according
to policy.

The runtime must enforce finite limits, including maximum nesting depth,
maximum retry count, timeouts, and cycle or recursive-reference checks.

## Workflow structure

The common control nodes are:

- `sequence` for ordered stages;
- `selector` for fallback choices;
- `parallel` for independent checks;
- `condition` for context or policy branching;
- `subworkflow` for reusable nested production logic;
- `action` for atomic operations and Tool invocation;
- `approval` for human authorization;
- `review` for deterministic or semantic evaluation.

Recommended hierarchy:

```text
Workflow
→ Subworkflow
→ Stage or control node
→ Action
→ Tool invocation
```

## Shared Tool library

GUIF should integrate mature external capabilities rather than recreate their
algorithms. Workflows depend on stable capability identifiers; adapters bind
those capabilities to actual providers.

```text
Workflow requirement
→ Capability Registry
→ compatible Tool adapters
→ policy-based adapter selection
→ provider execution
```

Initial visual capabilities:

- `image-generation`;
- `image-editing`;
- `mask-generation`;
- `vision-analysis`;
- `ocr`;
- `background-removal`;
- `image-composition`;
- `visual-diff`;
- `figma-design`;
- `engine-export`.

Possible adapters include OpenAI image tools, FLUX or Stable Diffusion through
ComfyUI, SAM-family segmentation, OCR engines, background-removal libraries,
Figma APIs, image compositors, and game-engine exporters. Availability,
credentials, billing, and data-flow policies remain explicit.

Figma is a structured visual Tool and can be used in either context mode. It is
not a third lifecycle mode.

## Core contracts introduced in this iteration

`aipg.core` now defines initial contracts for:

- context modes;
- workflow and Artifact states;
- behavior-tree-like workflow nodes;
- nested workflow definitions;
- finite workflow stack frames;
- capability requirements;
- Tool adapter registration and resolution;
- Artifact registration and parent-first lineage;
- Domain Pack declarations;
- project and standalone production requests.

These contracts are intentionally small. They establish separation and
validation rules without claiming that the complete scheduler, persistence,
provider execution, semantic review, or recovery engine already exists.

## GUIF Domain Pack

The initial `GUIF_VISUAL_DOMAIN` definition declares visual context types,
Artifact kinds, workflow identifiers, and capability identifiers independently
from the Core.

GUIF remains compatible with existing `guif` imports and commands during the
migration. New domain-neutral code should use `aipg` contracts. Existing GUIF
production functions can be moved behind Domain Pack workflows incrementally.

## Migration sequence

1. Keep existing GUIF behavior and public compatibility APIs stable.
2. Introduce AIPG Core contracts and validation.
3. Register GUIF explicitly as the visual Domain Pack.
4. Move workflow manifests to nested graph definitions.
5. Move provider-specific calls behind Tool adapters.
6. Connect existing Artifact and approval records to Core registries.
7. Add persistent checkpoints and workflow resume.
8. Implement localized repaint, image layering, visual diff, and Figma sync as
   composable GUIF workflows.
9. Add additional Domain Packs without adding visual concepts to Core.

## Non-goals

This iteration does not:

- implement image generation or editing algorithms;
- claim external Tool availability;
- replace mature image, segmentation, OCR, or Figma tools;
- migrate every existing `guif` module immediately;
- treat metadata validation as semantic or visual proof;
- permit unbounded recursive workflows.

## Architectural principle

> AIPG governs production through reusable domain-neutral runtime contracts;
> GUIF supplies visual-production semantics and composes mature visual Tools
> into finite, reviewable, resumable workflows.
