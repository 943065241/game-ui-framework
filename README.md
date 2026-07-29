# Game UI Framework (GUIF)

**English** | [简体中文](README.zh-CN.md)

GUIF is a local-first, AI-agnostic framework for planning, directing, contracting, prompting, reviewing, approving, exporting, and evolving game UI production work.

## Status

`v1.0.0-alpha.16` — Workflow-driven Runtime Pipelines, real deterministic Planner, Director, Theme, Resource, Prompt, and Semantic QA Agents, persistent Approval decisions with controlled Prompt state transitions, relevance-based Context selection, resumable Task Runs, Engine Adapter exports, deterministic validation, protected editing, and Git-friendly Project knowledge.

## Product specification

The bilingual living product specification is maintained at [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md).

It defines GUIF's expected product, verified current state, missing capabilities, development phases, non-goals, risks, open questions, and acceptance criteria. Product direction, architecture, capability status, compatibility, or priority changes must update that specification in the same release or pull request.

## What works now

- `guif init <project>` creates an isolated Project workspace.
- `guif inspect [project]` summarizes Framework or Project state.
- `guif run "<requirement>" --project <project>` resolves a Workflow, selects relevant Context, executes Agents, and persists checkpoints.
- `planner` creates a validated structured UI Production Plan.
- `director` reviews composition, hierarchy, Theme constraints, Resource reuse, Memory constraints, conflicts, and approval points.
- `theme` resolves an active Project Theme or creates a reviewable inferred Theme contract.
- `resource` creates validated Resource manifest candidates without silently modifying Project files.
- `prompt` creates a versioned, provider-independent Prompt IR with jobs, constraints, references, output contracts, approval points, blockers, and provenance.
- `qa` performs deterministic semantic Contract QA, verifies cross-Agent consistency and execution safety, and creates an explicit Export Gate.
- Runtime persists Approval decisions and safely changes Prompt jobs between `review-required`, `blocked`, and `ready`.
- Approval, rejection, and change-request history is auditable and can be revised without deleting previous decisions.
- Project Workflow manifests can override built-in Workflows and declare executable `agents`.
- Task Runs are persisted, inspectable, resumable after failure, and list their Approval status.
- Project, Theme, Workflow, Resource, Image Asset, Pixel Protection, and Engine Adapter validation are available.
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

## ChatGPT-oriented Runtime flow

```text
User Requirement
  -> ChatGPT / Agent Host
  -> GUIF Runtime
  -> complete Project Context snapshot
  -> relevance-based Context selection
  -> resolved Workflow manifest
  -> Runtime Pipeline
       -> Planner
       -> Director
       -> Theme
       -> Resource
       -> Prompt
       -> Semantic QA
       -> Export contract
  -> persisted Task and Outputs
  -> Human / Host Approval decisions
  -> controlled Prompt and QA state refresh
  -> executable jobs only when every required approval passes
```

Runtime does not depend on OpenAI or any other model provider. A Host can call it directly:

```python
from pathlib import Path
from guif.runtime import Runtime

runtime = Runtime(Path.cwd())
task = runtime.run(
    "LeekParty",
    "Create a 1080x2340 portrait medieval harbor shop page, reuse the purchase button, and export Unity",
    pipeline="ui-production",
)

print(task.state["plan"])
print(task.state["direction"])
print(task.state["theme_contract"])
print(task.state["resource_contracts"])
print(task.state["prompt_ir"])
print(task.state["qa_report"])

approvals = runtime.get_approvals("LeekParty", task.task_id)
for approval_id in approvals["pending_ids"]:
    task = runtime.approve(
        "LeekParty",
        task.task_id,
        approval_id,
        actor="reviewer@example.com",
        comment="Approved for provider preparation.",
    )
```

Equivalent CLI start command:

```bash
guif run "Create a 1080x2340 portrait medieval harbor shop page, reuse the purchase button, and export Unity" \
  --project LeekParty \
  --pipeline ui-production
```

## Workflow-driven Pipelines

Workflow schema v2 contains human-readable steps and an executable Agent sequence:

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

Runtime resolves a Project Workflow first and falls back to the built-in Workflow with the same ID. Source, manager, steps, and Agent order are stored in `Task.state["pipeline"]`.

Resume is rejected when the persisted Agent sequence differs from the currently resolved Workflow, because continuing against a changed Pipeline is unsafe.

