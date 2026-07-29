# Game UI Framework (GUIF)

**English** | [简体中文](README.zh-CN.md)

GUIF is a local-first, AI-agnostic framework for planning, producing, reviewing, exporting, and evolving game UI work.

## Status

`v1.0.0-alpha.12` — Workflow-driven Runtime Pipelines, real deterministic Planner and Director Agents, relevance-based Context selection, persisted and resumable Task Runs, checkpointed execution, Engine Adapter exports, deterministic validation, protected editing, and Git-friendly Project knowledge.

## Product specification

The bilingual living product specification is maintained at [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md).

It defines GUIF's expected product, verified current state, missing capabilities, development phases, non-goals, risks, open questions, and acceptance criteria. Any iteration that changes GUIF's product direction or core capability status must update that document in the same release or pull request.

## What works now

- `guif init <project>` creates an isolated Project workspace.
- `guif inspect [project]` summarizes Framework or Project state, including persisted Run count.
- `guif run "<requirement>" --project <project>` resolves a Workflow into a Runtime Pipeline, selects relevant Context, executes Agents, and persists checkpoints.
- The built-in `planner` creates a validated structured UI Production Plan.
- The built-in `director` reviews composition, hierarchy, Theme constraints, Resource reuse, Memory constraints, conflicts, and approval points.
- Runtime ranks Project Memory, Resource manifests, and Project Workflow manifests against the current Requirement and active Theme.
- Project Workflow manifests can override built-in Workflows and define the ordered `agents` executed by Runtime.
- Workflow schema v1 remains readable; GUIF infers a compatible Agent sequence from the legacy `manager` field.
- `guif run-list --project <project>` lists persisted Task Runs.
- `guif run-show <task-id> --project <project>` loads a complete persisted Task snapshot.
- `guif run-resume <task-id> --project <project>` retries a failed or interrupted Task from its next executable Agent.
- `guif plan "<requirement>"` keeps the original routed Plan JSON workflow for backward compatibility.
- `guif validate <project>` validates Project semantics, Themes, Workflows, and Resource manifests.
- `guif record <type> "<message>"` stores reusable Project knowledge.
- `guif resource-create`, `resource-show`, and `resource-validate` manage Production Resource contracts.
- `guif asset-validate <manifest> <asset>` checks dimensions, format, Alpha, and naming.
- `guif export <project> --target <engine>` validates, copies, and prepares assets through an Engine Adapter.
- `guif compose-edit` and `guif qa-pixels` preserve and verify protected pixels.
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

The intended entry point is natural-language work directed through ChatGPT or another Agent Host:

```text
User Requirement
  -> ChatGPT / Agent Host
  -> GUIF Runtime
  -> Project Context snapshot
  -> relevance-based Context selection
  -> resolved Workflow manifest
  -> Runtime Pipeline
  -> registered Agents
  -> persisted Task and Outputs
```

Runtime itself does not depend on OpenAI or any other model provider. A Host can call it directly:

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
```

The equivalent CLI command is:

```bash
guif run "Create a 1080x2340 portrait medieval harbor shop page, reuse the purchase button, and export Unity" \
  --project LeekParty \
  --pipeline ui-production
