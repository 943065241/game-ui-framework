# AIPG User Blueprint

This compact document preserves the stable plugin documentation contract while current implementation details remain in the canonical maintained documents.

- Current implementation: [PROJECT_STATUS.md](PROJECT_STATUS.md)
- Architecture: [AIPG_ARCHITECTURE.md](AIPG_ARCHITECTURE.md)
- Runtime behavior: [AIPG_WORKFLOW_RUNTIME.md](AIPG_WORKFLOW_RUNTIME.md)
- Future work: [../ROADMAP.md](../ROADMAP.md)

AIPG is the generic AI production runtime. GUIF is its visual-production Domain Pack and compatibility implementation.

## 5. Skill map

- `$aipg-framework` handles domain-neutral workflow, governance and Tool routing.
- `$game-ui-framework` handles GUIF visual production and compatibility workflows.
- `master-guided-layer-creation` remains a GUIF workflow identity where compatibility requires it.

## 6. Tool and capability map

Workflows depend on capabilities rather than provider identities.

```text
Workflow
→ CapabilityRequirement
→ ToolRegistry
→ ToolAdapter
→ Provider
```

Compatibility names used by the bundled plugin include `chatgpt-image`, `chatgpt-vision` and `dry-run`. Their presence in a contract does not claim that a real Provider is configured or available.

## 10. Version governance

- `VERSION` is the canonical development version.
- README files describe the current iteration.
- `PROJECT_STATUS.md` records current implementation truth.
- `ROADMAP.md` records future work only.
- `CHANGELOG.md` records completed history.

Historical release and iteration narratives are not maintained as separate status documents.
