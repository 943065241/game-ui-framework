# Game UI Framework (GUIF)

GUIF is a local-first, AI-agnostic framework for planning, producing, reviewing, and evolving game UI work.

## Status

`v1.0.0-alpha.4` — executable workflow manifests, project schema, theme, planning, memory, protected edit composition, and image QA bootstrap.

## What works now

- `guif init <project>` creates a project workspace.
- `guif inspect [project]` summarizes framework or project state.
- `guif plan "<requirement>"` routes a requirement and builds the plan from a resolved workflow manifest.
- `guif validate <project>` validates required directories, project semantics, active-theme references, theme files, and project workflow files.
- `guif record <type> "<message>"` stores decisions, lessons, mistakes, or best practices.
- `guif theme-create <name> <description> --project <project>` creates and activates a project theme.
- `guif theme-validate <theme.json>` validates a theme definition.
- `guif workflow-list [--project <project>]` lists built-in workflows and project overrides.
- `guif workflow-show <id> --project <project>` shows the resolved workflow used by the planner.
- `guif workflow-validate <workflow.json>` validates a workflow manifest.
- `guif compose-edit <original> <generated> <mask> <output>` composites only the editable mask area over the original image.
- `guif qa-pixels <original> <edited> <mask>` verifies that protected pixels remain unchanged.
- Tests cover project creation, routing, memory, themes, schema validation, workflow overrides, pixel QA, and protected composition.
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
guif workflow-list --project LeekParty
guif workflow-show theme-direction --project LeekParty
guif plan "Create a medieval harbor shop effect image" --project LeekParty
guif inspect LeekParty
guif validate LeekParty
guif record decision "Use one harbor window and warm sunset lighting" --project LeekParty
```

## Workflow manifests

GUIF ships with five executable workflow manifests:

- `effect-image`
- `theme-direction`
- `resource-production`
- `quality-assurance`
- `framework-evolution`

A project can override any built-in workflow by placing a valid JSON manifest at:

```text
projects/<project>/workflows/<workflow-id>.json
```

The planner resolves the project override first, then falls back to the built-in workflow. The resolved workflow name, manager, source, and exact steps are embedded in every generated plan.

Example override:

```json
{
  "schema_version": 1,
  "id": "theme-direction",
  "name": "LeekParty Theme Review",
  "manager": "Theme Manager",
  "steps": [
    "Load the active medieval harbor theme",
    "Check warm sunset lighting and clean material rendering",
    "Reject pirate skulls, excessive noise, and unrelated neon styling",
    "Record the approved direction"
  ]
}
```

## Protected local-edit workflow

```bash
guif compose-edit original.png generated.png mask.png composed.png
guif qa-pixels original.png composed.png mask.png
```

White mask pixels are editable. Black mask pixels are protected. The composition step copies generated pixels only inside the editable area, and the QA step verifies that protected pixels are unchanged.

## Project validation contract

`project.json` is checked semantically, not only for existence. GUIF validates its schema version, project name, lifecycle status, creation timestamp, current-theme type, and whether the referenced theme file exists. Every theme JSON and project workflow JSON is also validated during `guif validate`.

## Operating principles

1. Natural language first.
2. Git is the long-term source of truth.
3. Effect images and production assets remain separate.
4. Local image edits must preserve non-target pixels through mask-based composition.
5. Every confirmed decision can be recorded and reviewed.

## Repository direction

The next planned release focuses on production resource manifests and deterministic export contracts for dimensions, transparency, naming, and target-engine metadata.
