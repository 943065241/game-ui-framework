# GUIF for Codex

This skills-only Codex plugin turns GUIF into a natural-language game UI workflow.

After one-time plugin installation, a user can say:

> 用 GUIF 做一个 2340×1080 的中世纪港口横屏交易页，左侧聊天，中间行情，右侧盘口，底部只有做多、做空、撤单。

Codex then handles GUIF initialization, private Theme binding, requirement submission, approval gates, real image/vision Host handoff, revisions, and gated export internally.

## One-time installation

Add this repository as a Codex plugin marketplace:

```bash
codex plugin marketplace add 943065241/game-ui-framework
```

Install **game-ui-framework** from the Codex Plugins interface, then start a new Codex session. The Skill can trigger automatically from a matching game UI request, or explicitly with `$game-ui-framework`.

## No server deployment

This is a local skills-only plugin. It does not require an HTTPS service or custom GPT Action. Codex executes the bundled GUIF bridge inside the checked-out plugin snapshot.

The framework code still runs locally as part of the plugin. “No deployment” means no separate server; it does not mean the repository code is magically available before the plugin is installed.

## Safety and privacy

- GUIF credentials and private records live under Codex `PLUGIN_DATA`, outside Project Git.
- Natural-language requests and Theme JSON are passed through private files rather than shell arguments.
- Real image and visual-inspection capabilities are required for production completion.
- The plugin never fabricates image bytes, semantic findings, signatures, or attestations.
- Production does not silently fall back to dry-run behavior.
- `chatgpt-image` and `chatgpt-vision` are replaceable truthful defaults.
- `Legacy ProviderAdapter` remains explicit compatibility only.
