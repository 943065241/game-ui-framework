from __future__ import annotations

import io
import json
from pathlib import Path

from PIL import Image

from guif.core import init_project
from guif.resource import create_resource_manifest
from guif.runtime import Runtime
from guif.tools import HostProfile

PROJECT = "SampleGame"


def _create_ready_project(tmp_path: Path) -> None:
    root = init_project(tmp_path, PROJECT)
    Runtime(tmp_path).create_private_theme(
        "Fictional Geometric Arcade",
        {
            "description": "Synthetic abstract arcade UI direction for tool tests.",
            "palette": ["test blue", "test gray"],
            "materials": ["matte polymer", "brushed alloy"],
            "lighting": "flat studio light",
            "must_include": ["hexagonal navigation", "abstract tokens"],
            "avoid": ["real brands", "photoreal people"],
        },
        project=PROJECT,
        actor="test-host",
    )
    source_dir = root / "source"
    source_dir.mkdir()
    (source_dir / "action-button.png").write_bytes(b"approved-reference")
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


def _run_ready_task(runtime: Runtime):
    task = runtime.run(
        PROJECT,
        "Create a 1080x2340 portrait fictional geometric arcade shop page, reuse the action button, and export Unity",
        pipeline="ui-production",
    )
    for approval_id in list(task.state["approval_state"]["required_ids"]):
        task = runtime.approve(
            PROJECT,
            task.task_id,
            approval_id,
            actor="TestReviewer",
        )
    return task


def _png_bytes(width: int = 8, height: int = 8) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", (width, height), (100, 120, 140, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_new_project_defaults_to_chatgpt_host_and_image_tool(tmp_path: Path) -> None:
    root = init_project(tmp_path, "Demo")
    config = json.loads((root / "project.json").read_text(encoding="utf-8"))

    assert config["execution"]["mode"] == "production"
    assert config["execution"]["default_host"] == "chatgpt"
    assert config["execution"]["tools"]["image-generation"]["primary"] == "chatgpt-image"
    runtime = Runtime(tmp_path)
    assert runtime.get_host_profile()["host_id"] == "chatgpt"
    assert {item["tool_id"] for item in runtime.list_tools()} == {"chatgpt-image", "dry-run"}


def test_default_execution_prepares_chatgpt_handoff_and_waits_for_result(tmp_path: Path) -> None:
    _create_ready_project(tmp_path)
    runtime = Runtime(tmp_path)
    task = _run_ready_task(runtime)
    job_id = task.state["prompt_ir"]["jobs"][0]["id"]

    task = runtime.execute_job(PROJECT, task.task_id, job_id)

    assert task.status == "waiting-for-tool-result"
    assert task.state["tool_resolution"]["selected_tool_id"] == "chatgpt-image"
    assert task.state["tool_resolution"]["source"] == "project"
    assert task.state["tool_resolution"]["status"] == "waiting-for-result"
    handoffs = runtime.list_tool_handoffs(PROJECT, task.task_id)
    assert len(handoffs) == 1
    assert handoffs[0]["tool_id"] == "chatgpt-image"
    assert handoffs[0]["host_id"] == "chatgpt"
    assert handoffs[0]["status"] == "waiting-for-result"
    assert runtime.list_artifacts(PROJECT, task.task_id) == ()
    run_dir = runtime.store.run_dir(PROJECT, task.task_id)
    assert (run_dir / "tool-resolution.json").is_file()
    assert (run_dir / "tool-handoffs.json").is_file()


def test_chatgpt_host_can_submit_external_image_artifact(tmp_path: Path) -> None:
    _create_ready_project(tmp_path)
    runtime = Runtime(tmp_path)
    task = _run_ready_task(runtime)
    job_id = task.state["prompt_ir"]["jobs"][0]["id"]
    task = runtime.execute_job(PROJECT, task.task_id, job_id)
    handoff = runtime.list_tool_handoffs(PROJECT, task.task_id)[0]

    task = runtime.submit_tool_result(
        PROJECT,
        task.task_id,
        handoff["handoff_id"],
        content=_png_bytes(),
        filename="menu-page.png",
        mime_type="image/png",
        width=8,
        height=8,
        model_id="chatgpt-image",
        metadata={"submitted_by": "chatgpt"},
    )

    assert task.status == "completed"
    artifacts = runtime.list_artifacts(PROJECT, task.task_id)
    assert len(artifacts) == 1
    assert artifacts[0]["simulation"] is False
    assert artifacts[0]["visual"] is True
    assert artifacts[0]["provider"]["provider_id"] == "chatgpt-image"
    assert artifacts[0]["provider"]["metadata"]["host_id"] == "chatgpt"
    assert runtime.list_tool_handoffs(PROJECT, task.task_id)[0]["status"] == "completed"
    assert task.state["approval_state"]["provider_executed"] is True
    assert task.state["qa_report"]["artifact_review"]["status"] == "not-run"


