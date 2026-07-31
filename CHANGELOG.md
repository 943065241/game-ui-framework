# Changelog

All notable framework changes are recorded here. Candidate entries describe
unreleased work and do not imply adoption or publication.

## 1.1.0-beta.1 — 2026-07-31

### Added

- AIPG (AI Production & Governance Framework) as the domain-neutral top-level
  framework identity.
- A registered Domain Pack model with `framework-governance` and
  `visual-production` built-ins.
- GUIF as the compatible game UI and visual-production domain.
- Workflow manifest schema v3 with domain, required context, stages, creation
  direction, and constraint policy.
- `master-guided-layer-creation`, where a master effect image guides style and
  layout without requiring pixel matching.
- A bottom-to-top layered composition state model, per-layer creative freedom,
  scoped downstream invalidation, recomposition approval, and export manifest.
- The `aipg` Python facade and CLI entry point.

### Changed

- Plugin display identity and package metadata now use AIPG naming.
- The existing `guif` package, CLI command, Skill, schemas, and environment
  variables remain compatibility surfaces.

### Documentation

- Added AIPG architecture, GUIF migration, master-guided workflow, and candidate
  release notes.
- Added a comprehensive user blueprint covering Skills, Tools, Domain Packs,
  Workflows, Artifacts, approvals, privacy, version governance, publication,
  recovery, extension contracts, end-to-end journeys, and operational
  checklists.
- Updated README files, plugin metadata, version checks, and contributor name.

### Validation

- Added wholly fictional domain and layered-workflow regression fixtures.
- No user Theme, image, conversation, credential, or private evidence is part
  of the public candidate.
