# Game UI Framework (GUIF)

**English** | [简体中文](README.zh-CN.md)

GUIF is a local-first, provider-independent framework for planning, directing, contracting, approving, executing, inspecting, revising, and exporting game UI production work.

## Status

`v1.0.0-alpha.18` adds the Visual Artifact Inspection Contract and Revision Planning layer. GUIF can now distinguish real visual images from simulation receipts, verify persisted file identity, inspect image metadata against Prompt Output Contracts, create provider-neutral Visual Inspection Requests, persist Visual Review records, create traceable Revision Plans, and mark superseded Artifacts as stale.

The built-in production flow currently contains deterministic Planner, Director, Theme, Resource, Prompt, and Semantic QA Agents, persistent Approval gates, Provider Adapter execution, a deterministic Dry-run Provider, Artifact Registry, Visual Review Service, resumable Task Runs, protected editing, and Engine Adapter metadata exports.

## Product specification

The bilingual living product specification is maintained at [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md). Product direction, architecture, capability status, compatibility, priorities, risks, and acceptance criteria must be updated there in the same release or pull request as implementation changes.

## Current executable flow

```text
User Requirement
  -> ChatGPT / Agent Host
  -> GUIF Runtime
       -> Project Context snapshot and relevance selection
       -> Workflow -> Pipeline
       -> Planner
       -> Director
       -> Theme Contract
       -> Resource Contract Bundle
       -> Model-neutral Prompt IR
       -> Semantic Contract QA
       -> persistent Approval Gate
       -> Provider Adapter
       -> Artifact Registry
       -> Visual Review Service
            -> eligibility and file-integrity checks
            -> deterministic image metadata checks
            -> optional Visual Inspection Adapter
            -> Revision Plan
       -> future Revision Execution
       -> future gated Export Agent
```

Runtime and Prompt IR remain independent from OpenAI or any other model provider.

## What works now

- `guif init <project>` creates an isolated Project workspace.
- `guif run "<requirement>" --project <project>` resolves a Workflow, selects relevant Context, executes Agents, and persists checkpoints.
- Planner, Director, Theme, Resource, Prompt, and Semantic QA perform real deterministic domain work.
- Approval decisions are persisted and control whether Prompt jobs are executable.
- Provider execution is rejected unless Task, Prompt, Approval, Contract QA, Capability, and Reference gates pass.
- `dry-run` produces deterministic non-visual execution receipts without external calls or billing.
- Successful execution registers Artifact identity, file, SHA-256, MIME, dimensions, provider metadata, references, Output Contract, Approval snapshot, and provenance.
- Visual review distinguishes simulations from real image Artifacts.
- Real image Artifacts are checked for supported MIME, safe persisted path, file existence, SHA-256 identity, dimensions, format, Alpha, and registered metadata.
- A model-neutral `VisualInspectionRequest` carries visual instructions, negative constraints, Output Contract, references, and acceptance criteria to a compatible inspection Adapter.
- Without an inspection Adapter, semantic visual status remains explicitly `not-run`; metadata validation is never presented as visual-quality approval.
- Visual findings can create persisted Revision Plans linked to the original Prompt job and Artifact.
- A newer Artifact from the same Prompt job can explicitly supersede an older Artifact, which becomes `stale` while provenance is retained.
- Task Runs remain inspectable and resumable after Pipeline failures.
- Tests target Python 3.10, 3.11, and 3.12.

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

Pillow is used for image metadata inspection and is included by the `dev` and `image` extras.

## Python API example

```python
from pathlib import Path

from guif.runtime import Runtime
from guif.visual_review import VisualReviewService

workspace = Path.cwd()
runtime = Runtime(workspace)

task = runtime.run(
    "LeekParty",
    "Create a 1080x2340 portrait medieval harbor shop page for Unity",
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

artifact = runtime.list_artifacts("LeekParty", task.task_id)[0]
task = VisualReviewService(workspace).review(
    "LeekParty",
    task.task_id,
    artifact["artifact_id"],
)

print(task.state["qa_report"]["artifact_review"])
```

Because `dry-run` produces `simulation: true` and `visual: false`, this review returns `not-applicable`, not a visual pass.

## Approval and Provider gates

A Prompt job can execute only when all of these conditions hold:

```text
Task.status == completed
Prompt IR.status == ready
Job.executable == true
Approval == approved or not-required
Contract QA == passed
Provider capabilities satisfy the Job
required Reference files are bound
```

Approval does not write inferred Theme or Resource proposals into Project truth and does not call a Provider by itself. Provider attempts are checkpointed before invocation; failures preserve the completed Task, Approval history, request snapshot, and error evidence.

## Visual Artifact eligibility

A visual review begins by checking the Artifact record:

