# Repository Audit — 1.1.0-dev.9

Date: 2026-07-31

## Result

The repository is structurally coherent and the validated `1.1.0-dev.8` code
line passed CI on Python 3.10, 3.11 and 3.12. The main consolidation problem is
documentation drift rather than conflicting runtime implementations.

## Confirmed clean boundaries

- No active `aipg.core` implementation remains.
- Generic runtime contracts live under focused `aipg` modules.
- GUIF remains a compatibility and visual-production implementation.
- Tool discovery and Tool execution governance are separated.
- Package discovery includes both `aipg*` and `guif*`.
- Published package version remains `1.1.0b1`; development iterations are tracked
  independently in README and project-status documentation.

## Drift identified

### Workflow Runtime guide

`docs/AIPG_WORKFLOW_RUNTIME.md` still lists checkpoint restoration and
Capability Registry execution as future work, although both are implemented by
`RecoverableWorkflowEngine` and `ToolRegistry`.

Required correction:

- document `RecoverableWorkflowEngine`
- document `restore_run`
- document completed-node cursors and at-least-once failure semantics
- document Capability execution and Tool governance
- remove completed items from the limitations and next-iteration sections

### AIPG/GUIF iteration guide

`docs/AIPG_CORE_GUIF_ITERATION.md` describes only the initial contract phase.
It should include the current engine, event, checkpoint restoration and Tool
Runtime boundaries.

### README status

README should advance to `1.1.0-dev.9`, link to `PROJECT_STATUS.md`, record the
validated `1.1.0-dev.8` CI matrix, and identify repository consolidation as the
current milestone.

### Changelog

The Unreleased section already covers recovery but should explicitly record Tool
health, configuration validation, standard errors/results, timeout, retries,
fallback and the compatibility restoration of pure `resolve()` discovery.

## Code observations

- `WorkflowEngine` and `RecoverableWorkflowEngine` are intentionally separate,
  but the public documentation must explain which one deployments should use.
- `aipg.__init__` is a broad compatibility facade and imports visual GUIF
  helpers. This is acceptable during migration but should not become the only
  import surface for runtime-only deployments.
- `Parallel` is a semantic node implemented with deterministic ordered
  execution. Documentation must avoid implying concurrency.
- `InMemoryCheckpointStore` is not durable. Production recovery requires an
  external store implementation.
- Provider Adapters are contracts and test fixtures; no real provider should be
  advertised as available without deployment configuration.

## Consolidation actions

1. Added `docs/PROJECT_STATUS.md` as the canonical current-status and ownership
   map.
2. Recorded this audit separately so drift and follow-up work are explicit.
3. Preserve all existing GUIF compatibility surfaces.
4. Do not delete compatibility modules until migrated workflows have regression
   coverage.
5. Keep README development version increments mandatory for every direct-main
   iteration.

## Remaining document sync

The README, Workflow Runtime guide, iteration guide and Changelog still require
in-place updates. GitHub rejected the first in-place replacement attempts during
this audit, so those updates must be retried without claiming they were applied.
