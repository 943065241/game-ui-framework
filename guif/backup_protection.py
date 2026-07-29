from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Protocol

from guif.fault_injection import FaultInjector

PROTECTION_SCHEMA_VERSION = 1
PROTECT_COMMAND_ENV = "GUIF_BACKUP_PROTECT_COMMAND_JSON"
UNPROTECT_COMMAND_ENV = "GUIF_BACKUP_UNPROTECT_COMMAND_JSON"
PROTECTOR_ID_ENV = "GUIF_BACKUP_PROTECTOR_ID"
PROTECT_TIMEOUT_ENV = "GUIF_BACKUP_PROTECT_TIMEOUT_SECONDS"


class BackupProtectionError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _private_permissions(path: Path) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    if path.is_symlink():
        raise BackupProtectionError("Protection receipt must not be a symbolic link")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    if temporary.is_symlink() or (temporary.exists() and not temporary.is_file()):
        raise BackupProtectionError("Protection receipt temporary path is unsafe")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _private_permissions(temporary)
    temporary.replace(path)
    _private_permissions(path)


def _read_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackupProtectionError(f"Invalid protection receipt: {path}") from exc
    if not isinstance(value, dict):
        raise BackupProtectionError("Protection receipt must be a JSON object")
    return value


def _validate_regular(path: Path, label: str) -> Path:
    raw = path.expanduser()
    if raw.is_symlink():
        raise BackupProtectionError(f"{label} must not be a symbolic link")
    resolved = raw.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Unknown {label.lower()}: {resolved}")
    return resolved


def _validate_destination(path: Path, label: str) -> Path:
    raw = path.expanduser()
    if raw.is_symlink():
        raise BackupProtectionError(f"{label} must not be a symbolic link")
    if raw.exists():
        raise BackupProtectionError(f"{label} already exists; GUIF will not overwrite it")
    resolved = raw.resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def _receipt_path(protected_path: Path) -> Path:
    return protected_path.with_suffix(protected_path.suffix + ".guif-protection.json")


def _normalize_argv(values: Iterable[str]) -> tuple[str, ...]:
    argv = tuple(str(value) for value in values)
    if not argv or any(not value for value in argv):
        raise ValueError("External protection argv must contain non-empty strings")
    placeholders = " ".join(argv)
    if "{input}" not in placeholders or "{output}" not in placeholders:
        raise ValueError("External protection argv must include {input} and {output}")
    return argv


class BackupProtectionAdapter(Protocol):
    adapter_id: str

    def protect(self, source: Path, destination: Path) -> None:
        ...

    def unprotect(self, source: Path, destination: Path) -> None:
        ...