Built-in executable Workflows:

- `ui-production`
- `planning`
- `effect-image`
- `theme-direction`
- `resource-production`
- `quality-assurance`
- `framework-evolution`

## Relevance-based Context selection

Runtime loads the complete Project Context snapshot and creates a deterministic, budgeted selection for the current Requirement.

It ranks Markdown Memory records, Production Resource manifests, and Project Workflow manifests. English tokens and Chinese character n-grams are supported. Generic English stop words are removed, and unrelated records are excluded.

The persisted result is stored in:

```python
task.state["context_selection"]
```

It contains selected records, scores, matched terms, budgets, total counts, and omitted counts. Resume uses the persisted selection instead of silently rebuilding a failed Task against changed Project knowledge.

## Structured production Agents

### Planner

The deterministic Planner creates Page type, orientation, canvas dimensions, target Engine, active Theme constraints, Resource reuse candidates, missing Resource suggestions, Deliverables, QA criteria, dependencies, risks, open questions, and a Context summary.

```python
task.state["plan"]
```

Output: `ui-production-plan`.

### Director

The Director creates page-specific composition zones, focal order, interaction hierarchy, relevant Memory constraints, Resource reuse decisions, blocking conflicts, approval points, and handoff instructions.

Status: `ready`, `needs-review`, or `blocked`.

```python
task.state["direction"]
```

Output: `art-direction-review`.

### Theme

The Theme Agent resolves the active Project Theme or infers a reviewable deterministic preset for recognized directions such as medieval harbor, natural trading, soft-neon party, or minimal UI. Unknown directions remain `blocked`. Memory constraints are merged into `must_include` or `avoid`, and contradictions become explicit conflicts.

```python
task.state["theme_contract"]
```

Output: `resolved-theme-contract`.

An inferred Theme is not automatically activated or written into `projects/<project>/themes/`.

### Resource

The Resource Agent identifies approved existing reuse, unresolved reuse candidates, validated manifests for missing assets, dimension provenance, Engine import hints, blocking conflicts, approval points, and handoff instructions.

```python
task.state["resource_contracts"]
```

Output: `resource-contract-bundle`.

Generated manifests use `review-before-write`; Runtime does not create or overwrite Project Resource files without explicit approval and a future materialization operation.

### Prompt

The Prompt Agent converts Plan, Director review, Theme contract, and Resource bundle into a model-neutral Prompt IR.

```python
task.state["prompt_ir"]
```

Output: `model-neutral-prompt-ir`.

Prompt IR schema v1 contains:

- provider binding fields, initially `provider_id: null` and `model_id: null`;
- a global Page, Composition, Theme, and Negative Constraint contract;
- one Effect Image job and zero or more Production Asset jobs;
- structured Objective, Composition, Visual, Content, and Technical instructions;
- approved Resource references and exact Output Contracts;
- per-job Acceptance Criteria;
- required Provider capabilities;
- Approval Points, Blockers, Handoff, and full Provenance.

Jobs are executable only when Prompt IR status is `ready`. A `review-required` or `blocked` IR remains inspectable and persisted, but a Provider Adapter must not execute it automatically.

### Semantic QA

Semantic QA performs deterministic Contract checks before any Provider or Export step:

- Prompt IR schema validity;
- complete upstream Output provenance;
- Page, orientation, and canvas consistency;
- preservation of Theme `must_include` and `avoid` constraints;
- one-to-one Resource Candidate and Production Job coverage;
- Resource Output Contract validity and equality;
- approved-reference boundaries;
- Provider capability completeness;
- Prompt executable flags and persisted Approval state consistency.

```python
task.state["qa_report"]
```

Output: `semantic-qa-report`.

QA status is `passed`, `review-required`, or `blocked`. No visual Semantic QA Adapter exists yet. When no generated Artifact is registered, `artifact_review.status` is `not-run` and Export remains blocked even when Contract checks pass.

## Persistent Approval API

Each Prompt IR initializes a persisted Approval state:

```python
task.state["approval_state"]
```

Approval status is one of:

```text
not-required
pending
approved
rejected
changes-requested
```

Each decision records the Approval ID, decision, actor, optional comment, timestamp, source, and question. The latest decision per Approval ID controls the gate, while `history` remains append-only.

Controlled transition rules:

