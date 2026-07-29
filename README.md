# Game UI Framework (GUIF)

**English** | [简体中文](README.zh-CN.md)

GUIF is a local-first game UI production framework with configurable Hosts and Tools. ChatGPT is the default Host, `chatgpt-image` is the default image generation/editing Tool, and `chatgpt-vision` is the default semantic visual inspector. All remain replaceable contracts rather than hard-coded Core dependencies.

## Status

`v1.0.0-beta.2` is a maintenance and provenance hardening release for the frozen conversation MVP:

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
  -> non-mutating soak profiles
  -> verifiable wheel / sdist hash provenance
```

Beta.2 preserves public API version `1` and every conversation-facing stage/action frozen in alpha.28. The Python package version is `1.0.0b2`.

Important documents:

- [Living product specification](docs/GUIF_PRODUCT_SPEC.md)
- [Beta.2 release notes](docs/RELEASE_NOTES_BETA2.md)
- [Beta.2 security review](docs/SECURITY_REVIEW_BETA2.md)
- [Beta.1 release notes](docs/RELEASE_NOTES_BETA1.md)
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

CI runs tests on Python 3.10, 3.11, and 3.12, treats Pillow deprecation warnings as errors, builds a wheel and source distribution, generates and verifies hash provenance, installs the generated wheel, verifies `guif.__version__`, and runs a CLI contract smoke test.

## Release artifact provenance

Build both release formats:

```bash
python -m build
```

Generate a machine-readable SHA-256 manifest bound to the Git commit and package metadata:

```bash
guif-ready provenance \
  --workspace . \
  --dist dist \
  --git-commit <40-or-64-character-hex-commit>
```

Verify it independently:

```bash
guif-ready provenance \
  --workspace . \
  --dist dist \
  --git-commit <same-commit> \
  --verify
```

`dist/SHA256SUMS.json` records:

```text
package name and version
Git commit
Python implementation/version and build platform
wheel and sdist filenames, sizes, and SHA-256 hashes
wheel METADATA and sdist PKG-INFO name/version agreement
```

This is **hash-only provenance**. GUIF does not claim a cryptographic signature, trusted builder attestation, or third-party supply-chain certification when no such system was used.

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

A new Conversation begins at `theme-confirmation`. Supported Theme paths are:

```text
theme-list       list private historical choices
theme-select     select an existing private Theme
theme-create     create and bind a new private Theme
theme-derive     create an immutable new Theme version
theme-unbound    explicitly continue without a Theme
```

Real user Theme content remains in the private Theme Library outside framework and Project Git. Public examples and tests use only wholly fictional fixtures.

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

GUIF coordinates Task-scoped Host Work discovery, Task etags, exclusive leases, Actor-bound one-time claims, immutable Attachment retrieval, real result submission, Artifact registration, deterministic metadata review, authenticated semantic review, and the next user-facing stage.

The local Python package does not fabricate pixels and cannot enter ChatGPT's internal tool runtime by itself. ChatGPT or another configured Host must embed `ChatGPTHostLoop` or consume the authenticated Gateway work API. Metadata review never claims Theme consistency, composition, readability, or usability passed; those conclusions require an authenticated semantic visual result.

## Controlled Revision

Actionable visual findings produce a versioned Revision Job and a separate approval gate. Initial generation Approval never authorizes editing. The source Artifact remains active until the replacement is real, non-simulation, lineage-valid, and semantically reviewed as passed.

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

Verify or plan a restore:

```bash
guif-ready backup-verify /path/to/portable.guif-private.zip
guif-ready backup-restore /path/to/portable.guif-private.zip
```

Restore is plan-first. Applying `--conflict replace --apply` creates a portable pre-restore backup, materializes each file atomically, and verifies SHA-256 after writing.

## External backup protection boundary

GUIF does not implement custom cryptography or bundle a specific encryption program. It coordinates an explicitly configured external program through an argv array with `shell=False`.

```bash
export GUIF_BACKUP_PROTECTOR_ID='local-encryption-tool'
export GUIF_BACKUP_PROTECT_COMMAND_JSON='["/path/to/protect-tool","encrypt","--input","{input}","--output","{output}"]'
export GUIF_BACKUP_UNPROTECT_COMMAND_JSON='["/path/to/protect-tool","decrypt","--input","{input}","--output","{output}"]'
export GUIF_BACKUP_PROTECT_TIMEOUT_SECONDS='300'
```

The external program should obtain keys/passphrases through its own protected mechanism. Do not put secrets directly in the JSON argv configuration.

```bash
guif-ready backup-protect \
  /path/to/portable.guif-private.zip \
  /protected/location/portable.guif-private.zip.protected

