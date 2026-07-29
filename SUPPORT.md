# GUIF Support Policy

This policy applies to `v1.0.0-beta.2`. It is a compatibility and maintenance statement, not a service-level agreement.

## Supported releases

- The current beta is supported until it is superseded by a newer beta.
- When practical and safe, the immediately previous beta may receive security fixes for 30 days after supersession.
- Direct upgrade assurance is provided from `v1.0.0-alpha.27` and `v1.0.0-alpha.28` to the current beta implementation, `v1.0.0-beta.2`.
- Earlier, unknown, or future releases require a manual migration review.

## Frozen public contract

Beta.2 preserves public API version `1` and the conversation-facing stages/actions frozen in alpha.28. A breaking product-facing change requires:

1. a new public API version;
2. an explicit migration path;
3. synchronized tests, release notes, English/Chinese documentation, product specification, and package metadata.

Private schema changes must be detected before mutation and applied through a recorded migration. Silent private-data upgrades are not supported.

The explicit Legacy `ProviderAdapter` remains a compatibility path. ChatGPT, `chatgpt-image`, and `chatgpt-vision` remain defaults, not mandatory Core dependencies. `dry-run` remains test/development-only and is not a production fallback.

## Release provenance scope

Beta.2 provides hash-only provenance for built wheel and source distribution artifacts. It records artifact SHA-256, size, package metadata, Git commit, and basic build-environment metadata.

This policy does not claim:

- a cryptographic publisher signature;
- a trusted build attestation;
- a third-party supply-chain certification;
- protection when both artifacts and the manifest are replaced by the same attacker.

A future release must integrate a real signing or trusted-attestation system before making any signed-provenance claim.

## Security reporting

Do not post any of the following in a public issue:

- Host credentials, bearer tokens, leases, claims, signing keys, or secret environment values;
- real Theme content, prompts, private Conversation records, images, Attachments, or backup archives;
- private paths or operational evidence that could identify a user project.

Provide a minimal redacted reproduction that uses wholly fictional data. Revoke exposed credentials immediately.

## External dependencies

GUIF cannot guarantee availability or correctness of third-party Hosts, Tools, reverse proxies, encryption programs, secret managers, storage systems, or Git providers. External backup protection remains responsible for cryptography, key custody, and disaster recovery.

## Out of scope

The beta support window does not include:

- a hosted SLA;
- release signing or trusted build attestation;
- distributed consensus for file-backed leases and Work claims;
- automatic remote private-data synchronization;
- internet-edge reverse proxy operation;
- recovery of lost external encryption keys;
- removal of already published private data from forks, caches, or third-party clones.
