# Game UI Framework (GUIF)

**English** | [简体中文](README.zh-CN.md)

GUIF is a local-first game UI production framework with configurable Hosts and Tools. ChatGPT is the default Host and `chatgpt-image` is the default image generation and editing Tool, but neither is a hard-coded Core dependency.

## Status

`v1.0.0-alpha.23` separates user Theme data from framework and project Git repositories.

A Theme is now private, user-owned, versioned data. The public framework repository contains only contracts, storage interfaces, workflow code, tests, and fictional fixtures. Real Theme names, visual rules, palettes, materials, conversation decisions, and iteration history are stored outside the repository.

```text
new conversation
  -> confirm Theme
       -> select a historical Theme
       -> create a new Theme
       -> derive a new version
       -> explicitly continue unbound
  -> bind Theme ID + version + snapshot hash
  -> run planning and production
  -> update Theme through conversation
  -> publish another immutable Theme version
```

The bilingual living product specification is maintained at [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md). Privacy migration and repository-history guidance are in [`docs/PRIVACY_MIGRATION.md`](docs/PRIVACY_MIGRATION.md).

## Private data layout

Set `GUIF_DATA_HOME` to choose the private data parent. Without it, GUIF uses a hidden sibling directory outside the workspace repository.

```text
<private-data-root>/
  themes/<theme-id>/
    index.json
    versions/1.json
    versions/2.json
  conversation-theme-bindings/<conversation-id>.json
  project-theme-bindings/<project>.json
  runs/<project>/<task-id>/
  plans/<project>/
  migrations/
  privacy-reports/
```

Project Git does not receive full Theme content. Persisted Task Context contains only:

```json
{
  "active_theme_ref": {
    "theme_id": "theme-example",
    "version": 2,
    "snapshot_hash": "sha256...",
    "privacy": "private"
  }
}
```

The full Theme is hydrated only while the Runtime is executing inside the approved private-data boundary.

## Conversation-first Theme resolution

```python
from pathlib import Path
from guif.runtime import Runtime, ThemeResolutionRequired

runtime = Runtime(Path.cwd())
resolution = runtime.prepare_conversation_theme(
    "conversation-001",
    project="SampleGame",
)
```

An unbound new conversation returns `confirmation-required`. Visual production does not silently infer a framework preset. The Host must select, create, derive, or explicitly continue without a Theme.

Create and bind a fully fictional example Theme:

```python
record = runtime.create_private_theme(
    "Geometric Arcade",
    {
        "description": "Abstract shapes and neutral test surfaces.",
        "palette": ["test blue", "test gray"],
        "materials": ["matte polymer"],
        "lighting": "flat studio light",
        "must_include": ["hexagonal navigation"],
        "avoid": ["real brands"],
    },
    actor="host",
    conversation_id="conversation-001",
    project="SampleGame",
)
```

Derive a new immutable version from conversation feedback:

```python
revision = runtime.derive_private_theme(
    record["theme_id"],
    {"lighting": "soft top light"},
    from_version=1,
    actor="host",
    conversation_id="conversation-001",
)
```

Version 1 remains unchanged. The conversation binding moves to the approved new version.

## Private Runtime evidence

Task Runs and natural-language Plans are also private because they may include prompts, Theme contracts, review findings, and user decisions.

```text
public project tree
  project.json
  workflows/
  production-assets/          approved production truth only
  memory/                     explicitly project-owned records

private data tree
  themes/
  runs/
  plans/
  conversation bindings/
```

Legacy project-local Runs remain readable for migration, but new Runs are written only to private storage.

## Migration and privacy audit

```python
report = runtime.migrate_legacy_project_themes(
    "SampleGame",
    actor="migration",
)

audit = runtime.audit_privacy(
    sensitive_terms=("private phrase",),
)
```

Migration imports legacy Theme files into the private library, removes project-local Theme files and bindings, and writes a private migration report. The working-tree audit detects common private-data paths and optional caller-supplied sensitive terms.

Removing a file from the current branch does **not** erase prior commits, pull-request diffs, forks, caches, release archives, or clones. GUIF does not perform an automatic destructive history rewrite. Follow the incident-response steps in the privacy migration guide after identifying the exact exposure scope.

## Existing production flow

```text
private Theme selection
  -> Planner / Director / Theme / Resource / Prompt
  -> Approval
  -> configured image Tool or ChatGPT handoff
  -> Artifact Registry
  -> metadata and semantic Visual Review
  -> controlled Revision
  -> Gated Export
  -> Project truth / Engine output / audit / rollback
```

Gated Export continues to require completed Task state, approved contracts, passing visual review, valid Artifact SHA-256 identity, resolved Revisions, and Engine compatibility before any production file is written.

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
- Private storage is file-backed and does not yet provide encryption-at-rest, remote synchronization, retention policy, or concurrent leases.
- Conversation and approval actors are strings rather than authenticated identities.
- Current-tree privacy audit cannot prove removal from Git history, forks, caches, or external clones.
- Git change sets, signed manifests, and authenticated Host callbacks remain future work.

## Next phase

The next priority is **alpha.24: Authenticated Host API and Git Change Management**: authenticated actors, optimistic concurrency and Task leases, stable Host result callbacks, Git change sets, branch/commit/diff/revert integration, and Export transaction linkage.
