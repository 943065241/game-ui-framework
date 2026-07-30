# GUIF Codex bridge reference

The Skill invokes the bridge internally. The user should not be asked to copy these commands.

## Common invocation

Resolve the bridge relative to the loaded SKILL.md. With `PLUGIN_ROOT`, its bundled-root path is:

```bash
python "$PLUGIN_ROOT/plugins/game-ui-framework/skills/game-ui-framework/scripts/guif_codex.py" \
  --workspace "$PWD" \
  <command>
```

Optional `--project` and `--conversation` values select a non-default context. The bridge persists that selection privately for the workspace.

## Conversation commands

| Command | Purpose |
| --- | --- |
| `start` | Initialize or reopen Project, private Host credential, and Conversation. |
| `status` | Return the current public GUIF stage and contextual actions. |
| `theme-create --name NAME --content-file FILE [--source-file IMAGE]` | Create and select a private Theme; a supplied image is automatically registered as a private master reference. |
| `theme-select --theme-id ID [--version N]` | Select a private historical Theme. |
| `theme-derive --theme-id ID --updates-file FILE [--source-file IMAGE]` | Create an immutable derived Theme version and optionally register a new Theme reference image. |
| `theme-unbound` | Continue without a Theme only after an explicit user choice. |
| `source-import --source-file IMAGE --source-usage USAGE` | Register an external image as `editable-source`, `theme-reference`, or `master-reference`, then repair the blocked edit contract. |
| `source-external-edit` | Record the user's explicit choice to leave the formal GUIF editing chain. |
| `submit --request-file FILE` | Submit the complete natural-language requirement from a private file. |
| `approve` | Approve the current Initial or Revision gate. |
| `request-changes --comment-file FILE` | Request changes at the current gate. |
| `reject` | Reject the current gate. |
| `continue` | Continue the next approved framework step. |
| `recover` | Reconcile private Conversation and Task state. |
| `retry` | Resume from a persisted recoverable failure. |
| `export [--target-engine ENGINE]` | Execute the final gated export. |

## Source registration decision

An edit request without a registered source enters `source-import-required`. Present the actions returned by GUIF and wait for the user's choice.

### Import and continue

```bash
python "$PLUGIN_ROOT/plugins/game-ui-framework/skills/game-ui-framework/scripts/guif_codex.py" \
  --workspace "$PWD" \
  source-import \
  --source-file ACTUAL_SOURCE_IMAGE \
  --source-kind user-upload \
  --source-usage editable-source
```

Use `conversation-temporary-image` for a file materialized from the current conversation, `user-upload` for an uploaded image, `external-file` for another local source, and `guif-artifact` only for a genuine existing GUIF Artifact.

The command copies the image into the private Source Library, calculates and verifies its identity, registers a task-bound Source Artifact, rebuilds the protected image-editing contract, and continues automatically only when the current approval already authorizes production.

### Add to Theme or master

Use `theme-reference` or `master-reference`. When a source image is supplied directly to `theme-create` or `theme-derive`, registration is automatic because the user's Theme/master instruction is explicit. The real image remains private; the Theme stores only a private source reference.

### Leave the formal chain

`source-external-edit` records that later ordinary image editing is not a formal GUIF result. Never label ordinary output as approval-gated, lineage-protected, visually reviewed, or export-ready through GUIF.

## Real Host handoff

Run `host-prepare` only after approval when GUIF reports that Host work is available. Its response includes a private `host_session`, a work contract, and any immutable attachment paths. An `image-editing` work item created from an imported source must expose that registered source as an immutable attachment.

### Image generation or editing

1. Invoke a real Codex image capability using the returned work contract and attachments.
2. Save the actual output image to a file.
3. Submit it:

```bash
python "$PLUGIN_ROOT/plugins/game-ui-framework/skills/game-ui-framework/scripts/guif_codex.py" \
  --workspace "$PWD" \
  host-complete-image \
  --session SESSION \
  --image ACTUAL_IMAGE_PATH \
  --model-id chatgpt-image
```

The model ID is a replaceable truthful identity. Do not claim `chatgpt-image` when another implementation produced the file.

### Semantic visual inspection

The real vision result file must be a JSON object:

```json
{
  "status": "passed",
  "summary": "Fictional artifact passed the requested semantic checks.",
  "findings": []
}
```

A non-passing result contains concrete structured findings. Submit it with:

```bash
python "$PLUGIN_ROOT/plugins/game-ui-framework/skills/game-ui-framework/scripts/guif_codex.py" \
  --workspace "$PWD" \
  host-complete-visual \
  --session SESSION \
  --result-file ACTUAL_RESULT_JSON \
  --inspector-id chatgpt-vision
```

Metadata-only checks must never be converted into a semantic `passed` result.

### Abort

When the real Host action cannot be completed after a work item has been claimed, run `host-abort --session SESSION` to release the lease. Do not submit placeholder bytes or invented findings.

## Private storage

The bridge stores all credentials, context files, source images, claim tokens, attachments, and private framework records below `PLUGIN_DATA`. `GUIF_CODEX_PLUGIN_DATA` is an explicit test or managed-runtime override. Neither location belongs in Project Git.

Private requirement, Theme, source, and decision files should be placed under `PLUGIN_DATA/input/`. Delete temporary inputs after the corresponding GUIF operation when they are no longer needed; the registered canonical source remains in the private Source Library.
