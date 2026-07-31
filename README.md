# AIPG — AI Production & Governance Framework

**English** | [简体中文](README.zh-CN.md)

> Build governed AI production systems, not just prompts.

AIPG is a local-first framework for routing, executing, reviewing, revising,
and exporting AI production through explicit governance. GUIF is retained as
the game UI and visual-production domain.

ChatGPT / Codex is the default Host. Image generation, semantic vision, layout
tools, engines, and future production capabilities are replaceable Tool
contracts rather than hard-coded Core dependencies.

## Release status

Version `1.1.0-beta.1` is formally adopted and published. It establishes AIPG
as the top-level framework while retaining GUIF as the compatible visual domain.

- Python package: `aipg-framework==1.1.0b1`
- New import and CLI: `aipg`
- Compatibility import and CLI: `guif`
- Visual domain Skill: `$game-ui-framework`
- Framework Skill: `$aipg-framework`
- Workflow schemas v1 and v2 remain supported

Important documents:

- [Changelog](CHANGELOG.md)
- [AIPG architecture](docs/AIPG_ARCHITECTURE.md)
- [Detailed user blueprint and usage map](docs/AIPG_USER_BLUEPRINT.md)
- [GUIF-to-AIPG migration](docs/MIGRATING_GUIF_TO_AIPG.md)
- [Master-guided layer workflow](docs/MASTER_GUIDED_LAYER_WORKFLOW.md)
- [Release notes](docs/RELEASE_NOTES_AIPG_1_1_BETA1.md)
- [Existing GUIF product specification](docs/GUIF_PRODUCT_SPEC.md)
- [Candidate Change workflow](docs/IMPROVEMENT_WORKFLOW.md)
- [Support policy](SUPPORT.md)

## Architecture

```text
AIPG Core
├─ intent and domain routing
├─ workflow runtime and recovery
├─ approvals and revision scopes
├─ Artifact lineage and protected sources
├─ Host and Tool routing
├─ evidence and review
├─ Candidate Change and adoption
└─ gated export

Domain Packs
├─ Framework Governance
└─ GUIF Visual Production
```

AIPG Core does not need to understand buttons, image alpha, Theme, or visual
layers. These belong to GUIF. Future audio, text, code, video, and game-content
domains can register their own workflows, context, Artifacts, Tools, review
criteria, and exporters.

Theme is not a top-level AIPG prerequisite. AIPG first selects a domain and
workflow; that workflow declares the context it requires.

## Production and improvement loops

Production:

```text
request
-> domain and workflow
-> required context
-> production contract
-> approval
-> real Host/Tool execution
-> Artifact and lineage
-> deterministic and semantic review
-> revision when needed
-> gated export
```

Framework improvement:

```text
observed problem
-> diagnosis
-> candidate proposal
-> isolated candidate
-> real evidence
-> adoption decision
-> publication and refresh
-> regression
-> resume production
```

Candidate authorization does not authorize adoption, merge, publication, or
stable Tool-route changes. Metadata checks do not prove visual quality or
semantic correctness.

## GUIF Visual Production

GUIF remains the compatible visual domain and supports:

- effect-image generation and editing;
- private Theme and source registration;
- protected source lineage;
- semantic visual review;
- resource production and engine export;
- master-guided layer creation.

### Master-guided layer creation

The master effect image provides style, layout, hierarchy, and intent. It is
not a pixel-matching target.

```text
Theme and master
-> coarse semantic layer analysis
-> layer-plan approval
-> bottom-to-top creation
-> recomposition after every layer
-> semantic visual review
-> scoped layer revision
-> final approval
-> independent assets and manifest export
```

Hard constraints protect functional roles, layout anchors, asset boundaries,
required content, transparency, and output contracts. Shape details, materials,
texture, lighting, and decoration remain soft guidance. Every layer receives
low, medium, or high creative freedom.

## Workflow manifest v3

New domain workflows can declare:

```json
{
  "schema_version": 3,
  "id": "master-guided-layer-creation",
  "domain": "visual-production",
  "requires": ["theme", "master-reference"],
  "creation_direction": "bottom-to-top",
  "stages": [
    "master-approval",
    "layer-analysis",
    "layer-plan-approval",
    "progressive-layer-creation",
    "recomposition-review",
    "final-approval",
    "engine-export"
  ],
  "constraint_policy": {
    "master_role": "style-and-layout-guidance",
    "pixel_matching": false,
    "creative_freedom": "adaptive"
  }
}
```

## Development

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest -q
```

On macOS or Linux, use `.venv/bin/python`.

The repository includes pre-existing Windows-specific tests involving symlink
behavior and private temporary directories. Candidate validation should record
the stable baseline and compare candidate results rather than misattribute
environment failures.

## Privacy and assurance

Real Themes, prompts, source images, conversation records, credentials, private
paths, candidate evidence, and generated artifacts remain outside Framework
Git and Project Git by default. Public tests and examples use wholly fictional
fixtures.

AIPG does not fabricate pixels, Tool availability, semantic findings, candidate
results, or successful export. External Tool permissions, billing, credentials,
and data flow remain explicit.

## Compatibility

AIPG 1.x keeps the existing `guif` package, command, Skill, schemas, private
storage variables, Theme records, Source records, Artifact records, and
Candidate Change contracts. New framework-wide integrations should use AIPG
naming; visual integrations may continue to use GUIF.

## License

MIT.
