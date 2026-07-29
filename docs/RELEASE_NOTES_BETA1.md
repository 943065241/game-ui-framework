# GUIF v1.0.0-beta.1 Release Notes

Release date: 2026-07-29

## Summary

Beta.1 hardens the alpha.28 frozen MVP without expanding the normal conversation workflow. Public API version `1`, the conversation-facing stages/actions, the private Theme boundary, ChatGPT-first Host/Tool defaults, Approval gates, semantic visual review, controlled Revision, Gated Export, and explicit legacy Provider compatibility remain intact.

## New production-hardening controls

### External backup protection boundary

GUIF now supports a configured external encryption/decryption program through `BackupProtectionService` and `ExternalCommandProtectionAdapter`.

The adapter:

- executes an argv array with `shell=False`;
- requires explicit `{input}` and `{output}` placeholders;
- enforces a timeout;
- requires a non-empty regular output file;
- publishes protected/recovered files atomically;
- refuses to overwrite an existing destination or receipt;
- records source/protected SHA-256 and size evidence;
- never persists the external command or secret environment values.

GUIF deliberately does not implement custom cryptography. The external program remains responsible for algorithms, key generation, key custody, rotation, and recovery.

New commands:

```text
guif-ready backup-protect
guif-ready backup-protection-verify
guif-ready backup-unprotect
```

The CLI reads external adapter settings from environment variables and has no silent unprotected fallback.

### Supported alpha upgrade assurance

`UpgradeAssuranceService` supports explicit upgrade planning and recorded execution from:

```text
1.0.0-alpha.27
1.0.0-alpha.28
```

The default gate requires a portable backup, checks private schema state, blocks unsupported source releases and secret-bearing records, applies only recorded supported repairs, and verifies that public API version `1` remains preserved.

New command:

```text
guif-ready upgrade --source-release 1.0.0-alpha.28
```

Use `--apply` only after reviewing the plan and creating a verified backup.

### Fault injection gate

The new `FaultInjector` is disabled by default. Environment-driven faults require both:

```text
GUIF_FAULT_POINTS=<named points>
GUIF_ALLOW_FAULT_INJECTION=1
```

Beta.1 tests inject failures immediately before protected backup publication and verify that the original archive remains valid and temporary/protected outputs are not left behind.

Fault injection is a test/development facility and is never a production fallback.

### Bounded soak and latency checks

`HardeningService.soak()` repeatedly exercises non-mutating production reads:

- Project validation;
- private schema scan;
- signed operation-ledger verification;
- non-persisting Conversation stage derivation;
- optional backup verification.

It records iteration counts, sanitized failures, total/mean/p50/p95/max latency, and an optional p95 threshold in the private hardening report area.

New command:

```text
guif-ready soak
```

### Packaged installation verification

CI now builds both wheel and source distribution on Python 3.10, 3.11, and 3.12, installs the generated wheel, checks `guif.__version__`, and runs a `guif-ready contract` smoke test after installation.

### Support and deprecation contract

`guif-ready support` and `SUPPORT.md` publish the beta support window, supported upgrade sources, security-reporting rules, and breaking-change requirements.

## Compatibility

The compatibility document preserves the existing `release: 1.0.0-alpha.28` field as the origin of the frozen public contract. Beta.1 adds:

```text
current_release: 1.0.0-beta.1
channel: beta
```

This avoids changing the meaning of an existing field while making the active implementation explicit.

## Privacy

No real user Theme, prompt, Conversation record, credential, image, backup, or operational evidence is included in this release. Public tests use wholly fictional fixtures.

Portable backups continue to exclude Host credential verifiers and operation-ledger signing keys. Protection receipts contain hashes and filenames but no secret material or command argv.

## Known limitations

- GUIF does not bundle or endorse a specific encryption program.
- Protected files are only recoverable while the external program and its keys remain available.
- File-backed leases and Work claims remain single-node coordination.
- The built-in WSGI Gateway is not an internet-edge reverse proxy.
- ChatGPT product integration must still embed the Host loop or consume the authenticated Gateway API.
- Existing Pillow `Image.getdata()` deprecation warnings remain and are scheduled for a later maintenance release.
