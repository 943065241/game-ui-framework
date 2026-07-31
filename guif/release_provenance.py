from __future__ import annotations

import hashlib
import json
import platform
import sys
import tarfile
import zipfile
from datetime import datetime, timezone
from email.parser import Parser
from pathlib import Path, PurePosixPath
from typing import Any

from guif import __version__

PROVENANCE_SCHEMA_VERSION = 1
DEFAULT_MANIFEST_NAME = "SHA256SUMS.json"


class ReleaseProvenanceError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _metadata_fields(text: str, source: str) -> tuple[str, str]:
    parsed = Parser().parsestr(text)
    name = str(parsed.get("Name") or "").strip()
    version = str(parsed.get("Version") or "").strip()
    if not name or not version:
        raise ReleaseProvenanceError(f"Artifact metadata is missing Name or Version: {source}")
    return name, version


def _wheel_metadata(path: Path) -> tuple[str, str]:
    try:
        with zipfile.ZipFile(path) as archive:
            candidates = sorted(
                name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
            )
            if len(candidates) != 1:
                raise ReleaseProvenanceError(
                    f"Wheel must contain exactly one dist-info METADATA file: {path.name}"
                )
            text = archive.read(candidates[0]).decode("utf-8")
    except (OSError, UnicodeDecodeError, zipfile.BadZipFile, KeyError) as exc:
        raise ReleaseProvenanceError(f"Invalid wheel artifact: {path.name}") from exc
    return _metadata_fields(text, path.name)


def _sdist_metadata(path: Path) -> tuple[str, str]:
    """Read the canonical top-level PKG-INFO from a source distribution.

    Setuptools sdists can also contain an ``*.egg-info/PKG-INFO`` copy. Only the
    canonical ``<sdist-root>/PKG-INFO`` member represents the archive metadata
    contract that build frontends consume.
    """

    try:
        with tarfile.open(path, mode="r:*") as archive:
            candidates = sorted(
                (
                    member
                    for member in archive.getmembers()
                    if member.isfile()
                    and PurePosixPath(member.name).name == "PKG-INFO"
                    and len(PurePosixPath(member.name).parts) == 2
                ),
                key=lambda member: member.name,
            )
            if len(candidates) != 1:
                raise ReleaseProvenanceError(
                    f"Source distribution must contain exactly one top-level PKG-INFO file: {path.name}"
                )
            extracted = archive.extractfile(candidates[0])
            if extracted is None:
                raise ReleaseProvenanceError(f"Could not read PKG-INFO: {path.name}")
            text = extracted.read().decode("utf-8")
    except (OSError, UnicodeDecodeError, tarfile.TarError) as exc:
        raise ReleaseProvenanceError(f"Invalid source distribution: {path.name}") from exc
    return _metadata_fields(text, path.name)


