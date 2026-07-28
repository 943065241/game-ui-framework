# Game UI Framework (GUIF)

GUIF is a local-first, AI-agnostic framework for planning, producing, reviewing, and evolving game UI work.

## Status

`v1.0.0-alpha.2` — executable theme, planning, memory, protected edit composition, and image QA bootstrap.

## What works now

- `guif init <project>` creates a project workspace.
- `guif inspect [project]` summarizes framework or project state.
- `guif plan "<requirement>"` creates a routed task plan.
- `guif validate <project>` validates required files and configuration.
- `guif record <type> "<message>"` stores decisions, lessons, mistakes, or best practices.
- `guif theme-create <name> <description> --project <project>` creates and activates a project theme.
- `guif theme-validate <theme.json>` validates a theme definition.
- `guif compose-edit <original> <generated> <mask> <output>` composites only the editable mask area over the original image.
- `guif qa-pixels <original> <edited> <mask>` verifies that protected pixels remain unchanged.
- Rule-based routing selects Director, Theme, Resource, QA, or Framework Manager.
- Tests run with `pytest` and GitHub Actions.

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
guif plan "Create a medieval harbor shop effect image" --project LeekParty
guif inspect LeekParty
guif validate LeekParty
guif record decision "Use one harbor window and warm sunset lighting" --project LeekParty
```

## Protected local-edit workflow

```bash
guif compose-edit original.png generated.png mask.png composed.png
guif qa-pixels original.png composed.png mask.png
```

White mask pixels are editable. Black mask pixels are protected. The composition step copies generated pixels only inside the editable area, and the QA step verifies that protected pixels are unchanged.

## Operating principles

1. Natural language first.
2. Git is the long-term source of truth.
3. Effect images and production assets remain separate.
4. Local image edits must preserve non-target pixels through mask-based composition.
5. Every confirmed decision can be recorded and reviewed.

## Repository direction

This bootstrap intentionally starts small and executable. Later releases will add atlas export, adapter plugins, richer schemas, workflow manifests, and production integrations without replacing the CLI contract.
