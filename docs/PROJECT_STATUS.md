# AIPG Project Status

This is the canonical implementation-status map for the repository. README files provide the short public overview, `ROADMAP.md` contains future work, and `CHANGELOG.md` records completed history.

## Current development line

- Development version: `1.1.0-dev.10` from the root `VERSION` file
- Published package version: `1.1.0-beta.1`
- Integration policy: direct commits to `main`
- Validated baseline: `1.1.0-dev.8` passed CI on Python 3.10, 3.11 and 3.12
- Compatibility policy: preserve existing `guif` imports, commands, schemas and records while generic responsibilities migrate into `aipg`

## Ownership map

### AIPG owns

- Workflow graph, lifecycle state and finite call stacks
- Workflow execution, nested calls and lifecycle events
- Checkpoint boundaries, restoration and resumable cursors
- Capability requirements, Tool discovery and execution governance
- Generic Artifact identity, status, ancestry and lineage
- Project and standalone context modes
- Domain Pack registration

### GUIF owns

- Theme and visual-production context
- Images, masks, layers, composites and other visual Artifact semantics
- Visual Workflows and visual action implementations
- Visual Review and approval specializations
- Visual exporters and external visual Tool adapters
- Existing compatibility CLIs, schemas and storage conventions

## Implemented runtime capabilities

- Synchronous Workflow lifecycle engine
- Sequence, Selector, deterministic ordered Parallel, Condition, Action, Subworkflow, Approval and Review nodes
- Nested Workflow execution through a finite call stack
- Synchronous in-memory Event Bus
- CheckpointStore protocol and InMemoryCheckpointStore
- Schema-versioned checkpoint restoration with completed-node cursors
- Capability-to-ToolAdapter execution without provider coupling in Workflow definitions
- Backward-compatible capability discovery through `resolve()`
- Tool health and configuration validation at execution time
- Standard Tool errors and execution-result contracts
- Timeout, bounded retry and deterministic provider fallback policies
- Generic Artifact registry and lineage contracts
- AIPG-owned Domain Registry with GUIF Visual Production registration

## Explicit limitations

- Parallel nodes are ordered and deterministic, not concurrent
- No durable scheduler or external execution queue exists yet
- The default checkpoint store is in-memory
- Restored failing actions use at-least-once execution semantics
- No real Provider Adapter is claimed available by the framework itself
- Not every GUIF Workflow has migrated to WorkflowEngine
- Approval persistence, compensation and rollback are not implemented
- Semantic visual correctness remains a GUIF and Tool responsibility

## Public module map

```text
aipg/
├─ runtime.py          Workflow graph, state, stack and validation
├─ engine.py           lifecycle and graph execution
├─ recovery.py         checkpoint restoration and capability execution
├─ checkpoints.py      persistence-neutral checkpoint boundary
├─ events.py           runtime event delivery
├─ capabilities.py     Tool discovery and execution governance
├─ artifacts.py        generic Artifact registry and lineage
├─ context.py          project and standalone context modes
└─ domains/            Domain Pack model and registrations

guif/
└─ compatibility and visual-production implementation
```

## Documentation roles

- `VERSION`: canonical development version
- `README.md` and `README.zh-CN.md`: public overview
- `docs/PROJECT_STATUS.md`: current implementation truth
- `ROADMAP.md`: future priorities only
- `CHANGELOG.md`: chronological completed changes
- `docs/AIPG_ARCHITECTURE.md`: durable architecture and principles
- `docs/AIPG_WORKFLOW_RUNTIME.md`: current Workflow Runtime behavior
- `docs/MIGRATING_GUIF_TO_AIPG.md`: compatibility migration guidance

## Repository consolidation

The one-time repository audit and the early iteration-specific AIPG/GUIF document were removed after their still-valid conclusions were merged here and into the roadmap. New iteration-specific status documents should not be created.
