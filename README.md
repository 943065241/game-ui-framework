# Game UI Framework (GUIF)

**English** | [简体中文](README.zh-CN.md)

GUIF is a local-first, AI-agnostic framework for planning, directing, contracting, prompting, approving, executing, reviewing, exporting, and evolving game UI production work.

## Status

`v1.0.0-alpha.17` — Workflow-driven Runtime Pipelines, deterministic Planner, Director, Theme, Resource, Prompt, and Semantic QA Agents, persistent Approval decisions, Provider Adapter execution gates, a deterministic Dry-run Provider, persisted Artifact records, relevance-based Context selection, resumable Task Runs, Engine Adapter exports, deterministic validation, protected editing, and Git-friendly Project knowledge.

## Product specification

The bilingual living product specification is maintained at [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md).

Product direction, architecture, capability status, compatibility, priorities, risks, and acceptance criteria must be updated there in the same release or pull request as the implementation change.

## What works now

- `guif init <project>` creates an isolated Project workspace.
- `guif run "<requirement>" --project <project>` resolves a Workflow, selects relevant Context, executes Agents, and persists checkpoints.
- `planner` creates a validated UI Production Plan.
- `director` reviews composition, hierarchy, Theme constraints, Resource reuse, Memory constraints, conflicts, and approval points.
- `theme` resolves an active Theme or creates a reviewable inferred Theme contract.
- `resource` creates validated Resource Manifest candidates without silently modifying Project truth.
- `prompt` creates a provider-independent Prompt IR with jobs, constraints, references, output contracts, blockers, approvals, capabilities, and provenance.
- `qa` performs deterministic Contract QA and maintains an explicit Export Gate.
- Approval decisions are persisted and control whether Prompt jobs are executable.
- Provider execution is rejected unless the Task is complete, Prompt IR is `ready`, required approvals are satisfied, Contract QA passes, and Provider capabilities match.
- The built-in `dry-run` Provider produces deterministic non-visual execution receipts without making an external call.
- Successful Provider execution registers an Artifact record with identity, path, SHA-256, MIME type, dimensions, provider metadata, references, output contract, approval snapshot, and QA state.
- Provider failures are persisted without changing the completed Task lifecycle or deleting Approval history.
- Task Runs are inspectable and resumable after Pipeline failures.
- Project, Theme, Workflow, Resource, Image Asset, protected-pixel, and Engine Adapter validation are available.
- The test suite targets Python 3.10, 3.11, and 3.12.

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

## End-to-end contract flow

```text
User Requirement
  -> ChatGPT / Agent Host
  -> GUIF Runtime
       -> complete Project Context snapshot
       -> relevance-based Context selection
       -> Workflow -> Pipeline
       -> Planner
       -> Director
       -> Theme
       -> Resource
       -> Prompt IR
       -> Semantic Contract QA
       -> persistent Approval
       -> Provider Adapter
       -> Artifact Registry
       -> future Visual QA / Revision
       -> future gated Export Agent
```

Runtime remains independent from OpenAI and other model providers.

```python
from pathlib import Path
from guif.runtime import Runtime

runtime = Runtime(Path.cwd())
task = runtime.run(
    "LeekParty",
    "Create a 1080x2340 portrait medieval harbor shop page and export Unity",
    pipeline="ui-production",
)

for approval_id in task.state["approval_state"]["required_ids"]:
    task = runtime.approve(
        "LeekParty",
        task.task_id,
        approval_id,
        actor="reviewer@example.com",
    )

job_id = task.state["prompt_ir"]["jobs"][0]["id"]
task = runtime.execute_job(
    "LeekParty",
    task.task_id,
    job_id,
    provider_id="dry-run",
)

print(runtime.list_artifacts("LeekParty", task.task_id))
```

## Workflow-driven Pipelines

Workflow schema v2 declares both human-readable steps and executable Agents:

```json
{
  "schema_version": 2,
  "id": "ui-production",
  "name": "Complete UI Production",
  "manager": "UI Director",
  "steps": [
    "Create a structured UI production plan",
    "Review art direction and resource reuse",
    "Resolve theme constraints",
    "Resolve production resource contracts",
    "Build model-neutral generation instructions",
    "Run semantic and technical QA"
  ],
  "agents": ["planner", "director", "theme", "resource", "prompt", "qa", "export"]
}
```

Project Workflows override built-in Workflows with the same ID. Runtime persists the resolved source, manager, steps, and Agent order. Resume is rejected when the current Agent order differs from the stored Pipeline.

## Approval gate

Approval decisions are stored in:

```text
projects/<project>/runs/<task-id>/approvals.json
```

Supported decisions:

```text
approved
rejected
changes-requested
```

Gate behavior:

