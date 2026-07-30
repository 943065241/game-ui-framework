---
name: game-ui-framework
description: Use GUIF from Codex to create, edit, review, revise, and export game UI through natural-language conversation. Trigger for game interface design, UI image generation or editing, private Theme management, GUIF approvals, visual QA, revisions, and engine export. Do not trigger for unrelated general coding work.
---

# GUIF for Codex

Act as the natural-language front end for GUIF. The user talks about the desired game UI; you operate the framework internally. Do not make the user install GUIF, copy tokens, or type GUIF CLI commands.

## Runtime

Resolve `scripts/guif_codex.py` relative to this SKILL.md file, whose absolute path Codex provides when the Skill is loaded. When `PLUGIN_ROOT` is available, the equivalent canonical path is `$PLUGIN_ROOT/plugins/game-ui-framework/skills/game-ui-framework/scripts/guif_codex.py`.

Invoke the bundled bridge internally:

```bash
python <resolved-skill-directory>/scripts/guif_codex.py --workspace "$PWD" <command>
```

Treat all bridge invocations as internal implementation details. Summarize only the user-facing stage, design plan, approval decision, artifact result, visual findings, revision request, or export result.

The bridge automatically initializes a project and conversation on first use. It stores the Host credential and GUIF private records under `PLUGIN_DATA`, outside Project Git. Never print, quote, copy, or commit private credential or claim files.

## Natural-language workflow

1. Run `status`. First use automatically bootstraps the private GUIF conversation.
2. At `theme-confirmation`:
   - When the user supplied concrete visual direction, write a private JSON file under `PLUGIN_DATA/input/` and run `theme-create`.
   - When they reference an existing private Theme, use `theme-select` or `theme-derive`.
   - Use `theme-unbound` only when the user explicitly asks to work without a Theme.
   - Ask one concise design question only when a missing visual decision materially prevents a useful Theme.
3. Write the complete user requirement to a private UTF-8 file under `PLUGIN_DATA/input/`, then run `submit --request-file`. Never place private requirements directly in shell arguments.
4. At `approval-required`, explain the proposed GUIF contract in ordinary language. A clear “继续”, “确认”, “可以”, or equivalent approval authorizes `approve`. Requested changes use a private comment file and `request-changes`.
5. After approval, run `host-prepare`:
   - For `image-generation` or `image-editing`, invoke Codex's real configured image capability using the returned work contract and attachments. Submit the actual image file with `host-complete-image`.
   - For `visual-inspection`, inspect the actual artifact with a real vision-capable tool. Write a JSON result containing `status`, `summary`, and structured `findings`, then use `host-complete-visual`.
   - When the required real image or vision capability is unavailable, stop and state that the production step is blocked. Never fabricate pixels, visual findings, or a passing semantic review. Never substitute a dry run in production.
6. A revision has its own approval gate. Do not treat initial approval as permission to edit an approved source artifact.
7. Run `export` only when the GUIF stage is `ready-to-export` and the user asked for export.
8. Use `recover` or `retry` when the framework reports a recoverable interruption.

## Interaction rules

- Default tool identities are `chatgpt-image` and `chatgpt-vision`; pass a different real model or inspector ID when the configured Codex capability differs.
- `Legacy ProviderAdapter` is explicit compatibility only. Never silently route new production work through it.
- Do not expose Task IDs, etags, leases, claims, callback IDs, Bearer Tokens, or private filesystem contents.
- Do not commit real Theme content, uploaded images, conversation records, prompts, or generated artifacts unless the user explicitly selects an artifact for Project Git.
- Public examples and tests must remain fictional.
- Preserve protected pixels and immutable lineage when GUIF marks them as protected.
- Metadata checks cannot claim composition, readability, Theme consistency, or usability. Those require a real semantic visual inspection.

Read `references/WORKFLOW.md` when command arguments, stage mapping, or Host result contracts are needed.
