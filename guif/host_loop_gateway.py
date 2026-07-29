from __future__ import annotations

import hashlib
import ipaddress
import json
import ssl
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

from guif.auth import AuthenticationError
from guif.host_gateway import (
    DEFAULT_MAX_BODY_BYTES,
    GATEWAY_READ_CAPABILITY,
    MAX_JSON_BODY_BYTES,
    ProductionHostGateway,
    ThreadingWSGIServer,
    _bearer,
    _etag_header,
    _header,
    _int_header,
    _read_body,
    _required_header,
    _safe_segment,
)
from guif.runtime import Runtime

HOST_WORK_READ_CAPABILITY = "host-work:read"
HOST_WORK_CLAIM_CAPABILITY = "host-work:claim"


class ProductionHostLoopGateway:
    """WSGI Gateway extension for claimable image and semantic visual work."""

    def __init__(
        self,
        workspace: Path,
        *,
        runtime: Runtime | None = None,
        max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    ) -> None:
        self.workspace = workspace.resolve()
        self.runtime = runtime or Runtime(self.workspace)
        self.base = ProductionHostGateway(
            self.workspace,
            runtime=self.runtime,
            max_body_bytes=max_body_bytes,
        )
        self.max_body_bytes = max_body_bytes

    @staticmethod
    def _json_from_body(body: bytes, label: str) -> dict[str, Any]:
        try:
            value = json.loads(body.decode("utf-8")) if body else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"{label} must be a UTF-8 JSON object") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{label} must be a JSON object")
        return value

    @staticmethod
    def _binary_response(
        start_response: Callable[..., Any],
        status: int,
        content: bytes,
        *,
        mime_type: str,
        filename: str,
        sha256: str,
    ) -> list[bytes]:
        reason = "OK" if status == 200 else "Error"
        safe_filename = Path(filename).name or "attachment.bin"
        start_response(
            f"{status} {reason}",
            [
                ("Content-Type", mime_type),
                ("Content-Length", str(len(content))),
                ("Content-Disposition", f'attachment; filename="{safe_filename}"'),
                ("Cache-Control", "no-store"),
                ("X-Content-Type-Options", "nosniff"),
                ("X-GUIF-Content-SHA256", sha256),
                ("ETag", f'"sha256:{sha256}"'),
            ],
        )
        return [content]

    def _descriptor(self, actor: dict[str, Any]) -> dict[str, Any]:
        payload = self.base._descriptor(actor)
        endpoints = list(payload.get("endpoints", []))
        endpoints.extend(
            [
                "GET /v1/work?project={project}",
                "GET /v1/work/{project}/{work_id}",
                "POST /v1/work/{project}/{work_id}/claim",
                "GET /v1/work/{project}/{work_id}/attachments/{attachment_id}",
                "POST /v1/work/{project}/{work_id}/result",
            ]
        )
        payload["schema_version"] = 2
        payload["service"] = "guif-chatgpt-host-loop-gateway"
        payload["endpoints"] = endpoints
        payload["host_work"] = {
            "claimable": True,
            "work_kinds": [
                "image-generation",
                "image-editing",
                "visual-inspection",
            ],
            "default_visual_inspector": "chatgpt-vision",
            "one_time_claim_secret": True,
            "attachment_download": True,
            "result_idempotency": True,
        }
        return payload

    def __call__(
        self,
        environ: dict[str, Any],
        start_response: Callable[..., Any],
    ) -> list[bytes]:
        method = str(environ.get("REQUEST_METHOD") or "GET").upper()
        path = str(environ.get("PATH_INFO") or "/")
        segments = [segment for segment in path.strip("/").split("/") if segment]
        try:
            if method == "GET" and segments == ["v1", "descriptor"]:
                token = _bearer(environ)
                actor = self.runtime.authenticate_actor(
                    token,
                    required_capabilities=(GATEWAY_READ_CAPABILITY,),
                )
                return self.base._response(
                    start_response,
                    200,
                    self._descriptor(actor.to_dict()),
                )

            if method == "GET" and segments == ["v1", "work"]:
                token = _bearer(environ)
                actor = self.runtime.authenticate_actor(
                    token,
                    required_capabilities=(HOST_WORK_READ_CAPABILITY,),
                )
                query = parse_qs(str(environ.get("QUERY_STRING") or ""))
                project_values = query.get("project", [])
                if not project_values:
                    raise ValueError("Host work listing requires a project query parameter")
                project = _safe_segment(project_values[0], "project")
                capabilities = tuple(
                    item
                    for value in query.get("capability", [])
                    for item in value.split(",")
                    if item
                )
                statuses = tuple(
                    item
                    for value in query.get("status", ["available,claimed"])
                    for item in value.split(",")
                    if item
                )
                limit = int(query.get("limit", ["100"])[0])
                records = self.runtime.list_host_work(
                    project,
                    capabilities=capabilities,
                    statuses=statuses,
                    limit=limit,
                )
                return self.base._response(
                    start_response,
                    200,
                    {
                        "schema_version": 1,
                        "status": "ready",
                        "project": project,
                        "authenticated_actor": actor.to_dict(),
                        "work": list(records),
                        "count": len(records),
                    },
                )

            if len(segments) >= 4 and segments[:2] == ["v1", "work"]:
                project = _safe_segment(segments[2], "project")
                work_id = _safe_segment(segments[3], "work_id")

                if method == "GET" and len(segments) == 4:
                    token = _bearer(environ)
                    actor = self.runtime.authenticate_actor(
                        token,
                        required_capabilities=(HOST_WORK_READ_CAPABILITY,),
                    )
                    record = self.runtime.get_host_work(project, work_id)
                    return self.base._response(
                        start_response,
                        200,
                        {
                            "schema_version": 1,
                            "status": "ready",
                            "authenticated_actor": actor.to_dict(),
                            "work": record,
                        },
                    )

                if method == "POST" and segments[4:] == ["claim"]:
                    body = _read_body(environ, maximum=MAX_JSON_BODY_BYTES)
                    content_type = (_header(environ, "Content-Type") or "").split(";", 1)[0].strip().lower()
                    if content_type != "application/json":
                        raise ValueError("Host work claim requires Content-Type: application/json")
                    request = self._json_from_body(body, "Host work claim")
                    token = _bearer(environ)
                    actor = self.runtime.authenticate_actor(
                        token,
                        required_capabilities=(HOST_WORK_CLAIM_CAPABILITY,),
                    )
                    ttl_seconds = int(request.get("ttl_seconds", 300))

                    def claim() -> tuple[int, dict[str, Any], dict[str, Any], bool]:
                        result = self.runtime.claim_host_work(
                            project,
                            work_id,
                            bearer_token=token,
                            ttl_seconds=ttl_seconds,
                        )
                        response = {
                            "schema_version": 1,
                            "status": "claimed",
                            **result,
                        }
                        stored = {
                            "schema_version": 1,
                            "status": "claimed",
                            "work": result.get("work"),
                            "secret_visible_once": True,
                            "secret_replayable": False,
                        }
                        return 201, response, stored, False

                    return self.base._mutation(
                        environ,
                        start_response,
                        body=body,
                        actor=actor.to_dict(),
                        action=claim,
                        fingerprint_headers={"content_type": content_type},
                    )

                if (
                    method == "GET"
                    and len(segments) == 6
                    and segments[4] == "attachments"
                ):
                    attachment_id = _safe_segment(segments[5], "attachment_id")
                    token = _bearer(environ)
                    claim_token = _required_header(environ, "X-GUIF-Work-Claim")
                    descriptor, content = self.runtime.get_host_work_attachment(
                        project,
                        work_id,
                        attachment_id,
                        bearer_token=token,
                        claim_token=claim_token,
                    )
                    return self._binary_response(
                        start_response,
                        200,
                        content,
                        mime_type=str(descriptor.get("mime_type") or "application/octet-stream"),
                        filename=str(descriptor.get("label") or attachment_id),
                        sha256=str(descriptor.get("sha256") or hashlib.sha256(content).hexdigest()),
                    )

                if method == "POST" and segments[4:] == ["result"]:
                    token = _bearer(environ)
                    claim_token = _required_header(environ, "X-GUIF-Work-Claim")
                    lease_token = _required_header(environ, "X-GUIF-Lease-Token")
                    expected = _etag_header(environ)
                    work = self.runtime.get_host_work(project, work_id)
                    kind = str(work.get("kind") or "")
                    if kind == "visual-inspection":
                        body = _read_body(environ, maximum=MAX_JSON_BODY_BYTES)
                        content_type = (_header(environ, "Content-Type") or "").split(";", 1)[0].strip().lower()
                        if content_type != "application/json":
                            raise ValueError("Visual result requires Content-Type: application/json")
                        request = self._json_from_body(body, "Visual result")
                        findings = request.get("findings", [])
                        if not isinstance(findings, list):
                            raise ValueError("Visual result findings must be an array")

                        def visual() -> tuple[int, dict[str, Any], dict[str, Any], bool]:
                            receipt = self.runtime.complete_host_visual_work(
                                project,
                                work_id,
                                bearer_token=token,
                                claim_token=claim_token,
                                lease_token=lease_token,
                                expected_task_etag=expected,
                                status=str(request.get("status") or ""),
                                findings=tuple(item for item in findings if isinstance(item, dict)),
                                summary=str(request.get("summary") or ""),
                                inspector_id=str(request.get("inspector_id") or "chatgpt-vision"),
                                metadata=request.get("metadata") if isinstance(request.get("metadata"), dict) else None,
                            )
                            return 200, receipt, receipt, True

                        return self.base._mutation(
                            environ,
                            start_response,
                            body=body,
                            actor=None,
                            action=visual,
                            fingerprint_headers={
                                "task_etag": expected,
                                "kind": kind,
                            },
                        )

                    if kind not in {"image-generation", "image-editing"}:
                        raise ValueError(f"Unsupported Host work kind: {kind or 'missing'}")
                    body = _read_body(environ, maximum=self.max_body_bytes)
                    if not body:
                        raise ValueError("Image result body must not be empty")
                    filename = _required_header(environ, "X-GUIF-Filename")
                    mime_type = (_header(environ, "Content-Type") or "application/octet-stream").split(";", 1)[0].strip().lower()
                    content_sha256 = _header(environ, "X-GUIF-Content-SHA256")
                    width = _int_header(environ, "X-GUIF-Width")
                    height = _int_header(environ, "X-GUIF-Height")
                    model_id = _header(environ, "X-GUIF-Model-ID")
                    request_id = _header(environ, "X-GUIF-Request-ID")

                    def image() -> tuple[int, dict[str, Any], dict[str, Any], bool]:
                        receipt = self.runtime.complete_host_image_work(
                            project,
                            work_id,
                            bearer_token=token,
                            claim_token=claim_token,
                            lease_token=lease_token,
                            expected_task_etag=expected,
                            content=body,
                            filename=filename,
                            mime_type=mime_type,
                            content_sha256=content_sha256,
                            width=width,
                            height=height,
                            model_id=model_id,
                            request_id=request_id,
                        )
                        return 200, receipt, receipt, True

                    return self.base._mutation(
                        environ,
                        start_response,
                        body=body,
                        actor=None,
                        action=image,
                        fingerprint_headers={
                            "task_etag": expected,
                            "kind": kind,
                            "filename": filename,
                            "mime_type": mime_type,
                            "width": width,
                            "height": height,
                            "model_id": model_id,
                        },
                    )

            return self.base(environ, start_response)
        except Exception as exc:
            status, code = self.base._error_status(exc)
            message = str(exc) if status < 500 else "Gateway operation failed"
            return self.base._response(
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


def _loopback_host(host: str) -> bool:
    normalized = host.strip().lower()
    if normalized == "localhost":
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def create_host_loop_gateway_server(
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
            "ChatGPT Host Loop Gateway binds to loopback by default; remote binding requires explicit TLS configuration"
        )
    if (tls_cert is None) != (tls_key is None):
        raise ValueError("tls_cert and tls_key must be provided together")
    if not loopback and (tls_cert is None or tls_key is None):
        raise ValueError("Remote Gateway binding requires TLS certificate and key files")
    if tls_cert is not None and not tls_cert.is_file():
        raise FileNotFoundError(f"TLS certificate does not exist: {tls_cert}")
    if tls_key is not None and not tls_key.is_file():
        raise FileNotFoundError(f"TLS key does not exist: {tls_key}")
    application = ProductionHostLoopGateway(
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


def serve_host_loop_gateway(
    workspace: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    allow_remote: bool = False,
    tls_cert: Path | None = None,
    tls_key: Path | None = None,
) -> None:
    server = create_host_loop_gateway_server(
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
    print(f"GUIF ChatGPT Host Loop Gateway listening on {scheme}://{address}:{selected_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


__all__ = [
    "HOST_WORK_CLAIM_CAPABILITY",
    "HOST_WORK_READ_CAPABILITY",
    "ProductionHostLoopGateway",
    "create_host_loop_gateway_server",
    "serve_host_loop_gateway",
]
