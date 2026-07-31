# Migrating GUIF to AIPG

## Naming

- Top-level framework and plugin display name: **AIPG Framework**.
- Visual-production domain: **GUIF Visual Production**.
- New Python facade and CLI: `aipg`.
- Compatibility Python package and CLI: `guif`.

## Compatibility contract

AIPG 1.x keeps these surfaces:

- imports from `guif`;
- the `guif` executable;
- `$game-ui-framework`;
- existing Workflow schema v1 and v2;
- existing private-data environment variables;
- existing Theme, Source, Candidate Change, and Artifact records.

New domain-neutral code should import from `aipg`. Visual code may continue to
use `guif`.

## Plugin migration

The candidate plugin ID changes from `game-ui-framework` to
`aipg-framework`. The repository URL remains unchanged during the candidate.
Do not claim that an installed GUIF snapshot was renamed in place. Adoption,
publication, plugin refresh, and a new Codex session remain required.

## Workflow migration

Existing projects need no immediate manifest rewrite. Schema v1 and v2
workflows resolve to their registered built-in domain. New workflows should use
schema v3 and declare their domain and required context explicitly.

## Theme behavior

Theme confirmation is no longer described as an AIPG top-level prerequisite.
GUIF workflows can continue to require Theme. The master-guided workflow
requires both Theme and a master reference.
