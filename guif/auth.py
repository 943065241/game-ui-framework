from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from guif.private_data import PrivateDataLayout

HOST_CREDENTIAL_SCHEMA_VERSION = 1
ACTOR_IDENTITY_SCHEMA_VERSION = 1
TOKEN_PREFIX = "guifh1"
PBKDF2_ITERATIONS = 200_000


class AuthenticationError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def _derive(secret: str, salt: bytes, iterations: int) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        secret.encode("utf-8"),
        salt,
        iterations,
    ).hex()


def _normalized(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


@dataclass(frozen=True)
class AuthenticatedActor:
    actor_id: str
    host_id: str
    credential_id: str
    capabilities: tuple[str, ...]
    roles: tuple[str, ...] = ()
    issuer: str = "guif-local"
    authentication_method: str = "private-bearer-token"
    authenticated_at: str = field(default_factory=_now)
    schema_version: int = ACTOR_IDENTITY_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["authenticated"] = True
        return payload

    def require(self, capabilities: Iterable[str]) -> None:
        missing = sorted(set(_normalized(capabilities)) - set(self.capabilities))
        if missing:
            raise AuthenticationError(
                f"Authenticated actor {self.actor_id} lacks capabilities: {', '.join(missing)}"
            )


class HostCredentialStore:
    """Private, file-backed Host credentials with one-time bearer secrets."""

    def __init__(self, workspace: Path, *, data_root: Path | None = None) -> None:
        self.workspace = workspace
        self.layout = PrivateDataLayout(workspace, data_root)

    def _path(self, credential_id: str) -> Path:
        if not credential_id or Path(credential_id).name != credential_id:
            raise ValueError(f"Invalid credential_id: {credential_id}")
        return self.layout.host_credentials / f"{credential_id}.json"

    @staticmethod
    def _public(record: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in record.items()
            if key not in {"secret_hash", "salt"}
        }

    def register(
        self,
        actor_id: str,
        host_id: str,
        capabilities: Iterable[str],
        *,
        roles: Iterable[str] = (),
        created_by: str = "local-admin",
        expires_at: str | None = None,
    ) -> dict[str, Any]:
        normalized_actor = actor_id.strip()
        normalized_host = host_id.strip()
        normalized_creator = created_by.strip()
        normalized_capabilities = _normalized(capabilities)
        normalized_roles = _normalized(roles)
        if not normalized_actor or not normalized_host or not normalized_creator:
            raise ValueError("actor_id, host_id, and created_by must not be empty")
        if not normalized_capabilities:
            raise ValueError("A Host credential requires at least one capability")

        credential_id = "cred-" + uuid4().hex[:16]
        secret = secrets.token_urlsafe(32)
        salt = secrets.token_bytes(16)
        record = {
            "schema_version": HOST_CREDENTIAL_SCHEMA_VERSION,
            "credential_id": credential_id,
            "actor_id": normalized_actor,
            "host_id": normalized_host,
            "capabilities": list(normalized_capabilities),
            "roles": list(normalized_roles),
            "status": "active",
            "issuer": "guif-local",
            "algorithm": "pbkdf2-hmac-sha256",
            "iterations": PBKDF2_ITERATIONS,
            "salt": salt.hex(),
            "secret_hash": _derive(secret, salt, PBKDF2_ITERATIONS),
            "created_by": normalized_creator,
            "created_at": _now(),
            "expires_at": expires_at,
            "revoked_at": None,
            "revoked_by": None,
            "revoke_reason": None,
        }
        _write_json(self._path(credential_id), record)
        return {
            "credential": self._public(record),
            "bearer_token": f"{TOKEN_PREFIX}.{credential_id}.{secret}",
            "secret_visible_once": True,
        }

    def list(self, *, include_revoked: bool = False) -> tuple[dict[str, Any], ...]:
        if not self.layout.host_credentials.exists():
            return ()
        records: list[dict[str, Any]] = []
        for path in sorted(self.layout.host_credentials.glob("cred-*.json")):
            try:
                record = _read_json(path)
            except (OSError, ValueError, json.JSONDecodeError):
                continue
            if include_revoked or record.get("status") == "active":
                records.append(self._public(record))
        records.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return tuple(records)

    def get(self, credential_id: str) -> dict[str, Any]:
        path = self._path(credential_id)
        if not path.is_file():
            raise ValueError(f"Unknown Host credential: {credential_id}")
        return self._public(_read_json(path))

    def authenticate(
        self,
        bearer_token: str,
        *,
        required_capabilities: Iterable[str] = (),
        expected_host_id: str | None = None,
    ) -> AuthenticatedActor:
        parts = bearer_token.strip().split(".", 2)
        if len(parts) != 3 or parts[0] != TOKEN_PREFIX:
            raise AuthenticationError("Invalid Host bearer token format")
        _, credential_id, secret = parts
        path = self._path(credential_id)
        if not path.is_file():
            raise AuthenticationError("Unknown Host credential")
        record = _read_json(path)
        if record.get("schema_version") != HOST_CREDENTIAL_SCHEMA_VERSION:
            raise AuthenticationError("Unsupported Host credential schema")
        if record.get("status") != "active":
            raise AuthenticationError(f"Host credential is not active: {record.get('status')}")
        expires_at = record.get("expires_at")
        if isinstance(expires_at, str) and expires_at:
            try:
                if datetime.fromisoformat(expires_at) <= datetime.now(timezone.utc):
                    raise AuthenticationError("Host credential has expired")
            except ValueError as exc:
                raise AuthenticationError("Host credential expiration is invalid") from exc
        if expected_host_id is not None and record.get("host_id") != expected_host_id:
            raise AuthenticationError(
                f"Host credential identity mismatch: expected {expected_host_id}, got {record.get('host_id')}"
            )
        try:
            salt = bytes.fromhex(str(record["salt"]))
            iterations = int(record["iterations"])
            actual = _derive(secret, salt, iterations)
        except (KeyError, TypeError, ValueError) as exc:
            raise AuthenticationError("Host credential verifier is invalid") from exc
        if not hmac.compare_digest(str(record.get("secret_hash") or ""), actual):
            raise AuthenticationError("Host bearer token verification failed")

        actor = AuthenticatedActor(
            actor_id=str(record["actor_id"]),
            host_id=str(record["host_id"]),
            credential_id=credential_id,
            capabilities=_normalized(record.get("capabilities", [])),
            roles=_normalized(record.get("roles", [])),
            issuer=str(record.get("issuer") or "guif-local"),
        )
        actor.require(required_capabilities)
        return actor

    def revoke(
        self,
        credential_id: str,
        *,
        actor: str,
        reason: str,
    ) -> dict[str, Any]:
        normalized_actor = actor.strip()
        normalized_reason = reason.strip()
        if not normalized_actor or not normalized_reason:
            raise ValueError("actor and reason must not be empty")
        path = self._path(credential_id)
        if not path.is_file():
            raise ValueError(f"Unknown Host credential: {credential_id}")
        record = _read_json(path)
        if record.get("status") == "revoked":
            return self._public(record)
        record["status"] = "revoked"
        record["revoked_at"] = _now()
        record["revoked_by"] = normalized_actor
        record["revoke_reason"] = normalized_reason
        _write_json(path, record)
        return self._public(record)

    def rotate(
        self,
        credential_id: str,
        *,
        actor: str,
        reason: str = "credential rotation",
    ) -> dict[str, Any]:
        current = self.get(credential_id)
        self.revoke(credential_id, actor=actor, reason=reason)
        replacement = self.register(
            str(current["actor_id"]),
            str(current["host_id"]),
            current.get("capabilities", []),
            roles=current.get("roles", []),
            created_by=actor,
            expires_at=current.get("expires_at"),
        )
        replacement["replaces_credential_id"] = credential_id
        return replacement


__all__ = [
    "ACTOR_IDENTITY_SCHEMA_VERSION",
    "AuthenticatedActor",
    "AuthenticationError",
    "HOST_CREDENTIAL_SCHEMA_VERSION",
    "HostCredentialStore",
]
