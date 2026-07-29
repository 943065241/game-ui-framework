# Game UI Framework (GUIF)

**English** | [简体中文](README.zh-CN.md)

GUIF is a local-first game UI production framework with configurable Hosts and Tools. It plans, directs, contracts, approves, executes, inspects, revises, and exports game UI work while keeping Project files and Git as the long-term source of truth.

## Status

`v1.0.0-alpha.19` makes Host and Tool selection configurable. ChatGPT is the default Host and `chatgpt-image` is the default production Tool for image generation and editing. Missing or unavailable Tools now fail closed into recoverable waiting states; GUIF never silently falls back to `dry-run` for production work.

The release also adds external Tool handoffs, Host result submission, layered Tool configuration, Tool manifests, health checks, Adapter scaffolding, and Task schema v3 waiting states.

## Product specification

The bilingual living product specification is maintained at [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md). Product direction, architecture, capability status, compatibility, priorities, risks, and acceptance criteria must be updated there in the same release or pull request as implementation changes.

## Default product path

```text
User
  -> ChatGPT Host                         default, configurable
  -> GUIF Runtime
       -> Context selection
       -> Workflow -> Pipeline
       -> Planner / Director / Theme / Resource
       -> Model-neutral Prompt IR
       -> Contract QA
       -> persistent Approval Gate
       -> Tool Resolver
            -> chatgpt-image              default production Tool
            -> another registered Tool    Project / Workspace / Task override
            -> dry-run                    explicit test-only selection
       -> external Tool Handoff or direct execution
       -> Artifact Registry
       -> Visual Review / Revision
       -> gated Export
```

ChatGPT has two separate architectural roles:

- **ChatGPT Host** manages conversation, user confirmation, orchestration, and result presentation.
- **`chatgpt-image` Tool** performs image generation or editing through an external-callback handoff.

They are defaults, not hard-coded dependencies. A custom Host or Tool can replace either role independently.

## Host, Tool, and Adapter

A **Host** declares the capabilities available in the current environment. The default Host profile is:

```json
{
  "host_id": "chatgpt",
  "capabilities": [
    "image-generation",
    "image-editing",
    "protected-region-editing",
    "transparent-output",
    "visual-inspection",
    "github-operation"
  ]
}
```

A **Tool** declares a versioned Manifest:

```json
{
  "tool_id": "chatgpt-image",
  "version": "1.0",
  "execution_mode": "external-callback",
  "capabilities": [
    "image-generation",
    "image-editing",
    "protected-region-editing",
    "transparent-output"
  ],
  "input_contract": "prompt-ir-job-v1",
  "output_contract": "artifact-submission-v1",
  "production_allowed": true
}
```

A **Tool Adapter** translates GUIF's Tool Request into either:

- a direct execution result; or
- an external Host handoff that later receives a submitted result file.

Legacy `ProviderAdapter` execution remains available when `provider_id` is supplied explicitly, but new product APIs use the broader Tool terminology.

## Configuration precedence

Tool selection is resolved in this order:

```text
explicit Tool on this execution
  -> Task execution override
  -> Project configuration
  -> Workspace configuration
  -> Framework default
```

New Projects include:

```json
{
  "execution": {
    "schema_version": 1,
    "mode": "production",
    "default_host": "chatgpt",
    "tools": {
      "image-generation": {
        "primary": "chatgpt-image",
        "fallback": []
      },
      "image-editing": {
        "primary": "chatgpt-image",
        "fallback": []
      }
    }
  }
}
```

Workspace configuration can be stored in `.guif/config.json`. Task-level overrides may be stored in `task.state["execution_overrides"]`.

## Missing Tool behavior

When a required capability is not configured, not registered, unhealthy, unsupported by the current Host, or missing required Reference files, GUIF does not execute a simulation automatically. It persists a resolution record and changes the Task to:

```text
waiting-for-tool
```

The record contains:

- required capability and complete capability set;
- selected Tool and configuration source;
- Host and execution mode;
- health result;
- compatible registered candidates;
- reason and recovery actions.

The user or Host can then:

1. bind a registered Tool;
2. connect or install another Tool;
3. create and implement an Adapter scaffold;
4. explicitly select `dry-run` for contract testing;
5. cancel the pending execution.

After configuration, execute the same persisted Job again. Planning, Approval, and existing Context are not repeated.

## ChatGPT external handoff

Calling `Runtime.execute_job()` without `tool_id` or `provider_id` uses the configured Tool. With the default Project configuration, GUIF creates a `chatgpt-image` handoff and changes the Task to:

```text
waiting-for-tool-result
```

```python
job_id = task.state["prompt_ir"]["jobs"][0]["id"]
task = runtime.execute_job("LeekParty", task.task_id, job_id)

handoff = runtime.list_tool_handoffs("LeekParty", task.task_id)[0]
```

The handoff contains the full Prompt Job, bound References, Approval snapshot, Host action, safety constraints, and expected submission contract.

After ChatGPT generates or edits the image, the Host submits the real file:

```python
task = runtime.submit_tool_result(
    "LeekParty",
    task.task_id,
    handoff["handoff_id"],
    content=image_bytes,
    filename="shop-page.png",
    mime_type="image/png",
    width=1080,
    height=2340,
    model_id="chatgpt-image",
)
```

