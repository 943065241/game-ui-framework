# GUIF v1.0.0-beta.3 Release Notes

Release: `v1.0.0-beta.3`  
Codex plugin: `1.0.0-beta.3`  
Python package: `1.0.0b2`  
Public API Version: `1`

## Summary

Beta.3 adds a governed Candidate Change and Tool Trial workflow to GUIF's production loop. Production work can pause at a safe checkpoint while an isolated Improvement Case diagnoses a framework, Skill, workflow, Theme-policy, provider-routing, or Tool problem. The candidate must then pass its own trial approval, evidence review, adoption decision, publication or scoped configuration step, plugin refresh when required, and formal regression before the original Production Task resumes.

This release does not treat trial approval as permission to adopt, merge, publish, replace a stable Tool route, or overwrite stable framework behavior.

## Candidate Change workflow

GUIF now records framework improvement as an object separate from the Production Task that exposed the problem.

The workflow supports:

- preserving the Production Task checkpoint while diagnosis and experimentation proceed;
- classifying the affected layer instead of assuming every problem is a Skill defect;
- recording observed behavior, expected behavior, diagnosis, candidate changes, validation, privacy constraints, and a fictional public regression fixture;
- building code or Skill candidates in an isolated source-repository development session;
- linking candidate branches, commits, and versions;
- recording real stable-baseline and candidate evidence;
- requiring an explicit user decision to adopt, continue adjusting, or reject the candidate;
- publishing adopted framework changes and running a formal regression before resuming production.

## Two independent approval gates

Beta.3 separates:

1. **Trial approval**, which authorizes only an isolated experiment.
2. **Adoption approval**, which is available only after real candidate evidence is presented.

Neither approval is inferred from the other. Trial approval does not authorize Git merge, release, stable configuration mutation, or plugin replacement.

## Tool discovery and isolated Tool trials

A Tool change is now evaluated as a capability-routing decision:

- a registered, available, and healthy Tool can be selected for a Task-only trial;
- stable Project and Workspace routes remain unchanged during the trial;
- permissions, data scope, external calls, billing, credentials, Host support, registration, availability, and health must be disclosed before use;
- an unavailable or unregistered Tool becomes a Tool-integration candidate instead of a simulated successful trial;
- unsupported integrations require an Adapter, permission disclosure, health checks, real result callbacks, failure recovery, and contract tests.

Adopted Tool-route changes apply only to the user-confirmed Task, Project, or Workspace scope.

## Real evidence and visual review

A candidate cannot be adopted without a real candidate result. Visual candidates additionally require real semantic visual inspection. Metadata-only checks cannot claim composition, readability, Theme consistency, noise reduction, or usability.

Candidate evidence remains isolated from stable production evidence. Candidate artifacts are not presented as stable production outputs before adoption.

## Publication, refresh, and regression

Adopted code, Skill, workflow, Theme-policy, provider-routing, and Tool-integration changes enter a publication stage. GUIF records the repository, branch, pull request, merge commit, and minimum plugin version.

When a refreshed plugin is required, the current Host session cannot claim hot reload. The user must refresh Game UI Framework and start a new Codex session. Formal regression then reproduces the original scenario. Production resumes only after the regression passes or the candidate is explicitly rejected.

## Compatibility

Public API Version remains `1`, and the Python package remains `1.0.0b2`. Beta.3 changes the Codex plugin workflow without claiming a Python package version increase. Existing production approval, revision, semantic review, Gated Export, recovery, privacy, and provenance boundaries remain in force.

## CI and validation

The beta.3 repository reports:

- 177 passing tests;
- Python 3.10, 3.11, and 3.12 coverage;
- wheel and source-distribution build checks;
- hash-provenance generation and verification;
- generated-wheel installation;
- CLI contract checks.

## Privacy

Real user Themes, prompts, images, Conversation records, credentials, candidate evidence, private development bundles, and generated artifacts remain outside the public repository by default. Public examples and regression fixtures must be wholly fictional.