```

## Workflow-driven Pipelines

Workflow schema v2 contains both human-readable steps and an executable Agent sequence:

```json
{
  "schema_version": 2,
  "id": "ui-production",
  "name": "Complete UI Production",
  "manager": "UI Director",
  "steps": [
    "Create a structured UI production plan",
    "Review art direction and resource reuse"
  ],
  "agents": ["planner", "director", "theme", "resource", "prompt", "qa", "export"]
}
```

Runtime resolves a Project Workflow first and falls back to the built-in Workflow with the same ID. The resolved Workflow becomes the Pipeline used for execution. Its source, manager, steps, and Agent order are saved in `Task.state["pipeline"]` for auditing.

A failed Task is not resumed when its stored Agent sequence differs from the currently resolved Workflow, because continuing against a changed Pipeline would be unsafe.

Built-in executable Workflows include:

- `ui-production`
- `planning`
- `effect-image`
- `theme-direction`
- `resource-production`
- `quality-assurance`
- `framework-evolution`

## Relevance-based Context selection

Runtime loads the complete Project Context snapshot and then creates a deterministic, budgeted selection for the current Requirement.

The selection ranks:

- Markdown Memory records from `memory/**/*.md`;
- Production Resource manifests;
- Project Workflow manifests.

Ranking uses Requirement terms plus semantic values from the active Theme. English tokens and Chinese character n-grams are supported. Generic English stop words are removed, and unrelated records are excluded rather than included only because of their type.

The result is stored in:

```python
task.state["context_selection"]
```

It contains selected records, relevance scores, matched terms, budgets, total counts, and omitted counts. Resume uses the persisted selection rather than silently rebuilding the failed Task against new Project knowledge.

The complete Context remains in `context.json`; the selected subset exists to keep Agent inputs focused and auditable.

## Structured Planner Agent

The Planner is model-neutral and deterministic. It does not call an LLM. It converts the Requirement and Project Context into a validated Plan schema containing:

- detected Page type, orientation, and canvas dimensions;
- target Engine;
- active Theme contract, positive requirements, and exclusions;
- reusable Resource candidates with reasons and scores;
- suggested missing Resource contracts;
- Deliverables and QA criteria;
- ordered execution steps and dependencies;
- risks, open questions, and Context summary.

The Plan is available in:

```python
task.state["plan"]
```

and the persisted Output index as:

```text
ui-production-plan
```

## Structured Director Agent

The Director consumes the Planner output and creates a validated art-direction review. It currently provides:

- page-specific portrait or landscape composition zones;
- focal order and interaction hierarchy;
- active Theme palette, materials, lighting, required elements, and exclusions;
- Memory-derived constraints such as `must`, `avoid`, `不要`, and `必须` decisions;
- approved, review-required, or weak Resource reuse decisions;
- blocking conflicts and human approval points;
- structured handoff instructions for Theme, Resource, Prompt, and QA work.

The Director returns one of:

```text
ready
needs-review
blocked
```

The review is available in:

```python
task.state["direction"]
```

and the persisted Output index as:

```text
art-direction-review
```

Planner and Director are now real domain Agents. `theme`, `resource`, `prompt`, `qa`, and `export` remain Contract Agents and do not yet complete their intended production responsibilities automatically.

## Persisted Task Runs

Each Runtime execution is saved under:

```text
projects/<project>/runs/<task-id>/
```

A Run contains:

```text
task.json       complete Task snapshot and lifecycle state
context.json    Project Context snapshot used by the Run
events.jsonl    audit event representation
outputs.json    registered Output index
error.json      failure details, present only while failed
```

Pipelines checkpoint the Task before and after every Agent. When an Agent fails, GUIF records the failing Agent, exception type, message, and retry index. `run-resume` reloads the saved Task and continues from that index. Completed Tasks cannot be resumed.

## Runtime contract

```text
Runtime
  -> Context Loader
  -> Context Retriever
  -> Workflow Resolver
  -> Pipeline
  -> Task Store
  -> Agent Registry
  -> Task + Outputs
```

Default `ui-production` Workflow:

```text
planner
  -> director
  -> theme
  -> resource
  -> prompt
  -> qa
  -> export
```

Each Agent receives and returns the same mutable `Task`. Agents do not directly invoke one another. Runtime alone resolves and executes the Agent order declared by the Workflow.

Runtime Context currently loads:

- `project.json`
- the active Project Theme when configured
- Project Workflow manifests
- Production Resource manifests
- Project Memory records

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

The generic Exporter delegates engine-specific preparation to Adapters:

```text
Exporter
  -> GenericAdapter
  -> UnityAdapter
  -> GodotAdapter
  -> UnrealAdapter
```

The Adapter Registry lives in `guif/adapters/`. The core Exporter validates and stages assets; Adapters own engine-specific metadata generation.

Current behavior:

- `generic`: copies the validated asset without a Sidecar.
- `unity`: writes `<asset>.guif-unity.json` with Sprite and Mipmap import hints.
- `godot`: writes `<asset>.guif-godot.json` with Texture import hints.
- `unreal`: writes `<asset>.guif-unreal.json` with UI Texture Group and Mipmap hints.

These JSON Sidecars are deterministic GUIF metadata, not native engine-generated files.

## Operating principles

1. Natural language is the primary user interface; CLI remains an implementation, debugging, and CI interface.
2. Git and Project files are the long-term source of truth.
3. Runtime orchestration stays model-agnostic.
4. Workflow manifests are the executable source of Pipeline order.
5. Agents receive focused, persisted Context selections instead of silently relying on unbounded Project data.
6. Agents do not depend on or directly invoke one another.
7. Runtime Runs must be inspectable, persisted, and recoverable.
8. Effect Images and Production Assets remain separate.
9. Engine-specific behavior belongs in Adapters, not the Framework Core.
10. Local edits preserve non-target pixels through mask-based composition.
11. A release is complete only when Feature, Test, CI, the English README, the Chinese README, Version Metadata, and the Product Specification agree.

## Repository direction

The next priority is to implement a real Theme Agent and Resource Agent so the approved Plan and Director review can become concrete production contracts. After that, GUIF should define the model-neutral Prompt IR before integrating Generation tools. Priorities and acceptance criteria are maintained in [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md).
