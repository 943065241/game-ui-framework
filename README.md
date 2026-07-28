# Game UI Framework (GUIF)

GUIF is a local-first, AI-agnostic framework for planning, producing, reviewing, exporting, and evolving game UI work.

## Status

`v1.0.0-alpha.7` — executable workflows, project and theme contracts, resource manifests, actual-asset validation, deterministic export, protected editing, memory, and QA.

## What works now

- `guif init <project>` creates a project workspace.
- `guif inspect [project]` summarizes framework or project state.
- `guif plan "<requirement>"` routes a requirement through a resolved workflow manifest.
- `guif validate <project>` validates project semantics, themes, workflows, and resource manifests.
- `guif record <type> "<message>"` stores reusable decisions, lessons, mistakes, or best practices.
- `guif theme-create` and `guif theme-validate` manage theme definitions.
- `guif workflow-list`, `workflow-show`, and `workflow-validate` manage workflow manifests.
- `guif resource-create`, `resource-show`, and `resource-validate` manage production resource contracts.
- `guif asset-validate <manifest> <asset>` checks dimensions, format, alpha, and output naming.
- `guif export <project> --target <engine>` validates and stages all matching assets with a JSON report.
- `guif compose-edit` and `guif qa-pixels` preserve and verify protected pixels.
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
guif resource-create trade-button-long button 264 134 png \
  --project LeekParty \
  --target-engine unity \
  --source source/trade-button-long.png
guif asset-validate \
  projects/LeekParty/production-assets/trade-button-long.resource.json \
  projects/LeekParty/source/trade-button-long.png
guif export LeekParty --target unity
guif validate LeekParty
```

## Production resource manifests

A resource manifest defines a deterministic production contract:

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
  "source": "source/trade-button-long.png"
}
```

Manifest validation covers lowercase kebab-case IDs, supported resource types and formats, positive dimensions, alpha requirements, extension consistency, target-engine metadata, and source metadata.

Resource manifests are stored at:

```text
projects/<project>/production-assets/<resource-id>.resource.json
```

## Actual asset validation

```bash
guif asset-validate <manifest.resource.json> <asset.png>
```

The command opens the actual image and compares its dimensions, detected format, alpha-channel capability, and filename with the manifest. A mismatch returns exit code `1`.

## Deterministic export pipeline

```bash
guif export LeekParty --target unity
```

The exporter:

1. discovers every `*.resource.json` manifest in the project;
2. selects resources marked for the requested engine or `generic`;
3. resolves each source path relative to the project root;
4. validates the actual image before copying it;
5. cleans stale output by default;
6. copies passing assets using the manifest `output_name`;
7. writes `export-report.json` with exported files, failures, and pass/fail state.

Default output:

```text
projects/<project>/exports/<target-engine>/
```

Use a custom directory or preserve existing files with:

```bash
guif export LeekParty --target unity --output build/ui
guif export LeekParty --target unity --no-clean
```

The export command returns exit code `1` when any selected resource fails validation, making it suitable for CI and engine-import staging.

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
6. A release is complete only when feature, tests, CI, docs, and version metadata agree.

## Repository direction

The next planned release focuses on engine-specific export adapters and reproducible export metadata, starting with Unity-oriented naming and import hints without coupling the core framework to one engine.
