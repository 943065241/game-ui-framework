# Codex plugin integration

GUIF includes a skills-only Codex plugin under `plugins/game-ui-framework` and a repository marketplace at `.agents/plugins/marketplace.json`.

## Intended user experience

After one-time installation, the user works only through natural language in Codex:

> 用 GUIF 设计一个虚构的中世纪港口交易页。横屏，左侧聊天，中间行情，右侧盘口，底部只保留做多、做空和撤单。

The Skill automatically performs framework bootstrap, private Theme handling, requirement submission, contextual approval, Host work handoff, real visual inspection, controlled Revision, recovery, and gated export.

The user is not expected to run `guif-ready` or `guif-conversation`, manage a Bearer Token, or handle Task IDs, etags, leases, claims, and callbacks.

## Architecture

```text
natural-language Codex conversation
  -> GUIF Codex Skill
  -> private bundled bridge
  -> ConversationWorkflowService
  -> real Codex image / vision capability
  -> authenticated GUIF Host Work completion
  -> Artifact / semantic review / Revision / gated export
```

This is not an internet service and does not require an HTTPS deployment. The plugin executes the bundled Python framework locally in the Codex environment.

## Plugin files

```text
.agents/plugins/marketplace.json
plugins/game-ui-framework/
  .codex-plugin/plugin.json
  README.md
  skills/game-ui-framework/
    SKILL.md
    references/WORKFLOW.md
    scripts/guif_codex.py
```

## Private data boundary

The bridge uses Codex `PLUGIN_DATA` as its private root and configures GUIF `GUIF_DATA_HOME` below that root. Per-workspace context, Host credentials, Theme records, Conversation records, claims, retrieved attachments, prompts, results, and reports therefore stay outside Project Git.

`GUIF_CODEX_PLUGIN_DATA` is an explicit managed-runtime and test override. It does not change the privacy requirement.

A newly issued GUIF Bearer Token is persisted with private file permissions and omitted from bridge output. Natural-language requests, Theme JSON, and decision comments are read from private files rather than shell arguments.

## Real Host contract

The bridge prepares actual GUIF Host Work and hands Codex the work contract plus immutable attachment paths. Codex must then invoke a genuine configured image or vision capability and submit the resulting file or structured inspection result.

The bridge deliberately provides no simulation completion command. Missing image or vision capability is a blocking configuration condition, not permission to invent output.

Default truthful identities are `chatgpt-image` and `chatgpt-vision`; callers can replace them with the actual configured model/inspector identity. The legacy `ProviderAdapter` remains an explicit compatibility path and is not silently selected by the plugin.

## Installation

```bash
codex plugin marketplace add 943065241/game-ui-framework
```

Install `game-ui-framework` from the Codex Plugins interface and start a new session. The Skill may be triggered implicitly by a matching request or explicitly with `$game-ui-framework`.

## Validation

`tests/test_codex_plugin.py` verifies:

- marketplace, plugin manifest, and Skill discovery contracts;
- bridge syntax;
- private first-use bootstrap without Token disclosure;
- no Host Token in Project Git workspace files;
- natural-language request submission and approval;
- creation of real image Host work without a fake completion;
- safe abort and lease release for an unfinished Host session.
