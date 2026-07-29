from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from wsgiref.util import setup_testing_defaults

import pytest
from PIL import Image

from guif.core import init_project
from guif.host_gateway import ProductionHostGateway, create_gateway_server
from guif.resource import create_resource_manifest
from guif.runtime import Runtime, Task

PROJECT = "SampleGame"
THEME = {
    "description": "A wholly fictional geometric interface fixture.",
    "palette": ["test blue", "test gray"],
    "materials": ["matte polymer"],
    "lighting": "flat studio light",
    "must_include": ["hexagonal navigation"],
    "avoid": ["real brands"],
}


def _png_bytes(width: int = 8, height: int = 8) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", (width, height), (100, 120, 140, 255)).save(
        buffer,
        format="PNG",
    )
    return buffer.getvalue()


def _request(
    app: ProductionHostGateway,
    method: str,
    path: str,
    *,
    body: bytes = b"",
    headers: dict[str, str] | None = None,
    query: str = "",
) -> tuple[int, dict[str, str], dict[str, object]]:
    environ: dict[str, object] = {}
    setup_testing_defaults(environ)
    environ["REQUEST_METHOD"] = method
    environ["PATH_INFO"] = path
    environ["QUERY_STRING"] = query
    environ["wsgi.input"] = io.BytesIO(body)
    environ["CONTENT_LENGTH"] = str(len(body))
    for name, value in (headers or {}).items():
        key = name.upper().replace("-", "_")
        if key == "CONTENT_TYPE":
            environ["CONTENT_TYPE"] = value
        elif key == "CONTENT_LENGTH":
            environ["CONTENT_LENGTH"] = value
        else:
            environ["HTTP_" + key] = value
    captured: dict[str, object] = {}

    def start_response(status: str, response_headers: list[tuple[str, str]]) -> None:
        captured["status"] = status
        captured["headers"] = response_headers

    content = b"".join(app(environ, start_response))
    status_code = int(str(captured["status"]).split(" ", 1)[0])
    response_headers = {
        name: value for name, value in captured.get("headers", [])  # type: ignore[arg-type]
    }
    payload = json.loads(content.decode("utf-8"))
    assert isinstance(payload, dict)
    return status_code, response_headers, payload


def _create_ready_project(tmp_path: Path) -> Runtime:
    root = init_project(tmp_path, PROJECT)
    runtime = Runtime(tmp_path)
    runtime.create_private_theme(
        "Fictional Geometric Fixture",
        THEME,
        project=PROJECT,
        actor="test-bootstrap",
    )
    source_dir = root / "source"
    source_dir.mkdir()
    (source_dir / "action-button.png").write_bytes(b"fictional-reference")
    create_resource_manifest(
        tmp_path,
        PROJECT,
        "action-button",
        "button",
        264,
        134,
        "png",
        target_engine="unity",
        source="source/action-button.png",
    )
    return runtime


def _ready_handoff(runtime: Runtime) -> tuple[object, dict[str, object]]:
    task = runtime.run(
        PROJECT,
        "Create a 1080x2340 fictional geometric shop page, reuse the action button, and export Unity",
    )
    for approval_id in list(task.state["approval_state"]["required_ids"]):
        task = runtime.approve(
            PROJECT,
            task.task_id,
            approval_id,
            actor="legacy-test-reviewer",
        )
    job_id = task.state["prompt_ir"]["jobs"][0]["id"]
    task = runtime.execute_job(PROJECT, task.task_id, job_id)
    handoff = dict(runtime.list_tool_handoffs(PROJECT, task.task_id)[0])
    return task, handoff


def test_signed_operation_ledger_detects_content_and_tail_tampering(tmp_path: Path) -> None:
    runtime = Runtime(tmp_path)
    ledger = runtime.operation_ledger
    first = ledger.append(
        "synthetic.operation",
        "completed",
        actor={"actor_id": "fictional-operator"},
        scope={"project": "Synthetic"},
        details={"result": "one"},
    )
    ledger.append(
        "synthetic.operation",
        "completed",
        actor={"actor_id": "fictional-operator"},
        scope={"project": "Synthetic"},
        details={"result": "two"},
    )
    verified = ledger.verify()
    assert verified["status"] == "verified"
    assert verified["entry_count"] == 2
    assert first["signature"]

    lines = ledger.entries_path.read_text(encoding="utf-8").splitlines()
    tampered = json.loads(lines[0])
    tampered["details"]["result"] = "modified"
    lines[0] = json.dumps(tampered, sort_keys=True)
    ledger.entries_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    report = ledger.verify()
    assert report["status"] == "invalid"
    assert any("Payload hash mismatch" in error for error in report["errors"])

    second_runtime = Runtime(tmp_path / "second")
    second_ledger = second_runtime.operation_ledger
    second_ledger.append("one", "completed")
    second_ledger.append("two", "completed")
    remaining = second_ledger.entries_path.read_text(encoding="utf-8").splitlines()[:1]
    second_ledger.entries_path.write_text("\n".join(remaining) + "\n", encoding="utf-8")
    tail_report = second_ledger.verify()
    assert tail_report["status"] == "invalid"
    assert any("head sequence" in error.lower() for error in tail_report["errors"])


