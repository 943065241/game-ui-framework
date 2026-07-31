# AIPG User Blueprint

> A detailed usage map for AIPG â€” AI Production & Governance Framework  
> Document version: `1.1.0-beta.1-candidate.2`  
> Applies to: AIPG Core, GUIF Visual Production, Codex Skills, Host/Tool
> routing, Artifact governance, versioning, publication, recovery, and export

## 1. How to read this blueprint

This document is for four audiences:

| Audience | Start here | Primary concern |
| --- | --- | --- |
| Production user | Sections 2, 3, 11 | What to ask for and when approval is needed |
| Art or UI user | Sections 5, 8, 11.2â€“11.4 | Theme, master image, layers, visual review, export |
| Project owner | Sections 6, 7, 9, 10 | Tools, privacy, evidence, recovery, release governance |
| Framework developer | Sections 4, 6, 9, 12, 13 | Domain Packs, Workflow v3, adapters, compatibility |

The name is **AIPG**, not AIGP:

- **AIPG**: the domain-neutral AI Production & Governance Framework.
- **GUIF**: the game UI and visual-production domain inside AIPG.

## 2. The complete map

```mermaid
flowchart TD
    U["User intent"] --> H["Codex / ChatGPT Host"]
    H --> S{"Skill routing"}
    S -->|Framework-wide| AS["$aipg-framework"]
    S -->|Game UI / visual| GS["$game-ui-framework"]

    AS --> R["AIPG domain and workflow router"]
    GS --> VD["GUIF Visual Production domain"]
    R --> D{"Registered Domain Pack"}
    D --> FG["Framework Governance"]
    D --> VD
    D --> FD["Future domains: audio, text, code, video, game content"]

    FG --> CW["Candidate Change workflow"]
    VD --> W{"Visual workflow"}
    W --> UI["UI production"]
    W --> EI["Effect image"]
    W --> ED["Image editing"]
    W --> MG["Master-guided layer creation"]
    W --> RP["Resource production"]
    W --> QA["Quality assurance"]

    UI --> C["Required context"]
    EI --> C
    ED --> C
    MG --> C
    RP --> C
    C --> P["Production contract"]
    P --> A{"Approval gate"}
    A -->|Approved| TR["Tool resolution"]
    A -->|Changes requested| P
    A -->|Rejected| X["Stop without production mutation"]

    TR --> TI["chatgpt-image"]
    TR --> DR["dry-run: contract testing only"]
    TR --> IT["Registered external Tool Adapter"]
    TI --> AR["Real Artifact registration"]
    IT --> AR
    DR --> SR["Simulation receipt; never a visual result"]

    AR --> MR["Metadata review"]
    MR --> VR["Semantic visual review via chatgpt-vision or registered inspector"]
    VR -->|Passed| EG["Export gate"]
    VR -->|Findings| RV["Scoped revision + new approval"]
    RV --> TR
    EG --> EA["Engine Adapter: generic / Unity / Godot / Unreal"]
    EA --> OUT["Exported assets + manifest + provenance"]

    CW --> CP["Candidate proposal"]
    CP --> CT["Isolated candidate"]
    CT --> CE["Real candidate evidence"]
    CE --> AD{"Adoption decision"}
    AD -->|Adopt| PUB["PR, CI, merge, release"]
    AD -->|Adjust| CT
    AD -->|Reject| ST["Stable version retained"]
    PUB --> REF["Plugin refresh + new Host session"]
    REF --> REG["Formal regression"]
    REG --> RES["Resume paused production"]
```

The map has three non-negotiable boundaries:

1. A Skill decides and governs work; it does not fabricate Tool output.
2. A Tool creates or inspects the real result; metadata alone cannot prove
   semantic quality.
3. A candidate cannot become stable merely because code exists; publication,
   refresh, and regression remain separate states.

## 3. The user-facing entry map

Users normally describe the desired outcome in natural language. They should
not need to manage Task IDs, leases, callback IDs, private paths, credentials,
or low-level runtime commands.

```mermaid
flowchart LR
    Q["What do you want produced?"] --> V{"Primarily visual?"}
    V -->|No| G["Use $aipg-framework"]
    V -->|Yes| UI{"Game UI or visual asset?"}
    UI -->|Yes| GU["Use $game-ui-framework"]
    UI -->|No / uncertain| G

    GU --> SRC{"Existing protected source?"}
    SRC -->|Edit it| EDIT["Image-editing workflow"]
    SRC -->|No| MASTER{"Need reusable layers?"}
    MASTER -->|No| SINGLE["Effect-image / UI-production workflow"]
    MASTER -->|Yes| LAYER["Master-guided-layer-creation"]

    G --> CH{"Changing framework or Tool?"}
    CH -->|No| ROUTE["Select registered domain + workflow"]
    CH -->|Yes| CAND["Candidate Change governance"]
```

### Recommended natural-language entry prompts

| Intent | Example user request | Expected routing |
| --- | --- | --- |
| General production | â€œUse AIPG to plan and govern this production task.â€ | `$aipg-framework` |
| Game UI creation | â€œUse GUIF to design a sci-fi shop screen.â€ | `$game-ui-framework` |
| Existing-image edit | â€œUse GUIF to edit this registered source without changing the character.â€ | GUIF image editing |
| Layered creation | â€œUse the master as style/layout guidance and create assets bottom to top.â€ | Master-guided layer creation |
| Tool integration | â€œIntegrate a layout Tool for editable UI structure.â€ | AIPG Tool Integration Candidate |
| Framework evolution | â€œTurn this workflow into a reusable domain workflow.â€ | AIPG Candidate Change |
| Export | â€œExport the approved assets for Unity.â€ | GUIF export gate + Unity adapter |

## 4. Responsibility model

### 4.1 AIPG Core

AIPG Core owns domain-neutral governance:

- intent and domain routing;
- Workflow loading and validation;
- task state and checkpoints;
- approval gates;
- Artifact identity and lineage;
- protected Source policy;
- Tool discovery and routing;
- deterministic QA boundaries;
- semantic-review requirements;
- revision scope;
- Candidate Change;
- adoption and publication records;
- recovery and gated export.

AIPG Core does **not** need to understand:

- buttons, panels, visual hierarchy, image alpha, or Theme semantics;
- how a model creates pixels;
- how Unity imports a sprite;
- how an audio, text, code, or video domain evaluates quality.

Those belong to Domain Packs, Tools, inspectors, and exporters.

### 4.2 Domain Pack

A Domain Pack defines production-specific behavior.

| Field | Meaning |
| --- | --- |
| Domain ID | Stable routing identity |
| Workflows | Workflows registered by the domain |
| Context types | Theme, master, source, requirements, or domain data |
| Artifact kinds | Domain-specific output types |
| Review criteria | What deterministic and semantic review must evaluate |
| Tool capabilities | Capabilities required from Tool Adapters |
| Export adapters | Supported delivery targets |
| Compatibility names | Previous names retained during migration |

Current built-in Domain Packs:

| Domain | Status | Workflows |
| --- | --- | --- |
| `framework-governance` | Implemented | Framework evolution and Candidate Change |
| `visual-production` | Implemented as GUIF | Planning, UI production, effect image, Theme direction, resources, QA, master-guided layers |
| Audio | Not implemented | Requires a future Domain Pack |
| Text / narrative | Not implemented | Requires a future Domain Pack |
| Code production | Not implemented | Requires a future Domain Pack |
| Video | Not implemented | Requires a future Domain Pack |
| Game content | Not implemented | Requires a future Domain Pack |

â€œFuture domainâ€ means architecturally allowed, not currently available.

### 4.3 Workflow

A Workflow is a declared production route. It determines:

- required context;
- ordered stages;
- participating agents;
- approval points;
- constraint policy;
- capability requirements;
- review requirements;
- revision behavior;
- export prerequisites.

Workflow Manifest v3 fields:

| Field | Required | Purpose |
| --- | --- | --- |
| `schema_version` | Yes | Manifest contract version |
| `id` | Yes | Stable workflow identity |
| `name` | Yes | Human-readable name |
| `domain` | Yes | Owning Domain Pack |
| `manager` | Yes | Coordinating role |
| `agents` | Yes | Executing agent sequence |
| `steps` | Yes | Human-readable production steps |
| `requires` | Yes | Required context types |
| `stages` | Yes | Governed lifecycle stages |
| `creation_direction` | Yes | Ordered or unordered production |
| `constraint_policy` | Yes | Hard/soft constraint semantics |

