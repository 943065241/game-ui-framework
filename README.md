# Game UI Framework (GUIF)

**English** | [简体中文](README.zh-CN.md)

GUIF is a local-first, AI-agnostic framework for planning, directing, contracting, reviewing, exporting, and evolving game UI production work.

## Status

`v1.0.0-alpha.13` — Workflow-driven Runtime Pipelines, real deterministic Planner, Director, Theme, and Resource Agents, relevance-based Context selection, persisted and resumable Task Runs, Engine Adapter exports, deterministic validation, protected editing, and Git-friendly Project knowledge.

## Product specification

The bilingual living product specification is maintained at [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md).

It defines GUIF's expected product, verified current state, missing capabilities, development phases, non-goals, risks, open questions, and acceptance criteria. Product direction, architecture, capability status, compatibility, or priority changes must update that specification in the same release or pull request.

## What works now

- `guif init <project>` creates an isolated Project workspace.
- `guif inspect [project]` summarizes Framework or Project state.
- `guif run "<requirement>" --project <project>` resolves a Workflow, selects relevant Context, executes Agents, and persists checkpoints.
- `planner` creates a validated structured UI Production Plan.
- `director` reviews composition, hierarchy, Theme constraints, Resource reuse, Memory constraints, conflicts, and approval points.
- `theme` resolves an active Project Theme or produces a reviewable inferred Theme contract.
- `resource` converts Plan and Director decisions into validated Resource manifest candidates without silently modifying Project files.
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
       -> QA
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
    "Resolve production resource contracts"
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

The selection ranks:

- Markdown Memory records from `memory/**/*.md`;
- Production Resource manifests;
- Project Workflow manifests.

English tokens and Chinese character n-grams are supported. Generic English stop words are removed, and unrelated records are excluded. The result is stored in:

```python
task.state["context_selection"]
```

It contains selected records, scores, matched terms, budgets, total counts, and omitted counts. Resume uses the persisted selection rather than silently rebuilding the failed Task against new Project knowledge.

## Structured Planner Agent

The deterministic Planner creates:

- Page type, orientation, and canvas dimensions;
- target Engine;
- active Theme information and constraints;
- reusable Resource candidates with scores and reasons;
- missing Resource suggestions;
- Deliverables and QA criteria;
- execution dependencies;
- risks, open questions, and Context summary.

Outputs:

```python
task.state["plan"]
```

```text
ui-production-plan
```

## Structured Director Agent

The Director consumes the Plan and creates:

- page-specific composition zones;
- focal order and interaction hierarchy;
- Theme palette, materials, lighting, required elements, and exclusions;
- relevant Memory constraints;
- Resource reuse decisions;
- blocking conflicts and approval points;
- handoff instructions for later Agents.

Its status is `ready`, `needs-review`, or `blocked`.

Outputs:

```python
task.state["direction"]
```

```text
art-direction-review
```

## Structured Theme Agent

The Theme Agent consumes the Plan and Director review.

When an active Project Theme exists, it produces a validated `ready` contract using that Theme. When no active Theme exists, it can infer a reviewable deterministic preset for recognized directions such as medieval harbor, natural trading, soft-neon party, or minimal UI. Unknown directions remain `blocked` rather than receiving invented production values.

Memory-derived constraints are merged into `must_include` or `avoid`, and contradictory constraints are exposed as blocking conflicts.

Outputs:

```python
task.state["theme_contract"]
```

```text
resolved-theme-contract
```

Theme contract status:

```text
ready
review-required
blocked
```

An inferred Theme is not automatically activated or written into `projects/<project>/themes/`. It requires explicit review.

## Structured Resource Agent

The Resource Agent consumes the Plan, Director review, Theme contract, and Project Resource manifests. It produces:

- approved existing Resource reuse;
- reuse candidates that still require review;
- validated Resource manifest candidates for missing assets;
- proposed dimensions with explicit provenance such as `plan`, `canvas`, or `layout-proposal`;
- Engine-specific import hints;
- unresolved items, blocking conflicts, and approval points;
- Prompt, QA, and Export handoff instructions.

Outputs:

```python
task.state["resource_contracts"]
```

```text
resource-contract-bundle
```

The generated manifests conform to the existing Resource schema, but Runtime uses a `review-before-write` policy. It does not overwrite or create Project Resource files without explicit approval. This avoids turning deterministic layout proposals into unreviewed production truth.

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

guif resource-create trade-button-long button 264 134 png \
  --project LeekParty \
  --target-engine unity \
  --source source/trade-button-long.png \
  --import-settings '{"spriteMode":"Single","mipmapEnabled":false}'

guif export LeekParty --target unity
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
9. Effect Images and Production Assets remain separate.
10. Engine-specific behavior belongs in Adapters, not Framework Core.
11. Local edits preserve non-target pixels through mask-based composition.
12. A release is complete only when Feature, Test, CI, both READMEs, Version Metadata, and the Product Specification agree.

## Repository direction

The next priority is a model-neutral Prompt IR Agent that converts Plan, Director, Theme, and Resource contracts into a versioned, provider-independent generation instruction. Generation tool integration should begin only after that contract is stable. Priorities and acceptance criteria are maintained in [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md).