def _artifact_record(path: Path, artifact_type: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ReleaseProvenanceError(f"Release artifact must be a regular file: {path.name}")
    if artifact_type == "wheel":
        name, version = _wheel_metadata(path)
    elif artifact_type == "sdist":
        name, version = _sdist_metadata(path)
    else:
        raise ReleaseProvenanceError(f"Unsupported artifact type: {artifact_type}")
    return {
        "filename": path.name,
        "artifact_type": artifact_type,
        "size_bytes": path.stat().st_size,
        "sha256": _sha256_file(path),
        "metadata": {"name": name, "version": version},
    }


def _write_manifest(path: Path, payload: dict[str, Any]) -> None:
    if path.is_symlink():
        raise ReleaseProvenanceError("Provenance manifest must not be a symbolic link")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.exists() or temporary.is_symlink():
        temporary.unlink()
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _normalize_commit(value: str) -> str:
    commit = value.strip().lower()
    if len(commit) not in {40, 64} or any(
        character not in "0123456789abcdef" for character in commit
    ):
        raise ReleaseProvenanceError(
            "git_commit must be a 40- or 64-character hexadecimal commit identity"
        )
    return commit


def generate_hash_provenance(
    dist_dir: Path,
    *,
    git_commit: str,
    output_path: Path | None = None,
    expected_name: str = "aipg-framework",
    expected_version: str = __version__,
) -> dict[str, Any]:
    root = dist_dir.resolve()
    if not root.is_dir():
        raise ReleaseProvenanceError(f"Distribution directory does not exist: {root}")
    commit = _normalize_commit(git_commit)

    wheels = sorted(root.glob("*.whl"))
    sdists = sorted(root.glob("*.tar.gz"))
    if not wheels or not sdists:
        raise ReleaseProvenanceError("Both wheel and source distribution artifacts are required")

    artifacts = [
        *(_artifact_record(path, "wheel") for path in wheels),
        *(_artifact_record(path, "sdist") for path in sdists),
    ]
    metadata_pairs = {
        (record["metadata"]["name"], record["metadata"]["version"])
        for record in artifacts
    }
    if metadata_pairs != {(expected_name, expected_version)}:
        raise ReleaseProvenanceError(
            "Wheel and source distribution metadata must match the expected package name and version"
        )

    payload: dict[str, Any] = {
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "provenance_kind": "hash-only",
        "signature_present": False,
        "attestation_present": False,
        "package": {"name": expected_name, "version": expected_version},
        "git_commit": commit,
        "build_environment": {
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform": sys.platform,
        },
        "artifacts": artifacts,
        "generated_at": _now(),
    }
    destination = (output_path or (root / DEFAULT_MANIFEST_NAME)).resolve()
    _write_manifest(destination, payload)
    return {
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "status": "generated",
        "provenance_kind": "hash-only",
        "package": dict(payload["package"]),
        "git_commit": commit,
        "artifact_count": len(artifacts),
        "signature_present": False,
        "attestation_present": False,
        "manifest_written": True,
    }


def verify_hash_provenance(
    manifest_path: Path,
    *,
    dist_dir: Path | None = None,
    expected_git_commit: str | None = None,
) -> dict[str, Any]:
    manifest = manifest_path.resolve()
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseProvenanceError("Invalid release provenance manifest") from exc
    if not isinstance(payload, dict) or payload.get("schema_version") != PROVENANCE_SCHEMA_VERSION:
        raise ReleaseProvenanceError("Unsupported release provenance manifest schema")
    if payload.get("provenance_kind") != "hash-only":
        raise ReleaseProvenanceError("Unsupported provenance kind")
    if payload.get("signature_present") is not False or payload.get("attestation_present") is not False:
        raise ReleaseProvenanceError("Hash provenance must not claim a signature or attestation")
    manifest_commit = payload.get("git_commit")
    if not isinstance(manifest_commit, str):
        raise ReleaseProvenanceError("Provenance Git commit is missing")
    manifest_commit = _normalize_commit(manifest_commit)
    if expected_git_commit is not None and manifest_commit != _normalize_commit(expected_git_commit):
        raise ReleaseProvenanceError("Git commit does not match provenance manifest")

    package = payload.get("package")
    if not isinstance(package, dict):
        raise ReleaseProvenanceError("Provenance package metadata is missing")
    root = (dist_dir or manifest.parent).resolve()
    records = payload.get("artifacts")
    if not isinstance(records, list) or not records:
        raise ReleaseProvenanceError("Provenance manifest contains no artifacts")

    verified_types: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise ReleaseProvenanceError("Invalid provenance artifact record")
        filename = str(record.get("filename") or "")
        if not filename or Path(filename).name != filename:
            raise ReleaseProvenanceError("Unsafe artifact filename in provenance manifest")
        artifact_type = str(record.get("artifact_type") or "")
        path = root / filename
        actual = _artifact_record(path, artifact_type)
        if actual["size_bytes"] != record.get("size_bytes") or actual["sha256"] != record.get("sha256"):
            raise ReleaseProvenanceError(f"Artifact hash or size mismatch: {filename}")
        if actual["metadata"] != record.get("metadata"):
            raise ReleaseProvenanceError(f"Artifact metadata mismatch: {filename}")
        if actual["metadata"] != {
            "name": package.get("name"),
            "version": package.get("version"),
        }:
            raise ReleaseProvenanceError(f"Package metadata is inconsistent: {filename}")
        verified_types.add(artifact_type)
    if verified_types != {"wheel", "sdist"}:
        raise ReleaseProvenanceError("Provenance must verify both wheel and source distribution")

    return {
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "status": "verified",
        "provenance_kind": "hash-only",
        "package": dict(package),
        "git_commit": manifest_commit,
        "artifact_count": len(records),
        "signature_present": False,
        "attestation_present": False,
    }


__all__ = [
    "DEFAULT_MANIFEST_NAME",
    "PROVENANCE_SCHEMA_VERSION",
    "ReleaseProvenanceError",
    "generate_hash_provenance",
    "verify_hash_provenance",
]
