# Game UI Framework (GUIF)

**English** | [简体中文](README.zh-CN.md)

GUIF is a local-first game UI production framework with configurable Hosts and Tools. ChatGPT is the default Host, `chatgpt-image` is the default image generation/editing Tool, and `chatgpt-vision` is the default semantic visual inspector. All remain replaceable contracts rather than hard-coded Core dependencies.

## Status

`v1.0.0-alpha.27` adds a private conversation-first workflow that hides Task IDs, etags, leases, work claims, handoffs, and callbacks from the normal user path.

```text
open conversation
  -> confirm, create, derive, or explicitly skip private Theme
  -> describe the requested screen in natural language
  -> review and approve the generated production contract
  -> ChatGPT Host performs image generation or editing
  -> deterministic image metadata review
  -> chatgpt-vision semantic review
  -> independent revision approval when needed
  -> gated export
```

The bilingual living specification is maintained at [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md). Privacy migration and repository-history guidance remain in [`docs/PRIVACY_MIGRATION.md`](docs/PRIVACY_MIGRATION.md).

## Conversation-first API

```python
from pathlib import Path
from guif.runtime import Runtime

runtime = Runtime(Path.cwd())
issued = runtime.register_host_credential(
    actor_id="conversation-host",
    host_id="chatgpt",
    capabilities=(
        "approval:decide",
        "export:execute",
        "host-work:read",
        "host-work:claim",
        "host-work:complete",
        "revision:decide",
        "task:lease",
        "task:resume",
        "tool:execute",
        "tool-result:submit",
        "visual-inspection:submit",
    ),
)

conversation = runtime.conversation_workflow(
    bearer_token=issued["bearer_token"],
)

view = conversation.open(
    "SampleGame",
    "conversation-001",
)
```

A default user view contains:

```text
conversation_id
project
stage
message
theme summary
contextual actions
safe Artifact summaries
recovery status
```

It does not contain Task IDs, Task etags, lease tokens, work claim tokens, Handoff IDs, Callback IDs, private file paths, or raw Theme content. Diagnostics can be requested explicitly for development and support.

## Theme confirmation

A new conversation starts at `theme-confirmation` unless it already has a private Theme binding.

```python
view = conversation.create_theme(
    "SampleGame",
    "conversation-001",
    "Fictional Orbital Fixture",
    {
        "description": "A wholly fictional orbital kiosk interface.",
        "palette": ["test violet", "test silver"],
        "materials": ["matte composite"],
        "lighting": "soft synthetic daylight",
        "must_include": ["circular menu"],
        "avoid": ["real brands"],
    },
)
```

Other supported paths are:

```text
select_theme       choose a historical private Theme
create_theme       create and bind a new Theme
derive_theme       create and bind a new immutable Theme version
continue_unbound   explicitly continue without a Theme for this conversation
```

Real Theme content stays in the private Theme Library outside framework and Project Git.

## Submit a natural-language request

```python
view = conversation.submit(
    "SampleGame",
    "conversation-001",
    "Create a 1080x2340 fictional orbital shop page and export Unity",
    request_key="chat-turn-001",
)
```

`request_key` provides idempotency. Repeating the same key and request returns the existing conversation state. Reusing it for different content fails closed instead of creating duplicate Tasks.

The initial result normally enters:

```text
approval-required
```

Approve without handling an Approval ID or Task lease:

```python
view = conversation.approve(
    "SampleGame",
    "conversation-001",
    comment="Proceed with the approved production contract.",
)
```

The service resolves the current approval context, obtains and consumes the required private lease, records the authenticated actor, and prepares the correct image work.

## Real image and visual loop

The ChatGPT product or another configured Host supplies the actual Tool callables:

```python
view = conversation.run_host_until_blocked(
    "SampleGame",
    "conversation-001",
    image_executor=call_chatgpt_image_tool,
    visual_inspector=call_chatgpt_visual_inspection,
)
```

