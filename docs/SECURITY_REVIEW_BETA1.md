# GUIF v1.0.0-beta.1 Security Review

Reviewed: 2026-07-29

## Scope

This review covers the beta.1 changes: external backup protection, protected-backup receipts, alpha upgrade assurance, fault injection, soak checks, packaging verification, and support policy. Existing Theme privacy, authenticated Host Gateway, Task leases, Work claims, signed operation ledger, Approval gates, visual review, Revision, Gated Export, and Git controls remain governed by their existing contracts.

## Threat model

Relevant attackers include:

- a process able to replace or tamper with backup/protection files;
- a malicious or misconfigured external encryption command;
- accidental secret disclosure through receipts, logs, command arguments, reports, or public fixtures;
- path traversal, symbolic-link substitution, output collision, or partial-file publication;
- an operator attempting an unsupported or unbacked upgrade;
- a forgotten failure-injection setting in a production environment;
- malformed private records intended to trigger silent migration.

An attacker with unrestricted access to the machine, external encryption keys, GUIF private data root, and full ability to rewrite every local record remains outside the local-only trust boundary.

## Findings and controls

### No custom cryptography

GUIF does not implement an encryption algorithm. `ExternalCommandProtectionAdapter` invokes an explicitly configured argv array with `shell=False`. The external program owns cryptographic design and key custody.

Risk retained: a weak or malicious external program can produce insecure output. GUIF verifies file identity and round-trip evidence, not cryptographic strength.

### No silent fallback

Missing or invalid protection configuration fails closed. GUIF does not silently copy an unprotected archive when protection was requested.

### Secret handling

Protection receipts persist only:

- adapter identifier;
- source/protected filenames;
- byte sizes;
- SHA-256 hashes;
- timestamps and schema/status markers.

They do not persist command argv, subprocess stdout/stderr, passphrases, key files, or secret environment values. External tools should read secrets from a protected secret manager, file descriptor, agent, or environment according to their own security model.

### Command execution

Commands are passed directly to `subprocess.run` with `shell=False`, a bounded timeout, and explicit `{input}`/`{output}` placeholders. GUIF does not concatenate a shell command string.

Risk retained: an operator can intentionally configure an unsafe executable or unsafe arguments. Adapter configuration is an administrative trust decision.

### File publication

Protected and recovered outputs are first written to a temporary path. GUIF requires a non-empty regular file, verifies evidence, and publishes via rename. Existing destination and receipt paths are rejected rather than overwritten.

The fault-injection test interrupts protection immediately before publication and confirms that:

- the original verified archive remains unchanged;
- the protected destination is absent;
- the temporary output is removed.

### Tamper evidence

A protection receipt binds the protected filename, size, SHA-256, adapter identity, and original archive evidence. Verification rejects a modified protected file, missing receipt, receipt schema mismatch, adapter mismatch, size mismatch, or hash mismatch.

This is tamper evidence, not authenticity against an attacker who can rewrite both the file and receipt. Long-term authenticity should use an external signed/encrypted backup system.

### Upgrade safety

Upgrade assurance requires an explicit source release. Alpha.27 and alpha.28 are supported. Unknown releases fail closed. A portable backup is required by default. Private schema blockers and raw secret-like fields prevent automatic migration. Applied repairs are recorded.

### Fault injection safety

Environment-driven faults require both a named point and `GUIF_ALLOW_FAULT_INJECTION=1`. A fault-point variable alone raises an error instead of enabling injection. Production deployments should unset both variables.

### Soak privacy

Soak reports contain aggregate timings, counts, sanitized error types/codes, and observed public stages. They do not include Task IDs, leases, claims, bearer tokens, raw Theme content, or Artifact bytes.

### Public repository privacy

All added tests use fictional names and content. No real user Theme, Conversation, image, credential, backup, or operational record is committed.

## Residual risks

- External encryption strength and key recovery are outside GUIF Core.
- SHA-256 receipts do not replace digital signatures or remote immutable storage.
- Local file permissions are best-effort and depend on the operating system and filesystem.
- Subprocess environment inheritance can expose secrets to the selected external executable by design.
- File-backed coordination is not suitable for untrusted multi-node distributed execution.
- Current privacy checks cannot erase data already published to forks, caches, logs, or third-party clones.

## Release decision

No beta.1 blocker was identified within the stated local-first trust boundary. Release is acceptable provided documentation continues to state that GUIF supplies a protection integration boundary, not built-in cryptography or key management.
