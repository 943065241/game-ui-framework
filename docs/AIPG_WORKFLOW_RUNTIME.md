# AIPG Workflow Runtime

## Purpose

AIPG owns the domain-neutral Workflow lifecycle and graph execution model. GUIF and future Domain Packs define Workflow templates and bind domain actions, while the Runtime owns run identity, state transitions, traversal, nested calls, retries, checkpoints, recovery, capability execution and lifecycle events.

```text
Domain Pack Workflow
        |
        v
RecoverableWorkflowEngine
        |
        +--> EventBus
        +--> WorkflowStack
        +--> Action / Condition Handlers
        +--> CapabilityRequirement
        +--> ToolRegistry
        +--> CheckpointStore
```

The Runtime does not know about images, layers, themes, Figma or provider-specific visual semantics.

## Runtime engines

### WorkflowEngine

`WorkflowEngine` provides synchronous lifecycle and graph execution. It registers Workflow definitions, action handlers and condition handlers, creates runs, validates contracts, traverses graphs and controls lifecycle transitions.

Important operations include:

- `create_run`
- `execute`
- `start`
- `pause`
- `resume`
- `execute_action`
- `complete`
- `fail`
- `retry`
- `cancel`
- `latest_checkpoint`

### RecoverableWorkflowEngine

`RecoverableWorkflowEngine` extends the execution path with schema-versioned checkpoints, deterministic completed-node cursors, run restoration and capability-based Tool execution.

Important operations include:

- `restore_run`
- checkpoint restoration into a finite Workflow stack
- completed-node skipping after recovery
- capability execution through `ToolRegistry`

A node recorded as completed is not executed again after restoration. A node that failed before its completion checkpoint may execute again, so recovery currently provides at-least-once semantics for that failing node.

## Graph traversal

Supported node behavior:

- `Sequence`: executes children in order.
- `Parallel`: currently executes children deterministically in order while preserving the semantic boundary for a future scheduler.
- `Selector`: executes children until one succeeds.
- `Condition`: selects the first child when true and the second child when false.
- `Action`: invokes a registered domain action.
- `Subworkflow`: pushes a child frame onto the finite call stack, executes the child graph and merges its context back into the parent frame.
- `Approval`: pauses in `Waiting Approval` without auto-completing the run.
- `Review`: emits review lifecycle events and executes its child graph.

## WorkflowRun and stack

A run contains a stable `run_id`, root Workflow definition, finite Workflow call stack, input and output values, current lifecycle state and an optional error.

The root run identity remains stable while child Workflow frames are pushed and popped. Child execution does not create an unrelated top-level run.

## CheckpointStore

`CheckpointStore` is the persistence boundary for runtime snapshots. The default `InMemoryCheckpointStore` is suitable for tests and embedded execution, but it is not durable.

A store implements:

- `save(run_id, checkpoint)`
- `latest(run_id)`
- `list(run_id)`

Snapshots include schema version, Workflow and node identity, state, retry count, stack frames, local context and completed-node cursors. A database, object store or event-log adapter can implement this protocol without changing Domain Pack Workflow definitions.

## Capability and Tool execution

Workflow definitions depend on capabilities rather than providers.

```text
Workflow
→ CapabilityRequirement
→ ToolRegistry
→ ToolAdapter
→ Provider
```

`resolve()` remains the backward-compatible capability and feature discovery API. Health, configuration validation, timeout, retry and fallback governance are applied during execution.

The Tool Runtime provides standard configuration, availability, authentication, timeout and retryable error contracts. Provider fallback is deterministic and bounded by `ToolExecutionPolicy`.

AIPG does not claim a Provider Adapter is available until its configuration, credentials, permissions and health checks are valid.

## EventBus

The current Event Bus is synchronous and in-memory. It supports exact event subscriptions and wildcard subscriptions.

Events include:

- `workflow.created`
- `workflow.started`
- `workflow.status_changed`
- `workflow.child_started`
- `workflow.child_completed`
- `workflow.completed`
- `node.started`
- `node.completed`
- `action.started`
- `action.completed`
- `capability.started`
- `capability.completed`
- `review.started`
- `review.completed`

## State transitions

The Runtime rejects lifecycle transitions that do not match the state machine. Terminal states cannot be resumed or completed again.

```text
Pending -> Running
Running -> Waiting Tool -> Running
Running -> Waiting Child -> Running
Running -> Waiting Approval -> Running
Running -> Reviewing -> Running
Running -> Completed
Running -> Failed -> Running (bounded retry)
Running -> Cancelled
```

## Domain Pack integration

A Domain Pack registers actions, conditions, Artifact semantics, reviews and exporters instead of embedding provider logic in the Runtime.

```python
engine.register_action("image-generation", generate_image)
engine.register_condition("has-master-image", has_master_image)
```

Action results are merged into the active frame context. Child Workflow results are copied into `child_result` and merged into the parent context.

## Current limitations

- `Parallel` is ordered and deterministic, not concurrent.
- No durable scheduler or external execution queue exists yet.
- The default CheckpointStore is in-memory.
- Recovery uses at-least-once semantics for the failing node.
- Approval persistence, compensation and rollback are not implemented.
- Not every GUIF Workflow has migrated to the AIPG Runtime.
- Real Provider Adapter availability depends on deployment configuration.

## Current priorities

1. Complete the first real Provider Adapter integration.
2. Add durable scheduler and queue contracts.
3. Add a durable CheckpointStore implementation.
4. Connect Artifact lifecycle updates to Workflow and capability outputs.
5. Migrate one production GUIF Workflow end-to-end.
