# Game UI Framework (GUIF)

**English** | [简体中文](README.zh-CN.md)

GUIF is a local-first game UI production framework with configurable Hosts and Tools. ChatGPT is the default Host, while image generation, image editing, visual inspection, Git operations, and export remain replaceable Tool capabilities.

## Status

`v1.0.0-alpha.20` closes the first controlled visual-revision loop. A Visual Review finding can now become a versioned edit Job, receive its own Approval decision, bind the original Artifact as an immutable SHA-256-verified reference, route through the configured image-editing Tool, register a replacement Artifact, run an automatic metadata recheck, and supersede the source only after a passing semantic visual review.

The default revision Tool remains `chatgpt-image` through an external ChatGPT Host handoff. GUIF Core does not pretend to generate or edit pixels itself.

## Product specification

The bilingual living product specification is maintained at [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md). Product direction, architecture, capability status, compatibility, priorities, risks, and acceptance criteria must change there in the same release or pull request as implementation changes.

## Default production path

```text
User
  -> ChatGPT Host                         default, configurable
  -> GUIF Runtime
       -> Context selection
       -> Workflow -> Pipeline
       -> Planner / Director / Theme / Resource
       -> Model-neutral Prompt IR
       -> Contract QA
       -> initial Approval Gate
       -> Tool Resolver
       -> image generation Tool
       -> Artifact Registry
       -> Visual Review
            -> finding
            -> Revision Plan
            -> versioned Revision Job
            -> independent Revision Approval
            -> image-editing Tool
            -> replacement Artifact
            -> automatic metadata recheck
            -> semantic visual recheck
            -> gated supersession
       -> gated Export
```

ChatGPT has two separate roles:

- **ChatGPT Host** handles conversation, confirmation, orchestration, Tool invocation, and result presentation.
- **`chatgpt-image` Tool** performs image generation or editing through a persisted external-callback handoff.

Both are defaults, not hard-coded GUIF Core dependencies.

## Controlled revision lifecycle

A Revision Plan created by Visual Review is not executable by itself.

```text
Revision Plan: proposed
  -> construct Revision Job
  -> approval-pending
  -> approve / reject / request changes
  -> ready
  -> Tool resolution
  -> waiting-for-tool-result
  -> replacement Artifact registered
  -> automatic metadata review
  -> semantic review
  -> source superseded only when replacement passes
```

### Revision Job construction

```python
revision_id = task.state["revision_plans"]["records"][0]["revision_id"]
task = runtime.create_revision_job("LeekParty", task.task_id, revision_id)

revision_job = runtime.list_revision_jobs("LeekParty", task.task_id)[0]
```

The Job preserves the original Prompt Job contracts and adds:

- `operation: edit`;
- Revision objectives derived from Visual findings;
- the source Artifact as `revision-source-artifact`;
- immutable expected SHA-256 identity;
- source Job, source Artifact, Review, and Revision Plan provenance;
- preservation constraints for unrelated and protected regions;
- a separate Revision Approval point;
- a new output Artifact requirement rather than in-place overwrite.

### Independent Revision Approval

```python
task = runtime.approve_revision(
    "LeekParty",
    task.task_id,
    revision_id,
    actor="art-director@example.com",
    comment="Proceed with the controlled edit.",
)
```

Supported decisions are:

```text
approved
rejected
changes-requested
```

The original production Approval does not automatically authorize later editing. Each constructed Revision Job must receive its own persisted decision and history.

### ChatGPT image-editing handoff

```python
task = runtime.execute_revision(
    "LeekParty",
    task.task_id,
    revision_id,
)

handoff = runtime.list_tool_handoffs("LeekParty", task.task_id)[-1]
```

With the default Project configuration, GUIF resolves `image-editing` to `chatgpt-image`. The handoff contains the source image reference, edit objectives, negative constraints, preservation rules, Output Contract, acceptance criteria, and Revision Approval snapshot.

After ChatGPT edits the image, the Host submits the real file:

```python
task = runtime.submit_tool_result(
    "LeekParty",
    task.task_id,
    handoff["handoff_id"],
    content=image_bytes,
    filename="shop-page-revision.png",
    mime_type="image/png",
    width=1080,
    height=2340,
    model_id="chatgpt-image",
)
```

GUIF registers the replacement, links it to the source, and immediately performs eligibility, file-integrity, and image-metadata review. Without a semantic inspector, the result remains `not-run` and the source remains active.

### Gated supersession

A replacement does not overwrite or deactivate its source merely because it was generated.

```text
replacement metadata passed, semantic review not-run
  -> source remains registered
  -> replacement is a candidate

replacement semantic review passed
  -> source becomes stale
  -> source.superseded_by = replacement
  -> replacement.supersedes includes source
  -> Revision Plan becomes resolved
```

A failed, blocked, or review-required replacement remains linked for audit but does not supersede the source.

