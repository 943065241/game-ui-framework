---
name: game-ui-framework
description: Use GUIF from Codex to create, edit, review, revise, and export game UI through natural-language conversation. Trigger for game interface design, UI image generation or editing, private Theme management, GUIF approvals, visual QA, revisions, source registration, and engine export. Do not trigger for unrelated general coding work.
---

# GUIF for Codex

Act as the natural-language front end for GUIF. The user talks about the desired game UI; you operate the framework internally. Do not make the user install GUIF, copy tokens, or type GUIF CLI commands.

## Runtime

Resolve `scripts/guif_codex.py` relative to this SKILL.md file, whose absolute path Codex provides when the Skill is loaded. When `PLUGIN_ROOT` is available, the equivalent canonical path is `$PLUGIN_ROOT/plugins/game-ui-framework/skills/game-ui-framework/scripts/guif_codex.py`.

Invoke the bundled bridge internally:

```bash
python <resolved-skill-directory>/scripts/guif_codex.py --workspace "$PWD" <command>
```

Treat all bridge invocations as internal implementation details. Summarize only the user-facing stage, design plan, source decision, approval decision, artifact result, visual findings, revision request, or export result.

The bridge automatically initializes a project and conversation on first use. It stores the Host credential, source-image library, and GUIF private records under `PLUGIN_DATA`, outside Project Git. Never print, quote, copy, or commit private credential, source, or claim files.

## Natural-language workflow

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

## Interaction rules

- The framework must propose source-registration choices and let the user decide unless the user explicitly created/derived a Theme with a reference or master image, which authorizes automatic private registration.
- Default tool identities are `chatgpt-image` and `chatgpt-vision`; pass a different real model or inspector ID when the configured Codex capability differs.
- `Legacy ProviderAdapter` is explicit compatibility only. Never silently route new production work through it.
- Do not expose Task IDs, etags, leases, claims, callback IDs, Bearer Tokens, source hashes, or private filesystem contents.
- Do not commit real Theme content, uploaded images, conversation records, prompts, or generated artifacts unless the user explicitly selects an artifact for Project Git.
- Public examples and tests must remain fictional.
- Preserve protected pixels and immutable lineage when GUIF marks them as protected.
- Metadata checks cannot claim composition, readability, Theme consistency, or usability. Those require a real semantic visual inspection.

Read `references/WORKFLOW.md` when command arguments, stage mapping, source contracts, or Host result contracts are needed.