The service automatically scopes work to the active conversation Task and coordinates:

```text
Host Work discovery
-> Task etag
-> exclusive Task lease
-> Actor-bound one-time Work claim
-> immutable Attachment retrieval
-> image or semantic result submission
-> Artifact registration
-> metadata review
-> semantic review
-> next user-facing stage
```

No work from another conversation is consumed by this call.

A semantic result can be:

```text
passed
review-required
blocked
```

Metadata alone never creates a semantic pass.

## Controlled revision

Actionable semantic findings create a Revision Plan and versioned Revision Job. The initial generation approval does not authorize editing.

The user-facing stage becomes:

```text
revision-approval-required
```

Calling `conversation.approve(...)` at that stage authorizes only the current Revision and prepares `image-editing` work. The original Artifact remains active until the replacement passes semantic review.

## Gated export

After contract QA and every active visual Artifact pass, the view becomes:

```text
ready-to-export
```

```python
view = conversation.export(
    "SampleGame",
    "conversation-001",
    target_engine="unity",
)
```

The service obtains the private export lease and invokes the existing authenticated Gated Export. Export still does not bypass Engine manifests, transaction evidence, backups, rollback, or Git Change controls.

## Recovery

Conversation records and checkpoints are private:

```text
<private-data-root>/conversation-workflows/<project>/conversation-<sha256>.json
```

Each checkpoint records the user-facing stage, persisted Task status, Task etag, Artifact count, and timestamp. Raw secrets are never written into the conversation record.

```python
view = conversation.recover("SampleGame", "conversation-001")
```

Recovery reconciles the private conversation record with persisted Tasks and Host Work. An orphaned session reference can be restored by matching the Task's private conversation binding. Failed pipeline work can be retried through `conversation.retry(...)` from its stored agent checkpoint.

## Command-line workflow

Set the Host token once in the environment:

```bash
export GUIF_HOST_TOKEN='guifh1....'
```

Then use conversation-level commands:

```bash
guif-conversation open \
  --project SampleGame \
  --conversation conversation-001

guif-conversation theme-list \
  --project SampleGame \
  --conversation conversation-001

guif-conversation submit \
  --project SampleGame \
  --conversation conversation-001 \
  --request-key chat-turn-001 \
  "Create a fictional orbital shop page and export Unity"

guif-conversation approve \
  --project SampleGame \
  --conversation conversation-001

guif-conversation status \
  --project SampleGame \
  --conversation conversation-001

guif-conversation recover \
  --project SampleGame \
  --conversation conversation-001
```

The CLI intentionally does not implement a fake image model. Actual image and vision execution still comes from the configured Host Tool integration or the authenticated Gateway work endpoints.

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
  operation-ledger/
  runs/
  plans/
  migrations/
  privacy-reports/
```

Real Themes, prompts, conversation decisions, work claims, attachments, Artifacts, findings, and runtime evidence remain outside framework and Project Git by default. Public tests and examples use only wholly fictional fixtures.

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

- The ChatGPT product must embed the conversation/Host loop or consume the Gateway work endpoints; this repository cannot wire itself into ChatGPT's internal Tool runtime.
- The semantic inspector is an authenticated external result contract, not an autonomous local vision model.
- Conversation, Work, and Task coordination is local file-backed coordination, not distributed consensus.
- Private storage does not yet provide encryption at rest, remote synchronization, retention policy, or multi-device conflict resolution.
- The conversation CLI manages state and approvals but cannot invoke ChatGPT-internal image tools from a standalone terminal.
- Current-tree privacy audit cannot prove removal from Git history, forks, caches, or external clones.

## Next phase

The next priority is **alpha.28: Usability Freeze and Beta Readiness**: one-command onboarding, private backup/restore, schema migration, failure diagnostics, end-to-end sample validation, compatibility guarantees, and an MVP scope freeze before `beta.1`.
