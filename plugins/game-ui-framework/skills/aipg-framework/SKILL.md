---
name: aipg-framework
description: Use AIPG from Codex to route and govern AI production across pluggable domains. Trigger for framework-wide production routing, domain selection, workflow registration, approvals, Artifact lineage, protected sources, Candidate Changes, evidence, controlled revision, recovery, and gated export. Use the GUIF sibling Skill for game UI and visual production details.
---

# AIPG for Codex

AIPG is the AI Production & Governance Framework. It owns domain-neutral
workflow routing and governance. GUIF is its game UI and visual-production domain.

## Architecture

Route requests in this order:

1. Identify the production domain and intended outcome.
2. Select a registered workflow.
3. Resolve only the context required by that workflow.
4. Present the production contract and required approvals.
5. Invoke truthful Host and Tool capabilities.
6. Register real Artifacts and lineage.
7. Perform deterministic and semantic review at their correct assurance level.
8. Apply revision scope, recovery, and gated export.

Never make Theme confirmation a top-level AIPG prerequisite. Theme and master
references belong to the GUIF visual-production domain.

## Built-in domains

- `framework-governance`: Candidate Change, evidence, adoption, publication,
  refresh, and regression.
- `visual-production`: GUIF workflows, including effect image, image editing,
  resources, QA, and master-guided layer creation.

## Compatibility

Keep the `guif` Python package, CLI alias, private-data environment variables,
existing schemas, and `$game-ui-framework` Skill operational during the AIPG
1.x migration. New domain-neutral integrations should use AIPG naming.

## Candidate Changes

Framework, workflow, policy, provider-routing, and Tool-integration changes
remain isolated from stable production. Real candidate evidence is required
before adoption. Trial authorization does not authorize merge or publication,
and adoption does not claim a running plugin snapshot was hot-reloaded.
