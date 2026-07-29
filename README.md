# Game UI Framework (GUIF)

**English** | [简体中文](README.zh-CN.md)

GUIF is a local-first game UI production framework with configurable Hosts and Tools. ChatGPT is the default Host and `chatgpt-image` is the default image generation and editing Tool, but neither is a hard-coded Core dependency.

## Status

`v1.0.0-alpha.22` adds the first production **Gated Export Agent**.

A generated file is no longer allowed to enter Project truth merely because a Tool returned it. GUIF now evaluates the persisted Task, initial Approval, Contract QA, aggregate Visual Review, active Artifact identity, approved Resource Contract, target Engine compatibility, and Revision resolution before any production file is written.

```text
Prompt / Revision Job
  -> Tool execution or ChatGPT handoff
  -> Artifact Registry
  -> metadata and semantic Visual Review
  -> active reviewed Artifact
  -> Gated Export Plan                 no Project mutation
  -> Gated Export Execute
       -> Project truth materialization
       -> Engine-specific export
       -> Export Manifest
       -> transaction audit and backups
  -> optional conflict-aware rollback
```

The bilingual living product specification is maintained at [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md).

## Export gate

`Runtime.prepare_gated_export()` creates a persisted, reviewable plan and does not modify Project files.

The plan checks:

- Task status is `completed`;
- initial Approval is `approved` or `not-required`;
- Contract QA is `passed`;
- aggregate `qa_report.export_gate.allowed` is true;
- at least one active `production-asset` Artifact exists;
- every selected Artifact is real, visual, reviewed, and not a simulation;
- Artifact files remain inside the Run directory and match registered SHA-256 values;
- every Artifact Output Contract exactly matches an approved Resource manifest candidate;
- no duplicate active Artifact exists for the same Resource;
- all Revision Plans are `resolved` or `rejected`;
- the Resource target is compatible with the selected Engine.

Any failed check produces a persisted `blocked` Export record. No production file is copied and no implicit fallback is used.

## Project truth materialization

A ready Export writes approved assets to:

```text
projects/<project>/production-assets/files/<output-name>
projects/<project>/production-assets/<resource-id>.resource.json
```

The materialized Resource manifest points to the managed Project source file. Existing files are backed up before replacement.

Only active `production-asset` Artifacts are materialized. Effect images, simulations, receipts, stale Artifacts, and unreviewed results remain available for provenance but do not enter production truth.

## Engine export

Each execution creates an immutable output directory:

```text
projects/<project>/exports/<engine>/<export-id>/
  <approved assets>
  <engine adapter metadata>
  export-manifest.json
```

Unity, Godot, Unreal, and Generic adapters remain supported. The Export Manifest records:

- Task and Export identity;
- target Engine and actor;
- gate snapshot;
- source Artifact, Job, Review, and SHA-256;
- materialized Project paths;
- Engine output paths and SHA-256;
- Adapter output and import hints.

The older `guif export` command remains available for validating and exporting Resource files that already exist in Project truth. New AI production flows should use the Task-bound gated Export API.

## Transaction audit and rollback

Each completed Export stores:

```text
projects/<project>/export-history/<export-id>/
  transaction.json
  backups/
```

The transaction records every Project truth mutation, whether a file previously existed, its prior hash, backup path, and exported hash.

Rollback is conflict-aware. GUIF compares current Project files with the hashes written by the Export. If a file changed afterward, rollback fails closed instead of overwriting newer work. A force rollback requires an explicit actor and reason and is recorded in the audit.

## Runtime API

```python
runtime = Runtime(workspace)

plan = runtime.prepare_gated_export(
    "LeekParty",
    task_id,
    target_engine="unity",
)

record = runtime.execute_gated_export(
    "LeekParty",
    task_id,
    target_engine="unity",
    actor="project-owner@example.com",
)

exports = runtime.list_gated_exports("LeekParty", task_id)
record = runtime.get_gated_export("LeekParty", task_id, record["export_id"])

rolled_back = runtime.rollback_gated_export(
    "LeekParty",
    task_id,
    record["export_id"],
    actor="project-owner@example.com",
    reason="Restore the previous production asset set.",
)
```

## CLI

```bash
guif run-export-plan <task-id> \
  --project LeekParty \
  --target unity

guif run-export-execute <task-id> \
  --project LeekParty \
  --target unity \
  --actor project-owner@example.com

guif run-export-list <task-id> --project LeekParty
guif run-export-show <task-id> <export-id> --project LeekParty

guif run-export-rollback <task-id> <export-id> \
  --project LeekParty \
  --actor project-owner@example.com \
  --reason "Restore the previous approved production set."
```

Use `--force` only after reviewing post-export conflicts.

## Persisted Run state

Task Run directories may now include:

```text
approvals.json
artifacts.json
executions.json
tool-resolution.json
tool-handoffs.json
visual-reviews.json
revision-plans.json
revision-execution.json
gated-exports.json
```

`run-list` includes `gated_export_count`, `completed_export_count`, and `latest_export_status`.

## Existing production capabilities

GUIF also provides:

- Workflow-driven Planner, Director, Theme, Resource, Prompt, and Semantic QA Agents;
- relevance-based Project Context selection;
- persistent initial and Revision Approval gates;
- configurable Host and Tool routing with ChatGPT defaults;
- registered, available, and installable Tool discovery;
- reviewable Tool connection requests and opaque Credential references;
- external ChatGPT image generation and editing handoffs;
- Artifact identity, provenance, SHA-256, MIME, dimensions, and References;
- deterministic metadata review and optional semantic Visual Inspectors;
- controlled Revision Jobs with immutable source binding and review-gated supersession;
- protected-pixel composition checks;
- deterministic legacy Resource export.

## Development

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
pip install -e .[dev]
pytest -q
```

## Current limitations

- ChatGPT product-side orchestration must still consume external handoffs and submit files automatically.
- The default semantic Visual Inspector Registry is empty.
- Gated Export currently materializes generated `production-asset` Artifacts; packaging approved reused Resources into the same transaction is a later extension.
- Rollback is file-based and does not yet create a Git branch or commit.
- Export actors are strings rather than authenticated Host identities.
- Remote object storage, retention policy, concurrent Export locking, and signed manifests are not implemented.

## Next phase

The next priority is **alpha.23: Authenticated Host API and Git Change Management**: stable Host result protocol, authenticated actors, optimistic concurrency, Git change sets, branch and commit creation, rollback integration, cancellation, and execution summaries.
