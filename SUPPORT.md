# GUIF Support Policy

This policy applies to `v1.0.0-beta.1`. It is a compatibility and maintenance statement, not a service-level agreement.

## Supported releases

- The current beta is supported until it is superseded by a newer beta.
- When practical and safe, the immediately previous beta may receive security fixes for 30 days after supersession.
- Direct upgrade assurance is provided from `v1.0.0-alpha.27` and `v1.0.0-alpha.28` to `v1.0.0-beta.1`.
- Earlier or unknown releases require a manual migration review.

## Frozen public contract

Beta.1 preserves public API version `1` and the conversation-facing stages/actions frozen in alpha.28. A breaking product-facing change requires:

1. a new public API version;
2. an explicit migration path;
3. synchronized tests, release notes, English/Chinese documentation, and package metadata.

Private schema changes must be detected before mutation and applied through a recorded migration. Silent private-data upgrades are not supported.

## Security reporting

Do not post any of the following in a public issue:

- Host credentials, bearer tokens, leases, claims, signing keys, or secret environment values;
- real Theme content, prompts, private Conversation records, images, Attachments, or backup archives;
- private paths or operational evidence that could identify a user project.

Provide a minimal redacted reproduction that uses fictional data. Revoke exposed credentials immediately.

## External dependencies

GUIF cannot guarantee availability or correctness of third-party Hosts, Tools, reverse proxies, encryption programs, secret managers, storage systems, or Git providers. External backup protection remains responsible for cryptography, key custody, and disaster recovery.

## Out of scope

The beta support window does not include:

- a hosted SLA;
- distributed consensus for file-backed leases and Work claims;
- automatic remote private-data synchronization;
- internet-edge reverse proxy operation;
- recovery of lost external encryption keys;
- removal of already published private data from forks, caches, or third-party clones.
