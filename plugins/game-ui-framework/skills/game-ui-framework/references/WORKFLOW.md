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

## Production commands

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
| `request-changes --comment-file FILE` | Request changes at the current production gate. |
| `reject` | Reject the current production gate. |
| `continue` | Continue the next approved production step. |
| `recover` | Reconcile private Conversation and Task state. |
| `retry` | Resume from a persisted recoverable failure. |
| `export [--target-engine ENGINE]` | Execute the final gated export. |

## Candidate Change commands

| Command | Purpose |
| --- | --- |
| `improvement-open --change-type TYPE --observed-file FILE --expected-file FILE [--proposal-file JSON]` | Pause the current production checkpoint and open a private Improvement Case. |
| `improvement-status` | Return the current Candidate Change state. |
| `improvement-propose --proposal-file JSON` | Add or replace the candidate proposal before trial approval. |
| `improvement-trial-approve` | Approve only an isolated trial. This does not authorize adoption, Git merge, publication, or stable configuration changes. |
| `improvement-trial-request-changes` | Return the case to proposal work. |
| `improvement-trial-reject` | Close the case and retain the stable version. |
| `improvement-bundle` | Produce a private, sanitized source-repository development handoff bundle. Never expose its path to the user. |
| `improvement-candidate-link --candidate-file JSON` | Link a candidate branch, commit, or version after it is built in the GUIF source repository. |
| `improvement-candidate-run` | Start an isolated executable Tool trial using a Task-only override. |
| `improvement-result --group stable|candidate --summary-file FILE [--artifact-file FILE]` | Record real comparison evidence. Candidate evidence is required before adoption. |
| `improvement-adopt` | Approve formal adoption after reviewing real candidate results. |
| `improvement-adoption-request-changes` | Return to candidate building after result review. |
| `improvement-adoption-reject` | Reject the candidate and retain the stable version and Tool routing. |
| `improvement-published --delivery-file JSON` | Record repository, branch, PR, merge commit, and minimum plugin version after an adopted code candidate is merged. |
| `improvement-refresh-confirm [--current-version VERSION]` | Confirm that the newly loaded plugin meets the required version. |
| `improvement-regression-pass --summary-file FILE` | Record a real passing replay of the original scenario. |
| `improvement-regression-fail --summary-file FILE` | Reopen candidate building after a failing formal regression. |
| `improvement-resume` | Restore the paused production Task after resolution or explicit rejection. |

## Proposal file

A proposal is a JSON object:

```json
{
  "summary": "Reduce unintended texture and noise during protected image edits.",
  "changes": [
    "Constrain edits to the approved region.",
    "Add negative constraints for grain, speckle, and unnecessary highlights.",
    "Add a semantic cleanliness review dimension."
  ],
  "affected_layers": [
    "Skill",
    "Prompt IR",
    "Visual Review"
  ],
  "validation_plan": [
    "Run the same fictional source image and edit objective under stable and candidate versions.",
    "Inspect real candidate pixels and ask the user to confirm the visual result."
  ],
  "safety_constraints": [
    "Do not commit the user's real source image.",
    "Do not merge before adoption approval.",
    "Do not replace semantic review with metadata."
  ],
  "public_fixture": "Use a fictional orbital market image with flat clean surfaces."
}
```

The user must approve the trial after seeing the proposal. Approval of this file does not authorize formal adoption.

## Candidate metadata file

For a code, Skill, workflow, or Tool-integration candidate:

```json
{
  "branch": "experiment/reduce-edit-noise",
  "commit": "candidate-commit-sha",
  "version": "1.0.0-beta.4-candidate.1",
  "notes": "Candidate remains isolated from the installed stable plugin."
}
```

At least one of `branch`, `commit`, or `version` is required.

## Candidate result evidence

Use a private text file for the summary. An optional real image or other result file is copied into the Improvement Case evidence directory. The public view only reports the evidence group, summary, MIME type, and aggregate Artifact count; it omits the private path and SHA-256.

Recommended visual trial:

```text
same fictional source
same edit objective
same canvas and protected region
stable result
candidate result
real semantic inspection
user adoption decision
```

Candidate evidence is mandatory. A stable baseline is recommended but not mandatory when no truthful baseline exists.

## Two independent approvals

```text
proposal
  -> trial approval
  -> isolated candidate
  -> real result review
  -> adoption approval
  -> publication or scoped Tool-route application
```

Trial approval never implies adoption. Adoption cannot be approved without real candidate evidence.

## Tool trial routing

Open a Tool change with:

```bash
improvement-open \
  --change-type tool-change \
  --observed-file OBSERVED \
  --expected-file EXPECTED \
  --proposal-file PROPOSAL \
  --tool-id figma \
  --capability structured-ui-layout \
  --adoption-scope project
```

GUIF evaluates Tool discovery:

- registered + available + healthy: `tool-trial`; `improvement-candidate-run` creates a new candidate Task with a Task-only Tool override;
- installable, unregistered, unavailable, unhealthy, or unknown: `tool-integration-change`; build an Adapter candidate instead of pretending the Tool can run.

The stable Project or Workspace routing is not changed by the trial. After the user approves adoption:

- `task`: apply only to the paused source Task;
- `project`: write the Project execution route;
- `workspace`: write the Workspace execution route.

A Tool trial should expose permission, data-scope, external-call, billing, credential, Host-support, availability, and health disclosures.

## Publication delivery file

```json
{
  "repository": "943065241/game-ui-framework",
  "branch": "feature/candidate-change",
  "pull_request": 35,
  "merge_commit": "merged-commit-sha",
  "minimum_plugin_version": "1.0.0-beta.3"
}
```

Publication is valid only after adoption approval. The current installed session still contains the old Skill and Runtime snapshot, so publication transitions to `plugin-refresh-required`.

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

The bridge stores credentials, context files, source images, Improvement Cases, candidate evidence, development bundles, claim tokens, attachments, and private framework records below `PLUGIN_DATA`. `GUIF_CODEX_PLUGIN_DATA` is an explicit test or managed-runtime override. Neither location belongs in Project Git.

Private requirement, Theme, source, proposal, candidate, evidence-summary, delivery, regression, and decision files should be placed under `PLUGIN_DATA/input/`. Delete temporary inputs after the corresponding operation when they are no longer needed; canonical private records remain available for recovery.
