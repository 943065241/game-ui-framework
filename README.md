# Game UI Framework (GUIF)

**English** | [简体中文](README.zh-CN.md)

GUIF is a local-first game UI production framework with configurable Hosts and Tools. ChatGPT is the default Host, `chatgpt-image` is the default image generation/editing Tool, and `chatgpt-vision` is the default semantic visual inspector. All three remain replaceable contracts rather than hard-coded Core dependencies.

## Status

`v1.0.0-alpha.26` adds a claimable ChatGPT-first Host work loop for real image generation, image editing, and semantic visual inspection.

```text
private Theme selection
  -> Prompt / Approval / Tool handoff
  -> image-generation or image-editing Host work
  -> authenticated claim + Task lease
  -> real Host image Tool invocation
  -> Artifact registration
  -> deterministic metadata review
  -> chatgpt-vision semantic inspection work
  -> pass, review-required, or blocked
  -> controlled Revision Job when needed
  -> Gated Export / Git Change Set
```

The bilingual living specification is maintained at [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md). Privacy migration and repository-history guidance remain in [`docs/PRIVACY_MIGRATION.md`](docs/PRIVACY_MIGRATION.md).

## What alpha.26 makes runnable

A persisted `chatgpt-image` handoff is now exposed as private Host work:

```text
image-generation
image-editing
visual-inspection
```

Each work item includes:

- Project, Task, Tool, Handoff, and Artifact identity;
- the approved Prompt Job or Visual Inspection Request;
- required capability and submission contract;
- immutable downloadable attachments with SHA-256 identity;
- available, claimed, or completed state;
- a one-time claim secret bound to an authenticated Actor;
- a result receipt linked to the registered Artifact or Visual Review.

Work records are stored outside framework and Project Git:

```text
<private-data-root>/host-work/<project>/work-*.json
```

The stored record never contains the raw claim token.

## Production Gateway workflow

Start the Gateway:

```bash
pip install -e .[dev]
guif-gateway --workspace . --host 127.0.0.1 --port 8765
```

Remote binding still requires explicit opt-in and TLS:

```bash
guif-gateway \
  --host 0.0.0.0 \
  --port 8765 \
  --allow-remote \
  --tls-cert server.crt \
  --tls-key server.key
```

Create a Host credential with the work-loop capabilities:

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
        "host-work:read",
        "host-work:claim",
        "host-work:complete",
        "task:lease",
        "tool-result:submit",
        "visual-inspection:submit",
        "export:execute",
    ),
)

bearer_token = issued["bearer_token"]  # shown once
```

### Discover work

```http
GET /v1/work?project=SampleGame&status=available
Authorization: Bearer guifh1....
```

### Claim work

```http
POST /v1/work/SampleGame/work-image-123/claim
Authorization: Bearer guifh1....
Content-Type: application/json
Idempotency-Key: claim-001

{"ttl_seconds": 300}
```

The response returns `guifw1.<work-id>.<secret>` once. Claim ownership is bound to the authenticated Actor and Credential.

### Download an immutable attachment

```http
GET /v1/work/SampleGame/work-visual-123/attachments/attachment-456
Authorization: Bearer guifh1....
X-GUIF-Work-Claim: guifw1....
```

GUIF rechecks path confinement, existence, and SHA-256 before returning bytes. Image-editing work can expose its immutable source Artifact this way; visual-inspection work exposes the Artifact being reviewed.

### Submit an image result

Acquire a Task lease through the existing `/lease` endpoint, then submit raw image bytes:

```http
POST /v1/work/SampleGame/work-image-123/result
Authorization: Bearer guifh1....
Idempotency-Key: image-result-001
If-Match: "task-sha256:..."
X-GUIF-Lease-Token: guifl1....
X-GUIF-Work-Claim: guifw1....
X-GUIF-Filename: fictional-screen.png
X-GUIF-Content-SHA256: <sha256>
X-GUIF-Width: 1080
X-GUIF-Height: 2340
X-GUIF-Model-ID: chatgpt-image
Content-Type: image/png

