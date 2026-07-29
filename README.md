# Game UI Framework (GUIF)

**English** | [简体中文](README.zh-CN.md)

GUIF is a local-first game UI production framework with configurable Hosts and Tools. ChatGPT is the default Host, while image generation, image editing, visual inspection, Git operations, and export remain replaceable Tool capabilities.

## Status

`v1.0.0-alpha.21` adds a reviewable Host and Tool discovery and connection workflow.

GUIF now distinguishes:

```text
registered   an Adapter exists in the current Runtime
available    the current Host or local Runtime can use it now
installable  a Catalog entry exists, but no Adapter is registered yet
```

Missing Tools still fail closed. The Runtime now links a persisted connection request to eligible `waiting-for-tool` resolutions rather than silently installing a Plugin, requesting a secret in plain text, or falling back to `dry-run`.

The controlled visual-revision loop from alpha.20 remains intact: Revision Plans become separately approved edit Jobs, source Artifacts are immutable and SHA-256 verified, and replacements supersede sources only after a passing semantic visual review.

## Product specification

The bilingual living product specification is maintained at [`docs/GUIF_PRODUCT_SPEC.md`](docs/GUIF_PRODUCT_SPEC.md). Feature implementation, tests, CI, both READMEs, version metadata, and this specification must agree for a release to be complete.

## Host discovery

```python
runtime = Runtime(workspace)
report = runtime.discover_host()
```

The report uses `guif-host-capability-discovery-v1` and includes:

- Host identity;
- advertised capabilities;
- currently available Tool IDs;
- Host metadata;
- discovery timestamp.

The default ChatGPT Host advertises `chatgpt-image`, image generation and editing, protected-region editing, transparent output, visual inspection, and Git operation capabilities.

## Tool discovery

```python
tools = runtime.discover_tools(project="LeekParty")
```

Each discovered record contains:

- `status` and complete `states`;
- registered, available, installable, and ready booleans;
- Tool Manifest or Catalog metadata;
- Host and execution mode;
- current Health Check;
- latest Project connection status;
- permission, data-scope, external-call, cost, credential, and Host-support disclosures.

Workspace installable entries may be declared in:

```text
.guif/tool-catalog.json
```

Example:

```json
{
  "tools": [
    {
      "tool_id": "custom-image",
      "name": "Custom Image Tool",
      "version": "1.0",
      "capabilities": ["image-generation", "image-editing"],
      "install_method": "plugin-manager",
      "source": "trusted-workspace-catalog",
      "permissions": ["network-access"],
      "data_scopes": ["prompt-job", "approved-reference-images"],
      "external_call": true,
      "billable": true,
      "requires_credentials": true,
      "credential_kind": "api-key-reference"
    }
  ]
}
```

A Catalog entry does not install or register the Tool.

## Connection workflow

```text
missing or unavailable Tool
  -> connection request
  -> review disclosures
  -> approve or reject
  -> installation-required / waiting-for-credentials / waiting-for-host-support
  -> Health Check retry
  -> connected
  -> execute the same persisted Job
```

Create and approve a request:

```python
request = runtime.request_tool_connection(
    "LeekParty",
    "image-generation",
    "chatgpt-image",
    requested_by="ChatGPT Host",
)

connected = runtime.approve_tool_connection(
    "LeekParty",
    request["request_id"],
    actor="project-owner@example.com",
    comment="Permissions and data scope reviewed.",
)
```

Rejecting a request never changes Project Tool configuration.

Approving an installable-only entry returns `installation-required`; GUIF does not auto-install it. Approving a Tool that requires credentials returns `waiting-for-credentials` until an opaque reference is supplied.

## Credential policy

GUIF connection state stores only references such as:

```text
env://CUSTOM_IMAGE_API_KEY
secret-manager://projects/leek-party/custom-image
```

It does not store the credential secret itself. Every request records:

```json
{
  "credential": {
    "required": true,
    "kind": "api-key-reference",
    "reference": "env://CUSTOM_IMAGE_API_KEY",
    "secret_stored_by_guif": false
  }
}
```

Credential resolution and secret storage remain the responsibility of the Host, Plugin, operating environment, or secret manager.

## Health retry

```python
retry = runtime.retry_tool_health("LeekParty", "chatgpt-image")
```

Health retries are appended to `tool-connections.json`. An already approved request can move to `connected` when Host, Tool, or credential configuration becomes healthy.

## Tool Adapter contract tests

```python
report = runtime.run_tool_contract_tests("chatgpt-image")
```

The runner performs no external call. It validates:

- Manifest schema and identity;
- capability declaration;
- input and output contracts;
- implementation of `prepare()` or `execute()` for the declared execution mode;
- permission, data-scope, cost, and credential disclosures;
- Health Check identity and status shape.

The generated Adapter scaffold now reminds implementers to complete disclosures and run:

```bash
guif tool-contract-test <tool-id>
```

A passing contract test does not install, trust, sign, or automatically register a Plugin.

## Default ChatGPT path

```text
User
  -> ChatGPT Host
  -> GUIF Runtime
  -> Approval
  -> Tool Resolver
  -> chatgpt-image
  -> external Handoff
  -> ChatGPT generates or edits the image
  -> Host submits the real file
  -> Artifact Registry
  -> Visual Review / controlled Revision
  -> gated Export
```

ChatGPT Host and `chatgpt-image` are defaults, not GUIF Core dependencies. `dry-run` remains explicit contract testing only and is never an implicit production fallback.

## CLI

```bash
guif host-discover

guif tool-discover --project LeekParty

guif tool-connect-request image-generation chatgpt-image \
  --project LeekParty \
  --requested-by "ChatGPT Host"

guif tool-connect-list --project LeekParty

guif tool-connect-approve <request-id> \
  --project LeekParty \
  --actor project-owner@example.com

guif tool-connect-reject <request-id> \
  --project LeekParty \
  --actor project-owner@example.com

guif tool-health-retry chatgpt-image --project LeekParty

guif tool-contract-test chatgpt-image
```

Existing production and revision commands remain available, including `run-execute`, `run-tool-submit`, `run-revision-create`, `run-revision-approve`, `run-revision-execute`, and `run-artifact-review`.

## Persistence

Project-level discovery and connection evidence is stored at:

```text
projects/<project>/tool-connections.json
```

It contains connection requests, decisions, disclosure snapshots, credential references, status transitions, and Health Check history. Task-specific resolution and handoff records remain in each Run directory.

## Current limitations

- GUIF does not yet install Plugins or dynamically load a newly installed Adapter.
- There is no authenticated Host or Approval identity yet.
- Credential references are not resolved by GUIF Core.
- Catalog entries are workspace-local and are not signed or remotely verified.
- ChatGPT product-side automatic handoff callback wiring remains outside GUIF Core.
- The default semantic Visual Inspector Registry is still empty.
- The built-in Export Agent remains Contract-only.

## Operating principles

1. Discovery is evidence, not installation.
2. Connection requires explicit approval.
3. Permissions, data scope, external calls, cost, and Credentials must be disclosed before connection.
4. GUIF stores credential references, never credential secrets.
5. Production Tool failures remain fail-closed.
6. Contract tests perform no external calls.
7. ChatGPT is the default Host and image Tool, not a hard-coded dependency.
8. Revision sources remain immutable and replacements require passing review before supersession.

## Next phase

The next priority is **alpha.22: Gated Export Agent**. It will consume active Artifact records, Contract QA, Visual Review, Revision resolution, and Project Resource contracts before materializing approved production assets into Project truth and engine-specific export outputs.
