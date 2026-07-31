# Changelog

All notable framework changes are recorded here. Candidate entries describe
unreleased work and do not imply adoption or publication.

## Unreleased — 1.1.0-dev.11

### Planned

- Implement the first real Provider Adapter behind the existing Tool contracts.
- Connect provider execution to `ToolRegistry` without exposing provider identity
  to Workflow definitions.
- Add configuration, health, standard error, retry and fallback integration
  coverage for the Adapter.
- Document deployment requirements without claiming availability before runtime
  configuration is complete.

## Unreleased — AIPG runtime refactor

### Added

- Focused `aipg.runtime`, `aipg.context`, `aipg.artifacts`, and
  `aipg.capabilities` contracts.
- Finite nested Workflow stack, child Workflow reference validation, and
  provider-neutral Tool adapter resolution.
- Generic Artifact lineage and GUIF Visual Production Domain Pack declaration.
- Authoritative `aipg.domains.DomainRegistry` with built-in visual-production
  and framework-governance registrations.
- Executable `WorkflowEngine` with run creation, lifecycle transitions,
  action binding, pause/resume, bounded retry, cancellation and output contract
  validation.
- Automatic graph traversal for Sequence, Parallel, Selector, Condition,
  Action, Subworkflow, Approval and Review nodes.
- Nested Workflow execution on the finite call stack with child context returned
  to the parent frame.
- Persistence-neutral `CheckpointStore` protocol and default
  `InMemoryCheckpointStore`.
- `RecoverableWorkflowEngine` with schema-versioned stack snapshots,
  deterministic completed-node cursors and checkpoint restoration.
- Capability execution through prioritized `ToolAdapter` selection without
  exposing provider identity to Workflow definitions.
- Domain-neutral synchronous `EventBus` and lifecycle events for Workflows,
  nodes, actions, capabilities, child Workflows and reviews.
- Contract tests for lifecycle, graph traversal, conditions, nested Workflows,
  recovery, capability execution, approval pauses, Domain Packs and Artifacts.

### Changed

- Refactored the existing AIPG implementation directly instead of introducing
  a parallel framework or replacement Core.
- Removed the experimental monolithic `aipg.core`; stable contracts are exported
  from focused AIPG modules and re-exported by `aipg`.
- Promoted Domain Pack ownership from `guif.domains` to `aipg.domains`;
  `guif.domains` now delegates to the AIPG registry as a compatibility surface.
- Promoted Workflow lifecycle, graph execution, recovery and capability routing
  into AIPG while keeping visual behavior outside the Runtime.
- Clarified that GUIF remains the compatible visual implementation while generic
  responsibilities migrate upward into AIPG incrementally.
- Updated README, architecture, migration and Workflow Runtime documentation to
  describe the compatibility-preserving strangler refactor.

### Compatibility

- Existing `guif` imports, commands, workflows, schemas, Theme records, Artifact
  records, Domain Pack helpers, and storage conventions remain supported.
- The Runtime remains synchronous and uses deterministic ordered execution for
  Parallel nodes. Checkpoint recovery currently provides at-least-once action
  semantics for a failing node and skips nodes recorded as completed.
- Distributed scheduling, durable external stores and semantic visual review
  remain future migrations.

## 1.1.0-beta.1 — 2026-07-31

### Added

- AIPG (AI Production & Governance Framework) as the domain-neutral top-level
  framework identity.
- A registered Domain Pack model with `framework-governance` and
  `visual-production` built-ins.
- GUIF as the compatible game UI and visual-production domain.
- Workflow manifest schema v3 with domain, required context, stages, creation
  direction, and constraint policy.
- `master-guided-layer-creation`, where a master effect image guides style and
  layout without requiring pixel matching.
- A bottom-to-top layered composition state model, per-layer creative freedom,
  scoped downstream invalidation, recomposition approval, and export manifest.
- The `aipg` Python facade and CLI entry point.

### Changed

- Plugin display identity and package metadata now use AIPG naming.
- The existing `guif` package, CLI command, Skill, schemas, and environment
  variables remain compatibility surfaces.

### Documentation

- Added AIPG architecture, GUIF migration, master-guided workflow, and candidate
  release notes.
- Added a comprehensive user blueprint covering Skills, Tools, Domain Packs,
  Workflows, Artifacts, approvals, privacy, version governance, publication,
  recovery, extension contracts, end-to-end journeys, and operational
  checklists.
- Updated README files, plugin metadata, version checks, and contributor name.

### Validation

- Added wholly fictional domain and layered-workflow regression fixtures.
- No user Theme, image, conversation, credential, or private evidence is part
  of the public candidate.
