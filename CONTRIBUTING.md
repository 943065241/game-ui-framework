# Contributing

AIPG is currently developed through direct commits to `main`. Keep every change small, testable and easy to review.

## Required checks

Before treating a commit as a stable development point:

1. Run the test suite.
2. Keep public API changes covered by tests.
3. Confirm compatibility behavior for existing `guif` imports and commands.
4. Do not claim Tool or Provider availability without valid configuration and health checks.

## Version and documentation policy

`VERSION` is the canonical development version.

For each development iteration:

- update `VERSION`;
- update the version and current focus in both README files;
- add completed work to `CHANGELOG.md`;
- update `docs/PROJECT_STATUS.md` when implementation truth changes;
- update `ROADMAP.md` only for future priorities.

Do not create permanent iteration-specific status or audit documents. Merge durable conclusions into the canonical documents instead.

## Architecture boundaries

- AIPG owns domain-neutral runtime, Artifact, Capability, Tool, context and Domain Pack contracts.
- GUIF owns visual-production semantics, visual workflows, review, exporters and compatibility APIs.
- Workflows depend on capabilities, not Provider identities.
- Mature external tools should be integrated through adapters rather than reimplemented.

## Change discipline

- Avoid unrelated refactors in feature commits.
- Preserve schema and compatibility contracts unless a migration path and regression tests are included.
- Keep `Parallel` documentation explicit that execution is currently deterministic and ordered, not concurrent.
- Treat `InMemoryCheckpointStore` as non-durable.
- Keep secrets, credentials, private assets and real production evidence out of the repository.

## Commit messages

Use focused messages such as:

```text
runtime: add durable checkpoint adapter contract
tools: add provider health validation
docs: synchronize workflow runtime behavior
tests: cover restored node skipping
```
