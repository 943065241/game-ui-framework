# Game UI Framework (GUIF)

GUIF is a local-first, AI-agnostic framework for planning, producing, reviewing, and evolving game UI work.

## Status

`v1.0.0-alpha.6` — executable workflow, project, theme, resource-manifest, asset-validation, protected-edit, memory, and QA bootstrap.

## What works now

- `guif init <project>` creates a project workspace.
- `guif inspect [project]` summarizes framework or project state.
- `guif plan "<requirement>"` routes a requirement through a resolved workflow manifest.
- `guif validate <project>` validates project semantics, themes, workflows, and production resource manifests.
- `guif record <type> "<message>"` stores decisions, lessons, mistakes, or best practices.
- `guif theme-create` and `guif theme-validate` manage theme definitions.
- `guif workflow-list`, `workflow-show`, and `workflow-validate` manage workflow manifests.
- `guif resource-create`, `resource-show`, and `resource-validate` manage deterministic production resource contracts.
- `guif asset-validate <manifest> <asset>` checks an actual image against dimensions, format, alpha, and output naming requirements.
- `guif compose-edit` preserves protected pixels during local image edits.
- `guif qa-pixels` verifies protected pixels at zero tolerance by default.
- Tests run with `pytest` and GitHub Actions on Python 3.10, 3.11, and 3.12.

## Install for development

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e .[dev]
```

## Quick start

```bash
guif init LeekParty
guif theme-create "Medieval Harbor" "Warm sunset harbor shop" --project LeekParty
guif resource-create trade-button-long button 264 134 png --project LeekParty --target-engine unity
guif resource-show projects/LeekParty/production-assets/trade-button-long.resource.json
guif asset-validate projects/LeekParty/production-assets/trade-button-long.resource.json trade-button-long.png
guif plan "Export transparent trading buttons" --project LeekParty
guif validate LeekParty
```

## Production resource manifests

A resource manifest defines the production contract before export:

```json
{
  "schema_version": 1,
  "id": "trade-button-long",
  "type": "button",
  "width": 264,
  "height": 134,
  "format": "png",
  "alpha_required": true,
  "target_engine": "unity",
  "output_name": "trade-button-long.png",
  "source": null
}
```

Current manifest validation covers:

- lowercase kebab-case IDs
- supported resource types and file formats
- positive pixel dimensions
- alpha-channel requirements
- output extension consistency
- target-engine metadata (`generic`, `unity`, `godot`, or `unreal`)

Resource manifests are stored at:

```text
projects/<project>/production-assets/<resource-id>.resource.json
```

`guif validate <project>` automatically validates every resource manifest in the project.

## Actual asset validation

```bash
guif asset-validate \
  projects/LeekParty/production-assets/trade-button-long.resource.json \
  trade-button-long.png
```

The command opens the actual image and compares it with the manifest. It reports:

- expected and actual pixel dimensions
- expected and detected image format
- whether an alpha channel is required and present
- expected and actual output filename
- a structured error list and pass/fail result

A mismatch returns exit code `1`, so the command can be used in CI or export scripts.

## Workflow manifests

GUIF ships with five built-in workflows: `effect-image`, `theme-direction`, `resource-production`, `quality-assurance`, and `framework-evolution`.

Projects can override a workflow at:

```text
projects/<project>/workflows/<workflow-id>.json
```

## Protected local-edit workflow

```bash
guif compose-edit original.png generated.png mask.png composed.png
guif qa-pixels original.png composed.png mask.png
```

White mask pixels are editable. Black mask pixels are protected.

## Operating principles

1. Natural language first.
2. Git is the long-term source of truth.
3. Effect images and production assets remain separate.
4. Local edits must preserve non-target pixels through mask-based composition.
5. Every confirmed decision can be recorded and reviewed.
6. A release version is not complete until feature, tests, CI, docs, and version metadata agree.

## Repository direction

The next planned release focuses on batch validation and deterministic export staging for all production assets in a project.