## Immutable source binding

Revision references include the source Artifact file and its expected SHA-256. Before an editing Tool receives the request, GUIF verifies:

```text
source remains inside the Project
file still exists
actual SHA-256 == registered source SHA-256
Tool supports image-editing and protected-region-editing
required References are bound
Revision Approval == approved
Contract QA == passed
```

A missing or modified source fails closed into `waiting-for-tool`; GUIF does not silently edit a different file.

## Configurable Host and Tool routing

Tool selection precedence remains:

```text
explicit Tool
  -> Task override
  -> Project configuration
  -> Workspace configuration
  -> Framework default
```

New Projects default to:

```json
{
  "execution": {
    "schema_version": 1,
    "mode": "production",
    "default_host": "chatgpt",
    "tools": {
      "image-generation": {"primary": "chatgpt-image", "fallback": []},
      "image-editing": {"primary": "chatgpt-image", "fallback": []}
    }
  }
}
```

Missing or unhealthy production Tools enter `waiting-for-tool`. `dry-run` is never an implicit production fallback.

## CLI

```bash
guif run-revision-list <task-id> --project LeekParty

guif run-revision-create <task-id> <revision-id> \
  --project LeekParty

guif run-revision-approval <task-id> <revision-id> \
  --project LeekParty

guif run-revision-approve <task-id> <revision-id> \
  --project LeekParty \
  --actor art-director@example.com

guif run-revision-execute <task-id> <revision-id> \
  --project LeekParty

guif run-tool-handoff-list <task-id> --project LeekParty

guif run-tool-submit <task-id> <handoff-id> edited.png \
  --project LeekParty \
  --mime-type image/png \
  --width 1080 \
  --height 2340

guif run-artifact-review <task-id> <replacement-artifact-id> \
  --project LeekParty \
  --inspector <inspector-id>
```

General Tool commands remain available:

```bash
guif host-show
guif tool-list
guif tool-health chatgpt-image --project LeekParty
guif tool-bind image-editing chatgpt-image --project LeekParty
guif tool-scaffold custom-editor image-editing protected-region-editing
```

## Persisted Task Run

```text
projects/<project>/runs/<task-id>/
  task.json
  context.json
  events.jsonl
  outputs.json
  approvals.json
  tool-resolution.json
  tool-handoffs.json
  executions.json
  artifacts.json
  visual-reviews.json
  revision-plans.json
  revision-execution.json
  artifacts/
  error.json                  only while Pipeline execution is failed
```

`run-list` includes Revision Plan count, Revision Job count, pending Revision Approval count, Tool Resolution status, Tool Handoff count, Artifact count, Review count, and aggregate Artifact Review status.

## Existing capabilities

GUIF also provides:

- deterministic Planner, Director, Theme, Resource, Prompt, and Semantic QA Agents;
- Workflow-driven Pipelines and persistent Task Runs;
- relevance-based Project Context selection;
- initial production Approval decisions and history;
- Tool Manifests, Registry, health checks, and layered resolution;
- ChatGPT external image handoffs and explicit result submission;
- Artifact identity, SHA-256, MIME, dimensions, References, and provenance;
- visual eligibility and deterministic image metadata checks;
- optional semantic Visual Inspection Adapters;
- protected-pixel composition checks;
- Generic, Unity, Godot, and Unreal export metadata Adapters.

## Install for development

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
pip install -e .[dev]
pytest -q
```

## Current limitations

- ChatGPT Host still needs product-side orchestration to consume a handoff and submit the resulting file automatically.
- The default Visual Inspector Registry is empty, so semantic review requires a Host-registered inspector.
- Revision Jobs support one source Artifact and one replacement result per execution attempt; multi-source and mask packages need a later contract.
- Tool installation, connection, permissions, cost disclosure, and Credentials remain Host-managed.
- Artifact storage is file-based and has no remote object store or retention policy.
- Approval actors are strings rather than authenticated Host identities.
- The built-in Export Agent remains Contract-only and does not yet materialize the final reviewed Artifact set.

## Operating principles

1. ChatGPT is the default Host, not a hard-coded dependency.
2. Image generation and editing are configurable Tools.
3. Every Revision Job has a separate Approval gate.
4. A revision source is immutable and hash-verified before Tool execution.
5. A replacement never overwrites the source file.
6. Metadata review is not semantic visual approval.
7. Supersession requires a passing replacement review.
8. Missing Tools or source References fail closed.
9. `dry-run` is explicit contract testing only.
10. Feature, Tests, CI, both READMEs, Version Metadata, and the Product Specification must agree for a release.

## Repository direction

The next priority is **alpha.21: Host and Tool Discovery plus Connection Workflow**. GUIF should distinguish registered, available, and installable Tools; persist connection requests; disclose permissions, data scope, external calls, cost, and Credentials; retry health checks; and validate Plugin contracts before registration.
