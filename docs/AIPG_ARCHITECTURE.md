# AIPG Architecture

## Positioning

AIPG is a local-first AI production workflow and governance framework. It
coordinates production without pretending that workflow metadata created real
media, semantic review, external Tool availability, or adoption evidence.

```text
AIPG Core
├─ intent and domain routing
├─ workflow runtime and checkpoints
├─ approvals and revision scopes
├─ Artifact lineage and protected sources
├─ Host and Tool capability routing
├─ deterministic and semantic review
├─ Candidate Change and adoption
└─ gated export and recovery

Domain Packs
├─ Framework Governance
└─ GUIF Visual Production
```

The Core understands domain-neutral concepts such as Workflow, Stage,
Artifact, Dependency, Constraint, Approval, Evidence, Revision, and Export.
Background layers, buttons, Theme, alpha, and visual composition belong to
GUIF.

## Routing

Theme is not an AIPG top-level state. A request is first classified by domain
and workflow. Each workflow then declares the context it requires.

```text
request
-> governance context
-> domain
-> workflow
-> required context
-> approval
-> real execution
-> review
-> export
```

## Workflow manifest v3

Schema v3 adds:

- `domain`;
- `requires`;
- `stages`;
- `creation_direction`;
- `constraint_policy`.

Schema v1 and v2 remain readable for compatibility.

## GUIF visual domain

GUIF retains existing game UI workflows and introduces
`master-guided-layer-creation`. The master image supplies style, layout
anchors, visual hierarchy, and intent. It is not a pixel-reconstruction target.

Each layer receives:

- the master and Theme references;
- the current composite;
- completed-layer lineage;
- future layer roles;
- hard production constraints;
- soft art direction;
- adaptive creative freedom;
- an output and review contract.

Production proceeds bottom to top. Each real layer is recomposed and visually
reviewed before the next one. Revising a layer preserves earlier protected
layers and invalidates downstream composites.
