# AIPG — AI Production & Governance Framework

**English** | [简体中文](README.zh-CN.md)

> Build governed AI production systems, not just prompts.

AIPG is a local-first framework for routing, executing, reviewing, revising,
and exporting AI production through explicit governance. GUIF remains the game
UI and visual-production Domain Pack.

ChatGPT / Codex is the default Host. Image generation, semantic vision, layout
tools, engines, and future production capabilities are replaceable Tool
contracts rather than hard-coded dependencies.

## Current iteration

- Development version: `1.1.0-dev.6`
- Last updated: `2026-07-31`
- Branch policy: direct commits to `main`
- Latest milestone: recoverable Workflow Runtime and Capability execution

Completed in the current development line:

- AIPG-owned Domain Registry
- executable Workflow lifecycle and Event Bus
- automatic Workflow Graph traversal
- nested Subworkflow call-stack execution
- CheckpointStore persistence boundary
- deterministic checkpoint restore and resume
- Capability → ToolAdapter → Provider execution

Next planned milestones:

- scheduler and durable execution queue
- Artifact lifecycle runtime and dependency graph
- GUIF Workflow migration onto the AIPG Runtime

Every direct iteration on `main` must increment this development version and
update this section, so repository visitors can identify new work immediately.

## Release status

Version `1.1.0-beta.1` is published. The current unreleased iteration directly
refactors the existing AIPG implementation; it does not create a second Core or
replace GUIF wholesale.

- Python package: `aipg-framework==1.1.0b1`
- Framework import and CLI: `aipg`
- Compatibility import and CLI: `guif`
- Visual domain Skill: `$game-ui-framework`
- Framework Skill: `$aipg-framework`
- Workflow schemas v1, v2, and v3 remain readable

Important documents:

- [Changelog](CHANGELOG.md)
- [AIPG architecture](docs/AIPG_ARCHITECTURE.md)
- [Current AIPG/GUIF refactor](docs/AIPG_CORE_GUIF_ITERATION.md)
- [Detailed user blueprint](docs/AIPG_USER_BLUEPRINT.md)
- [GUIF-to-AIPG migration](docs/MIGRATING_GUIF_TO_AIPG.md)
- [Master-guided layer workflow](docs/MASTER_GUIDED_LAYER_WORKFLOW.md)
- [Release notes](docs/RELEASE_NOTES_AIPG_1_1_BETA1.md)
- [GUIF product specification](docs/GUIF_PRODUCT_SPEC.md)

## Architecture

```text
AIPG
├─ runtime.py          workflow graph, state, stack, validation
├─ engine.py           lifecycle and graph execution
├─ recovery.py         checkpoint restore and deterministic resume
├─ checkpoints.py      persistence-neutral checkpoint boundary
├─ events.py           runtime event delivery
├─ context.py          project and standalone lifecycle
├─ artifacts.py        Artifact identity, status, ancestry, lineage
├─ capabilities.py     capability routing and Tool adapter execution
└─ domains/
   └─ visual.py        GUIF Visual Production registration

GUIF compatibility implementation
├─ existing workflows and CLIs
├─ Theme and visual context
├─ visual Artifact semantics
├─ visual review and exporters
└─ adapters for external visual Tools
```

The current refactor promotes generic responsibilities from the working GUIF
implementation into focused AIPG modules. Existing `guif` APIs remain available
while orchestration, Artifact, context, and capability contracts move upward
incrementally.

AIPG does not need to understand buttons, image alpha, Theme, masks, or visual
layers. Those concepts belong to GUIF. Future code, document, video, audio, and
game-content domains can reuse the same runtime contracts.

## Runtime model

Workflow definitions use a behavior-tree-like graph. Runtime execution uses a
hierarchical state machine with a finite call stack.

```text
Workflow
→ Subworkflow
→ Stage or control node
→ Action
→ Tool invocation
```

Parents wait while child workflows execute, then resume with declared child
results. Workflow status and Artifact status are independent.

## Context modes

- `project`: long-lived production context. GUIF commonly binds this to Theme,
  master references, approved assets, and export targets.
- `standalone`: finite one-off work such as localized repaint, image editing,
  image layering, or effect-image generation.

Figma is a Tool and structured design environment, not another lifecycle mode.

## Capability routing

Workflows request stable capabilities instead of providers.

```text
CapabilityRequirement
→ ToolRegistry
→ compatible ToolAdapter
→ provider execution
```

GUIF can register adapters for image generation, editing, segmentation, OCR,
vision, Figma, composition, visual diff, and engine export. AIPG does not claim
Tool availability until credentials, permissions, billing, and data flow are
configured.

## Development

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest -q
```

On macOS or Linux, use `.venv/bin/python`.

## Privacy and assurance

Real Themes, prompts, source images, conversation records, credentials, private
paths, candidate evidence, and generated artifacts remain outside Framework Git
and Project Git by default. Public tests and examples use fictional fixtures.

AIPG does not fabricate pixels, Tool availability, semantic findings, candidate
results, or successful export.

## Compatibility

AIPG 1.x keeps the existing `guif` package, command, Skill, schemas, private
storage variables, Theme records, Source records, Artifact records, and
Candidate Change contracts. New framework-wide integrations should use AIPG
naming; visual integrations may continue to use GUIF.

## License

MIT.
