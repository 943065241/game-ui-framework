# Codex plugin integration

GUIF includes a skills-only Codex plugin, a root plugin manifest, and a repository marketplace.

## Intended user experience

After one-time installation, the user works only through natural language in Codex:

> 用 GUIF 设计一个虚构的中世纪港口交易页。横屏，左侧聊天，中间行情，右侧盘口，底部只保留做多、做空和撤单。

The Skill automatically performs framework bootstrap, private Theme handling, source-image decisions, requirement submission, contextual approval, Host work handoff, real visual inspection, controlled Revision, recovery, and gated export.

The user is not expected to run `guif-ready` or `guif-conversation`, manage a Bearer Token, or handle Task IDs, etags, leases, claims, and callbacks.

## Architecture

```text
natural-language Codex conversation
  -> GUIF Codex Skill
  -> private bundled bridge
  -> bundled GUIF Python runtime
  -> source-aware ConversationWorkflowService
  -> private Source Library / registered Source Artifact
  -> real Codex image / vision capability
  -> authenticated GUIF Host Work completion
  -> Artifact / semantic review / Revision / gated export
```

This is not an internet service and does not require an HTTPS deployment. The marketplace installs the repository root as the plugin snapshot, so the Skill and the `guif/` runtime are present together. No separate GUIF package installation is required from the user.

## Protected source-image workflow

An image-editing request cannot execute until its source image is registered and immutably bound. When the referenced image came from the current conversation, an upload, or another external file, GUIF now enters:

```text
source-import-required
```

The normal user view explains the reason and offers four explicit decisions:

```text
import-source-and-continue
import-as-theme-reference
import-as-master-reference
continue-outside-guif
```

GUIF never silently chooses on the user's behalf. The first three choices copy the real image into the private Source Library, verify its SHA-256 identity, register a task-bound Source Artifact, rebuild the image-editing contract, and preserve an immutable attachment for the Host. The fourth choice records that subsequent ordinary editing is outside the formal GUIF production chain.

When the user explicitly creates or derives a Theme with a master/reference image, that instruction authorizes automatic private registration. The Theme stores a private source reference, not a Project Git path or raw image content. Later edit requests using that Theme can reuse the registered source without asking the user to import it again.

## Plugin files

```text
.codex-plugin/plugin.json
.agents/plugins/marketplace.json
guif/
plugins/game-ui-framework/
  README.md
  skills/game-ui-framework/
    SKILL.md
    references/WORKFLOW.md
    scripts/guif_codex.py
```

The Marketplace local source is the repository root (`.`). The root Manifest points Codex to `./plugins/game-ui-framework/skills/`. A subdirectory-only plugin source is intentionally not used because it would omit the bundled `guif/` runtime.

## Private data boundary

The bridge uses Codex `PLUGIN_DATA` as its private root and configures GUIF `GUIF_DATA_HOME` below that root. Per-workspace context, Host credentials, Source Library images, Theme records, Conversation records, claims, retrieved attachments, prompts, results, and reports therefore stay outside Project Git.

`GUIF_CODEX_PLUGIN_DATA` is an explicit managed-runtime and test override. It does not change the privacy requirement.

A newly issued GUIF Bearer Token is persisted with private file permissions and omitted from bridge output. Natural-language requests, Theme JSON, source images, and decision comments are read from private files rather than shell arguments. Public views omit private paths and source hashes.

## Real Host contract

The bridge prepares actual GUIF Host Work and hands Codex the work contract plus immutable attachment paths. Codex must then invoke a genuine configured image or vision capability and submit the resulting file or structured inspection result.

An imported source used for editing must produce `image-editing` Host Work with the registered source as an immutable attachment. The bridge deliberately provides no simulation completion command. Missing image or vision capability is a blocking configuration condition, not permission to invent output.

Default truthful identities are `chatgpt-image` and `chatgpt-vision`; callers can replace them with the actual configured model/inspector identity. The legacy `ProviderAdapter` remains an explicit compatibility path and is not silently selected by the plugin.

## Installation

```bash
codex plugin marketplace add 943065241/game-ui-framework
```

Install `game-ui-framework` from the Codex Plugins interface and start a new session. The Skill may be triggered implicitly by a matching request or explicitly with `$game-ui-framework`.

## Validation

`tests/test_codex_plugin.py` verifies:

- root Marketplace source and Manifest packaging;
- the installed plugin source contains both `guif/` and the Skill bridge;
- bridge syntax;
- private first-use bootstrap without Token disclosure;
- no Host Token or imported source image in Project Git workspace files;
- normal generation, Artifact registration, semantic visual completion, and `ready-to-export`;
- unregistered edit requests enter `source-import-required` with all four user decisions;
- importing a conversation image produces protected `image-editing` Host Work with an immutable attachment;
- Theme master images are auto-registered and reused by later edit requests;
- explicit exit from the formal GUIF editing chain is recorded without mislabeling the result.