<raw PNG bytes>
```

The result is registered through the authenticated callback contract. GUIF then automatically runs Artifact eligibility, file-integrity, dimensions, format, alpha, and registered-metadata checks. A passing metadata review creates `visual-inspection` work.

### Submit semantic visual inspection

```http
POST /v1/work/SampleGame/work-visual-123/result
Authorization: Bearer guifh1....
Idempotency-Key: visual-result-001
If-Match: "task-sha256:..."
X-GUIF-Lease-Token: guifl1....
X-GUIF-Work-Claim: guifw1....
Content-Type: application/json

{
  "inspector_id": "chatgpt-vision",
  "status": "review-required",
  "summary": "The hierarchy requires a controlled edit.",
  "findings": [
    {
      "id": "hierarchy-1",
      "severity": "review",
      "category": "composition-and-hierarchy",
      "code": "primary-action-too-weak",
      "message": "Increase the prominence of the fictional primary action.",
      "evidence": {"region": "lower-center"}
    }
  ]
}
```

Accepted statuses are:

```text
passed
review-required
blocked
```

A real semantic conclusion is claimed only after an authenticated inspector result is submitted. Metadata alone never becomes a semantic visual pass.

When actionable findings exist, GUIF automatically creates a versioned Revision Job. The Revision Job remains `approval-pending`; the initial generation Approval does not authorize editing.

## Embeddable ChatGPT Host loop

A Host integration can run the same flow without HTTP by supplying real image and vision callables:

```python
from guif.chatgpt_host_loop import ChatGPTHostLoop

loop = ChatGPTHostLoop(runtime, bearer_token=bearer_token)

loop.run_once(
    "SampleGame",
    image_executor=call_chatgpt_image_tool,
    visual_inspector=call_chatgpt_visual_inspection,
)
```

`ChatGPTHostLoop` handles discovery, Task etag, Task lease, claim ownership, immutable attachment retrieval, result submission, Artifact registration, and failure-safe lease release. The supplied callables perform the actual pixel generation/editing and semantic inspection.

## Important execution boundary

The local Python package cannot invoke ChatGPT's internal image tool by itself. Alpha.26 provides the production work queue, authenticated transport, attachment binding, and embeddable Host SDK required for ChatGPT or another Host to invoke its own tools and return the result.

Therefore:

```text
GUIF does not fabricate pixels.
GUIF does not infer a semantic pass from metadata.
dry-run does not become a production fallback.
The Host must supply the actual image and vision capabilities.
```

## Private data boundary

```text
<private-data-root>/
  themes/
  conversation-theme-bindings/
  project-theme-bindings/
  host-credentials/
  host-work/
  gateway-requests/
  operation-ledger/
  runs/
  plans/
  migrations/
  privacy-reports/
```

Real user Themes, conversation decisions, prompts, work claims, attachments, Runtime evidence, callback receipts, and semantic findings remain outside framework and Project Git by default. Public tests and examples use only fictional fixtures.

## Existing production controls

GUIF continues to provide:

- private, versioned Theme Library and conversation-first Theme selection;
- configurable Host and Tool discovery, connection, and routing;
- contract QA and persistent Approval gates;
- Artifact identity, SHA-256, MIME, dimensions, and immutable References;
- controlled Revision execution and review-gated supersession;
- Gated Export, Engine manifests, backups, rollback, and Git Change Sets;
- authenticated Actors, Task etags, exclusive leases, idempotency, and signed private operation evidence;
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

- The ChatGPT product must embed `ChatGPTHostLoop` or consume the Gateway work endpoints; the repository cannot wire itself into ChatGPT's internal tool runtime.
- The built-in semantic inspector is an authenticated external result contract, not an autonomous local vision model.
- Work claims and Task leases are local file-backed coordination, not distributed consensus locks.
- The built-in WSGI server is a single-node Host boundary, not an internet-edge reverse proxy.
- Private storage does not yet provide encryption at rest, remote synchronization, retention policy, or multi-device conflict resolution.
- Remote Git push, pull-request creation, protected-branch negotiation, and server-side check orchestration are not automated.
- Current-tree privacy audit cannot prove removal from Git history, forks, caches, or external clones.

## Next phase

The next priority is **alpha.27: Conversation-first User Workflow and Recovery**: one-command initialization, conversation session state, automatic Theme confirmation, project selection, generation/revision progress, resumable failed work, private backup and schema migration, and a user-facing flow that does not expose Task IDs, etags, leases, claims, or callback identifiers.
