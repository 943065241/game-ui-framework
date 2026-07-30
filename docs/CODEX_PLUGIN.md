# Codex plugin integration

GUIF includes a skills-only Codex plugin, a root plugin manifest, and a repository marketplace.

## Intended user experience

After one-time installation, the user works only through natural language in Codex:

> 用 GUIF 设计一个虚构的中世纪港口交易页。横屏，左侧聊天，中间行情，右侧盘口，底部只保留做多、做空和撤单。

The Skill performs framework bootstrap, private Theme and source handling, requirement submission, approval, real Host work, semantic review, controlled Revision, Candidate Changes, Tool trials, recovery, and gated export.

The user is not expected to manage GUIF CLI commands, Bearer Tokens, Task IDs, etags, leases, claims, callbacks, or private filesystem paths.

## Architecture

```text
natural-language Codex conversation
  -> GUIF Codex Skill
  -> private bundled bridge
  -> bundled GUIF Python runtime
  -> improvement-aware ConversationWorkflowService
       -> production Task
       -> private Improvement Case
  -> private Theme / Source / Candidate Evidence stores
  -> real Codex image / vision or another truthful Tool
  -> authenticated Host Work completion
  -> Artifact / semantic review / Revision / gated export
```

This is not an internet service and does not require an HTTPS deployment. The marketplace installs the repository root as the plugin snapshot, so the Skill and the `guif/` runtime are present together. No separate GUIF package installation is required.

## Protected source-image workflow

An image-editing request cannot execute until its source is registered and immutably bound. A conversation image, upload, or external file enters `source-import-required` and offers:

```text
import-source-and-continue
import-as-theme-reference
import-as-master-reference
continue-outside-guif
```

The first three choices copy the real image into the private Source Library, verify identity, register a task-bound Source Artifact, rebuild the edit contract, and preserve an immutable Host attachment. The fourth explicitly leaves the formal GUIF chain.

An explicit Theme or master-image instruction authorizes automatic private registration. The Theme stores a private source reference rather than raw bytes or a Project Git path.

## Candidate Change workflow

A Skill, framework, workflow, Theme-policy, provider-routing, or Tool problem creates a private Improvement Case instead of mutating the production Task.

```text
production checkpoint paused
  -> diagnosis and proposal
  -> trial approval
  -> isolated candidate
  -> real result review
  -> adoption approval
  -> publication or scoped Tool-route change
  -> plugin refresh when required
  -> formal regression
  -> production resume
```

Trial approval and adoption approval are separate. Trial approval never authorizes merge, publication, plugin replacement, or stable Tool routing. Adoption is unavailable until real candidate evidence has been recorded.

Code and Skill candidates are built in the GUIF source repository from a private sanitized development bundle. They are not merged before user adoption. Public tests use wholly fictional fixtures, never the user's real image.

## Tool trials

A requested Tool is first evaluated through Tool discovery.

- A registered, available, healthy Tool can run as an isolated candidate Task using a Task-only override. Stable Project and Workspace routing stays unchanged until adoption.
- An unknown, unavailable, unhealthy, installable-only, or unregistered Tool becomes `tool-integration-change`. GUIF does not pretend it can execute.

Tool adoption scope is explicit: `task`, `project`, or `workspace`. Capability routing remains granular: for example, Figma can handle structured editable layout without automatically replacing raster generation, pixel editing, semantic vision, or export.

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

The Marketplace local source is the repository root (`.`). A subdirectory-only source is intentionally avoided because it would omit the bundled `guif/` runtime.

## Private data boundary

The bridge uses Codex `PLUGIN_DATA` as its private root and configures `GUIF_DATA_HOME` below it. Host credentials, Theme records, Source Library images, Conversation records, Improvement Cases, candidate evidence, development bundles, claims, attachments, prompts, and reports stay outside Project Git.

Public views omit Bearer Tokens, claims, Task IDs, private paths, source hashes, and evidence hashes. Inputs are read from private files rather than shell arguments.

## Real Host contract

The bridge prepares actual GUIF Host Work and hands Codex the work contract plus immutable attachment paths. Codex must invoke a genuine configured image or vision capability and submit the actual result.

There is no simulation completion command. Missing capabilities block production. Metadata cannot become a semantic visual pass. Default truthful identities are `chatgpt-image` and `chatgpt-vision`; they remain replaceable. Legacy `ProviderAdapter` is explicit compatibility only.

## Installation and updates

```bash
codex plugin marketplace add 943065241/game-ui-framework
```

Install `game-ui-framework` from the Codex Plugins interface and start a new session. After a published GUIF update, refresh **Game UI Framework** in `/plugins` and start another new session. The old session must not claim a hot reload.

## Validation

`tests/test_codex_plugin.py` and `tests/test_improvement_workflow.py` cover:

- bundled plugin and Runtime packaging;
- private bootstrap without secret disclosure;
- source registration and Theme/master reuse;
- real image and semantic Host completion;
- private Improvement Case persistence;
- independent trial and adoption gates;
- candidate evidence privacy;
- code/Skill publication, plugin-version refresh, regression, and resume;
- supported Tool trial isolation and scoped adoption;
- unsupported Tool conversion to Tool integration work;
- prohibition on stable mutation before adoption.
