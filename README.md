# Game UI Framework (GUIF)

**English** | [简体中文](README.zh-CN.md)

GUIF is a local-first game UI production framework with configurable Hosts and Tools. ChatGPT is the default Host and `chatgpt-image` is the default image generation and editing Tool, but neither is a hard-coded Core dependency.

## Status

`v1.0.0-alpha.24` adds authenticated Host operations, optimistic Task concurrency, exclusive Task leases, stable external result callbacks, and Task-bound Git Change Sets.

```text
private Theme selection
  -> Prompt / Approval / Tool handoff
  -> authenticated Host actor
  -> optimistic Task etag
  -> exclusive expiring Task lease
  -> authenticated result callback
  -> Artifact / Review / Revision / Gated Export
  -> reviewable Git Change Set
  -> dedicated branch + commit
  -> optional revert commit
```

The bilingual living product specification is maintained at [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md). Privacy migration and repository-history guidance are in [`docs/PRIVACY_MIGRATION.md`](docs/PRIVACY_MIGRATION.md).

## Authenticated Host actors

Host credentials are private local records stored outside framework and Project Git. Registration returns a bearer token exactly once. GUIF persists only a PBKDF2-HMAC-SHA256 verifier, not the original secret.

```python
from pathlib import Path
from guif.runtime import Runtime

runtime = Runtime(Path.cwd())
issued = runtime.register_host_credential(
    actor_id="production-host",
    host_id="chatgpt",
    capabilities=(
        "task:lease",
        "approval:decide",
        "tool-result:submit",
        "export:execute",
        "export:rollback",
        "git:prepare",
        "git:commit",
        "git:revert",
    ),
    roles=("operator",),
    created_by="local-admin",
)

bearer_token = issued["bearer_token"]  # visible once
```

Credential metadata records the actor, Host, roles, capabilities, issuer, lifecycle, and optional expiration. Credentials can be listed, revoked, or rotated without exposing secret verifiers.

An authenticated operation stores a normalized actor snapshot:

```json
{
  "actor_id": "production-host",
  "host_id": "chatgpt",
  "credential_id": "cred-...",
  "capabilities": ["task:lease", "tool-result:submit"],
  "authenticated": true
}
```

## Optimistic Task concurrency

Every persisted Task has a deterministic etag:

```python
etag = runtime.get_task_etag("SampleGame", task_id)
```

A write operation rejects a stale etag rather than silently overwriting a newer Task state.

For exclusive operations, acquire an expiring lease:

```python
lease = runtime.acquire_task_lease(
    "SampleGame",
    task_id,
    bearer_token=bearer_token,
    expected_task_etag=etag,
    ttl_seconds=300,
    purpose="host-result-callback",
)

lease_token = lease["lease_token"]  # visible once
```

The lease binds:

- Project and Task identity;
- authenticated actor and credential;
- base Task etag;
- purpose;
- acquisition and expiration times;
- consumed, released, or expired lifecycle.

A second active lease is rejected. Mutating operations consume the lease after success. Stale Task state, expired leases, wrong actors, wrong credentials, and tampered lease tokens fail closed.

## Stable authenticated Host callback

The legacy `submit_tool_result()` API remains available for compatibility. Production Host integration should use `submit_authenticated_tool_result()`.

```python
content = Path("generated-screen.png").read_bytes()

task = runtime.submit_authenticated_tool_result(
    "SampleGame",
    task_id,
    handoff_id,
    bearer_token=bearer_token,
    lease_token=lease_token,
    expected_task_etag=etag,
    content=content,
    filename="generated-screen.png",
    mime_type="image/png",
    width=1080,
    height=2340,
    model_id="image-model",
)
```

The callback validates:

- Host credential and `tool-result:submit` capability;
- Host identity against the persisted handoff;
- Tool and execution identity;
- active lease ownership;
- expected Task etag;
- submitted content SHA-256;
- handoff status and idempotent callback identity.

Completed callback records are persisted as `host-callbacks.json` and link actor, lease, envelope, execution, handoff, content hash, and resulting Artifact.

## Authenticated Approval and Export

Approval and production writes can use the same identity and lease boundary:

```python
task = runtime.decide_approval_authenticated(
    "SampleGame",
    task_id,
    approval_id,
    "approved",
    bearer_token=bearer_token,
    lease_token=lease_token,
    expected_task_etag=etag,
    comment="Reviewed against the approved contract.",
)
```

```python
record = runtime.execute_gated_export_authenticated(
    "SampleGame",
    task_id,
    bearer_token=bearer_token,
    lease_token=lease_token,
    expected_task_etag=etag,
    target_engine="unity",
)
```

