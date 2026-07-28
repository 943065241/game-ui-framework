# Game UI Framework (GUIF)

GUIF is a local-first, AI-agnostic framework for planning, producing, reviewing, and evolving game UI work.

## Status

`v1.0.0-alpha.1` — executable bootstrap.

## What works now

- `guif init <project>` creates a project workspace.
- `guif inspect [project]` summarizes framework or project state.
- `guif plan "<requirement>"` creates a routed task plan.
- `guif validate [project]` validates required files and configuration.
- `guif record <type> "<message>"` stores decisions, lessons, mistakes, or best practices.
- Rule-based routing selects Director, Theme, Resource, QA, or Framework Manager.
- Tests run with `pytest`.

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
guif plan "Create a medieval harbor shop effect image" --project LeekParty
guif inspect LeekParty
guif validate LeekParty
guif record decision "Use one harbor window and warm sunset lighting" --project LeekParty
```

## Operating principles

1. Natural language first.
2. Git is the long-term source of truth.
3. Effect images and production assets remain separate.
4. Local image edits must preserve non-target pixels through mask-based composition.
5. Every confirmed decision can be recorded and reviewed.

## Repository direction

This bootstrap intentionally starts small and executable. Later releases will add image QA, atlas export, adapter plugins, richer schemas, and production integrations without replacing the CLI contract.
