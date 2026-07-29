# Game UI Framework (GUIF)

**English** | [简体中文](README.zh-CN.md)

GUIF is a local-first game UI production framework with configurable Hosts and Tools. ChatGPT is the default Host, `chatgpt-image` is the default image generation/editing Tool, and `chatgpt-vision` is the default semantic visual inspector. All remain replaceable contracts rather than hard-coded Core dependencies.

## Status

`v1.0.0-alpha.28` freezes the conversation-facing MVP and adds beta-readiness controls:

```text
one-command bootstrap
  -> private Theme confirmation
  -> natural-language production request
  -> contextual Approval
  -> real image generation or editing
  -> deterministic metadata review
  -> semantic visual review
  -> independently approved Revision when needed
  -> Gated Export
  -> verified private backup and recovery
```

Alpha.28 does not expand the product into another large subsystem. It stabilizes the alpha.27 workflow, gives private data an explicit backup/migration contract, and defines the compatibility boundary that beta.1 must preserve.

The bilingual living specification is maintained at [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md). Privacy migration and repository-history guidance remain in [`docs/PRIVACY_MIGRATION.md`](docs/PRIVACY_MIGRATION.md).

## One-command bootstrap

Install the development package:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
pip install -e .[dev]
```

Initialize a Project, create a ChatGPT Host credential, and open a private Conversation:

```bash
guif-ready start \
  --workspace . \
  --project SampleGame \
  --conversation conversation-001
```

The first call can create:

```text
projects/SampleGame/project.json
private Host credential
private Conversation Workflow record
Theme confirmation view
```

A newly issued Bearer token is displayed once. Store it in a protected secret manager or environment variable:

```bash
export GUIF_HOST_TOKEN='guifh1....'
```

The token is not written into Project Git, the Conversation record, backup manifests, diagnostics, or public output.

## Conversation-first workflow

After bootstrap, continue through the existing user-facing command:

```bash
guif-conversation open \
  --project SampleGame \
  --conversation conversation-001
```

A new Conversation begins at:

```text
theme-confirmation
```

Supported Theme paths:

```text
theme-list       list private historical choices
theme-select     select an existing private Theme
theme-create     create and bind a new private Theme
theme-derive     create an immutable new Theme version
theme-unbound    explicitly continue without a Theme
```

Real user Theme content remains in the private Theme Library outside framework and Project Git. Public repository examples use only wholly fictional fixtures.

Submit a natural-language request:

```bash
guif-conversation submit \
  --project SampleGame \
  --conversation conversation-001 \
  --request-key chat-turn-001 \
  "Create a fictional 1080x2340 observatory shop page and export Unity"
```

Approve the current initial or Revision gate without handling an Approval ID, Task ID, etag, lease, claim, Handoff ID, or Callback ID:

```bash
guif-conversation approve \
  --project SampleGame \
  --conversation conversation-001
```

The normal user view exposes only:

```text
conversation and project
current stage and message
private Theme summary
contextual actions
safe Artifact summaries
recovery availability
```

Low-level identities remain enforced beneath the facade and are available only through explicit diagnostics or developer APIs.

## Real image and visual loop

The configured Host supplies actual image and visual capabilities:

```python
view = conversation.run_host_until_blocked(
    "SampleGame",
    "conversation-001",
    image_executor=call_chatgpt_image_tool,
    visual_inspector=call_chatgpt_visual_inspection,
)
```

GUIF coordinates:

```text
Task-scoped Host Work discovery
-> Task etag
-> exclusive Task lease
-> Actor-bound one-time Work claim
-> immutable Attachment retrieval
-> real image or semantic result submission
-> Artifact registration
-> metadata review
-> semantic review
-> next user-facing stage
```

The local Python package does not fabricate pixels and cannot enter ChatGPT's internal tool runtime by itself. ChatGPT or another configured Host must embed the Host loop or consume the authenticated Gateway work endpoints.

Metadata review never claims that Theme consistency, composition, readability, or usability passed. Those conclusions require an authenticated semantic visual result.

## Controlled Revision

Actionable visual findings produce a versioned Revision Job and a separate approval gate:

```text
revision-approval-required
```

Initial generation Approval never authorizes editing. The source Artifact remains active until the replacement is real, non-simulation, lineage-valid, and semantically reviewed as passed.

## Verified private backup

Create the default portable backup:

```bash
guif-ready backup --workspace .
```

The default destination is:

```text
<private-data-root>/backups/portable-<timestamp>.guif-private.zip
```

The portable profile includes user-owned and recoverable production data such as:

```text
themes
conversation-theme-bindings
conversation-workflows
project-theme-bindings
runs
plans
host-work
migrations
privacy-reports
```

It deliberately excludes:

```text
Host credentials and credential verifiers
operation-ledger signing keys
Gateway request receipts
operation-audit authentication material
```

A `full-local` archive requires an explicit sensitive-material decision:

```bash
guif-ready backup \
  --workspace . \
  --profile full-local \
  --include-sensitive \
  --output /protected/offline/location/full-local.guif-private.zip
