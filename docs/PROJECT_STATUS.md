# AIPG Project Status

This document is the canonical implementation-status map for the repository.
README files provide the short public summary, while CHANGELOG records history.
Architecture documents explain design and must not be used as the only source
for determining whether a feature is implemented.

## Current development line

- Development version: `1.1.0-dev.9`
- Published package version: `1.1.0-beta.1`
- Integration policy: direct commits to `main`
- Compatibility policy: preserve existing `guif` imports, commands, schemas and records while generic responsibilities migrate into `aipg`

## Ownership map

### AIPG owns

- Workflow definitions, graph nodes, lifecycle state and finite call stacks
- Workflow execution, nested Workflow calls and lifecycle events
- Checkpoint persistence boundaries and deterministic restore cursors
- Capability requirements, Tool registration, health, routing and execution governance
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
- Sequence, Selector, deterministic Parallel, Condition, Action, Subworkflow, Approval and Review graph nodes
- Nested Workflow execution through a finite call stack
- Synchronous in-memory Event Bus
- CheckpointStore protocol and InMemoryCheckpointStore
- Schema-versioned checkpoint restoration with completed-node cursors
- Capability-to-ToolAdapter execution without provider coupling in Workflows
- Tool health and configuration validation
- Standard Tool error and execution-result contracts
- Timeout, bounded retry and deterministic provider fallback policies
- Generic Artifact registry and lineage contracts
- AIPG-owned Domain Registry with GUIF Visual Production registration

## Explicit limitations

- Parallel nodes are deterministic and ordered, not concurrent
- No durable scheduler or external execution queue exists yet
- The default checkpoint store is in-memory; durable stores are extension points
- Restored failing actions use at-least-once execution semantics
- No real Provider Adapter is claimed available by the framework itself
- Not every existing GUIF Workflow has migrated to WorkflowEngine
- Approval persistence, compensation and rollback are not implemented
- Semantic visual correctness still belongs to GUIF and real visual Tools

## Public module map

```text
aipg/
├─ runtime.py          Workflow graph, state, stack and validation
├─ engine.py           Lifecycle and graph execution
├─ recovery.py         Checkpoint restoration and capability execution bridge
├─ checkpoints.py      Persistence-neutral checkpoint boundary
├─ events.py           Runtime event delivery
├─ capabilities.py     Tool registry and execution governance
├─ artifacts.py        Generic Artifact registry and lineage
├─ context.py          Project and standalone context modes
└─ domains/            Domain Pack model and built-in registrations

guif/
└─ compatibility and visual-production implementation
```

## Documentation roles

- `README.md` and `README.zh-CN.md`: current version and public overview
- `docs/PROJECT_STATUS.md`: canonical current implementation status
- `CHANGELOG.md`: chronological changes
- `docs/AIPG_ARCHITECTURE.md`: target architecture and principles
- `docs/AIPG_WORKFLOW_RUNTIME.md`: current Workflow Runtime behavior
- `docs/AIPG_CORE_GUIF_ITERATION.md`: migration strategy and boundary

## Next priorities

1. Implement the first real Provider Adapter behind the Tool contracts.
2. Add scheduler and durable queue contracts without changing Workflow graphs.
3. Connect Artifact lifecycle updates to Workflow action and capability outputs.
4. Migrate one production GUIF Workflow end-to-end onto WorkflowEngine.
5. Add a durable CheckpointStore implementation and recovery integration tests.