guif-ready backup-protection-verify \
  /protected/location/portable.guif-private.zip.protected
guif-ready backup-unprotect \
  /protected/location/portable.guif-private.zip.protected \
  /recovery/location/portable.guif-private.zip
```

The boundary uses no shell, requires explicit configuration, has no unprotected fallback, enforces bounded execution, refuses destination/receipt overwrite, publishes through temporary files, binds original/protected size and SHA-256, and persists no command argv or secret environment value. Cryptographic strength, key custody, rotation, and disaster recovery remain the external program/operator's responsibility.

## Supported alpha upgrade assurance

Plan an upgrade from alpha.27 or alpha.28 to the current beta implementation:

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

Unknown source releases, unknown future schemas, invalid JSON, and raw secret-like fields fail closed. Full migration evidence stays in private upgrade/migration reports; public results do not return private paths.

## Fault injection

Fault injection is test/development-only and disabled by default. Environment activation requires both:

```bash
export GUIF_FAULT_POINTS='backup-protection.before-publish'
export GUIF_ALLOW_FAULT_INJECTION='1'
```

A fault-point variable without the explicit allow flag raises an error. Production environments should leave both variables unset.

## Extended non-mutating soak profiles

Profiles select bounded iteration counts:

```text
quick       10
standard    100
extended    1000
```

Run a profile and optionally write an independent machine-readable report:

```bash
guif-ready soak \
  --workspace . \
  --project SampleGame \
  --conversation conversation-001 \
  --profile standard \
  --max-p95-ms 1000 \
  --report reports/soak.json \
  --no-persist
```

`--iterations` remains an explicit custom override. Optional `--backup` adds repeated archive verification. Reports include total/mean/p50/p95/max timing, sanitized errors, observed public stages, threshold status, `production_state_mutated=false`, and a failure classification. A performance threshold miss is host/environment evidence requiring investigation; it is not by itself proof of a GUIF product correctness failure.

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

The compatibility contract keeps:

```text
release: 1.0.0-alpha.28
origin_release: 1.0.0-alpha.28
current_release: 1.0.0-beta.2
channel: beta
public_api_version: 1
```

`release` and `origin_release` identify the alpha.28 freeze origin. Breaking product-facing changes require a new public API version and an explicit migration path. The explicit legacy `ProviderAdapter` path remains available. Production Tool routing remains ChatGPT-first and configurable; `dry-run` remains test/development-only and is never a silent production fallback.

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
pytest -q -W error::DeprecationWarning:PIL
python -m build
guif-ready provenance --dist dist --git-commit <commit>
guif-ready provenance --dist dist --git-commit <commit> --verify
```

## Current limitations

- ChatGPT product integration must embed `ChatGPTHostLoop` or consume the Gateway work API; this repository cannot invoke ChatGPT internal image tools by itself.
- GUIF verifies external protection evidence but cannot assess cryptographic strength or recover lost keys.
- Hash provenance does not replace a real signing or trusted build-attestation system.
- File-backed Work claims and Task leases are single-node coordination, not distributed consensus.
- The built-in WSGI Gateway is not an internet-edge reverse proxy.
- Remote private-data synchronization, retention automation, and multi-device conflict resolution are not implemented.
- Current-tree privacy audit cannot prove removal from Git history, forks, caches, or external clones.