def test_gateway_health_descriptor_lease_and_one_time_secret_replay(tmp_path: Path) -> None:
    init_project(tmp_path, PROJECT)
    runtime = Runtime(tmp_path)
    task = Task(project=PROJECT, requirement="Synthetic task", pipeline="ui-production", context={})
    task.complete()
    runtime.store.save(task)
    issued = runtime.register_host_credential(
        "gateway-operator",
        "local-host",
        (
            "gateway:read",
            "ledger:read",
            "task:read",
            "task:lease",
        ),
    )
    token = issued["bearer_token"]
    app = ProductionHostGateway(tmp_path, runtime=runtime)

    status, _, health = _request(app, "GET", "/health")
    assert status == 200
    assert health["status"] == "healthy"

    status, _, descriptor = _request(
        app,
        "GET",
        "/v1/descriptor",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status == 200
    assert descriptor["authenticated_actor"]["actor_id"] == "gateway-operator"  # type: ignore[index]

    etag = runtime.get_task_etag(PROJECT, task.task_id)
    body = json.dumps(
        {
            "expected_task_etag": etag,
            "ttl_seconds": 60,
            "purpose": "gateway-test",
        }
    ).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Idempotency-Key": "lease-request-001",
    }
    status, response_headers, created = _request(
        app,
        "POST",
        f"/v1/tasks/{PROJECT}/{task.task_id}/lease",
        body=body,
        headers=headers,
    )
    assert status == 201
    assert created["lease_token"].startswith("guifl1.")  # type: ignore[union-attr]
    assert response_headers["X-GUIF-Request-ID"].startswith("gateway-request-")

    replay_status, _, replay = _request(
        app,
        "POST",
        f"/v1/tasks/{PROJECT}/{task.task_id}/lease",
        body=body,
        headers=headers,
    )
    assert replay_status == 409
    assert replay["code"] == "operation-conflict"

    status, _, summary = _request(
        app,
        "GET",
        f"/v1/tasks/{PROJECT}/{task.task_id}/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert status == 200
    assert summary["lease"]["status"] == "active"  # type: ignore[index]
    assert runtime.verify_operation_ledger()["status"] == "verified"
    operations = {
        entry["operation"] for entry in runtime.list_operation_ledger(limit=100)
    }
    assert "task.lease.acquire" in operations
    assert "gateway.request" in operations


def test_gateway_raw_callback_is_authenticated_idempotent_and_registers_once(
    tmp_path: Path,
) -> None:
    runtime = _create_ready_project(tmp_path)
    task, handoff = _ready_handoff(runtime)
    issued = runtime.register_host_credential(
        "chatgpt-gateway",
        str(handoff["host_id"]),
        ("task:lease", "tool-result:submit"),
    )
    token = issued["bearer_token"]
    app = ProductionHostGateway(tmp_path, runtime=runtime)
    etag = runtime.get_task_etag(PROJECT, task.task_id)

    lease_body = json.dumps(
        {
            "expected_task_etag": etag,
            "ttl_seconds": 60,
            "purpose": "host-result-callback",
        }
    ).encode("utf-8")
    lease_status, _, lease_response = _request(
        app,
        "POST",
        f"/v1/tasks/{PROJECT}/{task.task_id}/lease",
        body=lease_body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Idempotency-Key": "callback-lease-001",
        },
    )
    assert lease_status == 201
    lease_token = str(lease_response["lease_token"])

    content = _png_bytes()
    callback_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "image/png",
        "Content-Length": str(len(content)),
        "Idempotency-Key": "callback-result-001",
        "If-Match": f'"{etag}"',
        "X-GUIF-Lease-Token": lease_token,
        "X-GUIF-Filename": "synthetic-screen.png",
        "X-GUIF-Content-SHA256": hashlib.sha256(content).hexdigest(),
        "X-GUIF-Width": "8",
        "X-GUIF-Height": "8",
        "X-GUIF-Model-ID": "fictional-image-model",
    }
    status, _, receipt = _request(
        app,
        "POST",
        f"/v1/tasks/{PROJECT}/{task.task_id}/callbacks/{handoff['handoff_id']}",
        body=content,
        headers=callback_headers,
    )
    assert status == 200
    assert receipt["status"] == "completed"
    assert receipt["artifact_id"]
    assert len(runtime.list_artifacts(PROJECT, task.task_id)) == 1

    replay_status, _, replay = _request(
        app,
        "POST",
        f"/v1/tasks/{PROJECT}/{task.task_id}/callbacks/{handoff['handoff_id']}",
        body=content,
        headers=callback_headers,
    )
    assert replay_status == 200
    assert replay["idempotent_replay"] is True
    assert len(runtime.list_artifacts(PROJECT, task.task_id)) == 1
    assert runtime.get_task_lease(PROJECT, task.task_id)["status"] == "consumed"
    assert runtime.verify_operation_ledger()["status"] == "verified"


def test_gateway_rejects_oversized_body_and_non_loopback_without_tls(tmp_path: Path) -> None:
    app = ProductionHostGateway(tmp_path, max_body_bytes=1024)
    status, _, payload = _request(
        app,
        "POST",
        "/v1/tasks/Synthetic/task-1/callbacks/handoff-1",
        body=b"x" * 1025,
        headers={
            "Content-Type": "application/octet-stream",
            "Content-Length": "1025",
        },
    )
    assert status == 413
    assert payload["code"] == "request-too-large"

    with pytest.raises(ValueError, match="loopback"):
        create_gateway_server(tmp_path, host="0.0.0.0", port=0)
