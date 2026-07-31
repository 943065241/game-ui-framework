# AIPG Domain Registry Migration

## Goal

Make AIPG the single owner of Domain Pack definitions and workflow-to-domain routing while preserving the existing GUIF API.

## Before

`guif.domains` defined its own `DomainPack`, built-in domain dictionary, lookup helpers, and workflow ownership rules. AIPG separately defined `DomainPackDefinition` and the GUIF visual domain. This duplicated framework-level state and allowed the two registries to drift.

## After

```text
aipg.domains
├── model.py        DomainPackDefinition
├── registry.py     DomainRegistry and built-ins
├── governance.py   Framework Governance Domain Pack
└── visual.py       GUIF Visual Production Domain Pack

 guif.domains
└── compatibility aliases and delegated helpers
```

The authoritative registry now lives in AIPG. GUIF imports and re-exports it for compatibility.

## Compatibility

The following GUIF surfaces remain available:

- `guif.domains.DomainPack`;
- `guif.domains.BUILTIN_DOMAIN_PACKS`;
- `guif.domains.get_domain_pack`;
- `guif.domains.list_domain_packs`;
- `guif.domains.domain_for_workflow`.

`DomainPack` is now an alias of `aipg.domains.DomainPackDefinition`. The serialized representation retains the existing keys and adds capability identifiers under schema version 2.

## Next migration targets

1. Move generic workflow manifest routing out of GUIF.
2. Connect existing Artifact persistence to `aipg.artifacts` without changing storage records.
3. Move generic approval and review orchestration into focused AIPG modules.
4. Keep visual review criteria, Theme semantics, image workflows, and exporters in GUIF.
