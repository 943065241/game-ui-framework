# Game UI Framework (GUIF)

**English** | [简体中文](README.zh-CN.md)

GUIF is a local-first, AI-agnostic framework for planning, producing, reviewing, exporting, and evolving game UI work.

## Status

`v1.0.0-alpha.11` — Workflow-driven Runtime Pipelines, the first real structured Planner Agent, persisted and resumable Task Runs, checkpointed execution, project Context loading, Engine Adapter exports, deterministic validation, protected editing, Memory, Project, Theme, and Resource contracts.

## Product specification

The bilingual living product specification is maintained at [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md).

It defines GUIF's expected product, verified current state, missing capabilities, development phases, non-goals, risks, open questions, and acceptance criteria. Any iteration that changes GUIF's product direction or core capability status must update that document in the same release or pull request.

## What works now

- `guif init <project>` creates an isolated project workspace.
- `guif inspect [project]` summarizes framework or project state, including persisted Run count.
- `guif run "<requirement>" --project <project>` resolves a Workflow into a Runtime Pipeline, executes it, and persists checkpoints.
- The built-in `planner` is a real deterministic Agent that writes a structured UI production plan into the Task and Output index.
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
User requirement
  -> ChatGPT / Agent Host
  -> GUIF Runtime
  -> Project Context snapshot
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
    "Create a 1080x2340 portrait medieval harbor shop page and export it for Unity",
    pipeline="planning",
)
print(task.state["plan"])
```

The equivalent CLI command is:

```bash
guif run "Create a 1080x2340 portrait medieval harbor shop page and export it for Unity" \
  --project LeekParty \
  --pipeline planning
```

## Workflow-driven Pipelines

Workflow schema v2 contains both human-readable steps and an executable Agent sequence:

```json
{
  "schema_version": 2,
  "id": "planning",
  "name": "Structured UI Planning",
  "manager": "UI Director",
  "steps": [
    "Convert the requirement and project context into a structured production plan"
  ],
  "agents": ["planner"]
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

## Structured Planner Agent

The alpha.11 Planner is model-neutral and deterministic. It does not call an LLM. It converts the requirement and current Project Context into a validated Plan schema containing:

- detected page type, orientation, and canvas dimensions;
- target Engine;
- active Theme contract, positive requirements, and exclusions;
- reusable Resource candidates with reasons and scores;
- suggested missing Resource contracts;
- deliverables and QA criteria;
- ordered execution steps and dependencies;
- risks, open questions, and Context summary.

The Plan is available in both:

```python
task.state["plan"]
```

and the persisted Output index as:

```text
ui-production-plan
```

This is the first built-in Agent that performs real domain work. `director`, `theme`, `resource`, `prompt`, `qa`, and `export` are still Contract Agents and do not yet complete their intended production responsibilities automatically.

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

guif run "Plan a 1080x2340 portrait medieval harbor shop page for Unity" \
  --project LeekParty \
  --pipeline planning

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
5. Agents do not depend on or directly invoke one another.
6. Runtime Runs must be inspectable, persisted, and recoverable.
7. Effect Images and Production Assets remain separate.
8. Engine-specific behavior belongs in Adapters, not the Framework Core.
9. Local edits preserve non-target pixels through mask-based composition.
10. A release is complete only when Feature, Test, CI, the English README, the Chinese README, Version Metadata, and the Product Specification agree.

## Repository direction

The next priority is to replace the Contract-only Director with a real art-direction and reuse-review Agent, then add relevance-based Context and Memory retrieval. GUIF must continue proving the natural-language production loop with real Project tasks rather than expanding placeholder interfaces. Priorities and acceptance criteria are maintained in [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md).
