# Game UI Framework (GUIF)

GUIF is a local-first, AI-agnostic framework for planning, producing, reviewing, exporting, and evolving game UI work.

## Status

`v1.0.0-alpha.8` — engine-adapter exports, resource import hints, deterministic asset validation and staging, protected editing, memory, workflows, projects, and themes.

## What works now

- `guif init <project>` creates a project workspace.
- `guif inspect [project]` summarizes framework or project state.
- `guif plan "<requirement>"` routes a requirement through a resolved workflow manifest.
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

## Quick start

```bash
guif init LeekParty
guif resource-create trade-button-long button 264 134 png \
  --project LeekParty \
  --target-engine unity \
  --source source/trade-button-long.png \
  --import-settings '{"spriteMode":"Single","mipmapEnabled":false}'
guif export LeekParty --target unity
guif validate LeekParty
```

## Engine adapter layer

The generic exporter now delegates engine-specific preparation to adapters:

```text
Exporter
  -> GenericAdapter
  -> UnityAdapter
  -> GodotAdapter
  -> UnrealAdapter
```

The adapter registry lives in `guif/adapters/`. The core exporter only validates and stages assets; adapters own engine-specific metadata generation.

Current behavior:

- `generic`: copies the validated asset without a sidecar.
- `unity`: writes `<asset>.guif-unity.json` with sprite and mipmap import hints.
- `godot`: writes `<asset>.guif-godot.json` with texture import hints.
- `unreal`: writes `<asset>.guif-unreal.json` with UI texture-group and mipmap hints.

These JSON sidecars are deterministic GUIF metadata, not native engine-generated files. They provide a stable adapter contract without coupling the framework core to one engine.

## Resource import hints

Resource manifests support an optional `import_settings` object:

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
  "source": "source/trade-button-long.png",
  "import_settings": {
    "spriteMode": "Single",
    "pixelsPerUnit": 100,
    "mipmapEnabled": false
  }
}
```

Adapter defaults are merged first and project hints override them. This lets a project customize engine imports while keeping the generic resource contract portable.

## Deterministic export pipeline

```bash
guif export LeekParty --target unity
```

The exporter discovers matching manifests, resolves source files, validates actual images, cleans stale output by default, copies passing assets, runs the selected adapter, and writes `export-report.json` schema version 2. Each exported record includes adapter metadata paths and resolved import hints.

Default output:

```text
projects/<project>/exports/<target-engine>/
```

Additional options:

```bash
guif export LeekParty --target unity --output build/ui
guif export LeekParty --target unity --no-clean
```

## Operating principles

1. Natural language first.
2. Git is the long-term source of truth.
3. Effect images and production assets remain separate.
4. Engine-specific behavior belongs in adapters, not the framework core.
5. Local edits preserve non-target pixels through mask-based composition.
6. A release is complete only when feature, tests, CI, docs, and version metadata agree.

## Repository direction

The next planned release focuses on reproducible export fingerprints, checksums, and incremental export decisions so unchanged assets can be skipped safely.
