# Game UI Framework (GUIF)

**English** | [简体中文](README.zh-CN.md)

GUIF is a local-first game UI production framework with configurable Hosts and Tools. ChatGPT is the default Host and `chatgpt-image` is the default image generation and editing Tool, but neither is a hard-coded Core dependency.

## Status

`v1.0.0-alpha.25` adds a runnable authenticated Production Host Gateway and a private signed Operation Ledger.

```text
private Theme selection
  -> Prompt / Approval / Tool handoff
  -> authenticated Host actor
  -> Task etag + exclusive lease
  -> Production Host Gateway
  -> image result callback
  -> Artifact / Review / Revision
  -> Gated Export
  -> Git Change Set / Commit / Revert
  -> signed private Operation Ledger
```

The bilingual living product specification is maintained at [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md). Privacy migration and repository-history guidance are in [`docs/PRIVACY_MIGRATION.md`](docs/PRIVACY_MIGRATION.md).

## Production Host Gateway

Run the local Gateway:

```bash
pip install -e .[dev]
guif-gateway --workspace . --host 127.0.0.1 --port 8765
```

The default bind is loopback-only. A non-loopback bind requires both explicit `--allow-remote` and TLS certificate/key files:

```bash
guif-gateway \
  --host 0.0.0.0 \
  --port 8765 \
  --allow-remote \
  --tls-cert server.crt \
  --tls-key server.key
```

The built-in server is a small single-node Host boundary, not an internet-edge reverse proxy. Production deployments should still place policy-appropriate networking, certificate rotation, rate limiting, and process supervision around it.

### Gateway endpoints

```text
GET  /health
GET  /v1/descriptor
GET  /v1/tasks/{project}/{task_id}/summary
POST /v1/tasks/{project}/{task_id}/lease
POST /v1/tasks/{project}/{task_id}/approvals/{approval_id}
POST /v1/tasks/{project}/{task_id}/callbacks/{handoff_id}
POST /v1/tasks/{project}/{task_id}/exports
GET  /v1/ledger/verify
GET  /v1/ledger/entries?limit=100
```

All `/v1` endpoints require a GUIF bearer credential with the relevant capability. Mutating requests require an `Idempotency-Key`; exclusive mutations also require a Task etag and lease token.

### Create a Gateway credential

```python
from pathlib import Path
from guif.runtime import Runtime

runtime = Runtime(Path.cwd())
issued = runtime.register_host_credential(
    actor_id="production-host",
    host_id="chatgpt",
    capabilities=(
        "gateway:read",
        "task:read",
        "ledger:read",
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

bearer_token = issued["bearer_token"]  # shown once
```

GUIF persists a PBKDF2-HMAC-SHA256 verifier, never the original bearer secret.

### Acquire a Task lease over HTTP

```http
POST /v1/tasks/SampleGame/task-123/lease
Authorization: Bearer guifh1....
Content-Type: application/json
Idempotency-Key: lease-2026-001

{
  "expected_task_etag": "task-sha256:...",
  "ttl_seconds": 300,
  "purpose": "host-result-callback"
}
```

The lease token is returned once and is not stored in Gateway idempotency receipts. Replaying the same lease request cannot reveal the token again.

### Submit a generated or edited image

The callback body is the raw image file, avoiding base64 expansion:

```http
POST /v1/tasks/SampleGame/task-123/callbacks/handoff-456
Authorization: Bearer guifh1....
Idempotency-Key: result-2026-001
If-Match: "task-sha256:..."
X-GUIF-Lease-Token: guifl1....
X-GUIF-Filename: generated-screen.png
X-GUIF-Content-SHA256: <sha256>
X-GUIF-Width: 1080
X-GUIF-Height: 2340
X-GUIF-Model-ID: image-model
Content-Type: image/png

<raw PNG bytes>
```

The Gateway validates credential capability, Host/Tool/Handoff identity, Task etag, lease ownership, content size, optional content SHA-256, and idempotency before Artifact registration. Successful callback replays return the stored non-secret receipt and do not create duplicate Artifacts.

The default body limit is 32 MiB and can be changed with `--max-body-mb`.

## Signed Operation Ledger

Authenticated Runtime operations and Gateway request outcomes are appended to a private HMAC-SHA256 chain:

```text
<private-data-root>/operation-ledger/
  signing-key.json
  entries.jsonl
  head.json
```

Each entry records:

```text
sequence
operation + status
authenticated actor snapshot
Project / Task / object scope
sanitized request and result evidence
previous entry hash
payload hash
entry hash
HMAC signature
```