```

GUIF backup archives are integrity checked but are not encrypted at rest. Sensitive archives must be stored on protected encrypted media or in an encrypted secret-bearing backup system.

### Backup verification

```bash
guif-ready backup-verify /path/to/portable.guif-private.zip
```

Verification checks:

```text
manifest schema and manifest hash
canonical member paths
no path traversal
no duplicate members
no symbolic-link members
per-file size and SHA-256
total extraction limit
no unmanifested archive members
```

### Plan-first restore

A restore is dry-run by default:

```bash
guif-ready backup-restore /path/to/portable.guif-private.zip
```

Conflict policies:

```text
fail      block on any different existing file
skip      keep existing conflicting files
replace   replace conflicts after creating a portable pre-restore backup
```

Apply explicitly:

```bash
guif-ready backup-restore \
  /path/to/portable.guif-private.zip \
  --conflict replace \
  --apply
```

Restore writes each file atomically and verifies its SHA-256 after materialization.

## Recorded private schema migration

Scan private records without mutation:

```bash
guif-ready migrate --workspace .
```

Apply supported repairs explicitly:

```bash
guif-ready migrate \
  --workspace . \
  --apply \
  --actor local-owner
```

Alpha.28 keeps Conversation Workflow schema version 1 compatible while adding missing frozen-MVP metadata such as privacy and compatibility markers. Every applied repair is recorded in the private migration history and a private migration report.

Unknown future schemas, invalid JSON, and raw secret-like fields fail closed and require manual review.

## Privacy-safe diagnostics

```bash
guif-ready diagnose \
  --workspace . \
  --project SampleGame \
  --conversation conversation-001
```

Diagnostics check:

```text
Project structure and schemas
private storage availability
private schema migration state
operation-ledger integrity
Host credential capabilities
Conversation stage and recovery
portable backup presence
frozen compatibility contract
```

The default report does not expose Task IDs, etags, lease tokens, claim tokens, Handoff IDs, Callback IDs, Bearer tokens, or private storage paths. Persisted reports live under:

```text
<private-data-root>/diagnostics/<project>/
```

## End-to-end acceptance gate

```bash
guif-ready acceptance \
  --workspace . \
  --project SampleGame \
  --conversation conversation-001
```

The acceptance gate passes only when:

```text
no blocking readiness check exists
and
Conversation stage is ready-to-export or completed
```

Use `--require-completed` when final Gated Export must already have succeeded.

The gate never generates a fake image or treats a metadata-only Artifact as visually accepted.

## Frozen alpha.28 compatibility contract

```bash
guif-ready contract
```

The public API version is `1`. Beta.1 must preserve the frozen conversation stages and actions, or introduce a new public API version with an explicit migration path.

Frozen user-facing stages include:

```text
theme-confirmation
ready-for-request
approval-required
ready-to-produce
image-production
visual-review
revision-approval-required
revision-ready
tool-configuration-required
ready-to-export
completed
recoverable-error
attention-required
```

The explicit legacy `ProviderAdapter` path remains available for compatibility. Production Tool routing remains ChatGPT-first and configurable; `dry-run` remains test/development-only and is never a silent production fallback.

## Private data boundary

```text
<private-data-root>/
  themes/
  conversation-theme-bindings/
  conversation-workflows/
  project-theme-bindings/
  host-credentials/
  host-work/
  gateway-requests/
  operation-audit/
  operation-ledger/
  backups/
  diagnostics/
  runs/
  plans/
  migrations/
  privacy-reports/
```

Real Themes, prompts, Conversation decisions, approval evidence, Runtime state, Work claims, Attachments, image files, semantic findings, credentials, backup archives, and diagnostics remain outside framework and Project Git by default.

## Existing production controls

GUIF continues to provide:

- private, versioned Theme Library and conversation bindings;
- configurable Host and Tool discovery, connection, health, and routing;
- model-neutral Prompt IR, contract QA, and persistent Approval gates;
- Artifact identity, SHA-256, MIME, dimensions, immutable References, and provenance;
- authenticated image generation/editing and semantic visual inspection work;
- controlled Revision execution and review-gated supersession;
- Gated Export, Engine manifests, backups, rollback, and Git Change Sets;
- authenticated Actors, Task etags, exclusive leases, idempotency, and signed private operation evidence;
- current-tree privacy audit and legacy Theme migration.

## Development

```bash
pytest -q
```

CI runs on Python 3.10, 3.11, and 3.12.

## Current limitations

- ChatGPT product integration must still embed `ChatGPTHostLoop` or consume the Gateway work API; this repository cannot invoke ChatGPT internal image tools by itself.
- Portable archives are integrity checked but not encrypted.
- File-backed Work claims and Task leases are single-node coordination, not distributed consensus.
- The built-in WSGI Gateway is not an internet-edge reverse proxy.
- Remote private-data synchronization, retention policies, key rotation, and multi-device conflict resolution are not implemented.
- Current-tree privacy audit cannot prove removal from Git history, forks, caches, or external clones.
- Remote Git push, protected-branch negotiation, and server-side release orchestration remain outside the local Core.

## Next phase

The next release target is **beta.1: production hardening without expanding the frozen MVP**. Priorities are encrypted backup integration boundaries, upgrade testing from supported alpha versions, performance and failure-injection testing, packaged installation, release notes, and a documented support window.
