# Game UI Framework (GUIF)

**English** | [简体中文](README.zh-CN.md)

> **Build governed AI production systems, not just prompts.**

GUIF is a local-first workflow and governance framework for AI production. Its first and currently implemented production domain is **game UI**, while its workflow model—production tasks, approvals, artifacts, capability routing, candidate experiments, adoption, regression, and recovery—is designed to support broader AI production systems.

ChatGPT / Codex is the default **Host**. `chatgpt-image` is the default image generation and editing **Tool**, and `chatgpt-vision` is the default semantic visual inspector. These are replaceable contracts rather than hard-coded GUIF Core dependencies.

## Status

`v1.0.0-beta.3` adds the Candidate Change and Tool Trial workflow to the production loop.

- Python 3.10, 3.11, and 3.12 pass the complete CI pipeline.
- CI includes build, hash provenance, wheel installation, and CLI contract checks.
- 177 tests pass.
- Production Tasks and framework Improvement Cases are separate objects.
- A trial approval does not authorize adoption, merge, release, or stable Tool-route replacement.
- A candidate cannot be adopted without a real candidate artifact and real semantic visual evidence.

The Codex plugin version is `1.0.0-beta.3`. The Python package remains `1.0.0b2`; public API compatibility is governed by the project's compatibility contract.

Important documents:

- [Living product specification](docs/GUIF_PRODUCT_SPEC.md)
- [Support policy](SUPPORT.md)
- [Privacy migration guidance](docs/PRIVACY_MIGRATION.md)

## What GUIF is

GUIF coordinates two connected but isolated loops.

### 1. AI production loop

```text
Theme / production context
  -> natural-language request
  -> production plan
  -> contextual approval
  -> real generation or editing
  -> deterministic metadata review
  -> semantic visual review
  -> independently approved revision when needed
  -> gated export
```

### 2. Continuous-improvement loop

```text
problem found during production
  -> save checkpoint and pause Production Task
  -> create private Improvement Case
  -> diagnose the real cause
  -> propose candidate changes
  -> user approves an isolated trial
  -> build or run the candidate
  -> generate a real candidate result
  -> user reviews stable vs candidate evidence
  -> user adopts, adjusts, or rejects the candidate
  -> publish code or apply a scoped Tool route
  -> refresh the Host plugin
  -> run formal regression
  -> resume the original Production Task
```

The production task never becomes a code-development task. Improvement cases, candidate evidence, and development handoff packages remain in private storage and do not enter Project Git by default.

## Design principles

### Production and evolution are isolated

Stable production state is preserved while a candidate is investigated and tested independently.

### Trial approval and adoption approval are different

Trial approval allows an isolated experiment. It does not allow GUIF to merge code, publish a plugin, overwrite a stable Skill, or change a stable Tool route.

### Real evidence is required

A dry run, fabricated image, simulated semantic finding, or planned Tool call cannot be treated as a successful production result. Formal adoption requires a real candidate artifact and real semantic visual review.

### Diagnosis precedes classification

A repeated visual defect is not automatically classified as a Skill defect. GUIF can inspect Skill constraints, Prompt IR, edit scope, Theme rules, cumulative edit damage, review coverage, and Tool behavior before proposing a candidate.

### Capabilities are routed, not brands

A Tool replaces only the matching capability. For example, Figma may provide editable structured layout without replacing illustration generation, pixel-level editing, semantic review, or Unity export.

### Adoption is scoped

A Tool candidate may be adopted for:

- the current Task;
- the current Project;
- the entire Workspace.

Stable Project and Workspace routes remain unchanged during an isolated trial.

## Architecture

```text
User
  |
  v
Host: ChatGPT / Codex
  - understands intent
  - drives GUIF workflows
  - invokes image and vision Tools
  - edits candidate code or Skills
  - runs tests, Git, CI, and release operations
  |
  v
GUIF Core
  - Production Task
  - Conversation Workflow
  - Approval gates
  - Artifact and lineage records
  - Improvement Case
  - Candidate Change
  - Tool Trial
  - regression, checkpoint, and recovery
  |
  v
Tools / Adapters
  - GPT Image generation and editing
  - semantic visual inspection
  - structured-layout Tools
  - engine export adapters
  - other capability-specific integrations
```

The Host is the active operator. GUIF Core is the workflow and governance authority. Tools provide concrete capabilities.

## Simulated usage example: game UI production and GUIF improvement

The following conversation illustrates the intended user experience. It is a simulation of the workflow, not a claim that every external Tool shown is already integrated.

### Start production

**User**

> Use GUIF to create a 1920x1080 sci-fi inventory screen with the current Project Theme. Submit the plan first and do not generate before approval.

**GUIF Host**

> Production Task created. Theme confirmed. The plan includes a character equipment area, item grid, detail panel, and Unity export. Waiting for production approval.

**User**

> Approve production.

**GUIF Host**

> GPT Image generated a real candidate. Metadata review passed. Semantic visual review found that the layout is usable, but the edited detail panel contains visible noise.

### Enter Candidate Change

**User**

> This edit introduced obvious noise again. Treat it as a GUIF problem and enter the Candidate Change workflow.

**GUIF Host**

> The Production Task is paused and a checkpoint is saved. A private Improvement Case has been created.
>
> The diagnosis will compare:
> - editing constraints in the Skill;
> - Prompt IR and edit scope;
> - Theme cleanliness requirements;
> - cumulative damage from repeated edits;
> - semantic-review coverage;
> - the current image Tool's behavior.

**GUIF Host**

> Candidate A narrows the editable region and adds an explicit clean-surface constraint. Candidate B keeps the stable Skill and tests a different editing route. Approving a trial will not modify the stable Skill or Tool route.