The signed head checkpoint detects modified entries, broken ordering, missing middle entries, and tail deletion.

Inspect it with:

```bash
guif-ledger --workspace . descriptor
guif-ledger --workspace . verify
guif-ledger --workspace . list --limit 50
guif-ledger --workspace . list --operation host.callback.submit
```

Or through Runtime:

```python
report = runtime.verify_operation_ledger()
entries = runtime.list_operation_ledger(limit=100)
```

The ledger provides **local tamper evidence**, not public-key non-repudiation. An attacker who obtains the private ledger key and can rewrite every private ledger file can forge a replacement chain. Alpha.25 does not provide an external timestamp authority or remote immutable log.

## Authenticated operations

Every persisted Task has a deterministic etag:

```python
etag = runtime.get_task_etag("SampleGame", task_id)
```

Exclusive writes use an expiring Task lease bound to Project, Task, actor, credential, purpose, and base etag. Stale state, expired leases, wrong actors, wrong credentials, and tampered tokens fail closed.

Authenticated APIs include:

```text
acquire_task_lease / renew_task_lease / release_task_lease
submit_authenticated_tool_result
decide_approval_authenticated
execute_gated_export_authenticated
rollback_gated_export_authenticated
prepare_export_git_change
execute_git_change
revert_git_change
```

Each direct authenticated Runtime operation writes `started` and `completed` or `failed` ledger entries. Bearer tokens, lease tokens, image bytes, and credential verifiers are excluded from ledger details.

## Private Theme boundary

Real user Themes remain private, user-owned, and versioned outside framework and Project Git:

```text
<private-data-root>/
  themes/
  conversation-theme-bindings/
  project-theme-bindings/
  host-credentials/
  gateway-requests/
  operation-ledger/
  runs/<project>/<task-id>/
  plans/
  migrations/
  privacy-reports/
```

A new visual-design conversation must select, create, derive, or explicitly continue without a Theme. Persisted Task Context stores only Theme ID, version, snapshot hash, and privacy marker; full Theme content is hydrated inside the private boundary at runtime.

## Existing production flow

GUIF continues to provide:

- private versioned Theme Library and conversation-first Theme selection;
- Workflow-driven Planner, Director, Theme, Resource, Prompt, and Semantic QA Agents;
- configurable Host and Tool routing with ChatGPT defaults;
- Artifact identity, immutable References, SHA-256, MIME, and dimensions;
- deterministic metadata review and optional semantic Visual Inspectors;
- controlled Revision execution and review-gated supersession;
- Gated Export, Engine manifests, transaction audit, backups, and rollback;
- Task-bound Git Change Sets with plan, diff, branch, commit, and revert;
- current-tree privacy audit and legacy Theme migration.

## Command-line entry points

```text
guif          framework, Theme, Task, Artifact, QA, Revision, and Export commands
guif-ops      authenticated credentials, leases, callbacks, Approval, Export, and Git operations
guif-gateway  authenticated HTTP Host boundary
guif-ledger   private Operation Ledger inspection and verification
```

`guif-ops` reads bearer and lease tokens from `GUIF_HOST_TOKEN` and `GUIF_TASK_LEASE`, avoiding command-history exposure.

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

- The Gateway uses local GUIF bearer credentials; OIDC, mTLS client identity, hardware-backed keys, and remote identity providers are not implemented.
- The bundled WSGI server is suitable for a controlled single-node boundary, not direct exposure as a public internet edge.
- Task leases and ledger locking are process-local/file-backed rather than distributed coordination primitives.
- Legacy unauthenticated Runtime APIs remain for compatibility and can bypass alpha.25 authentication and ledger guarantees.
- The Operation Ledger uses a private symmetric HMAC key and is not a public signature or external immutable audit service.
- ChatGPT product-side orchestration must still be configured to call the Gateway endpoints automatically.
- The default semantic Visual Inspector Registry is empty.
- Private storage does not yet provide encryption-at-rest, remote synchronization, retention policy, or disaster-recovery replication.
- Git execution creates local branches and commits; remote push, pull requests, and protected-branch negotiation are not automated.
- Current-tree privacy audit cannot prove removal from Git history, forks, caches, or external clones.

## Next phase

The next priority is **alpha.26: Real ChatGPT Image Loop and Default Visual Inspector**: Host-side automatic handoff consumption, image generation/edit execution, result submission through the Gateway, default semantic visual inspection, revision retry orchestration, and an end-to-end runnable project acceptance test.