- unresolved required points keep Prompt IR `review-required`;
- a rejection or change request makes Prompt IR `blocked`;
- all required points approved and no non-Approval blocker makes Prompt IR `ready`;
- Prompt jobs become executable only in `ready`;
- changing a previous rejection or change request to approved can recover the gate;
- Semantic QA is rebuilt after every decision;
- the Task lifecycle remains `completed` because Approval is post-run governance;
- Approval never mutates Project Theme or Resource files and never calls a Provider.

Runtime API:

```python
runtime.get_approvals(project, task_id)
runtime.approve(project, task_id, approval_id, actor="reviewer", comment="...")
runtime.reject(project, task_id, approval_id, actor="reviewer", comment="...")
runtime.request_changes(project, task_id, approval_id, actor="reviewer", comment="...")
```

CLI:

```bash
guif run-approval-list <task-id> --project LeekParty

guif run-approve <task-id> <approval-id> \
  --project LeekParty \
  --actor reviewer@example.com \
  --comment "Approved"

guif run-reject <task-id> <approval-id> \
  --project LeekParty \
  --actor reviewer@example.com \
  --comment "Rejected because the composition conflicts with the brief"

guif run-request-changes <task-id> <approval-id> \
  --project LeekParty \
  --actor reviewer@example.com \
  --comment "Increase the primary action hierarchy"
```

## Persisted Task Runs

Each Runtime execution is saved under:

```text
projects/<project>/runs/<task-id>/
```

A Run contains:

```text
task.json       complete Task snapshot and lifecycle state
context.json    complete Project Context snapshot
events.jsonl    audit event representation
outputs.json    registered Output index
approvals.json  latest Approval state and append-only decision history
error.json      failure details, present only while failed
```

Pipelines checkpoint before and after every Agent. On failure, GUIF records the failing Agent, exception type, message, and retry index. `guif run-resume` continues from that position. Completed Tasks cannot be resumed, but their Approval state can still be reviewed and changed.

`guif run-list` includes `approval_status` and `pending_approval_count`.

## Quick start

```bash
guif init LeekParty

guif run "Create a 1080x2340 portrait medieval harbor shop page for Unity" \
  --project LeekParty \
  --pipeline ui-production

guif run-list --project LeekParty
guif run-show <task-id> --project LeekParty
guif run-approval-list <task-id> --project LeekParty
guif validate LeekParty
```

## Engine Adapter layer

```text
Exporter
  -> GenericAdapter
  -> UnityAdapter
  -> GodotAdapter
  -> UnrealAdapter
```

The core Exporter validates and stages assets. Adapters own Engine-specific metadata generation.

- `generic`: copies the validated asset without a Sidecar.
- `unity`: writes `<asset>.guif-unity.json`.
- `godot`: writes `<asset>.guif-godot.json`.
- `unreal`: writes `<asset>.guif-unreal.json`.

These JSON Sidecars are deterministic GUIF metadata, not native Engine-generated files.

## Operating principles

1. Natural language is the primary user interface; CLI remains an implementation, debugging, and CI interface.
2. Git and Project files are the long-term source of truth.
3. Runtime orchestration stays model-agnostic.
4. Workflow manifests are the executable source of Pipeline order.
5. Context selection is focused, persisted, and auditable.
6. Agents do not directly invoke one another.
7. Runtime Runs must be inspectable, persisted, and recoverable.
8. Inferred Theme and Resource proposals require review before Project files are changed.
9. Approval decisions are explicit, attributed, persisted, reversible through a new decision, and never silently inferred.
10. Prompt IR is provider-independent and requires every required Approval before execution.
11. Contract QA must not claim visual QA when no visual Artifact was inspected.
12. Export requires a passing explicit Export Gate.
13. Effect Images and Production Assets remain separate.
14. Engine-specific behavior belongs in Adapters, not Framework Core.
15. Local edits preserve non-target pixels through mask-based composition.
16. A release is complete only when Feature, Test, CI, both READMEs, Version Metadata, and the Product Specification agree.

## Repository direction

The next priority is a Provider Adapter and Artifact registration contract. It must consume only approved, executable Prompt jobs, preserve structured constraints and provenance, record capability and execution metadata, and never bypass the Approval or Semantic QA gates. Visual Semantic QA, Revision Loops, and the real Export Agent follow after Artifact registration is stable. Priorities and acceptance criteria are maintained in [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md).
