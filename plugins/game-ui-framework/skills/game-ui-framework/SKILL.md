---
name: game-ui-framework
description: Use the GUIF visual-production domain of AIPG from Codex to create, edit, review, revise, layer, and export game UI. Trigger for game interface design, master-guided layer creation, UI image generation or editing, private Theme management, source registration, approvals, visual QA, controlled revisions, and engine export. Do not trigger for non-visual production domains.
---

# GUIF Visual Production for AIPG

GUIF is the visual-production domain of AIPG (AI Production & Governance
Framework). Preserve the `$game-ui-framework` Skill name as a compatibility
entry point. Route framework-wide governance and non-visual production through
the sibling AIPG Skill.

## Master-guided layer creation

When the user wants a master effect image to guide style and layout while AI
creates reusable layers from bottom to top, select
`master-guided-layer-creation`.

- Treat the master as style and layout guidance, not a pixel-matching target.
- Require only functional roles, layout anchors, asset boundaries, protected
  content, and output contracts as hard constraints.
- Keep shape details, materials, texture, lighting, and decoration as soft
  guidance with low, medium, or high creative freedom per layer.
- Approve the coarse layer plan before production.
- Give each layer Host work the master, Theme, current composite, completed
  layers, and future layer roles.
- Recompose after every layer and perform real semantic visual inspection.
- A revision to one layer invalidates that layer and downstream composites, not
  protected earlier layers.
- Export independent assets, the final composite, and a composition manifest.

Act as the natural-language front end for GUIF. The user talks about the desired game UI or a GUIF workflow problem; you operate the framework internally. Do not make the user install GUIF, copy tokens, type GUIF CLI commands, or reason about private Runtime IDs.

## Runtime

Resolve `scripts/guif_codex.py` relative to this SKILL.md file, whose absolute path Codex provides when the Skill is loaded. When `PLUGIN_ROOT` is available, the equivalent canonical path is `$PLUGIN_ROOT/plugins/game-ui-framework/skills/game-ui-framework/scripts/guif_codex.py`.

Invoke the bundled bridge internally:

```bash
python <resolved-skill-directory>/scripts/guif_codex.py --workspace "$PWD" <command>
```

Treat bridge invocations as internal implementation details. Summarize only the user-facing stage, design plan, source decision, approval decision, Candidate Change proposal, real trial result, Tool disclosure, publication result, refresh requirement, regression result, artifact result, visual finding, revision request, or export result.

The bridge automatically initializes a project and conversation on first use. It stores Host credentials, source images, Improvement Cases, candidate evidence, and GUIF private records under `PLUGIN_DATA`, outside Project Git. Never print, quote, copy, or commit private credential, source, evidence, claim, or development-bundle paths.

## Production workflow

1. Run `status`. First use automatically bootstraps the private GUIF conversation.
2. At `theme-confirmation`:
   - When the user supplied concrete visual direction, write a private JSON file under `PLUGIN_DATA/input/` and run `theme-create`.
   - When the user explicitly says an image is the Theme reference or master, pass that real image with `theme-create --source-file`; GUIF automatically registers it in the private Source Library and binds it to the Theme.
   - When they reference an existing private Theme, use `theme-select` or `theme-derive`. Pass `--source-file` to `theme-derive` when adding a new Theme reference.
   - Use `theme-unbound` only when the user explicitly asks to work without a Theme.
   - Ask one concise design question only when a missing visual decision materially prevents a useful Theme.
3. Write the complete user requirement to a private UTF-8 file under `PLUGIN_DATA/input/`, then run `submit --request-file`. Never place private requirements directly in shell arguments.
4. At `source-import-required`, explain why the current image is not yet a protected GUIF source and present every framework-provided option. Do not choose silently:
   - “导入为可编辑源图并继续” → `source-import --source-usage editable-source`.
   - “导入并加入 Theme 参考” → `source-import --source-usage theme-reference`.
   - “导入并设为母版参考” → `source-import --source-usage master-reference`.
   - “退出正式链并普通编辑” → `source-external-edit`; clearly state that later output is not a formal GUIF result.
   Use the actual conversation/upload/temporary image file and truthful `--source-kind`. Never copy it into Project Git.
5. At `approval-required`, explain the proposed GUIF contract in ordinary language. A clear “继续”, “确认”, “可以”, or equivalent approval authorizes `approve`. Requested changes use a private comment file and `request-changes`.
6. After approval, run `host-prepare`:
   - For `image-generation` or `image-editing`, invoke Codex's real configured image capability using the returned work contract and immutable attachments. Submit the actual image file with `host-complete-image`.
   - For `visual-inspection`, inspect the actual artifact with a real vision-capable tool. Write a JSON result containing `status`, `summary`, and structured `findings`, then use `host-complete-visual`.
   - When the required real image or vision capability is unavailable, stop and state that the production step is blocked. Never fabricate pixels, visual findings, or a passing semantic review. Never substitute a dry run in production.
7. A revision has its own approval gate. Do not treat initial approval as permission to edit an approved source artifact.
8. Run `export` only when the GUIF stage is `ready-to-export` and the user asked for export.
9. Use `recover` or `retry` when the framework reports a recoverable interruption.

## Candidate Change workflow