```text
status is active, not stale
simulation == false
visual == true
MIME is image/png, image/jpeg, or image/webp
file path remains inside the Run directory
file exists
registered SHA-256 matches file bytes
```

Simulation receipts and non-visual files receive:

```text
status: not-applicable
visual_conclusion_claimed: false
```

Ineligible or corrupted visual Artifacts receive a blocking integrity finding.

## Deterministic image metadata review

For eligible images, GUIF inspects:

- actual width and height;
- actual image format;
- Alpha presence and image mode;
- consistency with the Prompt job `canvas` and `output_contract`;
- consistency with dimensions registered by the Provider result.

A metadata mismatch blocks the Artifact and creates a Revision Plan. A metadata pass alone does not claim Theme, composition, content, readability, or usability quality.

## Visual Inspection Adapter contract

A Visual Inspection Adapter receives:

```text
VisualInspectionRequest
  task and project identity
  Artifact and Prompt job identity
  file metadata
  Output Contract
  global page and Theme contract
  visual and content instructions
  negative constraints
  acceptance criteria
  required review dimensions
```

Adapters declare capabilities for:

```text
theme-consistency
composition-and-hierarchy
content-correctness
readability
usability
resource-compliance
```

The default Visual Inspector Registry is intentionally empty. Without a selected capable Adapter, semantic review remains `not-run` and Export remains closed.

## Revision Plans and supersession

Blocking, review, or warning findings can create a persisted Revision Plan containing:

```text
revision_id
source_job_id
source_artifact_id
finding_ids
revision objectives
preservation constraints
next step
```

Revision Plans do not overwrite the source Artifact. When a reviewed replacement is available, it can explicitly supersede the old Artifact. The old record becomes `stale` and points to `superseded_by`; the new record retains a `supersedes` list.

## CLI

```bash
guif init LeekParty

guif run "Create a medieval harbor shop page for Unity" \
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

guif visual-inspector-list
guif run-artifact-review <task-id> <artifact-id> \
  --project LeekParty

guif run-visual-review-list <task-id> --project LeekParty
guif run-revision-list <task-id> --project LeekParty

guif run-artifact-supersede <task-id> <old-artifact-id> <new-artifact-id> \
  --project LeekParty
```

`--inspector <id>` can be supplied to `run-artifact-review` when a Host or Plugin has registered a compatible Visual Inspection Adapter. The default CLI process has no semantic inspector registered.

## Persisted Task Run

```text
projects/<project>/runs/<task-id>/
  task.json
  context.json
  events.jsonl
  outputs.json
  approvals.json          when Prompt approval exists
  executions.json         after Provider attempts
  artifacts.json          after Artifact registration
  visual-reviews.json     after Artifact review
  revision-plans.json     when revisions are proposed
  artifacts/              persisted Artifact files
  error.json              only while Pipeline execution is failed
```

`run-list` includes Approval state, Artifact count, Provider execution count, Visual Review count, Revision Plan count, and aggregate Artifact Review status.

## Current limitations

- `dry-run` remains the only built-in Provider and generates no image pixels.
- The default Visual Inspector Registry is empty; no built-in model currently judges visual semantics.
- Revision Plans are persisted, but Revision Prompt construction and execution are not automated yet.
- Artifact storage is file-based and has no remote object storage, database, or retention policy.
- Approval actor identity is a string, not an authenticated Host identity.
- Existing Approvals and reviews are not yet invalidated automatically by upstream Contract hash changes.
- The built-in `export` Agent remains Contract-only and does not yet consume the final Artifact and Visual QA gate.

## Operating principles

1. Natural language is the primary interface; CLI is for implementation, debugging, and CI.
2. Git and Project files are the long-term source of truth.
3. Runtime, Prompt IR, Provider execution, and Visual Inspection contracts stay provider-independent.
4. Inferred Theme and Resource proposals require review before Project mutation.
5. Prompt jobs require explicit Approval and passing Contract QA before Provider execution.
6. Provider Capability and Reference gates are enforced before invocation.
7. Simulation receipts must never be described as visual Artifacts.
8. Metadata validation must never be described as semantic visual approval.
9. Visual findings and revisions must retain Artifact, Job, and Approval provenance.
10. Export requires passing Contract QA and passing review for every active visual Artifact.
11. A release is complete only when Feature, Tests, CI, both READMEs, Version Metadata, and the Product Specification agree.

## Repository direction

The next priority is **alpha.19: Revision Job Construction and Controlled Revision Execution**. GUIF should convert approved Revision Plans into versioned edit Jobs, preserve the source Artifact as an immutable reference, enforce a new Approval gate, execute through a compatible editing Provider, and automatically link the replacement Artifact without losing the previous review history.
