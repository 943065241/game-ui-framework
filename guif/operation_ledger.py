from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from guif.private_data import PrivateDataLayout

OPERATION_LEDGER_SCHEMA_VERSION = 1
OPERATION_LEDGER_KEY_SCHEMA_VERSION = 1
OPERATION_LEDGER_HEAD_SCHEMA_VERSION = 1
OPERATION_LEDGER_ALGORITHM = "hmac-sha256-chain-v1"
GENESIS_HASH = "0" * 64


class OperationLedgerError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _write_json(path: Path, payload: Any, *, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if private:
        try:
            os.chmod(temporary, 0o600)
        except OSError:
            pass
    temporary.replace(path)
    if private:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise OperationLedgerError(f"Expected JSON object: {path}")
    return value


class OperationLedger:
    """Append-only private HMAC chain for authenticated GUIF operations.

    This ledger provides local tamper evidence. It is not a public-key signature,
    remote timestamp authority, or protection against an attacker who can read the
    private signing key and rewrite every private ledger file.
    """

    def __init__(self, workspace: Path, *, data_root: Path | None = None) -> None:
        self.workspace = workspace
        self.layout = PrivateDataLayout(workspace, data_root)
        self.root = self.layout.operation_ledger
        self.entries_path = self.root / "entries.jsonl"
        self.head_path = self.root / "head.json"
        self.key_path = self.root / "signing-key.json"
        self._lock = threading.RLock()

    def _load_key(self, *, create: bool) -> dict[str, Any] | None:
        if self.key_path.is_file():
            record = _read_json(self.key_path)
            if record.get("schema_version") != OPERATION_LEDGER_KEY_SCHEMA_VERSION:
                raise OperationLedgerError("Unsupported operation ledger key schema")
            if record.get("algorithm") != OPERATION_LEDGER_ALGORITHM:
                raise OperationLedgerError("Unsupported operation ledger signing algorithm")
            try:
                secret = base64.urlsafe_b64decode(str(record["secret_b64"]).encode("ascii"))
            except (KeyError, ValueError, TypeError) as exc:
                raise OperationLedgerError("Operation ledger signing key is invalid") from exc
            if len(secret) < 32:
                raise OperationLedgerError("Operation ledger signing key is too short")
            return record
        if not create:
            return None
        secret = secrets.token_bytes(32)
        record = {
            "schema_version": OPERATION_LEDGER_KEY_SCHEMA_VERSION,
            "key_id": "ledger-key-" + secrets.token_hex(8),
            "algorithm": OPERATION_LEDGER_ALGORITHM,
            "secret_b64": base64.urlsafe_b64encode(secret).decode("ascii"),
            "created_at": _now(),
        }
        _write_json(self.key_path, record, private=True)
        return record

    @staticmethod
    def _secret(key_record: dict[str, Any]) -> bytes:
        return base64.urlsafe_b64decode(str(key_record["secret_b64"]).encode("ascii"))

    @staticmethod
    def _public_entry(entry: dict[str, Any]) -> dict[str, Any]:
        return _json_safe(entry)

    def _read_entries(self) -> list[dict[str, Any]]:
        if not self.entries_path.is_file():
            return []
        entries: list[dict[str, Any]] = []
        for line_number, line in enumerate(
            self.entries_path.read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise OperationLedgerError(
                    f"Operation ledger line {line_number} is invalid JSON"
                ) from exc
            if not isinstance(value, dict):
                raise OperationLedgerError(
                    f"Operation ledger line {line_number} is not a JSON object"
                )
            entries.append(value)
        return entries

    def _head(self) -> dict[str, Any] | None:
        return _read_json(self.head_path) if self.head_path.is_file() else None

    def descriptor(self) -> dict[str, Any]:
        key = self._load_key(create=False)
        head = self._head()
        return {
            "schema_version": OPERATION_LEDGER_SCHEMA_VERSION,
            "algorithm": OPERATION_LEDGER_ALGORITHM,
            "key_id": key.get("key_id") if isinstance(key, dict) else None,
            "status": "initialized" if key else "uninitialized",
            "entry_count": int(head.get("sequence", 0)) if isinstance(head, dict) else 0,
            "head_entry_hash": head.get("entry_hash") if isinstance(head, dict) else None,
            "private_storage": True,
            "limitations": [
                "local HMAC tamper evidence, not public-key non-repudiation",
                "an attacker with the private signing key can forge a replacement ledger",
            ],
        }

    def append(
        self,
        operation: str,
        status: str,
        *,
        actor: dict[str, Any] | str | None = None,
        scope: dict[str, Any] | None = None,
        details: dict[str, Any] | None = None,
        operation_id: str | None = None,
    ) -> dict[str, Any]:
        normalized_operation = operation.strip()
        normalized_status = status.strip()
        if not normalized_operation or not normalized_status:
            raise ValueError("operation and status must not be empty")
        normalized_operation_id = operation_id.strip() if isinstance(operation_id, str) else None
        if normalized_operation_id == "":
            raise ValueError("operation_id must not be empty")

        with self._lock:
            verification = self.verify()
            if verification["status"] == "invalid":
                raise OperationLedgerError(
                    "Operation ledger integrity verification failed: "
                    + "; ".join(verification.get("errors", []))
                )
            key = self._load_key(create=True)
            assert key is not None
            entries = self._read_entries()
            if normalized_operation_id:
                existing = next(
                    (
                        item
                        for item in entries
                        if item.get("operation_id") == normalized_operation_id
                    ),
                    None,
                )
                if isinstance(existing, dict):
                    return self._public_entry(existing)

            head = self._head()
            sequence = (int(head.get("sequence", 0)) if isinstance(head, dict) else 0) + 1
            previous_hash = (
                str(head.get("entry_hash"))
                if isinstance(head, dict) and head.get("entry_hash")
                else GENESIS_HASH
            )
            payload = {
                "schema_version": OPERATION_LEDGER_SCHEMA_VERSION,
                "sequence": sequence,
                "operation_id": normalized_operation_id,
                "occurred_at": _now(),
                "operation": normalized_operation,
                "status": normalized_status,
                "actor": _json_safe(actor),
                "scope": _json_safe(scope or {}),
                "details": _json_safe(details or {}),
                "previous_entry_hash": previous_hash,
                "key_id": key["key_id"],
            }
            payload_hash = _sha256(payload)
            entry_hash = _sha256(
                {
                    "sequence": sequence,
                    "previous_entry_hash": previous_hash,
                    "payload_hash": payload_hash,
                    "key_id": key["key_id"],
                }
            )
            signature = hmac.new(
                self._secret(key),
                _canonical_bytes(
                    {
                        "algorithm": OPERATION_LEDGER_ALGORITHM,
                        "key_id": key["key_id"],
                        "entry_hash": entry_hash,
                    }
                ),
                hashlib.sha256,
            ).hexdigest()
            entry = {
                **payload,
                "payload_hash": payload_hash,
                "entry_hash": entry_hash,
                "signature": signature,
                "entry_id": f"ledger-{sequence:012d}-{entry_hash[:12]}",
            }
            self.root.mkdir(parents=True, exist_ok=True)
            with self.entries_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
                handle.flush()
                try:
                    os.fsync(handle.fileno())
                except OSError:
                    pass
            head_record = {
                "schema_version": OPERATION_LEDGER_HEAD_SCHEMA_VERSION,
                "algorithm": OPERATION_LEDGER_ALGORITHM,
                "key_id": key["key_id"],
                "sequence": sequence,
                "entry_id": entry["entry_id"],
                "entry_hash": entry_hash,
                "signature": signature,
                "updated_at": _now(),
            }
            _write_json(self.head_path, head_record, private=True)
            return self._public_entry(entry)

    def list(
        self,
        *,
        limit: int = 100,
        operations: Iterable[str] = (),
        reverse: bool = True,
    ) -> tuple[dict[str, Any], ...]:
        if limit < 1 or limit > 10_000:
            raise ValueError("limit must be between 1 and 10000")
        selected = {item.strip() for item in operations if item.strip()}
        entries = self._read_entries()
        if selected:
            entries = [item for item in entries if str(item.get("operation")) in selected]
        if reverse:
            entries.reverse()
        return tuple(self._public_entry(item) for item in entries[:limit])

    def verify(self) -> dict[str, Any]:
        with self._lock:
            errors: list[str] = []
            entries: list[dict[str, Any]]
            try:
                entries = self._read_entries()
            except OperationLedgerError as exc:
                return {
                    "schema_version": 1,
                    "status": "invalid",
                    "valid": False,
                    "entry_count": 0,
                    "errors": [str(exc)],
                    "verified_at": _now(),
                }
            key = self._load_key(create=False)
            head = self._head()
            if not entries:
                if isinstance(head, dict) and int(head.get("sequence", 0)) != 0:
                    errors.append("Ledger head exists but entries are missing")
                return {
                    "schema_version": 1,
                    "status": "invalid" if errors else "empty",
                    "valid": not errors,
                    "entry_count": 0,
                    "key_id": key.get("key_id") if isinstance(key, dict) else None,
                    "head": head,
                    "errors": errors,
                    "verified_at": _now(),
                }
            if key is None:
                errors.append("Ledger entries exist but the signing key is missing")
                secret = b""
                key_id = None
            else:
                secret = self._secret(key)
                key_id = key.get("key_id")

            previous_hash = GENESIS_HASH
            for expected_sequence, entry in enumerate(entries, start=1):
                sequence = entry.get("sequence")
                if sequence != expected_sequence:
                    errors.append(
                        f"Entry sequence mismatch at position {expected_sequence}: {sequence}"
                    )
                if entry.get("previous_entry_hash") != previous_hash:
                    errors.append(f"Previous hash mismatch at sequence {expected_sequence}")
                payload = {
                    key: entry.get(key)
                    for key in (
                        "schema_version",
                        "sequence",
                        "operation_id",
                        "occurred_at",
                        "operation",
                        "status",
                        "actor",
                        "scope",
                        "details",
                        "previous_entry_hash",
                        "key_id",
                    )
                }
                payload_hash = _sha256(payload)
                if entry.get("payload_hash") != payload_hash:
                    errors.append(f"Payload hash mismatch at sequence {expected_sequence}")
                calculated_entry_hash = _sha256(
                    {
                        "sequence": sequence,
                        "previous_entry_hash": entry.get("previous_entry_hash"),
                        "payload_hash": payload_hash,
                        "key_id": entry.get("key_id"),
                    }
                )
                if entry.get("entry_hash") != calculated_entry_hash:
                    errors.append(f"Entry hash mismatch at sequence {expected_sequence}")
                if key_id is not None and entry.get("key_id") != key_id:
                    errors.append(f"Key identity mismatch at sequence {expected_sequence}")
                if secret:
                    expected_signature = hmac.new(
                        secret,
                        _canonical_bytes(
                            {
                                "algorithm": OPERATION_LEDGER_ALGORITHM,
                                "key_id": entry.get("key_id"),
                                "entry_hash": calculated_entry_hash,
                            }
                        ),
                        hashlib.sha256,
                    ).hexdigest()
                    if not hmac.compare_digest(
                        str(entry.get("signature") or ""), expected_signature
                    ):
                        errors.append(f"Signature mismatch at sequence {expected_sequence}")
                previous_hash = str(entry.get("entry_hash") or calculated_entry_hash)

            last = entries[-1]
            if not isinstance(head, dict):
                errors.append("Ledger head checkpoint is missing")
            else:
                if head.get("sequence") != len(entries):
                    errors.append("Ledger head sequence does not match the entry count")
                if head.get("entry_hash") != last.get("entry_hash"):
                    errors.append("Ledger head hash does not match the final entry")
                if head.get("signature") != last.get("signature"):
                    errors.append("Ledger head signature does not match the final entry")
                if key_id is not None and head.get("key_id") != key_id:
                    errors.append("Ledger head key identity does not match the signing key")
            return {
                "schema_version": 1,
                "status": "invalid" if errors else "verified",
                "valid": not errors,
                "entry_count": len(entries),
                "key_id": key_id,
                "head": head,
                "errors": errors,
                "verified_at": _now(),
            }


__all__ = [
    "OPERATION_LEDGER_ALGORITHM",
    "OPERATION_LEDGER_SCHEMA_VERSION",
    "OperationLedger",
    "OperationLedgerError",
]
