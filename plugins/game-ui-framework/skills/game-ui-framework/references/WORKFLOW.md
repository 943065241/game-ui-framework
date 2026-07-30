# GUIF Codex bridge reference

The Skill invokes the bridge internally. The user should not be asked to copy these commands.

## Common invocation

```bash
python "$PLUGIN_ROOT/skills/game-ui-framework/scripts/guif_codex.py" \
  --workspace "$PWD" \
  <command>
```

Optional `--project` and `--conversation` values select a non-default context. The bridge persists that selection privately for the workspace.

## Conversation commands

| Command | Purpose |
| --- | --- |
| `start` | Initialize or reopen Project, private Host credential, and Conversation. |
| `status` | Return the current public GUIF stage and contextual actions. |
| `theme-create --name NAME --content-file FILE` | Create and select a private Theme from a JSON file. |
| `theme-select --theme-id ID [--version N]` | Select a private historical Theme. |
| `theme-derive --theme-id ID --updates-file FILE` | Create an immutable derived Theme version. |
| `theme-unbound` | Continue without a Theme only after an explicit user choice. |
| `submit --request-file FILE` | Submit the complete natural-language requirement from a private file. |
| `approve` | Approve the current Initial or Revision gate. |
| `request-changes --comment-file FILE` | Request changes at the current gate. |
| `reject` | Reject the current gate. |
| `continue` | Continue the next approved framework step. |
| `recover` | Reconcile private Conversation and Task state. |
| `retry` | Resume from a persisted recoverable failure. |
| `export [--target-engine ENGINE]` | Execute the final gated export. |

## Real Host handoff

Run `host-prepare` only after approval when GUIF reports that Host work is available. Its response includes a private `host_session`, a work contract, and any immutable attachment paths.

### Image generation or editing

1. Invoke a real Codex image capability using the returned work contract and attachments.
2. Save the actual output image to a file.
3. Submit it:

```bash
python "$PLUGIN_ROOT/skills/game-ui-framework/scripts/guif_codex.py" \
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
python "$PLUGIN_ROOT/skills/game-ui-framework/scripts/guif_codex.py" \
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

The bridge stores all credentials, context files, claim tokens, attachments, and private framework records below `PLUGIN_DATA`. `GUIF_CODEX_PLUGIN_DATA` is an explicit test or managed-runtime override. Neither location belongs in Project Git.

Private requirement and Theme files should be placed under `PLUGIN_DATA/input/`. Delete temporary inputs after the corresponding GUIF operation when they are no longer needed.
