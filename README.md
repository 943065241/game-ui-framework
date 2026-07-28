# Game UI Framework (GUIF)

**English** | [简体中文](README.zh-CN.md)

GUIF is a local-first, AI-agnostic framework for planning, producing, reviewing, exporting, and evolving game UI work.

## Status

`v1.0.0-alpha.10` — persisted and resumable runtime task runs, checkpointed pipelines, composable agents, project-context loading, engine-adapter exports, deterministic validation, protected editing, memory, workflows, projects, and themes.

## Product specification

The bilingual living product specification is maintained at [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md).

It defines GUIF's expected product, verified current state, missing capabilities, development phases, non-goals, risks, open questions, and acceptance criteria. Any iteration that changes GUIF's product direction or core capability status must update that document in the same release or pull request.

## What works now

- `guif init <project>` creates an isolated project workspace.
- `guif inspect [project]` summarizes framework or project state, including persisted run count.
- `guif run "<requirement>" --project <project>` executes a runtime pipeline and persists checkpoints.
- `guif run-list --project <project>` lists persisted task runs.
- `guif run-show <task-id> --project <project>` loads a complete persisted task snapshot.
- `guif run-resume <task-id> --project <project>` retries a failed or interrupted task from its next executable agent.
- `guif plan "<requirement>"` creates the existing routed plan format.
- `guif validate <project>` validates project semantics, themes, workflows, and resource manifests.
- `guif record <type> "<message>"` stores reusable project knowledge.
- `guif resource-create`, `resource-show`, and `resource-validate` manage production contracts.
- `guif asset-validate <manifest> <asset>` checks dimensions, format, alpha, and naming.
- `guif export <project> --target <engine>` validates, copies, and prepares assets through an engine adapter.
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

## ChatGPT-oriented runtime flow

The intended entry point is natural-language work directed through ChatGPT or another agent host:

```text
User requirement
  -> ChatGPT / agent host
  -> GUIF Runtime
  -> project context snapshot
  -> selected pipeline
  -> registered agents
  -> persisted Task result
```

The runtime itself does not depend on OpenAI or any other model provider. A host can call it directly:

```python
from pathlib import Path
from guif.runtime import Runtime

runtime = Runtime(Path.cwd())
task = runtime.run(
    "LeekParty",
    "Create the medieval harbor shop page",
    pipeline="ui-production",
)
print(task.task_id)
print(task.to_dict())
```

The equivalent CLI command is:

```bash
guif run "Create the medieval harbor shop page" \
  --project LeekParty \
  --pipeline ui-production
```

## Persisted task runs

Each runtime execution is saved under:

```text
projects/<project>/runs/<task-id>/
```

A run contains:

```text
task.json       complete Task snapshot and lifecycle state
context.json    project-context snapshot used by the run
events.jsonl    append-style audit event representation
outputs.json    registered output index
error.json      failure details, present only while failed
```

Pipelines checkpoint the task before and after every Agent. When an Agent fails, GUIF records the failing Agent, exception type, message, and the index that should be retried. `run-resume` reloads the saved Task and continues from that index. Completed tasks cannot be resumed.

## Runtime contract

```text
Runtime
  -> Context Loader
  -> Task Store
  -> Pipeline
  -> Agent Registry
  -> Task
```

Default `ui-production` pipeline:

```text
planner
  -> director
  -> theme
  -> resource
  -> prompt
  -> qa
  -> export
```

Each Agent receives and returns the same mutable `Task`. Agents do not call one another. The Runtime alone resolves pipeline order through the Registry.

The built-in Agents still execute contract-level behavior: they record lifecycle events, responsibilities, and state transitions. They do not yet perform real semantic planning, image generation, visual review, or automatic production work.

Runtime Context currently loads:

- `project.json`
- the active project Theme when configured
- project Workflow manifests
- Production Resource manifests
- project Memory records

## Quick start

```bash
guif init LeekParty
guif run "Create a trade button" --project LeekParty
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

## Engine adapter layer

The generic Exporter delegates engine-specific preparation to adapters:

```text
Exporter
  -> GenericAdapter
  -> UnityAdapter
  -> GodotAdapter
  -> UnrealAdapter
```

The Adapter Registry lives in `guif/adapters/`. The core Exporter validates and stages assets; adapters own engine-specific metadata generation.

Current behavior:

- `generic`: copies the validated asset without a sidecar.
- `unity`: writes `<asset>.guif-unity.json` with Sprite and Mipmap import hints.
- `godot`: writes `<asset>.guif-godot.json` with Texture import hints.
- `unreal`: writes `<asset>.guif-unreal.json` with UI Texture Group and Mipmap hints.

These JSON sidecars are deterministic GUIF metadata, not native engine-generated files.

## Operating principles

1. Natural language is the primary user interface; CLI remains an implementation, debugging, and CI interface.
2. Git and project files are the long-term source of truth.
3. Runtime orchestration stays model-agnostic.
4. Agents do not depend on or directly invoke one another.
5. Runtime runs must be inspectable, persisted, and recoverable.
6. Effect images and production assets remain separate.
7. Engine-specific behavior belongs in adapters, not the framework core.
8. Local edits preserve non-target pixels through mask-based composition.
9. A release is complete only when feature, tests, CI, the English README, the Chinese README, version metadata, and the product specification agree.

## Repository direction

The next priority is a real structured Planner Agent and a unified relationship between Runtime Pipeline and project Workflow manifests. GUIF must prove one complete natural-language UI production loop before adding more placeholder Agents. Priorities and acceptance criteria are maintained in [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md).
