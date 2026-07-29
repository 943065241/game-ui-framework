from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import ssl
from datetime import datetime, timezone
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Any, Callable, Iterable
from urllib.parse import parse_qs, unquote
from uuid import uuid4
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from guif import __version__
from guif.auth import AuthenticationError
from guif.concurrency import ConcurrencyError, LeaseError
from guif.gated_export import GatedExportError
from guif.host_api import HostCallbackError
from guif.operation_ledger import OperationLedgerError
from guif.private_data import PrivateDataLayout
from guif.runtime import Runtime

HOST_GATEWAY_SCHEMA_VERSION = 1
GATEWAY_REQUEST_SCHEMA_VERSION = 1
DEFAULT_MAX_BODY_BYTES = 32 * 1024 * 1024
MAX_JSON_BODY_BYTES = 1024 * 1024
GATEWAY_READ_CAPABILITY = "gateway:read"
TASK_READ_CAPABILITY = "task:read"
LEDGER_READ_CAPABILITY = "ledger:read"


class HostGatewayError(RuntimeError):
    pass


class RequestTooLarge(HostGatewayError):
    pass


class IdempotencyConflict(HostGatewayError):
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


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        os.chmod(temporary, 0o600)
    except OSError:
        pass
    temporary.replace(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _header(environ: dict[str, Any], name: str) -> str | None:
    key = "HTTP_" + name.upper().replace("-", "_")
    value = environ.get(key)
    if value is None and name.lower() == "content-type":
        value = environ.get("CONTENT_TYPE")
    if value is None and name.lower() == "content-length":
        value = environ.get("CONTENT_LENGTH")
    return str(value) if value is not None else None


def _bearer(environ: dict[str, Any]) -> str:
    value = _header(environ, "Authorization") or ""
    prefix = "Bearer "
    if not value.startswith(prefix) or not value[len(prefix) :].strip():
        raise AuthenticationError("Missing or invalid Authorization bearer token")
    return value[len(prefix) :].strip()


def _required_header(environ: dict[str, Any], name: str) -> str:
    value = _header(environ, name)
    if value is None or not value.strip():
        raise ValueError(f"Missing required header: {name}")
    return value.strip()


def _etag_header(environ: dict[str, Any]) -> str:
    value = _header(environ, "If-Match") or _header(environ, "X-GUIF-Task-Etag")
    if value is None or not value.strip():
        raise ValueError("Missing required Task etag header: If-Match or X-GUIF-Task-Etag")
    normalized = value.strip()
    if normalized.startswith('W/"') and normalized.endswith('"'):
        normalized = normalized[3:-1]
    elif normalized.startswith('"') and normalized.endswith('"'):
        normalized = normalized[1:-1]
    if not normalized.startswith("task-sha256:"):
        raise ValueError("Task etag must use the task-sha256 format")
    return normalized


def _int_header(environ: dict[str, Any], name: str) -> int | None:
    value = _header(environ, name)
    if value is None or not value.strip():
        return None
    parsed = int(value)
    if parsed < 1:
        raise ValueError(f"{name} must be a positive integer")
    return parsed


def _safe_segment(value: str, label: str) -> str:
    decoded = unquote(value)
    if not decoded or decoded in {".", ".."} or "/" in decoded or "\\" in decoded:
        raise ValueError(f"Invalid {label}")
    return decoded


def _read_body(environ: dict[str, Any], *, maximum: int) -> bytes:
    length_value = _header(environ, "Content-Length")
    if length_value is not None and length_value.strip():
        try:
            length = int(length_value)
        except ValueError as exc:
            raise ValueError("Content-Length must be an integer") from exc
        if length < 0:
            raise ValueError("Content-Length must not be negative")
        if length > maximum:
            raise RequestTooLarge(f"Request body exceeds the {maximum}-byte limit")
        body = environ["wsgi.input"].read(length)
    else:
        body = environ["wsgi.input"].read(maximum + 1)
    if len(body) > maximum:
        raise RequestTooLarge(f"Request body exceeds the {maximum}-byte limit")
    return body


def _json_body(environ: dict[str, Any]) -> dict[str, Any]:
    content_type = (_header(environ, "Content-Type") or "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise ValueError("JSON endpoint requires Content-Type: application/json")
    body = _read_body(environ, maximum=MAX_JSON_BODY_BYTES)
    try:
        value = json.loads(body.decode("utf-8")) if body else {}
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Request body must be a UTF-8 JSON object") from exc
    if not isinstance(value, dict):
        raise ValueError("Request body must be a JSON object")
    return value


class GatewayRequestStore:
    """Private idempotency records. One-time secrets are never persisted."""

    def __init__(self, workspace: Path) -> None:
        self.layout = PrivateDataLayout(workspace)

    def _path(self, idempotency_key: str) -> Path:
        digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()
        return self.layout.gateway_requests / f"request-{digest}.json"

    def get(self, idempotency_key: str) -> dict[str, Any] | None:
        path = self._path(idempotency_key)
        return _read_json(path) if path.is_file() else None

    def begin(
        self,
        idempotency_key: str,
        *,
        method: str,
        path: str,
        request_hash: str,
    ) -> tuple[dict[str, Any], bool]:
        destination = self._path(idempotency_key)
        if destination.is_file():
            return _read_json(destination), False
        record = {
            "schema_version": GATEWAY_REQUEST_SCHEMA_VERSION,
            "request_id": "gateway-request-" + uuid4().hex,
            "idempotency_key_sha256": hashlib.sha256(
                idempotency_key.encode("utf-8")
            ).hexdigest(),
            "method": method,
            "path": path,
            "request_hash": request_hash,
            "status": "processing",
            "http_status": None,
            "response": None,
            "secret_replayable": False,
            "created_at": _now(),
            "completed_at": None,
            "error": None,
        }
        destination.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
        try:
            descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            return _read_json(destination), False
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(serialized)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        return record, True

    def complete(
        self,
        idempotency_key: str,
        record: dict[str, Any],
        *,
        http_status: int,
        response: dict[str, Any],
        secret_replayable: bool,
    ) -> dict[str, Any]:
        record["status"] = "completed"
        record["http_status"] = http_status
        record["response"] = response
        record["secret_replayable"] = secret_replayable
        record["completed_at"] = _now()
        record["error"] = None
        _write_json(self._path(idempotency_key), record)
        return record

    def fail(
        self,
        idempotency_key: str,
        record: dict[str, Any],
        *,
        http_status: int,
        error: dict[str, Any],
    ) -> dict[str, Any]:
        record["status"] = "failed"
        record["http_status"] = http_status
        record["completed_at"] = _now()
        record["error"] = error
        _write_json(self._path(idempotency_key), record)
        return record


class ProductionHostGateway:
    """Small authenticated WSGI boundary for production Host operations."""

    def __init__(
        self,
        workspace: Path,
        *,
        runtime: Runtime | None = None,
        max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    ) -> None:
        if max_body_bytes < 1024:
            raise ValueError("max_body_bytes must be at least 1024")
        self.workspace = workspace.resolve()
        self.runtime = runtime or Runtime(self.workspace)
        self.max_body_bytes = max_body_bytes
        self.requests = GatewayRequestStore(self.workspace)

    @staticmethod
    def _response(
        start_response: Callable[..., Any],
        status: int,
        payload: dict[str, Any],
        *,
        extra_headers: Iterable[tuple[str, str]] = (),
    ) -> list[bytes]:
        reason = {
            200: "OK",
            201: "Created",
            400: "Bad Request",
            401: "Unauthorized",
            404: "Not Found",
            409: "Conflict",
            413: "Payload Too Large",
            422: "Unprocessable Entity",
            500: "Internal Server Error",
            503: "Service Unavailable",
        }.get(status, "Error")
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        headers = [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Content-Length", str(len(body))),
            ("Cache-Control", "no-store"),
            ("X-Content-Type-Options", "nosniff"),
        ]
        headers.extend(extra_headers)
        start_response(f"{status} {reason}", headers)
        return [body]

    def _ledger_request(
        self,
        *,
        status: str,
        method: str,
        path: str,
        request_id: str,
        actor: dict[str, Any] | None,
        http_status: int,
        details: dict[str, Any],
    ) -> None:
        self.runtime.operation_ledger.append(
            "gateway.request",
            status,
            actor=actor,
            scope={"method": method, "path": path},
            details={
                "request_id": request_id,
                "http_status": http_status,
                **details,
            },
            operation_id=f"gateway:{request_id}:{status}",
        )

    @staticmethod
    def _idempotency_key(environ: dict[str, Any]) -> str:
        value = _required_header(environ, "Idempotency-Key")
        if len(value) > 128 or any(ord(character) < 33 or ord(character) > 126 for character in value):
            raise ValueError("Idempotency-Key must be 1-128 visible ASCII characters")
        return value

    def _mutation(
        self,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
        *,
        body: bytes,
        actor: dict[str, Any] | None,
        action: Callable[[], tuple[int, dict[str, Any], dict[str, Any], bool]],
        fingerprint_headers: dict[str, Any] | None = None,
    ) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD") or "POST").upper()
        path = str(environ.get("PATH_INFO") or "/")
        key = self._idempotency_key(environ)
        request_hash = hashlib.sha256(
            _canonical_bytes(
                {
                    "method": method,
                    "path": path,
                    "body_sha256": hashlib.sha256(body).hexdigest(),
                    "headers": fingerprint_headers or {},
                }
            )
        ).hexdigest()
        record, created = self.requests.begin(
            key,
            method=method,
            path=path,
            request_hash=request_hash,
        )
        request_id = str(record["request_id"])
        if not created:
            if record.get("request_hash") != request_hash:
                raise IdempotencyConflict(
                    "Idempotency-Key was already used for a different request"
                )
            if record.get("status") == "completed":
                if not record.get("secret_replayable"):
                    raise IdempotencyConflict(
                        "Completed request returned a one-time secret and cannot be replayed; inspect current state and use a new Idempotency-Key"
                    )
                response = dict(record.get("response") or {})
                response["idempotent_replay"] = True
                return self._response(
                    start_response,
                    int(record.get("http_status") or 200),
                    response,
                    extra_headers=(("X-GUIF-Request-ID", request_id),),
                )
            raise IdempotencyConflict(
                f"Idempotency-Key is already associated with request status {record.get('status')}"
            )

        try:
            http_status, response, stored_response, secret_replayable = action()
        except Exception as exc:
            error_status, code = self._error_status(exc)
            self.requests.fail(
                key,
                record,
                http_status=error_status,
                error={"type": type(exc).__name__, "code": code},
            )
            try:
                self._ledger_request(
                    status="failed",
                    method=method,
                    path=path,
                    request_id=request_id,
                    actor=actor,
                    http_status=error_status,
                    details={"error_type": type(exc).__name__, "error_code": code},
                )
            except Exception:
                pass
            raise
        self.requests.complete(
            key,
            record,
            http_status=http_status,
            response=stored_response,
            secret_replayable=secret_replayable,
        )
        self._ledger_request(
            status="completed",
            method=method,
            path=path,
            request_id=request_id,
            actor=actor,
            http_status=http_status,
            details={"response_status": stored_response.get("status")},
        )
        return self._response(
            start_response,
            http_status,
            response,
            extra_headers=(("X-GUIF-Request-ID", request_id),),
        )

    @staticmethod
    def _error_status(exc: Exception) -> tuple[int, str]:
        if isinstance(exc, AuthenticationError):
            return 401, "authentication-failed"
        if isinstance(exc, RequestTooLarge):
            return 413, "request-too-large"
        if isinstance(exc, FileNotFoundError):
            return 404, "not-found"
        if isinstance(exc, (ConcurrencyError, LeaseError, IdempotencyConflict)):
            return 409, "operation-conflict"
        if isinstance(exc, (HostCallbackError, GatedExportError)):
            return 422, "operation-rejected"
        if isinstance(exc, OperationLedgerError):
            return 503, "ledger-unavailable"
        if isinstance(exc, (ValueError, KeyError, json.JSONDecodeError)):
            return 400, "invalid-request"
        if isinstance(exc, RuntimeError):
            return 409, "runtime-conflict"
        return 500, "internal-error"

    def _descriptor(self, actor: dict[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": HOST_GATEWAY_SCHEMA_VERSION,
            "service": "guif-production-host-gateway",
            "version": __version__,
            "status": "ready",
            "authenticated_actor": actor,
            "host": self.runtime.get_host_profile(),
            "max_body_bytes": self.max_body_bytes,
            "operation_ledger": self.runtime.operation_ledger_descriptor(),
            "endpoints": [
                "GET /health",
                "GET /v1/descriptor",
                "GET /v1/tasks/{project}/{task_id}/summary",
                "POST /v1/tasks/{project}/{task_id}/lease",
                "POST /v1/tasks/{project}/{task_id}/approvals/{approval_id}",
                "POST /v1/tasks/{project}/{task_id}/callbacks/{handoff_id}",
                "POST /v1/tasks/{project}/{task_id}/exports",
                "GET /v1/ledger/verify",
                "GET /v1/ledger/entries?limit=100",
            ],
            "security": {
                "bearer_authentication": True,
                "capability_authorization": True,
                "task_etag_required_for_mutation": True,
                "task_lease_required_for_exclusive_mutation": True,
                "idempotency_key_required_for_post": True,
                "cors_enabled": False,
                "secrets_persisted_in_gateway_receipts": False,
            },
        }

    def __call__(
        self,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD") or "GET").upper()
        path = str(environ.get("PATH_INFO") or "/")
        try:
            if method == "GET" and path == "/health":
                verification = self.runtime.verify_operation_ledger()
                healthy = verification.get("status") != "invalid"
                return self._response(
                    start_response,
                    200 if healthy else 503,
                    {
                        "schema_version": HOST_GATEWAY_SCHEMA_VERSION,
                        "service": "guif-production-host-gateway",
                        "version": __version__,
                        "status": "healthy" if healthy else "degraded",
                        "operation_ledger": verification,
                    },
                )

            segments = [segment for segment in path.strip("/").split("/") if segment]
            if method == "GET" and segments == ["v1", "descriptor"]:
                token = _bearer(environ)
                actor = self.runtime.authenticate_actor(
                    token,
                    required_capabilities=(GATEWAY_READ_CAPABILITY,),
                )
                return self._response(start_response, 200, self._descriptor(actor.to_dict()))

            if method == "GET" and segments == ["v1", "ledger", "verify"]:
                token = _bearer(environ)
                self.runtime.authenticate_actor(
                    token,
                    required_capabilities=(LEDGER_READ_CAPABILITY,),
                )
                return self._response(start_response, 200, self.runtime.verify_operation_ledger())

            if method == "GET" and segments == ["v1", "ledger", "entries"]:
                token = _bearer(environ)
                self.runtime.authenticate_actor(
                    token,
                    required_capabilities=(LEDGER_READ_CAPABILITY,),
                )
                query = parse_qs(str(environ.get("QUERY_STRING") or ""))
                limit = int(query.get("limit", ["100"])[0])
                return self._response(
                    start_response,
                    200,
                    {
                        "schema_version": 1,
                        "entries": list(self.runtime.list_operation_ledger(limit=limit)),
                    },
                )

            if len(segments) >= 5 and segments[:2] == ["v1", "tasks"]:
                project = _safe_segment(segments[2], "project")
                task_id = _safe_segment(segments[3], "task_id")

                if method == "GET" and segments[4:] == ["summary"]:
                    token = _bearer(environ)
                    actor = self.runtime.authenticate_actor(
                        token,
                        required_capabilities=(TASK_READ_CAPABILITY,),
                    )
                    payload = self.runtime.operation_summary(project, task_id)
                    payload["authenticated_actor"] = actor.to_dict()
                    return self._response(
                        start_response,
                        200,
                        payload,
                        extra_headers=(("ETag", f'"{payload["task_etag"]}"'),),
                    )

                if method == "POST" and segments[4:] == ["lease"]:
                    body = _read_body(environ, maximum=MAX_JSON_BODY_BYTES)
                    content_type = (_header(environ, "Content-Type") or "").split(";", 1)[0].strip().lower()
                    if content_type != "application/json":
                        raise ValueError("Lease endpoint requires Content-Type: application/json")
                    try:
                        request = json.loads(body.decode("utf-8")) if body else {}
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise ValueError("Lease request must be a UTF-8 JSON object") from exc
                    if not isinstance(request, dict):
                        raise ValueError("Lease request must be a JSON object")
                    token = _bearer(environ)
                    actor = self.runtime.authenticate_actor(
                        token,
                        required_capabilities=("task:lease",),
                    )
                    expected = request.get("expected_task_etag")
                    if expected is None:
                        expected = self.runtime.get_task_etag(project, task_id)
                    ttl = request.get("ttl_seconds", 300)
                    purpose = request.get("purpose", "host-gateway-operation")

                    def acquire() -> tuple[int, dict[str, Any], dict[str, Any], bool]:
                        result = self.runtime.acquire_task_lease(
                            project,
                            task_id,
                            bearer_token=token,
                            expected_task_etag=str(expected),
                            ttl_seconds=int(ttl),
                            purpose=str(purpose),
                        )
                        response = {
                            "schema_version": 1,
                            "status": "created",
                            "lease": result["lease"],
                            "lease_token": result["lease_token"],
                            "secret_visible_once": True,
                        }
                        stored = {
                            "schema_version": 1,
                            "status": "created",
                            "lease": result["lease"],
                            "secret_visible_once": True,
                            "secret_replayable": False,
                        }
                        return 201, response, stored, False

                    return self._mutation(
                        environ,
                        start_response,
                        body=body,
                        actor=actor.to_dict(),
                        action=acquire,
                        fingerprint_headers={"content_type": content_type},
                    )

                if (
                    method == "POST"
                    and len(segments) == 6
                    and segments[4] == "approvals"
                ):
                    approval_id = _safe_segment(segments[5], "approval_id")
                    body = _read_body(environ, maximum=MAX_JSON_BODY_BYTES)
                    content_type = (_header(environ, "Content-Type") or "").split(";", 1)[0].strip().lower()
                    if content_type != "application/json":
                        raise ValueError("Approval endpoint requires Content-Type: application/json")
                    try:
                        request = json.loads(body.decode("utf-8")) if body else {}
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise ValueError("Approval request must be a UTF-8 JSON object") from exc
                    if not isinstance(request, dict):
                        raise ValueError("Approval request must be a JSON object")
                    token = _bearer(environ)
                    actor = self.runtime.authenticate_actor(
                        token,
                        required_capabilities=("approval:decide",),
                    )
                    lease_token = _required_header(environ, "X-GUIF-Lease-Token")
                    expected = _etag_header(environ)
                    decision = str(request.get("decision") or "")
                    comment = request.get("comment")

                    def decide() -> tuple[int, dict[str, Any], dict[str, Any], bool]:
                        task = self.runtime.decide_approval_authenticated(
                            project,
                            task_id,
                            approval_id,
                            decision,
                            bearer_token=token,
                            lease_token=lease_token,
                            expected_task_etag=expected,
                            comment=str(comment) if comment is not None else None,
                        )
                        state = task.state.get("approval_state", {})
                        receipt = {
                            "schema_version": 1,
                            "status": "completed",
                            "task_id": task_id,
                            "approval_id": approval_id,
                            "decision": decision,
                            "approval_status": state.get("status"),
                            "task_etag": self.runtime.get_task_etag(project, task_id),
                        }
                        return 200, receipt, receipt, True

                    return self._mutation(
                        environ,
                        start_response,
                        body=body,
                        actor=actor.to_dict(),
                        action=decide,
                        fingerprint_headers={"task_etag": expected},
                    )

                if (
                    method == "POST"
                    and len(segments) == 6
                    and segments[4] == "callbacks"
                ):
                    handoff_id = _safe_segment(segments[5], "handoff_id")
                    body = _read_body(environ, maximum=self.max_body_bytes)
                    if not body:
                        raise ValueError("Callback result body must not be empty")
                    token = _bearer(environ)
                    actor = self.runtime.authenticate_actor(
                        token,
                        required_capabilities=("tool-result:submit",),
                    )
                    lease_token = _required_header(environ, "X-GUIF-Lease-Token")
                    expected = _etag_header(environ)
                    filename = _required_header(environ, "X-GUIF-Filename")
                    mime_type = (_header(environ, "Content-Type") or "application/octet-stream").split(";", 1)[0].strip().lower()
                    content_sha256 = _header(environ, "X-GUIF-Content-SHA256")
                    width = _int_header(environ, "X-GUIF-Width")
                    height = _int_header(environ, "X-GUIF-Height")
                    model_id = _header(environ, "X-GUIF-Model-ID")
                    tool_id = _header(environ, "X-GUIF-Tool-ID")
                    request_id = _header(environ, "X-GUIF-Request-ID")

                    def callback() -> tuple[int, dict[str, Any], dict[str, Any], bool]:
                        task = self.runtime.submit_authenticated_tool_result(
                            project,
                            task_id,
                            handoff_id,
                            bearer_token=token,
                            lease_token=lease_token,
                            expected_task_etag=expected,
                            content=body,
                            filename=filename,
                            mime_type=mime_type,
                            content_sha256=content_sha256,
                            width=width,
                            height=height,
                            model_id=model_id,
                            tool_id=tool_id,
                            request_id=request_id,
                            metadata={"submitted_via": "production-host-gateway"},
                        )
                        callback_records = self.runtime.list_host_callbacks(project, task_id)
                        latest = callback_records[-1] if callback_records else {}
                        receipt = {
                            "schema_version": 1,
                            "status": "completed",
                            "task_id": task_id,
                            "task_status": task.status,
                            "task_etag": self.runtime.get_task_etag(project, task_id),
                            "handoff_id": handoff_id,
                            "callback_id": latest.get("callback_id"),
                            "artifact_id": latest.get("artifact_id"),
                            "content_sha256": hashlib.sha256(body).hexdigest(),
                        }
                        return 200, receipt, receipt, True

                    return self._mutation(
                        environ,
                        start_response,
                        body=body,
                        actor=actor.to_dict(),
                        action=callback,
                        fingerprint_headers={
                            "task_etag": expected,
                            "filename": filename,
                            "mime_type": mime_type,
                            "width": width,
                            "height": height,
                            "model_id": model_id,
                            "tool_id": tool_id,
                        },
                    )

                if method == "POST" and segments[4:] == ["exports"]:
                    body = _read_body(environ, maximum=MAX_JSON_BODY_BYTES)
                    content_type = (_header(environ, "Content-Type") or "").split(";", 1)[0].strip().lower()
                    if content_type != "application/json":
                        raise ValueError("Export endpoint requires Content-Type: application/json")
                    try:
                        request = json.loads(body.decode("utf-8")) if body else {}
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise ValueError("Export request must be a UTF-8 JSON object") from exc
                    if not isinstance(request, dict):
                        raise ValueError("Export request must be a JSON object")
                    token = _bearer(environ)
                    actor = self.runtime.authenticate_actor(
                        token,
                        required_capabilities=("export:execute",),
                    )
                    lease_token = _required_header(environ, "X-GUIF-Lease-Token")
                    expected = _etag_header(environ)
                    target = request.get("target_engine")

                    def export() -> tuple[int, dict[str, Any], dict[str, Any], bool]:
                        record = self.runtime.execute_gated_export_authenticated(
                            project,
                            task_id,
                            bearer_token=token,
                            lease_token=lease_token,
                            expected_task_etag=expected,
                            target_engine=str(target) if target is not None else None,
                        )
                        receipt = {
                            "schema_version": 1,
                            "status": record.get("status"),
                            "task_id": task_id,
                            "export_id": record.get("export_id"),
                            "target_engine": record.get("target_engine"),
                            "transaction": record.get("transaction"),
                            "export_manifest": record.get("export_manifest"),
                            "task_etag": self.runtime.get_task_etag(project, task_id),
                        }
                        return 200, receipt, receipt, True

                    return self._mutation(
                        environ,
                        start_response,
                        body=body,
                        actor=actor.to_dict(),
                        action=export,
                        fingerprint_headers={"task_etag": expected},
                    )

            return self._response(
                start_response,
                404,
                {"schema_version": 1, "status": "error", "code": "not-found"},
            )
        except Exception as exc:
            status, code = self._error_status(exc)
            message = str(exc) if status < 500 else "Gateway operation failed"
            return self._response(
                start_response,
                status,
                {
                    "schema_version": 1,
                    "status": "error",
                    "code": code,
                    "error_type": type(exc).__name__,
                    "message": message,
                },
            )


class ThreadingWSGIServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def _loopback_host(host: str) -> bool:
    normalized = host.strip().lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def create_gateway_server(
    workspace: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    allow_remote: bool = False,
    tls_cert: Path | None = None,
    tls_key: Path | None = None,
) -> WSGIServer:
    if port < 0 or port > 65535:
        raise ValueError("port must be between 0 and 65535")
    loopback = _loopback_host(host)
    if not loopback and not allow_remote:
        raise ValueError(
            "Production Host Gateway binds to loopback by default; use allow_remote only with an explicit TLS certificate and key"
        )
    if (tls_cert is None) != (tls_key is None):
        raise ValueError("tls_cert and tls_key must be provided together")
    if not loopback and (tls_cert is None or tls_key is None):
        raise ValueError("Remote Gateway binding requires TLS certificate and key files")
    if tls_cert is not None and not tls_cert.is_file():
        raise FileNotFoundError(f"TLS certificate does not exist: {tls_cert}")
    if tls_key is not None and not tls_key.is_file():
        raise FileNotFoundError(f"TLS key does not exist: {tls_key}")

    application = ProductionHostGateway(
        workspace,
        max_body_bytes=max_body_bytes,
    )
    server = make_server(
        host,
        port,
        application,
        server_class=ThreadingWSGIServer,
        handler_class=WSGIRequestHandler,
    )
    if tls_cert is not None and tls_key is not None:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(str(tls_cert), str(tls_key))
        server.socket = context.wrap_socket(server.socket, server_side=True)
    return server


def serve_gateway(
    workspace: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    allow_remote: bool = False,
    tls_cert: Path | None = None,
    tls_key: Path | None = None,
) -> None:
    server = create_gateway_server(
        workspace,
        host=host,
        port=port,
        max_body_bytes=max_body_bytes,
        allow_remote=allow_remote,
        tls_cert=tls_cert,
        tls_key=tls_key,
    )
    scheme = "https" if tls_cert is not None else "http"
    address, selected_port = server.server_address[:2]
    print(f"GUIF Production Host Gateway listening on {scheme}://{address}:{selected_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


__all__ = [
    "DEFAULT_MAX_BODY_BYTES",
    "GATEWAY_READ_CAPABILITY",
    "GatewayRequestStore",
    "HOST_GATEWAY_SCHEMA_VERSION",
    "HostGatewayError",
    "IdempotencyConflict",
    "LEDGER_READ_CAPABILITY",
    "ProductionHostGateway",
    "RequestTooLarge",
    "TASK_READ_CAPABILITY",
    "create_gateway_server",
    "serve_gateway",
]
