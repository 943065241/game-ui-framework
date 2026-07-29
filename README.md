# Game UI Framework (GUIF)

**English** | [简体中文](README.zh-CN.md)

GUIF is a local-first game UI production framework with configurable Hosts and Tools. ChatGPT is the default Host, `chatgpt-image` is the default image generation/editing Tool, and `chatgpt-vision` is the default semantic visual inspector. All remain replaceable contracts rather than hard-coded Core dependencies.

## Status

`v1.0.0-beta.1` hardens the frozen conversation MVP without expanding the normal user workflow:

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
  -> verified private backup / restore
  -> optional external backup protection
  -> recorded alpha-to-beta upgrade assurance
```

Beta.1 preserves public API version `1` and the conversation-facing stages/actions frozen in alpha.28. The package version is `1.0.0b1`.

Important documents:

- [Living product specification](docs/GUIF_PRODUCT_SPEC.md)
- [Beta.1 release notes](docs/RELEASE_NOTES_BETA1.md)
- [Beta.1 security review](docs/SECURITY_REVIEW_BETA1.md)
- [Support policy](SUPPORT.md)
- [Privacy migration guidance](docs/PRIVACY_MIGRATION.md)

## Installation

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
pip install -e .[dev]
```

CI builds a wheel and source distribution, installs the generated wheel, verifies `guif.__version__`, and runs a CLI contract smoke test on Python 3.10, 3.11, and 3.12.

## One-command bootstrap

Initialize a Project, create or validate a ChatGPT Host credential, and open a private Conversation:

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

The token is not written into Project Git, Conversation records, backup manifests, diagnostics, or public output.

## Conversation-first workflow

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

Real user Theme content remains in the private Theme Library outside framework and Project Git. Public examples use only wholly fictional fixtures.

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

The normal view exposes only the Conversation/Project, public stage, message, private Theme summary, contextual actions, safe Artifact summaries, and recovery availability. Low-level identities remain enforced beneath the facade.

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

The local Python package does not fabricate pixels and cannot enter ChatGPT's internal tool runtime by itself. ChatGPT or another configured Host must embed `ChatGPTHostLoop` or consume the authenticated Gateway work API.

Metadata review never claims Theme consistency, composition, readability, or usability passed. Those conclusions require an authenticated semantic visual result.

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

Default destination:

```text
<private-data-root>/backups/portable-<timestamp>.guif-private.zip
```

The portable profile includes recoverable user-owned production data such as Themes, Conversation bindings/records, runs, plans, Host Work, migrations, and privacy reports. It deliberately excludes Host credential verifiers, operation-ledger signing keys, Gateway request receipts, and operation-audit authentication material.

A `full-local` archive requires an explicit sensitive-material decision:

```bash
guif-ready backup \
  --workspace . \
  --profile full-local \
  --include-sensitive \
  --output /protected/offline/location/full-local.guif-private.zip
```

Unprotected GUIF archives provide integrity verification but are not encrypted at rest.

### Backup verification

```bash
guif-ready backup-verify /path/to/portable.guif-private.zip
```

Verification checks manifest schema/hash, canonical member paths, path traversal, duplicate/unmanifested members, symbolic links, per-file size/SHA-256, and total extraction limits.

### Plan-first restore

A restore is dry-run by default:

```bash
guif-ready backup-restore /path/to/portable.guif-private.zip
```

Conflict policies:

```text
fail      block on any different existing file
skip      keep existing conflicting files
replace   create a portable pre-restore backup, then replace conflicts
```

Apply explicitly:

```bash
guif-ready backup-restore \
  /path/to/portable.guif-private.zip \
  --conflict replace \
  --apply
```

Restore writes each file atomically and verifies its SHA-256 after materialization.

## External backup protection boundary

GUIF does not implement custom cryptography or bundle a specific encryption program. It can coordinate an explicitly configured external program using an argv array with `shell=False`.

Configure the external adapter through environment variables. The command values must be JSON arrays and must include `{input}` and `{output}` placeholders:

```bash
export GUIF_BACKUP_PROTECTOR_ID='local-encryption-tool'
export GUIF_BACKUP_PROTECT_COMMAND_JSON='["/path/to/protect-tool","encrypt","--input","{input}","--output","{output}"]'
export GUIF_BACKUP_UNPROTECT_COMMAND_JSON='["/path/to/protect-tool","decrypt","--input","{input}","--output","{output}"]'
export GUIF_BACKUP_PROTECT_TIMEOUT_SECONDS='300'
```

