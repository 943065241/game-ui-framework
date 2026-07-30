# GUIF Candidate Change and Tool Trial Workflow

GUIF keeps production work and framework improvement work separate.

```text
Production Conversation
  ├─ Production Task: design, image work, review, revision, export
  └─ Improvement Case: diagnose, trial, review, adopt, publish, refresh, regress
```

An Improvement Case is private and stored outside Project Git. The production Task is paused by reference; it is not converted into a code-development Task.

## Why two approvals are required

A request to “improve the Skill” or “try another Tool” does not prove that the proposed change is better. GUIF therefore uses two independent decisions:

```text
proposal
  -> trial approval
  -> isolated candidate
  -> real result review
  -> adoption approval
  -> publication or scoped Tool routing
```

Trial approval authorizes only an experiment. It does not authorize a merge, plugin update, or stable Tool-route mutation. Adoption approval is unavailable until real candidate evidence exists.

## Candidate Change types

```text
skill-change
framework-change
tool-change
tool-integration-change
theme-policy-change
workflow-change
provider-routing-change
multi-layer-change
```

Repeated image noise is not automatically classified as a Skill defect. The diagnosis should consider Prompt IR, protected edit scope, Theme policy, semantic review, cumulative revisions, and Tool behavior.

## Lifecycle

```text
proposal-required
trial-approval-required
candidate-building | candidate-ready
candidate-running
result-review-required
publishing-required
plugin-refresh-required
regression-validation-required
resolved
```

The rejection path ends in `closed-stable-retained`, after which the original production Task may resume without adopting the candidate.

## Code and Skill candidates

After trial approval, GUIF creates a private sanitized development handoff bundle. Development happens in the GUIF source repository on a candidate branch. The installed plugin snapshot must not be edited in place.

Before adoption:

- the candidate must remain unmerged;
- real user images must not be committed as public fixtures;
- candidate output must not be represented as stable production output;
- real image or semantic evidence must be recorded privately;
- public regression tests must use wholly fictional fixtures.

After the user reviews the real candidate result and approves adoption, the source-repository session may complete tests, CI, PR, and merge. Publication records repository, branch, PR, merge commit, and minimum plugin version. The user then refreshes the plugin, starts a new Codex session, and replays the original scenario.

## Tool trials

A Tool change is not always a framework code change.

GUIF first discovers the requested Tool and exposes its registration, availability, health, Host support, permissions, data scope, external calls, billing, and credential requirements.

```text
registered + available + healthy
  -> isolated Tool trial
  -> Task-only execution override
  -> stable Project/Workspace routing remains unchanged

unknown, unavailable, unregistered, unhealthy, or installable-only
  -> tool-integration-change
  -> Adapter candidate and contract validation
```

After a successful reviewed Tool trial, adoption applies only to the explicitly approved scope:

```text
task
project
workspace
```

Figma or another structured-design Tool should be routed by capability. It may replace a structured layout step without replacing raster illustration generation, pixel editing, semantic vision, or engine export.

## Privacy boundary

Private data includes:

```text
<private-data-root>/improvement-cases/
  <project>/
    improvement-*.json
    <case-id>/
      development-bundle.json
      evidence/
```

Public conversation views omit private paths, SHA-256 values, Task IDs, and raw evidence bytes. Improvement records, user images, prompts, and candidate outputs remain outside Project Git by default.

## Failure and recovery

A failed formal regression reopens candidate building. It does not silently mark the improvement as resolved. The original production Task resumes only after:

- the adopted candidate passes the required formal regression; or
- the user explicitly rejects the candidate and retains the stable version.

Production dry-run fallback, fabricated pixels, invented semantic findings, and silent Legacy ProviderAdapter routing remain prohibited.
