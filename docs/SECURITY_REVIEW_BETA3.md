# GUIF v1.0.0-beta.3 Security Review

Release: `v1.0.0-beta.3`  
Codex plugin: `1.0.0-beta.3`  
Python package: `1.0.0b2`  
Public API Version: `1`

## Review scope

This review covers the beta.3 Candidate Change, Tool Trial, adoption, publication, plugin-refresh, and regression workflow. It focuses on authorization boundaries, stable/candidate isolation, Tool routing, evidence integrity, and private-data handling. It does not replace the beta.1 and beta.2 reviews of credentials, Gateway operations, backup and restore, external protection, migration, Pillow compatibility, or hash-only release provenance.

## Security properties retained

Beta.3 preserves these existing boundaries:

- real user Themes, prompts, images, credentials, Conversation records, runtime evidence, backups, and private paths remain outside the public repository;
- GUIF does not fabricate pixels, Tool availability, candidate outcomes, or semantic visual findings;
- metadata checks cannot claim semantic visual quality;
- `dry-run` is test/development-only and is never a silent production fallback;
- Legacy `ProviderAdapter` remains explicit compatibility only;
- public examples and regression fixtures are wholly fictional;
- public API compatibility remains governed by Public API Version `1`.

## Authorization separation

The improvement workflow has two independent approvals.

Trial approval authorizes only an isolated experiment. It does not authorize:

- candidate adoption;
- Git merge or release;
- stable Skill or framework replacement;
- stable Project or Workspace Tool-route mutation;
- presentation of candidate artifacts as stable production results.

Adoption approval is requested only after real candidate evidence is available. Publication and scoped configuration occur only after adoption.

Residual risk: a Host integration could present ambiguous approval language. Host implementations should keep the trial and adoption decisions visibly separate and preserve the recorded decision context.

## Stable and candidate isolation

Production Tasks and Improvement Cases are separate records. The Production Task is preserved at a checkpoint while candidate work proceeds. Candidate source, configuration, artifacts, and evidence must not overwrite stable state before adoption.

Code and Skill candidates run in a source-repository development environment rather than modifying the installed plugin snapshot. Tool trials use Task-only overrides. Stable Project and Workspace routing remains unchanged until explicit adoption with a confirmed scope.

Residual risk: external development tools can still mutate files outside GUIF's control. Repository permissions, branch protection, review policy, and CI remain necessary controls.

## Tool discovery and integration review

Before a Tool trial, GUIF surfaces:

- permissions and data scope;
- external calls and billing;
- credentials;
- Host support;
- registration, availability, and health.

An unavailable or unregistered Tool cannot be reported as a successful real trial. It becomes a Tool-integration candidate requiring an Adapter, permission disclosure, health checks, result callbacks, failure recovery, and contract tests.

Residual risk: GUIF can record disclosures and health results but cannot independently guarantee an external provider's privacy, security, billing accuracy, service availability, or model behavior.

## Evidence integrity

Candidate adoption requires a real candidate result. Visual candidates require real semantic inspection; metadata-only checks are insufficient. Candidate evidence remains distinct from stable baseline evidence, and candidate artifacts cannot be labeled as stable production output before adoption.

GUIF records candidate branch, commit, version, result, and publication identifiers where applicable. These records improve traceability but are not a cryptographic attestation. Repository signing, trusted builders, and third-party supply-chain verification remain separate concerns.

## Publication and refresh boundary

After adoption, framework-level changes enter a publication stage. The workflow records repository, branch, pull request, merge commit, and minimum plugin version. A running Codex session cannot claim that an installed plugin snapshot was hot-reloaded. The user must refresh Game UI Framework and start a new session before refresh confirmation.

Formal regression must reproduce the original scenario before the paused Production Task resumes.

Residual risk: a regression can cover the recorded scenario but cannot prove the absence of every unrelated defect. CI breadth and release review remain required.

## Privacy review

Improvement Cases, candidate evidence, source images, prompts, private development handoff bundles, credentials, and generated artifacts remain private by default. No real private material should be copied into public regression fixtures or committed to the source repository.

Tool trials may transmit user data to an external service only within the disclosed and approved Tool scope. Adoption of a Tool does not silently broaden that data scope.

## Conclusion

Beta.3 strengthens governance around framework self-improvement and Tool experimentation by separating authorization stages, isolating candidate state, requiring real evidence, constraining Tool-route scope, and requiring refresh plus regression before production resumes. It does not eliminate the need for repository controls, trustworthy external Tools, secure credential custody, CI, or independent release provenance.