**User**

> Approve Candidate A trial.

### Review real candidate evidence

**GUIF Host**

> Candidate A was executed in isolation. A real image was produced and semantic visual review completed.
>
> Stable result: visible grain in the detail panel.
>
> Candidate A: cleaner panel, preserved typography, no new blocking findings.
>
> Choose: formally adopt, continue adjusting the candidate, or reject and keep the stable version.

**User**

> Formally adopt Candidate A.

**GUIF Host**

> Adoption approved. The candidate change may now enter the development and release path. CI passed, the plugin was refreshed, formal regression passed, and the original Production Task has resumed from its checkpoint.

### Try a different Tool

**User**

> The current Tool is not suitable for structured UI layout. Try Figma for layout only, scoped to this Project.

**GUIF Host**

> GUIF will first verify registration, availability, Host support, permissions, external data flow, pricing, and credentials.
>
> If Figma is available, GUIF will create an isolated candidate Task that uses Figma only for structured layout. If it is not integrated, GUIF will create a `tool-integration-change` candidate instead of pretending the call succeeded.

This example demonstrates the central GUIF rule: **a production system changes only after an isolated candidate produces real evidence and the user explicitly adopts it.**

## Installation

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
pip install -e .[dev]
```

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

## Conversation-first production

A new Conversation begins at `theme-confirmation`. Supported Theme paths include:

```text
theme-list       list private historical choices
theme-select     select an existing private Theme
theme-create     create and bind a new private Theme
theme-derive     create an immutable new Theme version
theme-unbound    explicitly continue without a Theme
```

Submit a natural-language request:

```bash
guif-conversation submit \
  --project SampleGame \
  --conversation conversation-001 \
  --request-key chat-turn-001 \
  "Create a fictional 1080x2340 observatory shop page and export Unity"
```

Approve the current initial or Revision gate:

```bash
guif-conversation approve \
  --project SampleGame \
  --conversation conversation-001
```

The normal user view hides low-level Approval IDs, Task IDs, etags, leases, claims, Handoff IDs, and Callback IDs while GUIF continues to enforce them beneath the facade.

## Real image and semantic visual loop

The configured Host supplies actual image and visual capabilities:

```python
view = conversation.run_host_until_blocked(
    "SampleGame",
    "conversation-001",
    image_executor=call_chatgpt_image_tool,
    visual_inspector=call_chatgpt_visual_inspection,
)
```

The local Python package does not fabricate pixels and cannot enter ChatGPT's internal Tool runtime by itself. ChatGPT / Codex or another configured Host must embed the Host loop or consume the authenticated Gateway work API.

Metadata review validates deterministic properties. It never claims that Theme consistency, composition, readability, noise, or usability passed; those conclusions require an authenticated semantic visual result.

## Controlled revision

Actionable visual findings produce a versioned Revision Job and a separate approval gate. Initial generation approval never authorizes editing. The source Artifact remains active until its replacement is real, non-simulated, lineage-valid, and semantically reviewed as passed.

## Tool Trial and integration changes

A Tool Trial checks:

- Tool registration, availability, and health;
- Host compatibility;
- permissions and data scope;
- external calls and pricing;
- credential requirements;
- capability match;
- adoption scope and rollback.

An unavailable or unknown Tool becomes a `tool-integration-change` candidate requiring an Adapter, permission declaration, health check, result-return contract, and contract tests. GUIF never converts an unavailable Tool into a fictional successful execution.

## Release artifact provenance

Build release artifacts:

```bash
python -m build
```

Generate and verify the SHA-256 provenance manifest:

```bash
guif-ready provenance \
  --workspace . \
  --dist dist \
  --git-commit <40-or-64-character-hex-commit>

guif-ready provenance \
  --workspace . \
  --dist dist \
  --git-commit <same-commit> \
  --verify
```

`dist/SHA256SUMS.json` binds package metadata and artifact hashes to the Git commit. This is hash-only provenance; it is not a cryptographic signature or trusted-builder attestation.

## Verified private backup

```bash
guif-ready backup --workspace .
guif-ready backup-verify /path/to/portable.guif-private.zip
guif-ready backup-restore /path/to/portable.guif-private.zip
```

Default destination:

```text
<private-data-root>/backups/portable-<timestamp>.guif-private.zip
```

Restore is plan-first. Sensitive local material requires an explicit `full-local` decision. Unprotected archives provide integrity verification but are not encrypted at rest.

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
  improvement-cases/
  candidate-evidence/
  development-handoffs/
  backups/
  diagnostics/
  upgrade-reports/
  hardening-reports/
  runs/
  plans/
  migrations/
  privacy-reports/
```

Real Themes, prompts, decisions, approvals, runtime state, images, semantic findings, credentials, improvement cases, candidate evidence, backups, and reports remain outside framework and Project Git by default.

## Development

```bash
pytest -q -W error::DeprecationWarning:PIL
python -m build
guif-ready provenance --dist dist --git-commit <commit>
guif-ready provenance --dist dist --git-commit <commit> --verify
```

## Current boundaries

- GUIF currently implements game UI as its primary production domain; broader AI production domains require domain contracts, Tools, review criteria, and export adapters.
- ChatGPT / Codex integration must embed the Host loop or consume the Gateway work API; the Python package cannot invoke product-internal Tools by itself.
- File-backed Work claims and Task leases provide single-node coordination, not distributed consensus.
- Hash provenance does not replace release signing or trusted build attestation.
- GUIF can verify external backup-protection evidence but cannot assess cryptographic strength or recover lost keys.
- The built-in WSGI Gateway is not an internet-edge reverse proxy.