Enter this workflow when the user explicitly says GUIF, the Skill, a workflow, or a Tool should be improved, or when the formal workflow has no safe executable path. Do not silently work around a framework defect.

1. Diagnose before choosing a layer. A repeated visual problem such as introduced noise may come from the Skill, Prompt IR, edit scope, Theme policy, visual review, cumulative revisions, or the current Tool. Do not assume `skill-change` merely because the user says “完善 Skill”.
2. Open one private Improvement Case with `improvement-open`. Preserve the production checkpoint and classify it as one of:
   - `skill-change`
   - `framework-change`
   - `tool-change`
   - `tool-integration-change`
   - `theme-policy-change`
   - `workflow-change`
   - `provider-routing-change`
   - `multi-layer-change`
3. The proposal must contain:
   - observed and expected behavior;
   - diagnosis and affected layers;
   - concrete candidate changes;
   - a real validation plan;
   - privacy and safety constraints;
   - a wholly fictional public regression fixture.
4. At `improvement-trial-approval-required`, explain that approval authorizes only an isolated experiment. It does not authorize Git merge, publication, stable configuration mutation, or plugin replacement.
5. After trial approval:
   - Code or Skill changes enter `improvement-candidate-building`. Use the private development handoff bundle in a GUIF source-repository development session. Do not edit the installed plugin snapshot.
   - A `tool-change` is first assessed through GUIF Tool discovery. A registered and available Tool becomes an isolated Tool trial. An unavailable or unregistered Tool becomes `tool-integration-change`; do not pretend it can run.
6. Candidate and stable states must remain isolated:
   - no merge to `main` before adoption approval;
   - no stable Tool-route mutation before adoption approval;
   - no candidate export presented as a stable production result;
   - no private user image committed as a public regression fixture.
7. Run or record real candidate evidence:
   - For an available Tool trial, use `improvement-candidate-run`; the candidate Task uses a Task-only Tool override while stable Project/Workspace routing remains unchanged.
   - For code or Skill candidates, link the branch/commit/version with `improvement-candidate-link`, run the candidate in its source-repository environment, and record the real result with `improvement-result`.
   - Stable baseline evidence is recommended for visual comparisons; candidate evidence is mandatory.
8. At `improvement-result-review-required`, show the actual candidate outcome and let the user decide:
   - “正式采用” → `improvement-adopt`;
   - “继续调整” → `improvement-adoption-request-changes`;
   - “放弃并保留稳定版本” → `improvement-adoption-reject`.
   This is the second approval gate. Trial approval never implies adoption.
9. After adoption:
   - A supported Tool change applies only to the user-confirmed `task`, `project`, or `workspace` scope and can resolve without a Git release.
   - A Skill, framework, workflow, Theme-policy, provider-routing, or Tool-integration change enters `improvement-publishing-required`. Only now may the source-repository session commit, run CI, open a PR, and merge after checks pass.
10. After publication, record the repository, branch, PR, merge commit, and minimum plugin version with `improvement-published`.
11. At `plugin-refresh-required`, tell the user to refresh **AIPG Framework** and start a new Codex session. The current session cannot claim a hot reload. In the new session, confirm the installed version with `improvement-refresh-confirm`.
12. Reproduce the original scenario. Record `improvement-regression-pass` only after real validation. A failed regression reopens candidate building. Resume the paused production Task only after resolution or explicit candidate rejection.

## Tool change rules

- Tool identity and capability are separate. Figma may be suitable for structured layout and editable layers, while a raster image Tool remains necessary for illustration generation or pixel-level editing.
- Do not replace every image capability merely because the user says “换成 Figma”. Explain which capability is changing.
- Before a Tool trial, surface permissions, data scope, external calls, billing, credentials, Host support, registration, availability, and health.
- An already supported Tool change is configuration, not automatically a framework code change.
- An unsupported Tool requires a Tool integration candidate with Adapter, permission disclosure, health checks, real result callbacks, failure recovery, and contract tests.
- Adoption scope must be explicit: current Task, current Project, or Workspace. Never silently make a global default.

## Interaction rules

- The framework must propose source-registration choices and let the user decide unless the user explicitly created or derived a Theme with a reference or master image, which authorizes automatic private registration.
- The two Candidate Change approvals are independent: approve trial first, approve adoption only after seeing real results.
- Default Tool identities are `chatgpt-image` and `chatgpt-vision`; pass a different truthful model or inspector ID when the configured capability differs.
- `Legacy ProviderAdapter` is explicit compatibility only. Never silently route new production or candidate work through it.
- Do not expose Task IDs, etags, leases, claims, callback IDs, Bearer Tokens, source hashes, private evidence paths, or private development-bundle paths.
- Do not commit real Theme content, uploaded images, conversation records, prompts, candidate evidence, or generated artifacts unless the user explicitly selects an artifact for Project Git.
- Public examples and tests must remain fictional.
- Preserve protected pixels and immutable lineage when GUIF marks them as protected.
- Metadata checks cannot claim composition, readability, Theme consistency, noise reduction, or usability. Those require a real semantic visual inspection and, for subjective adoption, user confirmation.

Read `references/WORKFLOW.md` when command arguments, stage mapping, source contracts, Candidate Change states, Tool trial rules, or Host result contracts are needed.
