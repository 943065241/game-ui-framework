# GUIF v1.0.0-beta.2 Security Review

Release: `v1.0.0-beta.2`  
Python package: `1.0.0b2`  
Public API Version: `1`

## Review scope

This review covers the beta.2 changes for Pillow compatibility, wheel/sdist hash provenance, extended non-mutating soak profiles, upgrade fixtures, and external backup protection adapter contract tests. It does not replace the beta.1 review of the broader private-data, Host Gateway, operation-ledger, backup, migration, and external protection architecture.

## Security properties retained

Beta.2 preserves the following boundaries:

- real Theme, Prompt, image, Conversation Record, Credential, Backup, Private Path, and runtime evidence stay outside the public repository;
- public fixtures are wholly fictional;
- GUIF does not fabricate image pixels or semantic visual-review results;
- metadata-only checks cannot claim Theme consistency, composition, readability, or usability;
- `dry-run` is limited to testing/development and is never a silent production fallback;
- ChatGPT, `chatgpt-image`, and `chatgpt-vision` remain defaults but are replaceable;
- Legacy `ProviderAdapter` remains an explicit compatibility path;
- external backup protection uses argv with `shell=False`, bounded timeout, required placeholders, non-empty regular output, collision rejection, atomic publication, and no unprotected fallback;
- GUIF persists no external protection command argv, key, passphrase, or secret environment value.

## Pillow compatibility review

The new pixel-data compatibility helper prefers the non-deprecated Pillow API and retains the old API only when the new method is unavailable. It does not alter pixel values, mask semantics, tolerance calculations, or protected-region counting.

CI promotes Pillow `DeprecationWarning` instances to errors, preventing the known warning class from silently returning.

Residual risk: a future Pillow release may change behavior beyond method naming. This requires normal dependency compatibility testing; it is not mitigated by pretending image semantics were inspected.

## Hash provenance review

The release provenance manifest binds built artifacts to:

- SHA-256 and byte size;
- package name and package version extracted from each artifact;
- a caller-supplied Git commit identity;
- basic build-environment metadata.

Verification rejects modified artifacts, metadata disagreement, unsafe filenames, missing wheel/sdist coverage, unsupported manifest claims, and expected-commit mismatch.

The manifest explicitly states:

```text
provenance_kind = hash-only
signature_present = false
attestation_present = false
```

This prevents GUIF from overstating the assurance level. Hash provenance detects accidental corruption and post-manifest artifact changes when the manifest itself is trusted. It does not establish publisher identity, trusted-builder identity, timestamp authority, or protection against an attacker who can replace both artifacts and manifest.

Recommended future improvement: integrate a real signing or trusted build-attestation system before making any signed-provenance claim.

## Soak profile review

Soak checks remain read-only and report `production_state_mutated=false`. An independently selected report path writes only the derived machine-readable report; it does not mutate GUIF production records.

Performance threshold failure is separated from contract correctness failure. This avoids turning normal machine variance into a false product-security or correctness claim.

Residual risk: local timing is environment-sensitive and should not be compared across unrelated hosts without controlled benchmarking conditions.

## Upgrade fixture review

The expanded test matrix validates fail-closed handling of unknown future schemas, invalid JSON, and secret-like field names. Secret values are not echoed into public test assertions or reports.

The fixtures contain no real user records, names, paths, credentials, images, prompts, or backup material.

## Backup protection adapter review

The expanded tests exercise timeout, process failure, malformed output, symlink output, collisions, receipt tampering, adapter identity mismatch, and recovered-hash mismatch. The expected result in every failure case is fail-closed behavior with source preservation and no accepted partial publication.

GUIF still does not assess external algorithm quality, key custody, key rotation, or recoverability. Those remain the external Tool/operator responsibility.

## Compatibility review

Public API Version remains `1`. The alpha.28 frozen Conversation Stage and Action sets are unchanged. Any future breaking change must increase the Public API Version and provide an explicit migration path.

## Conclusion

Beta.2 narrows maintenance and release-engineering risk without expanding GUIF into a custom cryptography, image-generation, semantic-vision, signing, or distributed-coordination system. The implemented assurance level is accurately described as compatibility maintenance, fail-closed contract testing, non-mutating hardening checks, and hash-only artifact provenance.