@dataclass(frozen=True)
class ExternalCommandProtectionAdapter:
    """Run a configured encryption/decryption program without a shell.

    GUIF does not implement custom cryptography. The external program owns its
    algorithm, key management, and secret environment variables. GUIF supplies
    only canonical input/output paths, timeout enforcement, atomic publication,
    hashes, and a secret-free receipt.
    """

    adapter_id: str
    protect_argv: tuple[str, ...]
    unprotect_argv: tuple[str, ...]
    timeout_seconds: int = 300

    def __post_init__(self) -> None:
        normalized_id = self.adapter_id.strip()
        if not normalized_id or Path(normalized_id).name != normalized_id:
            raise ValueError("adapter_id must be a non-empty path-safe identifier")
        object.__setattr__(self, "adapter_id", normalized_id)
        object.__setattr__(self, "protect_argv", _normalize_argv(self.protect_argv))
        object.__setattr__(self, "unprotect_argv", _normalize_argv(self.unprotect_argv))
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

    @staticmethod
    def _expand(argv: tuple[str, ...], source: Path, destination: Path) -> list[str]:
        return [
            value.replace("{input}", str(source)).replace("{output}", str(destination))
            for value in argv
        ]

    def _run(self, argv: tuple[str, ...], source: Path, destination: Path) -> None:
        command = self._expand(argv, source, destination)
        try:
            completed = subprocess.run(
                command,
                shell=False,
                check=False,
                capture_output=True,
                timeout=self.timeout_seconds,
                env=os.environ.copy(),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise BackupProtectionError(
                f"Backup protection adapter {self.adapter_id} could not complete"
            ) from exc
        if completed.returncode != 0:
            raise BackupProtectionError(
                f"Backup protection adapter {self.adapter_id} failed with exit code "
                f"{completed.returncode}"
            )
        if destination.is_symlink() or not destination.is_file():
            raise BackupProtectionError(
                f"Backup protection adapter {self.adapter_id} did not create a regular output file"
            )
        if destination.stat().st_size <= 0:
            raise BackupProtectionError(
                f"Backup protection adapter {self.adapter_id} created an empty output file"
            )

    def protect(self, source: Path, destination: Path) -> None:
        self._run(self.protect_argv, source, destination)

    def unprotect(self, source: Path, destination: Path) -> None:
        self._run(self.unprotect_argv, source, destination)


class BackupProtectionService:
    def __init__(
        self,
        adapter: BackupProtectionAdapter,
        *,
        fault_injector: FaultInjector | None = None,
    ) -> None:
        self.adapter = adapter
        self.faults = fault_injector or FaultInjector.disabled()

    def protect(self, archive_path: Path, protected_path: Path) -> dict[str, Any]:
        source = _validate_regular(archive_path, "Backup archive")
        destination = _validate_destination(protected_path, "Protected backup destination")
        receipt_path = _receipt_path(destination)
        if receipt_path.exists() or receipt_path.is_symlink():
            raise BackupProtectionError(
                "Protection receipt destination already exists; GUIF will not overwrite it"
            )
        temporary = destination.with_suffix(destination.suffix + ".protect.tmp")
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()
        try:
            self.adapter.protect(source, temporary)
            self.faults.hit("backup-protection.before-publish")
            protected_sha256 = _sha256_file(temporary)
            temporary.replace(destination)
            _private_permissions(destination)
            receipt = {
                "schema_version": PROTECTION_SCHEMA_VERSION,
                "status": "protected",
                "adapter_id": self.adapter.adapter_id,
                "source": {
                    "filename": source.name,
                    "sha256": _sha256_file(source),
                    "size_bytes": source.stat().st_size,
                },
                "protected": {
                    "filename": destination.name,
                    "sha256": protected_sha256,
                    "size_bytes": destination.stat().st_size,
                },
                "secret_material_persisted": False,
                "command_persisted": False,
                "created_at": _now(),
            }
            _write_json(receipt_path, receipt)
            return {
                **receipt,
                "protected_path": str(destination),
                "receipt_path": str(receipt_path),
            }
        except Exception:
            if destination.exists() and not receipt_path.exists():
                destination.unlink()
            raise
        finally:
            if temporary.exists() or temporary.is_symlink():
                temporary.unlink()

    def verify(self, protected_path: Path) -> dict[str, Any]:
        protected = _validate_regular(protected_path, "Protected backup")
        receipt_path = _receipt_path(protected)
        if receipt_path.is_symlink() or not receipt_path.is_file():
            raise BackupProtectionError("Protected backup is missing its receipt")
        receipt = _read_object(receipt_path)
        if receipt.get("schema_version") != PROTECTION_SCHEMA_VERSION:
            raise BackupProtectionError(
                f"Unsupported protection receipt schema: {receipt.get('schema_version')}"
            )
        if receipt.get("adapter_id") != self.adapter.adapter_id:
            raise BackupProtectionError(
                "Protection adapter identity does not match the protected backup receipt"
            )
        protected_record = receipt.get("protected")
        if not isinstance(protected_record, dict):
            raise BackupProtectionError("Protection receipt is missing protected file evidence")
        if protected_record.get("filename") != protected.name:
            raise BackupProtectionError("Protected backup filename does not match its receipt")
        if int(protected_record.get("size_bytes", -1)) != protected.stat().st_size:
            raise BackupProtectionError("Protected backup size does not match its receipt")
        actual_sha256 = _sha256_file(protected)
        if protected_record.get("sha256") != actual_sha256:
            raise BackupProtectionError("Protected backup SHA-256 does not match its receipt")
        return {
            "schema_version": 1,
            "status": "verified",
            "adapter_id": self.adapter.adapter_id,
            "protected_path": str(protected),
            "protected_sha256": actual_sha256,
            "receipt_path": str(receipt_path),
            "source": receipt.get("source"),
            "secret_material_persisted": False,
        }

    def unprotect(self, protected_path: Path, archive_path: Path) -> dict[str, Any]:
        verification = self.verify(protected_path)
        protected = Path(verification["protected_path"])
        destination = _validate_destination(archive_path, "Recovered backup destination")
        temporary = destination.with_suffix(destination.suffix + ".unprotect.tmp")
        if temporary.exists() or temporary.is_symlink():
            temporary.unlink()
        try:
            self.adapter.unprotect(protected, temporary)
            self.faults.hit("backup-protection.before-recovery-publish")
            source_record = verification.get("source")
            if not isinstance(source_record, dict):
                raise BackupProtectionError("Protection receipt is missing source evidence")
            if int(source_record.get("size_bytes", -1)) != temporary.stat().st_size:
                raise BackupProtectionError("Recovered backup size does not match source evidence")
            actual_sha256 = _sha256_file(temporary)
            if source_record.get("sha256") != actual_sha256:
                raise BackupProtectionError("Recovered backup SHA-256 does not match source evidence")
            temporary.replace(destination)
            _private_permissions(destination)
            return {
                "schema_version": 1,
                "status": "recovered",
                "adapter_id": self.adapter.adapter_id,
                "archive_path": str(destination),
                "archive_sha256": actual_sha256,
                "protected_path": str(protected),
                "completed_at": _now(),
            }
        finally:
            if temporary.exists() or temporary.is_symlink():
                temporary.unlink()


def _argv_from_env(name: str) -> tuple[str, ...]:
    raw = os.environ.get(name)
    if not raw:
        raise BackupProtectionError(f"Required external backup protection setting is missing: {name}")
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BackupProtectionError(f"{name} must be a JSON array of argv strings") from exc
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise BackupProtectionError(f"{name} must be a JSON array of argv strings")
    return tuple(value)


def external_adapter_from_env() -> ExternalCommandProtectionAdapter:
    adapter_id = os.environ.get(PROTECTOR_ID_ENV, "external-encryption-tool")
    try:
        timeout_seconds = int(os.environ.get(PROTECT_TIMEOUT_ENV, "300"))
    except ValueError as exc:
        raise BackupProtectionError(f"{PROTECT_TIMEOUT_ENV} must be an integer") from exc
    return ExternalCommandProtectionAdapter(
        adapter_id=adapter_id,
        protect_argv=_argv_from_env(PROTECT_COMMAND_ENV),
        unprotect_argv=_argv_from_env(UNPROTECT_COMMAND_ENV),
        timeout_seconds=timeout_seconds,
    )


__all__ = [
    "BackupProtectionAdapter",
    "BackupProtectionError",
    "BackupProtectionService",
    "ExternalCommandProtectionAdapter",
    "PROTECTION_SCHEMA_VERSION",
    "external_adapter_from_env",
]
