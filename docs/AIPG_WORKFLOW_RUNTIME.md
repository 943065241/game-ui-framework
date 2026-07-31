# AIPG Workflow Runtime

## Purpose

AIPG owns the domain-neutral Workflow lifecycle and graph execution model. GUIF
and future Domain Packs define Workflow templates and bind domain actions, while
the Runtime owns run identity, state transitions, traversal, nested calls,
retries, checkpoints and lifecycle events.

```text
Domain Pack Workflow
        |
        v
WorkflowEngine
        |
        +--> EventBus
        +--> WorkflowStack
        +--> Action / Condition Handlers
        +--> CheckpointStore
```

The Runtime does not know about images, layers, themes, Figma, OpenAI or any
other visual or provider-specific concept.

## Public contracts

### WorkflowEngine

`WorkflowEngine` registers Workflow definitions, action handlers and condition
handlers. It creates runs, validates contracts, traverses graphs and controls
lifecycle transitions.

Important operations:

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

### Graph traversal

`execute` traverses the registered root node automatically.

Supported node behavior:

- `Sequence`: executes children in order.
- `Parallel`: currently executes children deterministically in order while
  preserving the parallel semantic boundary for a future scheduler.
- `Selector`: executes children until one succeeds.
- `Condition`: selects the first child when true and second child when false.
- `Action`: invokes a registered domain action.
- `Subworkflow`: pushes a child frame onto the finite call stack, executes the
  child graph and merges its context back into the parent frame.
- `Approval`: pauses in `Waiting Approval` without auto-completing the run.
- `Review`: emits review lifecycle events and executes its child graph.

### WorkflowRun

A run contains:

- stable `run_id`
- root Workflow definition
- finite Workflow call stack
- input and output values
- current error, when present

The root run identity remains stable while child Workflow frames are pushed and
popped. Child execution does not create an unrelated top-level run.

### CheckpointStore

`CheckpointStore` is the persistence boundary for runtime snapshots. The default
`InMemoryCheckpointStore` is suitable for tests and embedded execution.

A store implements:

- `save(run_id, checkpoint)`
- `latest(run_id)`
- `list(run_id)`

Snapshots are written after actions, child Workflow completion, pause, failure,
completion and cancellation. They include Workflow id, node id, state, retry
count, stack depth and local context.

A database, object store or event-log adapter can implement this protocol
without changing Domain Pack Workflow definitions.

### EventBus

The initial Event Bus is synchronous and in-memory. It supports exact event
subscriptions and wildcard subscriptions.

Events include Workflow, node, action, child Workflow and review lifecycle
notifications such as:

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
- `review.started`
- `review.completed`

## State transitions

The Runtime rejects lifecycle transitions that do not match the state machine.
Terminal states cannot be resumed or completed again.

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

A Domain Pack registers actions and conditions instead of embedding provider
calls in the Workflow Engine.

```python
engine.register_action("image-generation", generate_image)
engine.register_condition("has-master-image", has_master_image)
```

Action results are merged into the active frame context. Child Workflow results
are copied into `child_result` and merged into the parent context.

## Current limitations

This iteration does not yet provide:

- asynchronous or truly concurrent Parallel execution
- durable scheduler queues
- automatic restoration of a run from serialized checkpoints
- provider selection and invocation through Capability Registry
- approval service persistence
- compensation or rollback handlers

## Next iteration

1. Route action capability requirements through `ToolRegistry`.
2. Add checkpoint restoration and resumable graph cursors.
3. Adapt one GUIF Workflow to execute through `WorkflowEngine`.
4. Add scheduler contracts for asynchronous and truly parallel execution.
5. Add Artifact production events and lineage updates around action results.
