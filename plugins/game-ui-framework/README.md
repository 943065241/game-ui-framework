# GUIF for Codex

This skills-only Codex plugin turns GUIF into a natural-language game UI production and improvement workflow.

After one-time installation, a user can say:

> 用 GUIF 做一个 2340×1080 的中世纪港口横屏交易页，左侧聊天，中间行情，右侧盘口，底部只有做多、做空、撤单。

The same conversation can also identify a Skill, framework, workflow, or Tool problem and enter a private Candidate Change flow without silently bypassing the formal production controls.

## One-time installation

```bash
codex plugin marketplace add 943065241/game-ui-framework
```

Install **game-ui-framework** from the Codex Plugins interface, then start a new Codex session. The Skill can trigger automatically from a matching game UI request, or explicitly with `$game-ui-framework`.

## Candidate Changes

GUIF separates production Tasks from private Improvement Cases:

```text
problem detected
  -> proposal
  -> trial approval
  -> isolated candidate
  -> real result review
  -> adoption approval
  -> publication or scoped Tool-route application
  -> refresh and regression when required
```

Trial approval does not authorize adoption. A code or Skill candidate cannot be merged before the user reviews real candidate evidence and confirms adoption.

A supported Tool can be trialed with a Task-only override, leaving stable Project and Workspace routes unchanged. An unsupported Tool such as an unavailable Figma integration becomes Tool-integration work rather than a fake successful trial.

## No server deployment or separate GUIF install

This is a local skills-only plugin. It does not require an HTTPS service, custom GPT Action, or a separate `pip install`. The Marketplace installs the repository root so the plugin snapshot contains both the Skill bridge and the bundled `guif/` Python runtime.

“No deployment” means no separate server; it does not mean the repository code is available before the plugin is installed.

## Safety and privacy

- GUIF credentials, Themes, source images, Improvement Cases, candidate evidence, and development bundles live under Codex `PLUGIN_DATA`, outside Project Git.
- Natural-language requests and private records are passed through private files rather than shell arguments.
- Public fixtures and tests are fictional; real user images are not used as public regression assets.
- Real image and visual-inspection capabilities are required for production and candidate evidence.
- The plugin never fabricates image bytes, semantic findings, signatures, or attestations.
- Production and candidate work do not silently fall back to dry-run behavior.
- `chatgpt-image` and `chatgpt-vision` are replaceable truthful defaults.
- Stable Tool routing changes only after explicit adoption and only at the approved Task, Project, or Workspace scope.
- `Legacy ProviderAdapter` remains explicit compatibility only.
