# GUIF v1.0.0-beta.2 Release Notes

Release: `v1.0.0-beta.2`  
Python package: `1.0.0b2`  
Public API Version: `1`

## Summary

Beta.2 is a maintenance and release-provenance hardening release. It preserves the Conversation stages and actions frozen in alpha.28 while improving Pillow compatibility, release artifact verification, non-mutating soak profiles, upgrade fixtures, and backup protection adapter coverage.

## Pillow maintenance

GUIF now uses a small compatibility boundary for flattened pixel access:

- prefers Pillow's current `get_flattened_data()` API when available;
- retains `getdata()` only as an explicit compatibility path for supported older Pillow releases;
- keeps protected-region pixel comparison and masked-composition counting behavior unchanged;
- CI treats Pillow deprecation warnings as errors.

GUIF still does not infer or fabricate semantic visual quality from pixel metadata.

## Release artifact hash provenance

`guif-ready provenance` now generates and verifies `dist/SHA256SUMS.json` for built wheel and source distribution artifacts.

The manifest records:

- package name and version;
- Git commit identity;
- Python implementation/version and build platform;
- artifact filenames, sizes, and SHA-256 hashes;
- wheel `METADATA` and sdist `PKG-INFO` package metadata.

Generation fails unless both wheel and sdist are present and their metadata agrees with GUIF `1.0.0b2`. Verification fails on modified size, hash, metadata, unsafe filenames, missing artifact types, or commit mismatch.

This release declares **hash-only provenance**. It does not claim a cryptographic signature, trusted builder attestation, or external supply-chain certification.

## Extended non-mutating soak profiles

The `guif-ready soak` command now supports:

```text
quick       10 iterations
standard    100 iterations
extended    1000 iterations
```

`--iterations` remains available as an explicit custom override. `--report` can write a separate machine-readable JSON report. Every report continues to state:

```text
mutating_operations_performed=false
production_state_mutated=false
```

A P95 threshold miss is classified as host/environment performance evidence. It is not, by itself, reported as a GUIF product correctness failure.

## Upgrade assurance fixture expansion

Public tests now cover wholly fictional records for:

- alpha.27 current and migration-required states;
- alpha.28 current and migration-required states;
- unknown future schemas;
- invalid JSON;
- secret-like fields without echoing secret values;
- backup missing and backup present cases.

Supported upgrades remain alpha.27 and alpha.28 to the current beta implementation. Unknown sources and blocked private schemas fail closed.

## External backup protection adapter contract expansion

Public contract tests now cover:

- bounded timeout;
- external non-zero exit;
- empty or missing output;
- symbolic-link output;
- receipt and destination collisions;
- tampered receipt;
- wrong adapter identity;
- recovered archive hash mismatch.

The external boundary still uses `shell=False`, requires `{input}` and `{output}`, refuses overwrite, publishes atomically, and has no unprotected fallback. GUIF does not implement custom encryption or persist command argv, keys, passphrases, or secret environment values.

## Compatibility

The compatibility contract remains:

```text
release = 1.0.0-alpha.28
origin_release = 1.0.0-alpha.28
current_release = 1.0.0-beta.2
channel = beta
public_api_version = 1
```

The frozen Conversation Stage and Action sets are unchanged. The Legacy `ProviderAdapter` remains an explicit compatibility path. ChatGPT, `chatgpt-image`, and `chatgpt-vision` remain defaults, while Host and Tool contracts remain replaceable. `dry-run` remains test/development-only and is not a production fallback.

## CI and distribution

CI runs on Python 3.10, 3.11, and 3.12 and performs:

1. tests with Pillow deprecation warnings promoted to errors;
2. wheel and sdist build;
3. hash provenance generation and verification;
4. generated-wheel installation;
5. `guif.__version__ == "1.0.0b2"` verification;
6. `guif-ready contract` smoke testing.

## Privacy

No real user Theme, Prompt, image, Conversation Record, Credential, Backup, Private Path, or private runtime evidence is included. Public fixtures are wholly fictional.