def test_missing_or_unregistered_tool_fails_closed_without_dry_run_fallback(tmp_path: Path) -> None:
    _create_ready_project(tmp_path)
    config_path = tmp_path / "projects" / PROJECT / "project.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["execution"]["tools"]["image-generation"]["primary"] = "missing-image-tool"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    runtime = Runtime(tmp_path)
    task = _run_ready_task(runtime)
    job_id = task.state["prompt_ir"]["jobs"][0]["id"]

    task = runtime.execute_job(PROJECT, task.task_id, job_id)

    assert task.status == "waiting-for-tool"
    resolution = runtime.get_tool_resolution(PROJECT, task.task_id)
    assert resolution["selected_tool_id"] == "missing-image-tool"
    assert resolution["status"] == "waiting-for-tool"
    assert "not registered" in resolution["reason"]
    assert runtime.list_artifacts(PROJECT, task.task_id) == ()
    assert task.state.get("provider_executions") is None


def test_binding_tool_resumes_pending_resolution_without_replanning(tmp_path: Path) -> None:
    _create_ready_project(tmp_path)
    config_path = tmp_path / "projects" / PROJECT / "project.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["execution"]["tools"]["image-generation"]["primary"] = "missing-image-tool"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    runtime = Runtime(tmp_path)
    task = _run_ready_task(runtime)
    original_plan = dict(task.state["plan"])
    job_id = task.state["prompt_ir"]["jobs"][0]["id"]
    task = runtime.execute_job(PROJECT, task.task_id, job_id)
    assert task.status == "waiting-for-tool"

    runtime.bind_project_tool(PROJECT, "image-generation", "chatgpt-image")
    task = runtime.execute_job(PROJECT, task.task_id, job_id)

    assert task.status == "waiting-for-tool-result"
    assert task.state["plan"] == original_plan
    assert task.state["tool_resolution"]["selected_tool_id"] == "chatgpt-image"


def test_dry_run_requires_explicit_selection_in_production(tmp_path: Path) -> None:
    _create_ready_project(tmp_path)
    runtime = Runtime(tmp_path)
    task = _run_ready_task(runtime)
    job_id = task.state["prompt_ir"]["jobs"][0]["id"]

    task = runtime.execute_job(PROJECT, task.task_id, job_id, tool_id="dry-run")

    artifacts = runtime.list_artifacts(PROJECT, task.task_id)
    assert task.status == "completed"
    assert artifacts[0]["simulation"] is True
    assert artifacts[0]["visual"] is False
    assert task.state["tool_resolution"]["source"] == "explicit"
    assert task.state["tool_resolution"]["explicit"] is True


def test_host_capability_mismatch_waits_for_configuration(tmp_path: Path) -> None:
    _create_ready_project(tmp_path)
    host = HostProfile(host_id="custom-host", capabilities=frozenset())
    runtime = Runtime(tmp_path, host=host)
    task = _run_ready_task(runtime)
    job_id = task.state["prompt_ir"]["jobs"][0]["id"]

    task = runtime.execute_job(PROJECT, task.task_id, job_id)

    assert task.status == "waiting-for-tool"
    assert "not ready" in task.state["tool_resolution"]["reason"]
    assert task.state["tool_resolution"]["host_id"] == "custom-host"


def test_tool_scaffold_is_explicitly_not_implemented(tmp_path: Path) -> None:
    runtime = Runtime(tmp_path)
    root = runtime.scaffold_tool(
        "custom-image",
        ("image-generation", "transparent-output"),
    )
    manifest = json.loads((root / "tool.json").read_text(encoding="utf-8"))

    assert manifest["status"] == "adapter-required"
    assert manifest["implementation_ready"] is False
    assert (root / "adapter.py").is_file()
    assert (root / "tests" / "test_contract.py").is_file()