Authenticated actor and lease evidence are attached to Approval and Export records. Existing string-actor APIs remain compatibility paths and do not provide the alpha.24 authentication guarantee.

## Task-bound Git Change Sets

A completed Gated Export can be converted into a reviewable Git Change Set. Preparation does not create a branch or commit.

```python
change = runtime.prepare_export_git_change(
    "SampleGame",
    task_id,
    export_id,
    bearer_token=bearer_token,
    expected_task_etag=etag,
    branch_name="guif/sample-game/export-001",
)

diff = runtime.diff_git_change(
    "SampleGame",
    task_id,
    change["change_set_id"],
)
```

The plan records:

- repository and Project roots;
- source Task and completed Export;
- Export transaction SHA-256;
- base Git HEAD and branch;
- selected Project truth, Engine output, and transaction paths;
- proposed branch and commit message;
- working-tree status.

After review, acquire a fresh lease and execute:

```python
committed = runtime.execute_git_change(
    "SampleGame",
    task_id,
    change["change_set_id"],
    bearer_token=bearer_token,
    lease_token=lease_token,
    expected_task_etag=etag,
)
```

GUIF verifies that Git HEAD still matches the plan, creates a dedicated branch, stages only selected paths, commits them, records the staged diff hash, and links the commit back to the Gated Export.

A committed Change Set can produce a normal Git revert commit:

```python
reverted = runtime.revert_git_change(
    "SampleGame",
    task_id,
    change["change_set_id"],
    bearer_token=bearer_token,
    lease_token=lease_token,
    expected_task_etag=etag,
    reason="Restore the previous approved Project state.",
)
```

Revert fails closed when selected paths contain newer uncommitted changes.

## Operational CLI

Alpha.24 adds a separate `guif-ops` entry point so bearer and lease tokens can remain in environment variables instead of command history.

```bash
pip install -e .[dev]

guif-ops credential-create production-host chatgpt \
  task:lease tool-result:submit approval:decide \
  export:execute git:prepare git:commit git:revert

export GUIF_HOST_TOKEN='guifh1....'

guif-ops task-etag <task-id> --project SampleGame

guif-ops lease-acquire <task-id> \
  --project SampleGame \
  --expected-etag 'task-sha256:...'

export GUIF_TASK_LEASE='guifl1....'

guif-ops callback-submit <task-id> <handoff-id> generated.png \
  --project SampleGame \
  --expected-etag 'task-sha256:...'
```

Other commands include:

```text
credential-list / credential-revoke / credential-rotate
lease-show / lease-renew / lease-release
callback-list / callback-show
approval-decide
export-execute / export-rollback
git-plan / git-list / git-show / git-diff / git-commit / git-revert
summary
```

## Private data layout

```text
<private-data-root>/
  themes/
  conversation-theme-bindings/
  project-theme-bindings/
  host-credentials/
  runs/<project>/<task-id>/
    task.json
    task-lease.json
    host-callbacks.json
    git-changes.json
  plans/
  migrations/
  privacy-reports/
```

Full Theme content, Host credential verifiers, Task leases, callback evidence, natural-language Plans, and Runtime evidence remain outside framework and Project Git by default.

## Existing production flow

GUIF continues to provide:

- private versioned Theme Library and conversation-first Theme selection;
- Workflow-driven Planner, Director, Theme, Resource, Prompt, and Semantic QA Agents;
- configurable Host and Tool routing with ChatGPT defaults;
- Artifact identity, immutable References, SHA-256, MIME, and dimensions;
- deterministic metadata review and optional semantic Visual Inspectors;
- controlled Revision execution and review-gated supersession;
- Gated Export, Engine manifests, transaction audit, backups, and rollback;
- current-tree privacy audit and legacy Theme migration.

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

- Host credentials are local bearer credentials; OIDC, mTLS, hardware-backed keys, and remote identity providers are not implemented.
- Task leases are logical private-store leases, not operating-system or distributed locks. Legacy unauthenticated APIs can bypass them.
- Git Change Sets require a local Git executable, a named current branch, and configured Git author identity.
- Git execution creates local branches and commits; remote push, pull requests, protected-branch negotiation, and server-side checks are not automated.
- Callback content is submitted through the local Runtime API or CLI; a network callback server is not included.
- Private storage remains file-backed and does not provide encryption-at-rest, remote synchronization, or retention policy.
- The default semantic Visual Inspector Registry is empty.
- Current-tree privacy audit cannot prove removal from Git history, forks, caches, or external clones.

## Next phase

The next priority is **alpha.25: Production Host Gateway and Signed Operation Ledger**: network callback transport, OIDC or pluggable identity verification, cross-process locking, signed callback and Export receipts, remote Git push/PR integration, protected-branch checks, and durable operation recovery.
