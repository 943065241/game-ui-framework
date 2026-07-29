# Game UI Framework (GUIF)

**English** | [简体中文](README.zh-CN.md)

GUIF is a local-first, AI-agnostic framework for planning, directing, contracting, prompting, reviewing, exporting, and evolving game UI production work.

## Status

`v1.0.0-alpha.15` — Workflow-driven Runtime Pipelines, real deterministic Planner, Director, Theme, Resource, Prompt, and Semantic QA Agents, relevance-based Context selection, persisted and resumable Task Runs, Engine Adapter exports, deterministic validation, protected editing, and Git-friendly Project knowledge.

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
- Runtime ranks Project Memory, Resource manifests, and Project Workflow manifests against the current Requirement and active Theme.
- Project Workflow manifests can override built-in Workflows and declare executable `agents`.
- Workflow schema v1 remains readable through the legacy `manager` mapping.
- Task Runs are persisted, inspectable, and resumable after failure.
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
       -> Export
  -> persisted Task and Outputs
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
```

Equivalent CLI command:

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

The result is stored in:

```python
task.state["context_selection"]
```

It contains selected records, scores, matched terms, budgets, total counts, and omitted counts. Resume uses the persisted selection instead of silently rebuilding the failed Task against changed Project knowledge.

## Structured production Agents

### Planner

The deterministic Planner creates Page type, orientation, canvas dimensions, target Engine, active Theme constraints, Resource reuse candidates, missing Resource suggestions, Deliverables, QA criteria, dependencies, risks, open questions, and a Context summary.

```python
task.state["plan"]
```

```text
ui-production-plan
```

### Director

The Director creates page-specific composition zones, focal order, interaction hierarchy, relevant Memory constraints, Resource reuse decisions, blocking conflicts, approval points, and handoff instructions.

Status: `ready`, `needs-review`, or `blocked`.

```python
task.state["direction"]
```

```text
art-direction-review
```

### Theme

The Theme Agent resolves the active Project Theme or infers a reviewable deterministic preset for recognized directions such as medieval harbor, natural trading, soft-neon party, or minimal UI. Unknown directions remain `blocked`. Memory constraints are merged into `must_include` or `avoid`, and contradictions become explicit conflicts.

```python
task.state["theme_contract"]
```

```text
resolved-theme-contract
```

Status: `ready`, `review-required`, or `blocked`.

An inferred Theme is not automatically activated or written into `projects/<project>/themes/`.

### Resource

The Resource Agent identifies approved existing reuse, unresolved reuse candidates, validated manifests for missing assets, dimension provenance, Engine import hints, blocking conflicts, approval points, and handoff instructions.

```python
task.state["resource_contracts"]
```

```text
resource-contract-bundle
```

Generated manifests use `review-before-write`; Runtime does not create or overwrite Project Resource files without explicit approval.

### Prompt

The Prompt Agent converts Plan, Director review, Theme contract, and Resource bundle into a model-neutral Prompt IR.

```python
task.state["prompt_ir"]
```

```text
model-neutral-prompt-ir
```

Prompt IR schema v1 contains:

- provider binding fields, initially `provider_id: null` and `model_id: null`;
- a global Page, Composition, Theme, and Negative Constraint contract;
- one Effect Image job and zero or more Production Asset jobs;
- structured Objective, Composition, Visual, Content, and Technical instructions;
- approved Resource references and exact Output Contracts;
- per-job Acceptance Criteria;
- required capabilities such as `image-generation`, `image-editing`, `protected-region-editing`, or `transparent-output`;
- Approval Points, Blockers, Handoff, and full Provenance.

Status:

```text
ready
review-required
blocked
```

Jobs are executable only when Prompt IR status is `ready`. A review-required or blocked IR remains inspectable and persisted, but a Provider Adapter must not execute it automatically.

Prompt IR is not an OpenAI, image-model, or Figma payload. A later Provider Adapter may translate it, but must preserve instructions, negative constraints, references, output contracts, acceptance criteria, and provenance.

### Semantic QA

The alpha.15 QA Agent performs deterministic Contract QA before any Provider or Export step. It checks:

- Prompt IR schema validity;
- the complete upstream Output provenance chain;
- Page type, orientation, and canvas consistency between Plan and Prompt IR;
- preservation of Theme `must_include` and `avoid` constraints;
- one-to-one coverage between Resource Manifest Candidate and Production Asset Job;
- Resource Output Contract validity and equality;
- approved-reference boundaries;
- `review-before-execute` safety;
- required Provider capabilities.

```python
task.state["qa_report"]
```

```text
semantic-qa-report
```

QA status:

```text
passed
review-required
blocked
```

The report contains Checks, Findings, Revision Request, Artifact Review state, Provenance, Handoff, and an explicit:

```python
task.state["qa_report"]["export_gate"]
```

At alpha.15, no visual Semantic QA Adapter exists. When no generated Artifact is registered, the report records `artifact_review.status: "not-run"` and explicitly states that it does not claim visual quality results. Consequently, Export remains blocked even when Contract checks pass. This prevents contract-only reasoning from being presented as visual verification.

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
error.json      failure details, present only while failed
```

Pipelines checkpoint before and after every Agent. On failure, GUIF records the failing Agent, exception type, message, and retry index. `guif run-resume` continues from that position. Completed Tasks cannot be resumed.

## Quick start

```bash
guif init LeekParty

guif run "Create a 1080x2340 portrait medieval harbor shop page for Unity" \
  --project LeekParty \
  --pipeline ui-production

guif run-list --project LeekParty
guif run-show <task-id> --project LeekParty
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
9. Prompt IR is provider-independent and requires approval before execution.
10. Contract QA must not claim visual QA when no visual Artifact was inspected.
11. Export requires a passing explicit Export Gate.
12. Effect Images and Production Assets remain separate.
13. Engine-specific behavior belongs in Adapters, not Framework Core.
14. Local edits preserve non-target pixels through mask-based composition.
15. A release is complete only when Feature, Test, CI, both READMEs, Version Metadata, and the Product Specification agree.

## Repository direction

The next priority is an explicit Approval API and state transition contract. It must resolve Director, Theme, Resource, and Prompt approval points without mutating Project truth or enabling Provider execution implicitly. After that, GUIF can add Provider Adapters, Artifact registration, visual Semantic QA, Revision Loops, and a real Export Agent. Priorities and acceptance criteria are maintained in [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md).