Schema v1 and v2 remain readable for compatibility.

### 4.4 Skill

A Skill is the natural-language operating policy used by Codex. It:

- recognizes user intent;
- chooses a Domain and Workflow;
- translates user language into governed contracts;
- presents approval decisions;
- calls framework operations internally;
- invokes real Host capabilities when authorized;
- reports only safe user-facing state.

A Skill must not:

- fabricate a Tool result;
- hide a required source-registration choice;
- claim a dry run generated real media;
- expose private runtime identifiers or paths;
- treat metadata as semantic review;
- merge or publish a candidate without the required adoption state.

### 4.5 Host

The Host is the active operator environment. In the current implementation,
ChatGPT / Codex is the default Host.

Host responsibilities:

- understand natural-language intent;
- access configured capabilities;
- perform real Tool handoffs;
- return real files or structured findings;
- keep credentials and private attachments outside Project Git;
- never claim an unavailable capability ran successfully.

### 4.6 Tool

A Tool performs a concrete capability. Tool identity and capability are
different:

- `chatgpt-image` is a Tool identity.
- `image-generation`, `image-editing`, and `transparent-output` are
  capabilities.

One Tool can provide multiple capabilities; one Workflow can require several
capabilities.

### 4.7 Artifact

An Artifact is a registered result with identity and lineage. Registration does
not mean approval.

Typical Artifact states:

```text
real file returned
-> registered
-> metadata reviewed
-> semantic review pending
-> passed or findings
-> active or superseded
-> export eligible or blocked
```

### 4.8 Engine Adapter

An Engine Adapter translates approved production assets into a delivery target.
It is not the image-generation Tool.

Current adapters:

- `generic`;
- `unity`;
- `godot`;
- `unreal`.

## 5. Skill map

### 5.1 `$aipg-framework`

Use for:

- domain-neutral routing;
- creating or registering a new Domain Pack;
- registering Workflow v3;
- production governance outside visual-specific details;
- Candidate Change;
- Tool integration;
- provider routing;
- version migration;
- publication, refresh, regression, and recovery.

Do not use it as a substitute for a domain Skill when specialized production
rules already exist.

### 5.2 `$game-ui-framework`

Use for:

- game UI and visual interface production;
- private Theme lifecycle;
- master and source registration;
- image generation and editing;
- protected-region editing;
- effect images;
- master-guided layers;
- visual QA;
- revision;
- game-engine asset export.

It is the GUIF compatibility entry and the visual-production Skill of AIPG.

### 5.3 Skill selection precedence

| Situation | Primary Skill | Secondary behavior |
| --- | --- | --- |
| General or unknown domain | `$aipg-framework` | Route to a registered Domain Pack |
| Game UI request | `$game-ui-framework` | Use AIPG governance underneath |
| Visual workflow defect | `$game-ui-framework` | Open AIPG Candidate Change |
| Framework-wide defect | `$aipg-framework` | Diagnose affected layers |
| New Tool for visual layout | `$aipg-framework` + GUIF context | Integrate only the required capability |
| Existing GUIF project | `$game-ui-framework` | Preserve compatibility contracts |

### 5.4 Adding a future Skill

A new Domain Skill must declare:

1. trigger conditions;
2. Domain Pack ID;
3. supported Workflows;
4. required context;
5. approval behavior;
6. Tool capability mapping;
7. truthful completion criteria;
8. privacy rules;
9. Artifact and lineage policy;
10. revision and export policy;
11. Candidate Change behavior;
12. public fictional regression fixtures.

## 6. Tool and capability map

### 6.1 Current registered production Tools

| Tool | Capabilities | Execution | Production | External call | Credentials |
| --- | --- | --- | --- | --- | --- |
| `chatgpt-image` | Image generation, image editing, protected-region editing, transparent output | Host external callback | Allowed | Yes | Uses Host support; no separate framework credential |
| `dry-run` | Deterministic contract simulation for image jobs | Direct | Not allowed as real production | No | No |

### 6.2 Current semantic inspector

| Inspector | Capability | Result |
| --- | --- | --- |
| `chatgpt-vision` | Real semantic visual inspection through Host submission | Structured status, summary, findings |

An inspector result must come from inspection of the actual Artifact. A
filename, MIME type, width, height, or checksum cannot establish composition,
readability, Theme consistency, usability, or visual quality.

### 6.3 Tool resolution order

```mermaid
flowchart TD
    J["Workflow job requires capability"] --> EX{"Explicit Tool selected?"}
    EX -->|Yes| T["Use explicit Tool identity"]
    EX -->|No| TK{"Task route configured?"}
    TK -->|Yes| T
    TK -->|No| PR{"Project route configured?"}
    PR -->|Yes| T
    PR -->|No| WS{"Workspace route configured?"}
    WS -->|Yes| T
    WS -->|No| DF["Use framework default if registered"]
    T --> REG{"Tool registered?"}
    DF --> REG
    REG -->|No| WAIT["Waiting for Tool / integration required"]
    REG -->|Yes| CAP{"Capabilities satisfied?"}
    CAP -->|No| WAIT
    CAP -->|Yes| HEALTH{"Healthy and Host-supported?"}
    HEALTH -->|No| WAIT
    HEALTH -->|Yes| READY["Ready for governed execution"]
```

Resolution precedence is:

```text
explicit
> Task
> Project
> Workspace
> framework default
```

A candidate Tool trial uses a Task-only override. It must not silently mutate
Project or Workspace routing.

### 6.4 Tool readiness disclosure

Before an unfamiliar Tool is adopted, the user should see:

- registration status;
- availability;
- health;
- required capabilities;
- supported Host;
- permissions;
- input and output data scope;
- external calls;
- billing status when known;
- credential requirements;
- failure and retry behavior;
- adoption scope.

### 6.5 Unavailable Tools

An unavailable Tool has three legitimate outcomes:

1. Bind another registered healthy Tool.
2. Open a Tool Integration Candidate and build an Adapter.
3. Cancel the production step.

â€œPretend the Tool ranâ€ is never a valid outcome.

### 6.6 Tool Adapter contract

A production Tool Adapter needs:

- stable Tool ID and version;
- capability manifest;
- permissions and data scopes;
- Host support declaration;
- health check;
- execution mode;
- real result callback or direct result contract;
- Artifact registration;
- failure recovery;
- contract tests;
- production-allowed policy;
- truthful simulation marker.

### 6.7 Image Tool versus layout Tool

A raster Tool and a structured-layout Tool solve different problems:

