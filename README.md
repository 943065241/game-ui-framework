# Game UI Framework (GUIF)

GUIF is a local-first, AI-agnostic framework for planning, producing, reviewing, exporting, and evolving game UI work.

## Status

`v1.0.0-alpha.9` — runtime contracts, composable agents and pipelines, project-context loading, engine-adapter exports, deterministic validation, protected editing, memory, workflows, projects, and themes.

## What works now

- `guif init <project>` creates a project workspace.
- `guif inspect [project]` summarizes framework or project state.
- `guif run "<requirement>" --project <project>` executes a requirement through the runtime contract.
- `guif plan "<requirement>"` creates the existing routed plan format.
- `guif validate <project>` validates project semantics, themes, workflows, and resource manifests.
- `guif record <type> "<message>"` stores reusable project knowledge.
- `guif resource-create`, `resource-show`, and `resource-validate` manage production contracts.
- `guif asset-validate <manifest> <asset>` checks dimensions, format, alpha, and naming.
- `guif export <project> --target <engine>` validates, copies, and prepares assets through an engine adapter.
- `guif compose-edit` and `guif qa-pixels` preserve and verify protected pixels.
- Tests run on Python 3.10, 3.11, and 3.12.

## Install for development

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
pip install -e .[dev]
```

## ChatGPT-oriented runtime flow

The intended entry point is natural-language work directed through ChatGPT or another agent host:

```text
User requirement
  -> ChatGPT / agent host
  -> GUIF Runtime
  -> project context
  -> selected pipeline
  -> registered agents
  -> Task result
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
print(task.to_dict())
```

The equivalent CLI command is:

```bash
guif run "Create the medieval harbor shop page" \
  --project LeekParty \
  --pipeline ui-production
```

## Runtime contract

The alpha.9 runtime is an executable orchestration contract, not an implemented AI art worker.

```text
Runtime
  -> Context Loader
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

Each agent receives and returns the same mutable `Task`. Agents do not call one another. The runtime alone resolves pipeline order through the registry.

The built-in agents currently execute contract-level behavior: they record lifecycle events, responsibilities, and state transitions. Later releases can replace individual contracts with LLM, image-generation, Figma, GitHub, QA, or engine integrations without changing the runtime core.

Runtime context currently loads:

- `project.json`
- the active project theme when configured
- project workflow manifests
- production resource manifests
- project memory records

## Quick start

```bash
guif init LeekParty
guif run "Create a trade button" --project LeekParty
guif resource-create trade-button-long button 264 134 png \
  --project LeekParty \
  --target-engine unity \
  --source source/trade-button-long.png \
  --import-settings '{"spriteMode":"Single","mipmapEnabled":false}'
guif export LeekParty --target unity
guif validate LeekParty
```

## Engine adapter layer

The generic exporter delegates engine-specific preparation to adapters:

```text
Exporter
  -> GenericAdapter
  -> UnityAdapter
  -> GodotAdapter
  -> UnrealAdapter
```

The adapter registry lives in `guif/adapters/`. The core exporter validates and stages assets; adapters own engine-specific metadata generation.

Current behavior:

- `generic`: copies the validated asset without a sidecar.
- `unity`: writes `<asset>.guif-unity.json` with sprite and mipmap import hints.
- `godot`: writes `<asset>.guif-godot.json` with texture import hints.
- `unreal`: writes `<asset>.guif-unreal.json` with UI texture-group and mipmap hints.

These JSON sidecars are deterministic GUIF metadata, not native engine-generated files.

## Operating principles

1. Natural language is the primary user interface; CLI remains an implementation and CI interface.
2. Git is the long-term source of truth.
3. Runtime orchestration stays model-agnostic.
4. Agents do not depend on or directly invoke one another.
5. Effect images and production assets remain separate.
6. Engine-specific behavior belongs in adapters, not the framework core.
7. Local edits preserve non-target pixels through mask-based composition.
8. A release is complete only when feature, tests, CI, docs, and version metadata agree.

## Repository direction

The next step is to replace contract-only agents incrementally, beginning with a real Planner and persisted Task runs, while keeping the runtime usable and model-independent throughout the migration.