```text
pending approvals
  -> Prompt IR: review-required
  -> executable: false

rejected or changes-requested
  -> Prompt IR: blocked
  -> executable: false

all required approvals accepted and no other blockers
  -> Prompt IR: ready
  -> executable: true
```

Approval never writes Theme or Resource proposals into Project truth and never calls a Provider by itself. Decision history is append-only; the latest decision controls the current gate.

## Provider Adapter contract

Provider Adapters implement a model-neutral execution boundary:

```text
ExecutionRequest
  -> ProviderAdapter
  -> ExecutionResult
  -> Artifact Registry
```

The default registry currently contains:

```text
dry-run
```

The Dry-run Adapter supports the declared image capabilities for contract testing, but:

- performs no network or external Provider call;
- generates no image pixels;
- reports `simulation: true` and `visual: false`;
- writes a deterministic JSON execution receipt;
- reports `billable: false`.

A Provider cannot execute a Job unless:

1. the Runtime Task is `completed`;
2. Prompt IR is `ready`;
3. the Job is `executable: true`;
4. Approval status is `approved` or `not-required`;
5. Contract QA status is `passed`;
6. the Provider advertises every capability required by the Job;
7. Providers that require real references receive successfully bound Project files.

## Artifact Registry

Successful execution creates a file under:

```text
projects/<project>/runs/<task-id>/artifacts/
```

and persists registries in:

```text
artifacts.json
executions.json
```

An Artifact record contains:

```text
artifact_id
job_id and artifact_kind
provider, model, and request metadata
relative file path
SHA-256 and byte size
MIME type and dimensions
simulation and visual flags
Output Contract
bound Reference records
Approval snapshot
Prompt provenance
QA status
```

Artifact registration does not imply visual approval. The current Semantic QA Agent detects registered Artifact metadata but still records `artifact_review.status: "not-run"` because no visual inspection Adapter exists. Export therefore remains blocked.

## Provider failure behavior

Provider attempts are checkpointed before invocation. A failure records:

```text
execution_id
job_id
provider_id
attempt number
request snapshot
exception type and message
started_at and completed_at
```

The Task remains `completed`, Approval history remains intact, and no Artifact is registered for the failed attempt.

## CLI

```bash
guif init LeekParty

guif run "Create a 1080x2340 portrait medieval harbor shop page for Unity" \
  --project LeekParty \
  --pipeline ui-production

guif run-approval-list <task-id> --project LeekParty
guif run-approve <task-id> <approval-id> \
  --project LeekParty \
  --actor reviewer@example.com

guif provider-list

guif run-execute <task-id> <job-id> \
  --project LeekParty \
  --provider dry-run

guif run-artifact-list <task-id> --project LeekParty
guif run-artifact-show <task-id> <artifact-id> --project LeekParty

guif run-list --project LeekParty
guif run-show <task-id> --project LeekParty
guif validate LeekParty
```

## Persisted Task Run

```text
projects/<project>/runs/<task-id>/
  task.json
  context.json
  events.jsonl
  outputs.json
  approvals.json        when Prompt approval exists
  executions.json       after a Provider attempt
  artifacts.json        after Artifact registration
  artifacts/            Artifact files
  error.json            only while Pipeline execution is failed
```

`run-list` includes Approval status, pending Approval count, Artifact count, and Provider execution count.

## Current limitations

- `dry-run` is the only built-in Provider; no real image model is called.
- No visual Semantic QA Adapter exists.
- Artifact records are file-based and have no database, remote object storage, or retention policy.
- Approval actor identity is a string, not an authenticated Host identity.
- Existing Approval is not yet automatically invalidated by an upstream Contract hash change.
- The built-in `export` Agent remains Contract-only and does not yet consume Artifact and QA gates.
- Engine Sidecars are deterministic GUIF metadata, not native engine-generated imports.

## Operating principles

1. Natural language is the primary user interface; CLI is for implementation, debugging, and CI.
2. Git and Project files remain the long-term source of truth.
3. Runtime and Prompt IR stay provider-independent.
4. Workflow manifests are the executable source of Pipeline order.
5. Agents do not directly invoke one another.
6. Inferred Theme and Resource proposals require review before Project mutation.
7. Prompt jobs require explicit Approval and passing Contract QA before Provider execution.
8. Capability and Reference binding gates are enforced before Provider invocation.
9. Provider failures must preserve Task, Approval, and execution evidence.
10. Artifact registration does not imply visual QA.
11. Export requires an explicit passing Artifact and QA gate.
12. A release is complete only when Feature, Tests, CI, both READMEs, Version Metadata, and the Product Specification agree.

## Repository direction

The next priority is **alpha.18: Visual Artifact Inspection Contract and Revision Planning**. GUIF must distinguish real visual Artifacts from simulations, validate image metadata against Output Contracts, create structured visual-review requests, and preserve `not-run` whenever no capable inspection Adapter is available. Priorities and acceptance criteria are maintained in [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md).