GUIF then verifies handoff identity, registers the Artifact, preserves the Approval and execution record, restores the Task to `completed`, and refreshes QA. Artifact registration still does not imply visual approval.

## `dry-run` policy

`dry-run` is a deterministic contract-testing Tool. It:

- performs no external call;
- generates no image pixels;
- is not an automatic production candidate;
- reports `simulation: true`, `visual: false`, and `billable: false`;
- can be used in production mode only when selected explicitly.

```python
task = runtime.execute_job(
    "LeekParty",
    task.task_id,
    job_id,
    tool_id="dry-run",
)
```

A missing production Tool never silently becomes `dry-run`.

## Tool health and Adapter scaffold

```python
runtime.get_host_profile()
runtime.list_tools()
runtime.tool_health("chatgpt-image", project="LeekParty")
runtime.bind_project_tool("LeekParty", "image-generation", "chatgpt-image")
runtime.scaffold_tool(
    "custom-image",
    ("image-generation", "transparent-output"),
)
```

A generated scaffold contains:

```text
tools/<tool-id>/
  tool.json
  adapter.py
  config.schema.json
  README.md
  tests/test_contract.py
```

The scaffold is marked `adapter-required` and `implementation_ready: false`. It is not automatically registered or treated as usable.

## Existing production contracts

GUIF still provides:

- deterministic Planner, Director, Theme, Resource, Prompt, and Semantic QA Agents;
- relevance-based Project Context selection;
- persistent Approval decisions and history;
- Workflow-driven Pipelines and resumable Pipeline failures;
- Artifact identity, SHA-256, MIME, dimensions, References, and provenance;
- visual Artifact eligibility and deterministic image metadata review;
- optional Visual Inspection Adapter contract;
- persisted Revision Plans and Artifact supersession;
- protected-pixel editing checks;
- Generic, Unity, Godot, and Unreal export metadata Adapters.

## CLI

```bash
guif init LeekParty

guif host-show
guif tool-list
guif tool-health chatgpt-image --project LeekParty
guif tool-bind image-generation chatgpt-image --project LeekParty

guif run "Create a medieval harbor shop page for Unity" \
  --project LeekParty \
  --pipeline ui-production

guif run-approve <task-id> <approval-id> \
  --project LeekParty \
  --actor reviewer@example.com

# Default: resolve Project Tool and prepare a ChatGPT handoff
guif run-execute <task-id> <job-id> --project LeekParty

guif run-tool-resolution <task-id> --project LeekParty
guif run-tool-handoff-list <task-id> --project LeekParty

guif run-tool-submit <task-id> <handoff-id> output.png \
  --project LeekParty \
  --mime-type image/png \
  --width 1080 \
  --height 2340

# Explicit simulation only
guif run-execute <task-id> <job-id> \
  --project LeekParty \
  --tool dry-run

guif tool-scaffold custom-image image-generation transparent-output
```

Legacy Provider execution remains available through `--provider <id>`.

## Persisted Task Run

```text
projects/<project>/runs/<task-id>/
  task.json
  context.json
  events.jsonl
  outputs.json
  approvals.json
  tool-resolution.json    after Tool resolution
  tool-handoffs.json      after external-callback preparation
  executions.json         after Tool or legacy Provider attempts
  artifacts.json          after Artifact registration
  visual-reviews.json
  revision-plans.json
  artifacts/
  error.json              only while Pipeline execution is failed
```

`run-list` includes Tool resolution status, Tool handoff count, Approval status, Artifact count, execution count, Visual Review count, Revision Plan count, and aggregate Artifact Review status.

## Current limitations

- `chatgpt-image` is an external Host bridge; GUIF Core cannot invoke ChatGPT image capabilities by itself.
- The default CLI process can prepare a handoff, but the ChatGPT Host must generate or edit the image and submit the result.
- Tool installation and credentials remain Host-managed; alpha.19 persists recovery actions but does not install third-party software automatically.
- The default Visual Inspector Registry is empty.
- Revision Plans are persisted, but automatic Revision Job construction is not implemented yet.
- Artifact storage is file-based and has no remote object storage, database, or retention policy.
- Approval actor identity is still an unauthenticated string.
- The built-in `export` Agent remains Contract-only and does not yet consume the final visual QA gate.

## Operating principles

1. ChatGPT is the default Host, not a hard-coded dependency.
2. Image generation, image editing, inspection, Git operations, and export are configurable Tools.
3. Tool resolution uses explicit, Task, Project, Workspace, then Framework precedence.
4. Production execution fails closed when a Tool is missing or unhealthy.
5. `dry-run` is never an implicit production fallback.
6. External Tool completion requires an explicit result submission.
7. Simulation, metadata validation, and semantic visual approval remain distinct.
8. Inferred Theme and Resource proposals require review before Project mutation.
9. Artifact, Approval, execution, review, and revision provenance must be retained.
10. A release is complete only when Feature, Tests, CI, both READMEs, Version Metadata, and the Product Specification agree.

## Repository direction

The next priority is **alpha.20: Revision Job Construction and Controlled Revision Execution**. GUIF should convert an approved Revision Plan into a versioned edit Job, bind the source Artifact as an immutable Reference, create a new Approval gate, route the Job through the configured image-editing Tool, submit the replacement Artifact, and trigger automatic re-review without deleting prior provenance.
