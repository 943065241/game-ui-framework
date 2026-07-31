# AIPG — AI Production & Governance Framework

**English** | [简体中文](README.zh-CN.md)

> Build governed AI production systems, not just prompts.

AIPG is a generic AI production runtime. GUIF is its visual-production Domain Pack and compatibility implementation.

## Project status

- Development version: [`1.1.0-dev.10`](VERSION)
- Published package: `aipg-framework==1.1.0b1`
- Branch policy: direct commits to `main`
- Last validated baseline: Python 3.10, 3.11 and 3.12 CI passed for `1.1.0-dev.8`
- Current focus: repository consolidation and a single documentation source of truth

Canonical project documents:

- [Current implementation status](docs/PROJECT_STATUS.md)
- [Roadmap](ROADMAP.md)
- [Architecture](docs/AIPG_ARCHITECTURE.md)
- [Workflow Runtime](docs/AIPG_WORKFLOW_RUNTIME.md)
- [Changelog](CHANGELOG.md)
- [GUIF migration](docs/MIGRATING_GUIF_TO_AIPG.md)

## Architecture

```text
AIPG
├─ runtime.py          Workflow graph, state, stack and validation
├─ engine.py           lifecycle and graph execution
├─ recovery.py         checkpoint restoration and capability execution
├─ checkpoints.py      persistence-neutral checkpoint boundary
├─ events.py           runtime event delivery
├─ capabilities.py     Tool discovery and governed execution
├─ artifacts.py        generic Artifact registry and lineage
├─ context.py          project and standalone context modes
└─ domains/            Domain Pack model and registrations

GUIF
└─ visual-production semantics, workflows, review, exporters and compatibility APIs
```

## Current capabilities

- Hierarchical Workflow execution with nested Subworkflows
- Sequence, Selector, deterministic Parallel, Condition, Action, Approval and Review nodes
- Event Bus and lifecycle transitions
- Checkpoint persistence boundary, restore and resumable node cursors
- Capability-based Tool discovery and provider execution
- Tool health, configuration validation, timeout, retry and fallback governance
- Generic Artifact lineage and Domain Pack registration

The full capability matrix and explicit limitations are maintained in [PROJECT_STATUS.md](docs/PROJECT_STATUS.md).

## Tool routing

```text
Workflow
→ CapabilityRequirement
→ ToolRegistry
→ ToolAdapter
→ Provider
```

`resolve()` performs backward-compatible capability discovery. Execution-time governance applies health, configuration, timeout, retry and fallback policies.

## Development

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"
.venv/Scripts/python -m pytest -q
```

On macOS or Linux, use `.venv/bin/python`.

## Compatibility

AIPG 1.x preserves the existing `guif` package, commands, Skills, schemas and records while generic responsibilities migrate into `aipg`.

## Documentation policy

- `VERSION`: canonical development version
- README: short public overview
- `PROJECT_STATUS.md`: current implementation truth
- `ROADMAP.md`: future work only
- `CHANGELOG.md`: completed history
- architecture and runtime guides: durable design and behavior

Every direct iteration on `main` must update `VERSION`, README status and CHANGELOG when applicable.

## License

MIT.
