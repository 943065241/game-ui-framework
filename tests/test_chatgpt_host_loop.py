from __future__ import annotations

import io
import json
from pathlib import Path
from wsgiref.util import setup_testing_defaults

import pytest
from PIL import Image

from guif.chatgpt_host_loop import ChatGPTHostLoop
from guif.core import init_project
from guif.host_loop_gateway import ProductionHostLoopGateway
from guif.host_work import HostWorkClaimError
from guif.runtime import Runtime

PROJECT = "SampleGame"
THEME = {
    "description": "A wholly fictional geometric interface fixture.",
    "palette": ["test blue", "test gray"],
    "materials": ["matte polymer"],
    "lighting": "flat studio light",
    "must_include": ["hexagonal navigation"],
    "avoid": ["real brands"],
}
CAPABILITIES = (
    "gateway:read",
    "host-work:read",
    "host-work:claim",
    "host-work:complete",
    "task:lease",
    "tool-result:submit",
    "visual-inspection:submit",
)


def _png_bytes(width: int = 1080, height: int = 2340) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", (width, height), (100, 120, 140, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def _ready_runtime(tmp_path: Path) -> tuple[Runtime, object, str]:
    init_project(tmp_path, PROJECT)
    runtime = Runtime(tmp_path)
    runtime.create_private_theme(
        "Fictional Geometric Fixture",
        THEME,
        project=PROJECT,
        actor="test-bootstrap",
    )
    task = runtime.run(
        PROJECT,
        "Create a 1080x2340 fictional geometric shop page and export Unity",
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
    issued = runtime.register_host_credential(
        "chatgpt-host-loop",
        "chatgpt",
        CAPABILITIES,
        roles=("host-operator",),
    )
    return runtime, task, issued["bearer_token"]


def _image_executor(work: dict, attachments: tuple[dict, ...]) -> dict:
    assert work["kind"] == "image-generation"
    return {
        "content": _png_bytes(),
        "filename": "fictional-shop.png",
        "mime_type": "image/png",
        "width": 1080,
        "height": 2340,
        "model_id": "chatgpt-image",
        "metadata": {"fixture": True},
    }


def test_embedded_host_loop_registers_image_and_prepares_visual_work(tmp_path: Path) -> None:
    runtime, task, token = _ready_runtime(tmp_path)
    loop = ChatGPTHostLoop(runtime, bearer_token=token)

    receipt = loop.run_once(PROJECT, image_executor=_image_executor)

    assert receipt is not None
    assert receipt["status"] == "completed"
    assert receipt["artifact_id"]
    assert receipt["visual_work_id"]
    work = runtime.list_host_work(
        PROJECT,
        statuses=("available", "completed"),
        limit=100,
    )
    assert any(item["kind"] == "image-generation" and item["status"] == "completed" for item in work)
    visual = next(item for item in work if item["kind"] == "visual-inspection")
    assert visual["status"] == "available"
    assert visual["tool_id"] == "chatgpt-vision"
    artifact = runtime.list_artifacts(PROJECT, task.task_id)[0]
    assert artifact["qa"]["status"] == "not-run"
    assert artifact["qa"]["metadata_status"] == "passed"


def test_default_visual_inspector_passes_real_artifact(tmp_path: Path) -> None:
    runtime, task, token = _ready_runtime(tmp_path)
    loop = ChatGPTHostLoop(runtime, bearer_token=token)
    loop.run_once(PROJECT, image_executor=_image_executor)

    receipt = loop.run_once(
        PROJECT,
        visual_inspector=lambda work, attachments: {
            "inspector_id": "chatgpt-vision",
            "status": "passed",
            "summary": "The fictional fixture satisfies every supplied review dimension.",
            "findings": [],
            "metadata": {"semantic_pixels_inspected": True},
        },
    )

    assert receipt is not None
    assert receipt["status"] == "passed"
    artifact = runtime.list_artifacts(PROJECT, task.task_id)[0]
    assert artifact["qa"]["status"] == "passed"
    loaded = runtime.load_task(PROJECT, task.task_id)
    assert loaded.state["qa_report"]["artifact_review"]["status"] == "passed"
    assert loaded.state["qa_report"]["export_gate"]["allowed"] is True


def test_visual_findings_create_revision_job_with_independent_approval(tmp_path: Path) -> None:
    runtime, task, token = _ready_runtime(tmp_path)
    loop = ChatGPTHostLoop(runtime, bearer_token=token)
    loop.run_once(PROJECT, image_executor=_image_executor)

    receipt = loop.run_once(
        PROJECT,
        visual_inspector=lambda work, attachments: {
            "inspector_id": "chatgpt-vision",
            "status": "review-required",
            "summary": "Hierarchy requires a controlled edit.",
            "findings": [
                {
                    "id": "hierarchy-1",
                    "severity": "review",
                    "category": "composition-and-hierarchy",
                    "code": "primary-action-too-weak",
                    "message": "Increase the visual prominence of the fictional primary action.",
                    "evidence": {"region": "lower-center"},
                }
            ],
        },
    )

    assert receipt is not None
    assert receipt["status"] == "review-required"
    assert receipt["revision_id"]
    assert receipt["revision_job_created"] is True
    jobs = runtime.list_revision_jobs(PROJECT, task.task_id)
    assert len(jobs) == 1
    assert jobs[0]["status"] == "approval-pending"
    approval = runtime.get_revision_approval(PROJECT, task.task_id, receipt["revision_id"])
    assert approval["status"] == "pending"
    source = runtime.list_artifacts(PROJECT, task.task_id)[0]
    assert source["status"] == "registered"


def test_host_work_claim_is_bound_to_authenticated_actor(tmp_path: Path) -> None:
    runtime, task, token = _ready_runtime(tmp_path)
    work = runtime.list_host_work(PROJECT, statuses=("available",))[0]
    claimed = runtime.claim_host_work(
        PROJECT,
        work["work_id"],
        bearer_token=token,
    )
    other = runtime.register_host_credential(
        "different-host",
        "chatgpt",
        CAPABILITIES,
    )
    other_actor = runtime.authenticate_actor(other["bearer_token"])

    with pytest.raises(HostWorkClaimError):
        runtime.host_work.validate_claim(
            PROJECT,
            work["work_id"],
            other_actor,
            claimed["claim_token"],
        )


def _wsgi_request(
    application,
    method: str,
    path: str,
    *,
    query: str = "",
    headers: dict[str, str] | None = None,
    body: bytes = b"",
) -> tuple[int, dict[str, str], bytes]:
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
        else:
            environ["HTTP_" + key] = value
    captured: dict[str, object] = {}

    def start_response(status: str, response_headers: list[tuple[str, str]], exc_info=None):
        captured["status"] = status
        captured["headers"] = response_headers

    content = b"".join(application(environ, start_response))
    status_code = int(str(captured["status"]).split(" ", 1)[0])
    response_headers = {name: value for name, value in captured["headers"]}
    return status_code, response_headers, content


def test_gateway_lists_and_claims_host_work_without_persisting_claim_secret(tmp_path: Path) -> None:
    runtime, task, token = _ready_runtime(tmp_path)
    gateway = ProductionHostLoopGateway(tmp_path, runtime=runtime)
    authorization = {"Authorization": f"Bearer {token}"}

    status, _, body = _wsgi_request(
        gateway,
        "GET",
        "/v1/work",
        query=f"project={PROJECT}",
        headers=authorization,
    )
    payload = json.loads(body)
    assert status == 200
    work_id = payload["work"][0]["work_id"]

    status, _, body = _wsgi_request(
        gateway,
        "POST",
        f"/v1/work/{PROJECT}/{work_id}/claim",
        headers={
            **authorization,
            "Content-Type": "application/json",
            "Idempotency-Key": "claim-fictional-work-1",
        },
        body=b'{"ttl_seconds": 120}',
    )
    payload = json.loads(body)
    assert status == 201
    claim_token = payload["claim_token"]
    persisted = runtime.host_work.get(PROJECT, work_id)
    assert claim_token not in json.dumps(persisted)
    assert "token_hash" not in json.dumps(persisted)
