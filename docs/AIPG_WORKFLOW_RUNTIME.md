# AIPG Workflow Runtime

## Purpose

AIPG now owns the domain-neutral Workflow lifecycle. GUIF and future Domain
Packs define Workflow templates and bind domain actions, while the Runtime owns
run identity, state transitions, retries, checkpoints and lifecycle events.

```text
Domain Pack Workflow
        |
        v
WorkflowEngine
        |
        +--> EventBus
        +--> WorkflowStack
        +--> Action Handler
        +--> Checkpoint Snapshot
```

The Runtime does not know about images, layers, themes, Figma, OpenAI or any
other visual or provider-specific concept.

## Public contracts

### WorkflowEngine

`WorkflowEngine` registers Workflow definitions and action handlers, creates
runs, validates input/output contracts and controls lifecycle transitions.

Supported operations:

- `create_run`
- `start`
- `pause`
- `resume`
- `execute_action`
- `complete`
- `fail`
- `retry`
- `cancel`

### WorkflowRun

A run contains:

- stable `run_id`
- Workflow definition
- finite Workflow call stack
- input and output values
- current error, when present

### EventBus

The initial Event Bus is synchronous and in-memory. It supports exact event
subscriptions and wildcard subscriptions. This contract can later be backed by
a durable message system without changing Domain Pack Workflow definitions.

Lifecycle events currently include:

- `workflow.created`
- `workflow.started`
- `workflow.status_changed`
- `workflow.paused`
- `workflow.resumed`
- `workflow.retried`
- `workflow.completed`
- `workflow.failed`
- `workflow.cancelled`
- `action.started`
- `action.completed`

## State transitions

The Runtime rejects lifecycle transitions that do not match the state machine.
Terminal states cannot be resumed or completed again.

```text
Pending -> Running
Running -> Waiting Tool -> Running
Running -> Waiting Approval -> Running
Running -> Reviewing -> Revising -> Running
Running -> Completed
Running -> Failed -> Running (bounded retry)
Running -> Cancelled
```

The existing states for child Workflow waits remain part of the contract and
will be connected to nested execution in the next Runtime iteration.

## Checkpoints

The initial checkpoint implementation records in-memory snapshots after action
completion, pause, failure, completion and cancellation. Each snapshot contains:

- reason
- status
- current node
- retry count
- local context

This is intentionally a persistence-neutral contract. A later checkpoint store
will serialize and restore these snapshots.

## Domain Pack integration

A Domain Pack registers actions instead of embedding provider calls in the
Workflow Engine.

```python
engine.register_action("image-generation", generate_image)
```

The action handler receives the active `WorkflowFrame` and an argument mapping.
It returns a mapping merged into the frame local context. Provider selection
will move through the AIPG Capability Runtime rather than being hard-coded in
the action handler.

## Current limitations

This iteration is deliberately small and executable. It does not yet provide:

- durable scheduler queues
- persistent checkpoint restoration
- asynchronous or distributed execution
- automatic Workflow graph traversal
- nested child Workflow execution
- provider selection and invocation
- approval service persistence

Those capabilities should build on the current lifecycle and event contracts,
not replace them.

## Next iteration

1. Add graph traversal for Sequence, Selector, Condition and Parallel nodes.
2. Connect Subworkflow nodes to the finite Workflow call stack.
3. Add a persistence-neutral CheckpointStore interface.
4. Route action capability requirements through `ToolRegistry`.
5. Adapt one GUIF Workflow to execute through `WorkflowEngine` as the first
   end-to-end compatibility migration.