The external program should obtain keys/passphrases through its own protected mechanism. Do not put secrets directly in the JSON argv configuration.

Protect a verified archive:

```bash
guif-ready backup-protect \
  /path/to/portable.guif-private.zip \
  /protected/location/portable.guif-private.zip.protected
```

Verify the protected file and secret-free receipt:

```bash
guif-ready backup-protection-verify \
  /protected/location/portable.guif-private.zip.protected
```

Recover the original GUIF archive and verify it:

```bash
guif-ready backup-unprotect \
  /protected/location/portable.guif-private.zip.protected \
  /recovery/location/portable.guif-private.zip
```

The protection boundary:

```text
uses no shell
requires explicit configuration
has no unprotected fallback
uses bounded execution time
refuses destination/receipt overwrite
publishes through temporary files
binds original/protected size and SHA-256
persists no command argv or secret environment value
```

Cryptographic strength, key custody, rotation, and disaster recovery remain the external program/operator's responsibility.

## Supported alpha upgrade assurance

Plan an upgrade from alpha.27 or alpha.28:

```bash
guif-ready upgrade \
  --workspace . \
  --source-release 1.0.0-alpha.28
```

The default plan requires a portable backup and checks private schema compatibility. Apply only after review:

```bash
guif-ready upgrade \
  --workspace . \
  --source-release 1.0.0-alpha.28 \
  --apply \
  --actor local-owner
```

Unknown source releases, blocked private schemas, and raw secret-like fields fail closed. Applied repairs and upgrade evidence are stored privately under `upgrade-reports/` and `migrations/`.

## Fault injection

Fault injection is test/development-only and disabled by default. Environment activation requires both:

```bash
export GUIF_FAULT_POINTS='backup-protection.before-publish'
export GUIF_ALLOW_FAULT_INJECTION='1'
```

A fault-point variable without the explicit allow flag raises an error. Production environments should leave both variables unset.

## Bounded soak checks

Run repeatability and latency checks over non-mutating production reads:

```bash
guif-ready soak \
  --workspace . \
  --project SampleGame \
  --conversation conversation-001 \
  --iterations 100 \
  --max-p95-ms 1000
```

Optional `--backup` adds repeated archive verification. Reports include counts, sanitized errors, total/mean/p50/p95/max timing, observed public stages, and threshold status. Reports stay private under `hardening-reports/`.

## Diagnostics and acceptance

```bash
guif-ready diagnose \
  --workspace . \
  --project SampleGame \
  --conversation conversation-001

guif-ready acceptance \
  --workspace . \
  --project SampleGame \
  --conversation conversation-001
```

The acceptance gate passes only when no blocking readiness check exists and the Conversation is `ready-to-export` or `completed`. `--require-completed` requires final Gated Export to have succeeded.

## Compatibility and support

```bash
guif-ready contract
guif-ready support
```

The existing compatibility field remains:

```text
release: 1.0.0-alpha.28
```

because it identifies the origin of the frozen contract. Beta.1 adds:

```text
current_release: 1.0.0-beta.1
channel: beta
```

Public API version remains `1`. Breaking product-facing changes require a new public API version and an explicit migration path. See [SUPPORT.md](SUPPORT.md).

The explicit legacy `ProviderAdapter` path remains available. Production Tool routing remains ChatGPT-first and configurable; `dry-run` remains test/development-only and is never a silent production fallback.

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
  upgrade-reports/
  hardening-reports/
  runs/
  plans/
  migrations/
  privacy-reports/
```

Real Themes, prompts, Conversation decisions, approval evidence, Runtime state, Work claims, Attachments, image files, semantic findings, credentials, backup/protected archives, and reports remain outside framework and Project Git by default.

## Development

```bash
pytest -q
python -m build
```

## Current limitations

- ChatGPT product integration must embed `ChatGPTHostLoop` or consume the Gateway work API; this repository cannot invoke ChatGPT internal image tools by itself.
- GUIF verifies external protection evidence but cannot assess cryptographic strength or recover lost keys.
- File-backed Work claims and Task leases are single-node coordination, not distributed consensus.
- The built-in WSGI Gateway is not an internet-edge reverse proxy.
- Remote private-data synchronization, retention automation, and multi-device conflict resolution are not implemented.
- Current-tree privacy audit cannot prove removal from Git history, forks, caches, or external clones.
- Existing Pillow `Image.getdata()` deprecation warnings remain.