| Need | Appropriate capability |
| --- | --- |
| Painted background or illustration | Raster image genÛM½¶‰žËkºwµçM¥Í¥½¹Ìè()Ñ•áÐ)ÁÉ½Á½Í…°(´ø…¹‘¥‘…Ñ”µ‰Õ¥±…ÕÑ¡½É¥é…Ñ¥½¸(´ø¥Í½±…Ñ•¥µÁ±•µ•¹Ñ…Ñ¥½¸(´øÉ•…°•Ù¥‘•¹”(´ø…‘½ÁÑ¥½¸‘•¥Í¥½¸(´øÁÕ‰±¥…Ñ¥½¸)€()ð•¥Í¥½¸ð5•…¹¥¹œð)ð€´´´ð€´´´ð)ð	Õ¥±…¹‘¥‘…Ñ”ð5…ä¥µÁ±•µ•¹Ð…¹Ù…±¥‘…Ñ”¥¸¥Í½±…Ñ¥½¸ð)ðI•ÅÕ•ÍÐ¡…¹•ÌðI•ÑÕÉ¸Ñ¼…¹‘¥‘…Ñ”‰Õ¥±‘¥¹œð)ðI•©•Ð…¹‘¥‘…Ñ”ð-••ÀÍÑ…‰±”ÍåÍÑ•´ð)ð‘½ÁÐ…¹‘¥‘…Ñ”ðÕÑ¡½É¥é”ÁÕ‰±¥…Ñ¥½¸Ý½É­™±½Üð()‘½ÁÑ¥½¸¥ÌÙ…±¥½¹±ä…™Ñ•ÈÉ•…°…¹‘¥‘…Ñ”•Ù¥‘•¹”•á¥ÍÑÌ¸((ŒŒŒ€ä¸Ì¡…¹”±…ÍÍ¥™¥…Ñ¥½¸()ð¡…¹”ÑåÁ”ðUÍ”Ý¡•¸ð)ð€´´´ð€´´´ð)ðÍ­¥±°µ¡…¹•€ð9…ÑÕÉ…°µ±…¹Õ…”½Á•É…Ñ¥¹œÁ½±¥ä¥ÌÝÉ½¹œ½È¥¹½µÁ±•Ñ”ð)ð™É…µ•Ý½É¬µ¡…¹•€ð½É”‘½µ…¥¸µ¹•ÕÑÉ…°‰•¡…Ù¥½ÈµÕÍÐ¡…¹”ð)ðÝ½É­™±½Üµ¡…¹•€ðMÑ…”½É‘•È°…Ñ•Ì°½ÈÉ•ÅÕ¥É•½¹Ñ•áÐµÕÍÐ¡…¹”ð)ðµÕ±Ñ¤µ±…å•Èµ¡…¹•€ðM•Ù•É…°™É…µ•Ý½É¬±…å•ÉÌ¡…¹”Ñ½•Ñ¡•Èð)ðÑ¡•µ”µÁ½±¥äµ¡…¹•€ðQ¡•µ”ÍÑ½É…”°‰¥¹‘¥¹œ°½È…ÁÁ±¥…Ñ¥½¸ÉÕ±•Ì¡…¹”ð)ðÁÉ½Ù¥‘•ÈµÉ½ÕÑ¥¹œµ¡…¹•€ð1•…ä½ÁÉ½Ù¥‘•ÈÍ•±•Ñ¥½¸‰•¡…Ù¥½È¡…¹•Ìð)ðÑ½½°µ¡…¹•€ðMÝ¥Ñ Ñ¼…¸…±É•…‘äÉ•¥ÍÑ•É•…Ù…¥±…‰±”Q½½°ð)ðÑ½½°µ¥¹Ñ•É…Ñ¥½¸µ¡…¹•€ð9•Ü½ÈÕ¹ÍÕÁÁ½ÉÑ•Q½½°¹••‘Ì…¸‘…ÁÑ•Èð()¥…¹½Í¥ÌÍ¡½Õ±½¹Í¥‘•È…±°…™™•Ñ•±…å•ÉÌ‰•™½É”Í•±•Ñ¥¹œ„ÑåÁ”¸((ŒŒ€ÄÀ¸Y•ÉÍ¥½¸½Ù•É¹…¹”()%A¡…ÌÍ•Ù•É…°Ù•ÉÍ¥½¸…á•Ì¸Q¡•äµÕÍÐ¹½Ð‰”½±±…ÁÍ•¥¹Ñ¼½¹”¹Õµ‰•È¸((ŒŒŒ€ÄÀ¸ÄY•ÉÍ¥½¸…á•Ì()ðY•ÉÍ¥½¸ðá…µÁ±”ð½Ù•É¹Ìð)ð€´´´ð€´´´ð€´´´ð)ðA±Õ¥¸Ù•ÉÍ¥½¸ð€Ä¸Ä¸Àµ‰•Ñ„¸Å€ð%¹ÍÑ…±±•½‘•àÁ±Õ¥¸Í¹…ÁÍ¡½Ðð)ð…¹‘¥‘…Ñ”Á±Õ¥¸Ù•ÉÍ¥½¸ð€Ä¸Ä¸Àµ‰•Ñ„¸Äµ…¹‘¥‘…Ñ”¸É€ð%Í½±…Ñ•ÁÉ”µ…‘½ÁÑ¥½¸‰Õ¥±ð)ðAåÑ¡½¸Á…­…”Ù•ÉÍ¥½¸ð€Ä¸Ä¸ÁˆÅ€ð…¥Áœµ™É…µ•Ý½É­€‘¥ÍÑÉ¥‰ÕÑ¥½¸ð)ðAÕ‰±¥ŒA$Ù•ÉÍ¥½¸ð€Å€ð½µÁ…Ñ¥‰¥±¥ÑäÍÕÉ™…”ð)ð]½É­™±½ÜÍ¡•µ„ð€Í€ð]½É­™±½Üµ…¹¥™•ÍÐÍÑÉÕÑÕÉ”ð)ðÉÑ¥™…ÐÍ¡•µ„ð€Å€ðÉÑ¥™…ÐÉ•½ÉÍÑÉÕÑÕÉ”ð)ðQ…Í¬Í¡•µ„ð€É€°€Í€ðA•ÉÍ¥ÍÑ•Q…Í¬½µÁ…Ñ¥‰¥±¥Ñäð)ðQ¡•µ”Ù•ÉÍ¥½¸ð%µµÕÑ…‰±”¥¹Ñ••ÈÙ•ÉÍ¥½¸ðUÍ•Èµ½Ý¹•Q¡•µ”•Ù½±ÕÑ¥½¸ð)ðQ½½°µ…¹¥™•ÍÐÙ•ÉÍ¥½¸ðQ½½°µÍÁ•¥™¥Œ°”¹œ¸€Ä¸Á€ð‘…ÁÑ•È…Á…‰¥±¥Ñä‘•±…É…Ñ¥½¸ð)ð½µ…¥¸A…¬Í¡•µ„ð€Å€ð½µ…¥¸É•¥ÍÑÉä½¹ÑÉ…Ðð((ŒŒŒ€ÄÀ¸ÈM•µ…¹Ñ¥ŒÙ•ÉÍ¥½¹¥¹œÁ½±¥ä()ð¡…¹”ðY•ÉÍ¥½¸¥µÁ…Ðð)ð€´´´ð€´´´ð)ð½Õµ•¹Ñ…Ñ¥½¸±…É¥™¥…Ñ¥½¸½¹±äðA…Ñ ½È¹¼ÉÕ¹Ñ¥µ”Ù•ÉÍ¥½¸¡…¹”ð)ð	…­Ý…Éµ½µÁ…Ñ¥‰±”Ý½É­™±½Ü½Q½½°…Á…‰¥±¥Ñäð5¥¹½Èð)ð9•Ü½µ…¥¸A…¬ð5¥¹½Èð)ð9•Ü½ÁÑ¥½¹…°]½É­™±½ÜØÌð5¥¹½Èð)ð	Õœ™¥àÝ¥Ñ¡½ÕÐ½¹ÑÉ…Ð¡…¹”ðA…Ñ ð)ðA±Õ¥¸Á…­…¥¹œ½ÉÉ•Ñ¥½¸ðA…Ñ ð)ð	É•…­¥¹œÁÕ‰±¥ŒA$½ÈÁ•ÉÍ¥ÍÑ•Í¡•µ„ð5…©½È½È¹•ÜÁÕ‰±¥ŒA$Ù•ÉÍ¥½¸ð)ð…¹‘¥‘…Ñ”¥Ñ•É…Ñ¥½¸ð…¹‘¥‘…Ñ”ÍÕ™™¥à½¹±äÕ¹Ñ¥°…‘½ÁÑ¥½¸ð()AÉ•É•±•…Í”¥‘•¹Ñ¥™¥•ÉÌ‘¼¹½Ðµ…­”„‰É•…­¥¹œ¡…¹”Í…™”¸½µÁ…Ñ¥‰¥±¥ÑäÍÑ¥±°)É•ÅÕ¥É•Ì…¸•áÁ±¥¥Ðµ¥É…Ñ¥½¸Á…Ñ ¸((ŒŒŒ€ÄÀ¸Ì½µÁ…Ñ¥‰¥±¥ÑäÉÕ±•Ì()%A€Ä¹àÕÉÉ•¹Ñ±äÁÉ•Í•ÉÙ•Ìè((´Õ¥™€AåÑ¡½¸¥µÁ½ÉÐì(´Õ¥™€1$…±¥…Ìì(´€‘…µ”µÕ¤µ™É…µ•Ý½É­€ì(´•á¥ÍÑ¥¹œU%ÁÉ¥Ù…Ñ”µ‘…Ñ„•¹Ù¥É½¹µ•¹ÐÙ…É¥…‰±•Ìì(´]½É­™±½ÜÍ¡•µ„ØÄ…¹ØÈì(´•á¥ÍÑ¥¹œQ¡•µ”°M½ÕÉ”°ÉÑ¥™…Ð°Q…Í¬°…¹…¹‘¥‘…Ñ”É•½É‘ÌÝ¥Ñ¡¥¸‘•±…É•(€ÍÕÁÁ½ÉÑ•Í¡•µ…Ìì(´•áÁ±¥¥Ð1•…äAÉ½Ù¥‘•É‘…ÁÑ•È½µÁ…Ñ¥‰¥±¥Ñä¸()9•Ü‘½µ…¥¸µ¹•ÕÑÉ…°¥¹Ñ•É…Ñ¥½¹ÌÍ¡½Õ±ÕÍ”…¥Á€ìÙ¥ÍÕ…°¥¹Ñ•É…Ñ¥½¹Ìµ…äÕÍ”)Õ¥™€¸((ŒŒŒ€ÄÀ¸ÐI•±•…Í”½Ù•É¹…¹”()µ•Éµ…¥)™±½Ý¡…ÉÐQ(€€€%l‰%ÍÍÕ”€¼‘•Í¥É•¡…¹”‰t€´´øMl‰AÉ¥Ù…Ñ”%µÁÉ½Ù•µ•¹Ð…Í”‰t(€€€M€´´ø	Il‰…¹‘¥‘…Ñ”‰É…¹ ‰t(€€€	H€´´ø=l‰%µÁ±•µ•¹Ñ…Ñ¥½¸€¬‘½Ì€¬µ¥É…Ñ¥½¸‰t(€€€=€´´øQMQl‰U¹¥Ð°½¹ÑÉ…Ð°É•É•ÍÍ¥½¸°‰Õ¥±°¥¹ÍÑ…±°Ñ•ÍÑÌ‰t(€€€QMP€´´øY%l‰I•½ÉÉ•…°…¹‘¥‘…Ñ”•Ù¥‘•¹”‰t(€€€Y%€´´ø=AQì‰UÍ•È…‘½ÁÑÌü‰ô(€€€=AP€´´ùñ9¼°…‘©ÕÍÑð=(€€€=AP€´´ùñI•©•Ñð1=Ml‰±½Í”ìÍÑ…‰±”É•Ñ…¥¹•‰t(€€€=AP€´´ùñe•ÍðAUM!l‰AÕÍ …¹‘¥‘…Ñ”‰É…¹ ‰t(€€€AUM €´´øAIl‰=Á•¸AH‰t(€€€AH€´´ø%l‰I•ÅÕ¥É•$…¹É•Ù¥•Ü‰t(€€€$€´´ùñ…¥±ð=(€€€$€´´ùñA…ÍÍð5Il‰5•É”Ñ¼ÁÉ½Ñ•Ñ•µ…¥¸‰t(€€€5I€´´øQl‰I•±•…Í”Ù•ÉÍ¥½¸€¼Ñ…œ€¼Á…­…”‰t(€€€Q€´´øI=Il‰I•½ÉÉ•Á½Í¥Ñ½Éä°AH°µ•É”½µµ¥Ð°µ¥¹¥µÕ´Á±Õ¥¸Ù•ÉÍ¥½¸‰t(€€€I=I€´´øIIM!l‰UÍ•ÈÉ•™É•Í¡•ÌÁ±Õ¥¸‰t(€€€IIM €´´øMMM%=9l‰MÑ…ÉÐ„¹•Ü½‘•àÍ•ÍÍ¥½¸‰t(€€€MMM%=8€´´øIl‰I•Á±…ä™½Éµ…°É•É•ÍÍ¥½¸‰t(€€€I€´´ùñA…ÍÍðIMU5l‰I•ÍÕµ”ÁÉ½‘ÕÑ¥½¸‰t(€€€I€´´ùñ…¥±ð=)€((ŒŒŒ€ÄÀ¸ÔI•ÅÕ¥É•É•±•…Í”É•½É‘Ì()ÁÕ‰±¥Í¡•™É…µ•Ý½É¬¡…¹”É•½É‘Ìè((´É•Á½Í¥Ñ½Éäì(´‰É…¹ ì(´ÁÕ±°É•ÅÕ•ÍÐì(´µ•É”½µµ¥Ðì(´É•±•…Í•Ù•ÉÍ¥½¸ì(´µ¥¹¥µÕ´Á±Õ¥¸Ù•ÉÍ¥½¸ì(´‰Õ¥±…¹Ñ•ÍÐ½ÕÑ½µ”ì(´µ¥É…Ñ¥½¸¹½Ñ•Ìì(´É•™É•Í É•ÅÕ¥É•µ•¹Ðì(´™½Éµ…°É•É•ÍÍ¥½¸½ÕÑ½µ”¸((ŒŒŒ€ÄÀ¸ØY•ÉÍ¥½¸µ™¥±”µ…¥¹Ñ•¹…¹”¡•­±¥ÍÐ()]¡•¸„É•±•…Í”¡…¹•ÌÙ•ÉÍ¥½¸½È¥‘•¹Ñ¥Ñä°¥¹ÍÁ•Ð…¹ÕÁ‘…Ñ”è((´€¹½‘•àµÁ±Õ¥¸½Á±Õ¥¸¹©Í½¹€ì(´É•Á½Í¥Ñ½Éäµ…É­•ÑÁ±…”µ•Ñ…‘…Ñ„ì(´ÁåÁÉ½©•Ð¹Ñ½µ±€ì(´…¥Á€…¹Õ¥™€Á…­…”Ù•ÉÍ¥½¸•áÁ½ÍÕÉ”ì(´$Ù•ÉÍ¥½¸…ÍÍ•ÉÑ¥½¹Ìì(´I5…¹¡¥¹•Í”I5ì(´!91=ì(´…¹‘¥‘…Ñ”½É•±•…Í”¹½Ñ•Ìì(´…É¡¥Ñ•ÑÕÉ”…¹µ¥É…Ñ¥½¸‘½Õµ•¹ÑÌì(´Á±Õ¥¸M­¥±±Ì…¹Ñ¡•¥ÈÕÍ•Èµ™…¥¹œÉ•™É•Í ¹…µ”ì(´Á…­…”ÁÉ½Ù•¹…¹”•áÁ•Ñ…Ñ¥½¹Ìì(´Ñ•ÍÑÌÑ¡…Ð…ÍÍ•ÉÐÁ±Õ¥¸½Á…­…”¥‘•¹Ñ¥Ñä¸()!¥ÍÑ½É¥…°É•±•…Í”¹½Ñ•ÌÍ¡½Õ±É•µ…¥¸¡¥ÍÑ½É¥…±±ä…ÕÉ…Ñ”É…Ñ¡•ÈÑ¡…¸‰•¥¹œ)µ•¡…¹¥…±±äÉ•ÝÉ¥ÑÑ•¸¸((ŒŒ€ÄÄ¸¹µÑ¼µ•¹ÕÍ•È©½ÕÉ¹•åÌ((ŒŒŒ€ÄÄ¸Ä•¹•É…°½Ù•É¹•ÁÉ½‘ÕÑ¥½¸((Ä¸UÍ•È‘•ÍÉ¥‰•ÌÑ¡”½ÕÑ½µ”¸(È¸€‘…¥Áœµ™É…µ•Ý½É­€¥‘•¹Ñ¥™¥•ÌÑ¡”½µ…¥¸¸(Ì¸%AÍ•±•ÑÌ½ÈÉ•ÅÕ•ÍÑÌ„]½É­™±½Ü¸(Ð¸Q¡”]½É­™±½Ü‘•±…É•ÌÉ•ÅÕ¥É•½¹Ñ•áÐ¸(Ô¸5¥ÍÍ¥¹œ½¹Ñ•áÐ¥ÌÉ•ÅÕ•ÍÑ•Ý¥Ñ¡½ÕÐ•áÁ½Í¥¹œÉÕ¹Ñ¥µ”¥¹Ñ•É¹…±Ì¸(Ø¸ÁÉ½‘ÕÑ¥½¸½¹ÑÉ…Ð¥ÌÁÉ•Í•¹Ñ•¸(Ü¸UÍ•È…ÁÁÉ½Ù•Ì°É•ÅÕ•ÍÑÌ¡…¹•Ì°½ÈÉ•©•ÑÌ¸(à¸Q½½°É•Í½±ÕÑ¥½¸Ù•É¥™¥•Ì…Á…‰¥±¥Ñä…¹¡•…±Ñ ¸(ä¸I•…°É•ÍÕ±ÑÌ‰•½µ”É•¥ÍÑ•É•ÉÑ¥™…ÑÌ¸(ÄÀ¸I•ÅÕ¥É•É•Ù¥•ÜÉÕ¹Ì…ÐÑ¡”½ÉÉ•Ð…ÍÍÕÉ…¹”±•Ù•°¸(ÄÄ¸I•Ù¥Í¥½¹ÌÉ••¥Ù”¥¹‘•Á•¹‘•¹Ð…ÁÁÉ½Ù…°¸(ÄÈ¸áÁ½ÉÐ½ÕÉÌ½¹±äÝ¡•¸Ñ¡”…Ñ”Á…ÍÍ•Ì¸((ŒŒŒ€ÄÄ¸ÈÉ•…Ñ”½¹”…µ”U$•™™•Ð¥µ…”()MÕ•ÍÑ•É•ÅÕ•ÍÐè((øUÍ”U%Ñ¼É•…Ñ”„™¥Ñ¥½¹…°Í¤µ™¤¥¹Ù•¹Ñ½ÉäÍÉ••¸¸½¹™¥É´Ñ¡”Q¡•µ”…¹(øÁ±…¸‰•™½É”•¹•É…Ñ¥¹œ¸()áÁ•Ñ•É½ÕÑ”è()Ñ•áÐ(‘…µ”µÕ¤µ™É…µ•Ý½É¬(´øÙ¥ÍÕ…°µÁÉ½‘ÕÑ¥½¸(´ø•™™•Ðµ¥µ…”½ÈÕ¤µÁÉ½‘ÕÑ¥½¸(´øQ¡•µ”(´øÁ±…¸…ÁÁÉ½Ù…°(´ø¡…ÑÁÐµ¥µ…”(´øÉÑ¥™…Ð(´ø¡…ÑÁÐµÙ¥Í¥½¸(´ø™¥¹…°…ÁÁÉ½Ù…°(´ø½ÁÑ¥½¹…°•áÁ½ÉÐ)€((ŒŒŒ€ÄÄ¸ÌÉ•…Ñ”„±…å•É•…µ”U$()MÕ•ÍÑ•É•ÅÕ•ÍÐè((øUÍ”Ñ¡”…ÁÁÉ½Ù•µ…ÍÑ•È…ÌÍÑå±”…¹±…å½ÕÐÕ¥‘…¹”¸¹…±åé”½…ÉÍ”±…å•ÉÌ°(ø±•Ð$É•…Ñ¥Ù•±ä¥¹Ñ•ÉÁÉ•ÐÍ½™Ð‘•Ñ…¥±Ì°Ñ¡•¸ÁÉ½‘Õ”™É½´‰…­É½Õ¹Ñ¼(ø™½É•É½Õ¹…¹•áÁ½ÉÐ¥¹‘•Á•¹‘•¹Ð…ÍÍ•ÑÌ¸()áÁ•Ñ•É½ÕÑ”è()Ñ•áÐ(‘…µ”µÕ¤µ™É…µ•Ý½É¬(´øµ…ÍÑ•ÈµÕ¥‘•µ±…å•ÈµÉ•…Ñ¥½¸(´øQ¡•µ”€¬µ…ÍÑ•ÈµÉ•™•É•¹”(´øµ…ÍÑ•È…ÁÁÉ½Ù…°(´ø±…å•ÈµÁ±…¸…ÁÁÉ½Ù…°(´ø‰…­É½Õ¹(´øÕÉÉ•¹Ð½µÁ½Í¥Ñ”(´ø½¹Ñ…¥¹•È½™É…µ”(´øÕÉÉ•¹Ð½µÁ½Í¥Ñ”(´ø½¹ÑÉ½±Ì½½¹Ñ•¹Ð(´øÕÉÉ•¹Ð½µÁ½Í¥Ñ”(´ø‘•½É…Ñ¥½¸½•™™•ÑÌ(´ø™¥¹…°Í•µ…¹Ñ¥ŒÉ•Ù¥•Ü(´ø±…å•Èµ…¹¥™•ÍÐ€¬•¹¥¹”•áÁ½ÉÐ)€((ŒŒŒ€ÄÄ¸Ð‘¥Ð…¸•á¥ÍÑ¥¹œ¥µ…”Í…™•±ä((Ä¸U%¡•­ÌÝ¡•Ñ¡•ÈÑ¡”¥µ…”¥ÌÉ•¥ÍÑ•É•¸(È¸%˜¹½Ð°Ñ¡”ÕÍ•È¡½½Í•Ìè(€€€´•‘¥Ñ…‰±”Í½ÕÉ”ì(€€€´Q¡•µ”É•™•É•¹”ì(€€€´µ…ÍÑ•ÈÉ•™•É•¹”ì(€€€´±•…Ù”Ñ¡”™½Éµ…°¡…¥¸¸(Ì¸‘¥Ñ…‰±”µÍ½ÕÉ”É•¥ÍÑÉ…Ñ¥½¸É•…Ñ•Ì¥µµÕÑ…‰±”±¥¹•…”¸(Ð¸Q¡”•‘¥ÐÁ±…¸¥‘•¹Ñ¥™¥•ÌÁÉ½Ñ•Ñ•É•¥½¹Ì¸(Ô¸UÍ•È…ÁÁÉ½Ù•ÌÑ¡”•‘¥Ð¸(Ø¸I•…°•‘¥Ñ¥¹œ½ÕÉÌ¸(Ü¸AÉ½Ñ•Ñ•Á¥á•±Ì…¹Í•µ…¹Ñ¥ŒÅÕ…±¥Ñä…É”É•Ù¥•Ý•¸(à¸Á…ÍÍ¥¹œÉ•Á±…•µ•¹Ðµ…äÍÕÁ•ÉÍ•‘”Ñ¡”Í½ÕÉ”¸((ŒŒŒ€ÄÄ¸Ô‘„¹•ÜQ½½°()MÕ•ÍÑ•É•ÅÕ•ÍÐè((ø‘„ÍÑÉÕÑÕÉ•±…å½ÕÐQ½½°™½ÈU%½µÁ½¹•¹Ð¡¥•É…É¡ä°‰ÕÐ­••ÀÉ…ÍÑ•È(ø•¹•É…Ñ¥½¸½¸Ñ¡”ÕÉÉ•¹Ð¥µ…”Q½½°¸()áÁ•Ñ•É½ÕÑ”è()Ñ•áÐ(‘…¥Áœµ™É…µ•Ý½É¬(´ø…Á…‰¥±¥Ñä…¹…±åÍ¥Ì(´øQ½½°‘¥Í½Ù•Éä(´øÉ•¥ÍÑ•É•…¹¡•…±Ñ¡äü(€€€´øå•ÌèQ…Í¬µ½¹±äQ½½°ÑÉ¥…°(€€€´ø¹¼èQ½½°%¹Ñ•É…Ñ¥½¸…¹‘¥‘…Ñ”(´øÁ•Éµ¥ÍÍ¥½¹Ì½‘…Ñ„½‰¥±±¥¹œ½É•‘•¹Ñ¥…±Ì‘¥Í±½ÍÕÉ”(´ø‘…ÁÑ•È½¹ÑÉ…Ð(´øÉ•…°É•ÍÕ±Ð(´ø…‘½ÁÑ¥½¸Í½Á”)€((ŒŒŒ€ÄÄ¸Ø%µÁÉ½Ù”%A¥ÑÍ•±˜((Ä¸%‘•¹Ñ¥™ä½‰Í•ÉÙ•…¹•áÁ•Ñ•‰•¡…Ù¥½È¸(È¸¥…¹½Í”M­¥±°°]½É­™±½Ü°½É”°Q½½°°Q¡•µ”Á½±¥ä°AÉ½µÁÐ%H°É•Ù¥•Ü°…¹(€€•áÁ½ÉÐ±…å•ÉÌ¸(Ì¸=Á•¸½¹”%µÁÉ½Ù•µ•¹Ð…Í”¸(Ð¸AÉ•Í•ÉÙ”Ñ¡”ÁÉ½‘ÕÑ¥½¸¡•­Á½¥¹Ð¸(Ô¸	Õ¥±½¸…¸¥Í½±…Ñ•Í½ÕÉ”‰É…¹ ¸(Ø¸UÍ”™¥Ñ¥½¹…°ÁÕ‰±¥Œ™¥áÑÕÉ•Ì¸(Ü¸IÕ¸É•…°Ñ•ÍÑÌ…¹É•½É•Ù¥‘•¹”¸(à¸‘½ÁÐ°…‘©ÕÍÐ°½ÈÉ•©•Ð¸(ä¸™Ñ•È…‘½ÁÑ¥½¸°ÁÕ‰±¥Í Ñ¡É½Õ AH…¹$¸(ÄÀ¸I•™É•Í Ñ¡”Á±Õ¥¸…¹ÉÕ¸™½Éµ…°É•É•ÍÍ¥½¸¸((ŒŒ€ÄÈ¸I•½Ù•Éä…¹™…¥±ÕÉ”µ…À()ð…¥±ÕÉ”ðUÍ•ÈµÙ¥Í¥‰±”½ÕÑ½µ”ð½ÉÉ•ÐÉ•½Ù•Éäð)ð€´´´ð€´´´ð€´´´ð)ð5¥ÍÍ¥¹œQ¡•µ”É•ÅÕ¥É•‰äU%ðQ¡•µ”½¹™¥Éµ…Ñ¥½¸ðM•±•Ð°É•…Ñ”°‘•É¥Ù”°½È•áÁ±¥¥Ñ±ä½¹Ñ¥¹Õ”Õ¹‰½Õ¹¥˜…±±½Ý•ð)ð5¥ÍÍ¥¹œÉ•¥ÍÑ•É•Í½ÕÉ”ðM½ÕÉ”¥µÁ½ÉÐÉ•ÅÕ¥É•ðUÍ•È¡½½Í•ÌÍ½ÕÉ”ÕÍ…”ð)ðQ½½°¹½ÐÉ•¥ÍÑ•É•ð]…¥Ñ¥¹œ™½ÈQ½½°ð	¥¹°¥¹Ñ•É…Ñ”°½È…¹•°ð)ðQ½½°Õ¹¡•…±Ñ¡äð]…¥Ñ¥¹œ™½ÈQ½½°ðI•ÑÉä¡•…±Ñ °Í•±•Ð…¹½Ñ¡•ÈQ½½°°½È¥¹Ñ•É…Ñ”ð)ðáÑ•É¹…°…±±‰…¬¥¹Ñ•ÉÉÕÁÑ•ðI•½Ù•É…‰±”•ÉÉ½ÈðI•½Ù•È½ÈÉ•ÑÉäÁ•ÉÍ¥ÍÑ•Ý½É¬ð)ðM•µ…¹Ñ¥Œ™¥¹‘¥¹ÌðI•Ù¥Í¥½¸É•ÅÕ¥É•ðÉ•…Ñ”Í½Á•É•Ù¥Í¥½¸…¹…ÁÁÉ½Ù”Í•Á…É…Ñ•±äð)ð…¹‘¥‘…Ñ”™…¥±•ð…¹‘¥‘…Ñ”‰Õ¥±‘¥¹œð‘©ÕÍÐ…¹‘¥‘…Ñ”ìÍÑ…‰±”É•µ…¥¹ÌÕ¹¡…¹•ð)ðA±Õ¥¸ÁÕ‰±¥Í¡•‰ÕÐ½±Í•ÍÍ¥½¸…Ñ¥Ù”ðA±Õ¥¸É•™É•Í É•ÅÕ¥É•ðI•™É•Í Á±Õ¥¸…¹ÍÑ…ÉÐ¹•ÜÍ•ÍÍ¥½¸ð)ð½Éµ…°É•É•ÍÍ¥½¸™…¥±•ð…¹‘¥‘…Ñ”É•½Á•¹•ð¥à…¹É•ÁÕ‰±¥Í ì‘¼¹½ÐÉ•ÍÕµ”ÁÉ½‘ÕÑ¥½¸ð)ðáÁ½ÉÐ…Ñ”‰±½­•ðáÁ½ÉÐ‘•¹¥•ðI•Í½±Ù”…ÁÁÉ½Ù…±Ì°E°±¥¹•…”°½Èµ¥ÍÍ¥¹œÉÑ¥™…ÑÌð()I•½Ù•ÉäµÕÍÐÕÍ”Á•ÉÍ¥ÍÑ•¡•­Á½¥¹ÑÌ¸%ÐµÕÍÐ¹½Ð¥¹Ù•¹Ð½µÁ±•Ñ•Ý½É¬½È)‘ÕÁ±¥…Ñ”•áÑ•É¹…°½Á•É…Ñ¥½¹Ì‰±¥¹‘±ä¸((ŒŒ€ÄÌ¸áÑ•¹Í¥½¸‰±Õ•ÁÉ¥¹Ð((ŒŒŒ€ÄÌ¸Ä‘‘¥¹œ„½µ…¥¸A…¬()I•ÅÕ¥É•‘•±¥Ù•É…‰±•Ìè((´ÍÑ…‰±”½µ…¥¸%ì(´½µ…¥¸A…¬Í¡•µ„ì(´ÕÍ•Èµ™…¥¹œM­¥±°½ÈÉ½ÕÑ¥¹œÉÕ±•Ìì(´]½É­™±½Üµ…¹¥™•ÍÑÌì(´‘½µ…¥¸½¹Ñ•áÐÍ¡•µ…Ìì(´ÉÑ¥™…Ð­¥¹‘Ìì(´Q½½°…Á…‰¥±¥Ñ¥•Ì…¹…‘…ÁÑ•ÉÌì(´‘•Ñ•Éµ¥¹¥ÍÑ¥ŒEì(´Í•µ…¹Ñ¥Œ¥¹ÍÁ•Ñ½È½¹ÑÉ…Ðì(´É•Ù¥Í¥½¸Á½±¥äì(´•áÁ½ÉÑ•Èì(´ÁÉ¥Ù…äÁ½±¥äì(´™¥Ñ¥½¹…°™¥áÑÕÉ•Ìì(´µ¥É…Ñ¥½¸…¹Ù•ÉÍ¥½¸¹½Ñ•Ìì(´™…¥±ÕÉ”É•½Ù•ÉäÑ•ÍÑÌ¸((ŒŒŒ€ÄÌ¸È‘‘¥¹œ„]½É­™±½Ü()¡•­±¥ÍÐè((Ä¸%‘•¹Ñ¥™ä½µ…¥¸½Ý¹•ÉÍ¡¥À¸(È¸•™¥¹”ÕÍ•È¥¹Ñ•¹Ð…¹¹½¸µ½…±Ì¸(Ì¸•™¥¹”É•ÅÕ¥É•½¹Ñ•áÐ¸(Ð¸•™¥¹”½É‘•É•ÍÑ…•Ì¸(Ô¸•™¥¹”¡…É…¹Í½™Ð½¹ÍÑÉ…¥¹ÑÌ¸(Ø¸•™¥¹”…ÁÁÉ½Ù…°…Ñ•Ì¸(Ü¸•™¥¹”Q½½°…Á…‰¥±¥Ñ¥•Ì¸(à¸•™¥¹”ÉÑ¥™…Ð½ÕÑÁÕÑÌ¸(ä¸•™¥¹”‘•Ñ•Éµ¥¹¥ÍÑ¥Œ…¹Í•µ…¹Ñ¥ŒÉ•Ù¥•Ü¸(ÄÀ¸•™¥¹”É•Ù¥Í¥½¸¥¹Ù…±¥‘…Ñ¥½¸¸(ÄÄ¸•™¥¹”•áÁ½ÉÐÁÉ•É•ÅÕ¥Í¥Ñ•Ì¸(ÄÈ¸‘]½É­™±½ÜØÌµ…¹¥™•ÍÐ¸(ÄÌ¸‘™¥Ñ¥½¹…°Ñ•ÍÑÌ¸(ÄÐ¸UÁ‘…Ñ”½µ…¥¸É•¥ÍÑÉä°I5°!91=°…¹µ¥É…Ñ¥½¸¹½Ñ•Ì¸((ŒŒŒ€ÄÌ¸Ì‘‘¥¹œ…¸¹¥¹”‘…ÁÑ•È()¸¹¥¹”‘…ÁÑ•ÈÍ¡½Õ±è((´…•ÁÐ½¹±ä•áÁ½ÉÐµ•±¥¥‰±”ÉÑ¥™…ÑÌì(´ÁÉ•Í•ÉÙ”ÉÑ¥™…Ð…¹µ…¹¥™•ÍÐ¥‘•¹Ñ¥Ñäì(´µ…À‘¥µ•¹Í¥½¹Ì°…±Á¡„°Á¥Ù½Ð°Í±¥¥¹œ°¡¥•É…É¡ä°ÍÑ…Ñ•Ì°µ…Ñ•É¥…±Ì°…¹(€Ñ…É•ÐÍ•ÑÑ¥¹ÌÝ¡•É”ÍÕÁÁ½ÉÑ•ì(´É•Á½ÉÐ•á…Ñ±äÝ¡…ÐÝ…ÌÝÉ¥ÑÑ•¸ì(´™…¥°Í…™•±äÝ¥Ñ¡½ÕÐ±…¥µ¥¹œ•¹¥¹”¥µÁ½ÉÐÍÕ••‘•ì(´ÍÕÁÁ½ÉÐÉ½±±‰…¬½ÈÁÉ½Ù¥‘”„±•…È¹½¸µÉ½±±‰…¬‰½Õ¹‘…Éä¸((ŒŒŒ€ÄÌ¸Ð‘‘¥¹œ…¸¥¹ÍÁ•Ñ½È()¸¥¹ÍÁ•Ñ½È½¹ÑÉ…Ð¹••‘Ìè((´ÍÑ…‰±”¥¹ÍÁ•Ñ½È¥‘•¹Ñ¥Ñäì(´ÍÕÁÁ½ÉÑ•µ•‘¥„…¹É¥Ñ•É¥„ì(´Á•Éµ¥ÍÍ¥½¸…¹‘…Ñ„µÍ½Á”‘¥Í±½ÍÕÉ”ì(´…ÑÕ…°ÉÑ¥™…Ð…ÑÑ…¡µ•¹Ðì(´ÍÑÉÕÑÕÉ•ÍÑ…ÑÕÌ°ÍÕµµ…Éä°…¹™¥¹‘¥¹Ìì(´¹¼µ•Ñ…‘…Ñ„µ½¹±äÍ•µ…¹Ñ¥ŒÁ…ÍÌì(´É•ÑÉä…¹™…¥±ÕÉ”‰•¡…Ù¥½Èì(´Ñ•ÍÑÌÕÍ¥¹œ™¥Ñ¥½¹…°µ•‘¥„¸((ŒŒ€ÄÐ¸=Á•É…Ñ¥½¹…°¡•­±¥ÍÑÌ((ŒŒŒ	•™½É”ÁÉ½‘ÕÑ¥½¸((´lt½ÉÉ•Ð½µ…¥¸…¹]½É­™±½ÜÍ•±•Ñ•¸(´ltI•ÅÕ¥É•½¹Ñ•áÐ¥ÌÁÉ•Í•¹Ð¸(´ltI•…°Í½ÕÉ”ÕÍ…”¥ÌÉ•¥ÍÑ•É•¸(´ltQ½½°…Á…‰¥±¥Ñ¥•Ì…É”…Ù…¥±…‰±”…¹¡•…±Ñ¡ä¸(´ltA•Éµ¥ÍÍ¥½¹Ì°‘…Ñ„™±½Ü°É•‘•¹Ñ¥…±Ì°…¹‰¥±±¥¹œ…É”Õ¹‘•ÉÍÑ½½¸(´ltAÉ½‘ÕÑ¥½¸½¹ÑÉ…Ð¥Ì½µÁ±•Ñ”¸(´ltI•ÅÕ¥É•…ÁÁÉ½Ù…°¥ÌÉ•½É‘•¸((ŒŒŒ	•™½É”…•ÁÑ¥¹œ…¸ÉÑ¥™…Ð((´ltI•ÍÕ±Ð™¥±”¥ÌÉ•…°…¹É•¥ÍÑ•É•¸(´ltQ½½°…¹µ½‘•°¥‘•¹Ñ¥Ñä…É”ÑÉÕÑ¡™Õ°¸(´ltM¥µÕ±…Ñ¥½¸™±…œ¥Ì™…±Í”™½ÈÁÉ½‘ÕÑ¥½¸¸(´ltI•™•É•¹•Ì…¹±¥¹•…”…É”Ù…±¥¸(´lt5•Ñ…‘…Ñ„EÁ…ÍÍ•¸(´ltAÉ½Ñ•Ñ•µÁ¥á•°EÁ…ÍÍ•Ý¡•¸…ÁÁ±¥…‰±”¸(´ltM•µ…¹Ñ¥ŒÉ•Ù¥•ÜÕÍ•Ñ¡”É•…°ÉÑ¥™…Ð¸(´ltUÍ•È½¹™¥Éµ•ÍÕ‰©•Ñ¥Ù”…•ÁÑ…¹”Ý¡•¸É•ÅÕ¥É•¸((ŒŒŒ	•™½É”•áÁ½ÉÐ((´ltÑ¥Ù”ÉÑ¥™…ÑÌ…É”…ÁÁÉ½Ù•¸(´lt9¼‰±½­¥¹œÙ¥ÍÕ…°™¥¹‘¥¹ÌÉ•µ…¥¸¸(´ltI•ÅÕ¥É•±…å•È‘•Á•¹‘•¹¥•Ì…É”½µÁ±•Ñ”¸(´lt½µÁ½Í¥Ñ¥½¸µ…¹¥™•ÍÐ¥ÌÙ…±¥¸(´ltQ…É•Ð¹¥¹”‘…ÁÑ•È¥ÌÍÕÁÁ½ÉÑ•¸(´ltáÁ½ÉÐ‘•ÍÑ¥¹…Ñ¥½¸…¹½Ù•ÉÝÉ¥Ñ”Á½±¥ä…É”•áÁ±¥¥Ð¸(´ltI½±±‰…¬‰½Õ¹‘…Éä¥ÌÕ¹‘•ÉÍÑ½½¸((ŒŒŒ	•™½É”…‘½ÁÑ¥¹œ„™É…µ•Ý½É¬¡…¹”((´ltMÑ…‰±”‰…Í•±¥¹”É•½É‘•Ý¡•É”ÁÉ…Ñ¥…°¸(´lt…¹‘¥‘…Ñ”‰É…¹ …¹Ù•ÉÍ¥½¸±¥¹­•¸(´ltI•…°…¹‘¥‘…Ñ”•Ù¥‘•¹”É•½É‘•¸(´lt9¼ÕÍ•ÈµÁÉ¥Ù…Ñ”‘…Ñ„•¹Ñ•É•ÁÕ‰±¥Œ¥Ð¸(´lt	…­Ý…É½µÁ…Ñ¥‰¥±¥Ñä…ÍÍ•ÍÍ•¸(´ltI5°!91=°µ¥É…Ñ¥½¸°µ…¹¥™•ÍÑÌ°…¹Ñ•ÍÑÌÕÁ‘…Ñ•¸(´ltUÍ•È¡…ÌÉ•Ù¥•Ý•Ñ¡”…¹‘¥‘…Ñ”É•ÍÕ±Ð¸(´lt‘½ÁÑ¥½¸‘•¥Í¥½¸¥Ì•áÁ±¥¥Ð¸((ŒŒŒ	•™½É”ÁÕ‰±¥…Ñ¥½¸((´lt‘½ÁÑ¥½¸ÍÑ…Ñ”…ÕÑ¡½É¥é•ÌÁÕ‰±¥…Ñ¥½¸¸(´lt	É…¹ ¥ÌÁÕÍ¡•¸(´ltAH¥Ì½Á•¸Ý¥Ñ µ¥É…Ñ¥½¸…¹•Ù¥‘•¹”ÍÕµµ…Éä¸(´ltI•ÅÕ¥É•$Á…ÍÍ•Ì¸(´ltI•Ù¥•Ü¥ÍÍÕ•Ì…É”É•Í½±Ù•¸(´lt5…¥¸¥ÌÁÉ½Ñ•Ñ•™É½´Õ¹É•Ù¥•Ý•¡…¹•Ì¸(´ltI•±•…Í”Ù•ÉÍ¥½¸¥Ì½¹Í¥ÍÑ•¹Ð…É½ÍÌ™¥±•Ì¸(´ltI•Á½Í¥Ñ½Éä°AH°µ•É”½µµ¥Ð°…¹µ¥¹¥µÕ´Á±Õ¥¸Ù•ÉÍ¥½¸…É”É•½É‘•¸(´ltA±Õ¥¸É•™É•Í …¹¹•ÜµÍ•ÍÍ¥½¸É•ÅÕ¥É•µ•¹Ð¥Ì½µµÕ¹¥…Ñ•¸(´lt½Éµ…°É•É•ÍÍ¥½¸Á±…¸¥ÌÉ•…‘ä¸((ŒŒ€ÄÔ¸EÕ¥¬µÉ•™•É•¹”µ…ÑÉ¥à()ðUÍ•È…Í­Ì™½ÈðM­¥±°ð½µ…¥¸ð]½É­™±½Ü€¼ÁÉ½•ÍÌðAÉ¥µ…ÉäQ½½°½È…‘…ÁÑ•Èð-•ä…Ñ”ð)ð€´´´ð€´´´ð€´´´ð€´´´ð€´´´ð€´´´ð)ð•¹•É…°$ÁÉ½‘ÕÑ¥½¸ð€‘…¥Áœµ™É…µ•Ý½É­€ðI½ÕÑ•ðI•¥ÍÑ•É•]½É­™±½Üð…Á…‰¥±¥Ñäµ‘•Á•¹‘•¹ÐðA±…¸…ÁÁÉ½Ù…°ð)ð…µ”U$‘•Í¥¸ð€‘…µ”µÕ¤µ™É…µ•Ý½É­€ðY¥ÍÕ…°ðU$ÁÉ½‘ÕÑ¥½¸ð¡…ÑÁÐµ¥µ…•€ðAÉ½‘ÕÑ¥½¸…ÁÁÉ½Ù…°ð)ð=¹”•™™•Ð¥µ…”ð€‘…µ”µÕ¤µ™É…µ•Ý½É­€ðY¥ÍÕ…°ð™™•Ð¥µ…”ð¡…ÑÁÐµ¥µ…•€ðY¥ÍÕ…°É•Ù¥•Üð)ðAÉ½Ñ•Ñ•¥µ…”•‘¥Ðð€‘…µ”µÕ¤µ™É…µ•Ý½É­€ðY¥ÍÕ…°ð%µ…”•‘¥Ñ¥¹œð¡…ÑÁÐµ¥µ…•€ðM½ÕÉ”€¬É•Ù¥Í¥½¸…ÁÁÉ½Ù…°ð)ð1…å•É•U$…ÍÍ•ÑÌð€‘…µ”µÕ¤µ™É…µ•Ý½É­€ðY¥ÍÕ…°ð5…ÍÑ•ÈµÕ¥‘•±…å•ÉÌð¡…ÑÁÐµ¥µ…•€€¬¥¹ÍÁ•Ñ½Èð1…å•ÈµÁ±…¸€¬™¥¹…°…ÁÁÉ½Ù…°ð)ðY¥ÍÕ…°¥¹ÍÁ•Ñ¥½¸ð€‘…µ”µÕ¤µ™É…µ•Ý½É­€ðY¥ÍÕ…°ðEð¡…ÑÁÐµÙ¥Í¥½¹€ðI•…°ÉÑ¥™…ÐÉ•ÅÕ¥É•ð)ðU¹¥Ñä½ÕÑÁÕÐð€‘…µ”µÕ¤µ™É…µ•Ý½É­€ðY¥ÍÕ…°ðáÁ½ÉÐðU¹¥Ñä¹¥¹”‘…ÁÑ•ÈðáÁ½ÉÐ…Ñ”ð)ð½¹ÑÉ…Ðµ½¹±äÑ•ÍÐð•Ù•±½Á•È½½Á•É…Ñ½Èð¹äÍÕÁÁ½ÉÑ•ðá¥ÍÑ¥¹œ]½É­™±½Üð‘ÉäµÉÕ¹€ð9•Ù•ÈÑÉ•…Ñ•…ÌÁÉ½‘ÕÑ¥½¸ð)ð¡…¹”Q½½°É½ÕÑ”ð€‘…¥Áœµ™É…µ•Ý½É­€ð½Ù•É¹…¹”ðQ½½°¡…¹”ðI•¥ÍÑ•É•Q½½°ðÙ¥‘•¹”€¬…‘½ÁÑ¥½¸Í½Á”ð)ð%¹Ñ•É…Ñ”¹•ÜQ½½°ð€‘…¥Áœµ™É…µ•Ý½É­€ð½Ù•É¹…¹”ðQ½½°%¹Ñ•É…Ñ¥½¸…¹‘¥‘…Ñ”ð9•Ü‘…ÁÑ•Èð‘½ÁÑ¥½¸ð)ð¡…¹”™É…µ•Ý½É¬ð€‘…¥Áœµ™É…µ•Ý½É­€ð½Ù•É¹…¹”ð…¹‘¥‘…Ñ”¡…¹”ðM½ÕÉ”É•Á½Í¥Ñ½Éäð‘½ÁÑ¥½¸€¬ÁÕ‰±¥…Ñ¥½¸ð((ŒŒ€ÄØ¸½±‘•¸ÉÕ±•Ì((Ä¸I½ÕÑ”‰ä½µ…¥¸…¹]½É­™±½Ü‰•™½É”…Í­¥¹œ™½È‘½µ…¥¸µÍÁ•¥™¥Œ½¹Ñ•áÐ¸(È¸Q¡•µ”‰•±½¹ÌÑ¼U%°¹½ÐÑ¡”%AÑ½À±•Ù•°¸(Ì¸M­¥±°½Ù•É¹ÌìQ½½°•á•ÕÑ•ÌìÉÑ¥™…ÐÉ•½É‘ÌìÉ•Ù¥•Ü•Ù…±Õ…Ñ•Ì¸(Ð¸Q½½°¥‘•¹Ñ¥Ñä¥Ì¹½ÐÑ¡”Í…µ”…Ì…Á…‰¥±¥Ñä¸(Ô¸ÉäÉÕ¸¥Ì¹•Ù•È„É•…°µ•‘¥„É•ÍÕ±Ð¸(Ø¸5•Ñ…‘…Ñ„¥Ì¹•Ù•ÈÍ•µ…¹Ñ¥ŒÉ•Ù¥•Ü¸(Ü¸Ù•ÉäÉ•Ù¥Í¥½¸¡…Ì¥ÑÌ½Ý¸Í½Á”…¹…ÁÁÉ½Ù…°¸(à¸I•…°Í½ÕÉ•Ì…¹•Ù¥‘•¹”É•µ…¥¸ÁÉ¥Ù…Ñ”‰ä‘•™…Õ±Ð¸(ä¸…¹‘¥‘…Ñ”‘½•Ì¹½Ð…±Ñ•ÈÍÑ…‰±”ÁÉ½‘ÕÑ¥½¸¸(ÄÀ¸‘½ÁÑ¥½¸°ÁÕ‰±¥…Ñ¥½¸°Á±Õ¥¸É•™É•Í °…¹™½Éµ…°É•É•ÍÍ¥½¸…É”Í•Á…É…Ñ”(€€€ÍÑ…Ñ•Ì¸(ÄÄ¸	…­Ý…É½µÁ…Ñ¥‰¥±¥ÑäÉ•ÅÕ¥É•Ì•áÁ±¥¥Ð½¹ÑÉ…ÑÌ…¹µ¥É…Ñ¥½¸¸(ÄÈ¸%˜„…Á…‰¥±¥Ñä¥ÌÕ¹…Ù…¥±…‰±”°ÍÑ½ÀÑÉÕÑ¡™Õ±±ä½È¥¹Ñ•É…Ñ”¥ÓŠQ¹•Ù•È(€€€™…‰É¥…Ñ”ÍÕ•ÍÌ¸(