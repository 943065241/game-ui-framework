from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from guif.core import init_project
from guif.providers import ExecutionRequest, ExecutionResult, ProviderAdapter, ProviderRegistry
from guif.resource import create_resource_manifest
from guif.runtime import ProviderExecutionError, Runtime
from guif.theme import create_theme


class FailingProvider(ProviderAdapter):
    provider_id = "failing"
    capabilities = frozenset({"image-generation", "transparent-output"})
    requires_bound_references = False

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        raise RuntimeError("provider unavailable")


class LimitedProvider(ProviderAdapter):
    provider_id = "limited"
    capabilities = frozenset()
    requires_bound_references = False

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        raise AssertionError("capability gate should reject before execution")


def _create_ready_project(tmp_path: Path) -> None:
    root = init_project(tmp_path, "LeekParty")
    theme_path = create_theme(
        tmp_path,
        "LeekParty",
        "Medieval Harbor",
        "Warm, readable medieval harbor UI direction.",
    )
    theme = json.loads(theme_path.read_text(encoding="utf-8"))
    theme.update(
        {
            "palette": ["warm gold", "deep sea blue"],
            "materials": ["weathered wood", "aged brass"],
            "lighting": "warm sunset",
            "must_include": ["harbor view", "gold coins"],
            "avoid": ["pirate skulls", "dirty visual noise"],
        }
    )
    theme_path.write_text(json.dumps(theme), encoding="utf-8")
    source_dir = root / "source"
    source_dir.mkdir()
    (source_dir / "purchase-button.png").write_bytes(b"approved-reference")
    create_resource_manifest(
        tmp_path,
        "LeekParty",
        "purchase-button",
        "button",
        264,
        134,
        "png",
        target_engine="unity",
        source="source/purchase-button.png",
    )


def _run_task(tmp_path: Path, *, providers: ProviderRegistry | None = None):
    runtime = Runtime(tmp_path, providers=providers)
    task = runtime.run(
        "LeekParty",
        "Create a 1080x2340 portrait medieval harbor shop page, reuse the purchase button, and export Unity",
        pipeline="ui-production",
    )
    return runtime, task


def _approve_all(runtime: Runtime, task):
    for approval_id in list(task.state["approval_state"]["required_ids"]):
        task = runtime.approve(
            task.project,
            task.task_id,
            approval_id,
            actor="Reviewer",
        )
    return task


def test_dry_run_executes_only_after_approval_and_registers_artifact(tmp_path: Path) -> None:
    _create_ready_project(tmp_path)
    runtime, task = _run_task(tmp_path)
    job_id = task.state["prompt_ir"]["jobs"][0]["id"]

    with pytest.raises(ValueError, match="not ready"):
        runtime.execute_job("LeekParty", task.task_id, job_id)

    task = _approve_all(runtime, task)
    task = runtime.execute_job("LeekParty", task.task_id, job_id, provider_id="dry-run")

    artifacts = runtime.list_artifacts("LeekParty", task.task_id)
    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert runtime.get_artifact("LeekParty", task.task_id, artifact["artifact_id"]) == artifact
    assert artifact["provider"]["provider_id"] == "dry-run"
    assert artifact["simulation"] is True
    assert artifact["visual"] is False
    assert artifact["references"][0]["status"] == "bound"
    assert artifact["references"][0]["sha256"] == hashlib.sha256(b"approved-reference").hexdigest()

    run_dir = tmp_path / "projects" / "LeekParty" / "runs" / task.task_id
    artifact_path = run_dir / artifact["file"]["path"]
    assert artifact_path.is_file()
    assert hashlib.sha256(artifact_path.read_bytes()).hexdigest() == artifact["file"]["sha256"]
    assert (run_dir / "artifacts.json").is_file()
    assert (run_dir / "executions.json").is_file()

    assert task.state["approval_state"]["provider_executed"] is True
    assert task.state["provider_executions"]["attempts"][0]["status"] == "completed"
    assert task.state["qa_report"]["artifact_review"]["artifact_count"] == 1
    assert task.state["qa_report"]["artifact_review"]["status"] == "not-run"
    assert task.state["qa_report"]["export_gate"]["allowed"] is False
    assert runtime.list_runs("LeekParty")[0]["artifact_count"] == 1
    assert runtime.list_runs("LeekParty")[0]["provider_execution_count"] == 1


def test_provider_capability_gate_rejects_before_execution(tmp_path: Path) -> None:
    _create_ready_project(tmp_path)
    providers = ProviderRegistry((LimitedProvider(),))
    runtime, task = _run_task(tmp_path, providers=providers)
    task = _approve_all(runtime, task)
    job_id = task.state["prompt_ir"]["jobs"][0]["id"]

    with pytest.raises(ValueError, match="lacks required capabilities"):
        runtime.execute_job("LeekParty", task.task_id, job_id, provider_id="limited")

    persisted = runtime.load_task("LeekParty", task.task_id)
    assert "provider_executions" not in persisted.state
    assert runtime.list_artifacts("LeekParty", task.task_id) == ()


def test_provider_failure_is_persisted_without_losing_task_or_approval(tmp_path: Path) -> None:
    _create_ready_project(tmp_path)
    providers = ProviderRegistry((FailingProvider(),))
    runtime, task = _run_task(tmp_path, providers=providers)
    task = _approve_all(runtime, task)
    approval_history = list(task.state["approval_state"]["history"])
    job_id = task.state["prompt_ir"]["jobs"][0]["id"]

    with pytest.raises(ProviderExecutionError, match="provider unavailable"):
        runtime.execute_job("LeekParty", task.task_id, job_id, provider_id="failing")

    persisted = runtime.load_task("LeekParty", task.task_id)
    attempt = persisted.state["provider_executions"]["attempts"][0]
    assert persisted.status == "completed"
    assert persisted.state["approval_state"]["status"] == "approved"
    assert persisted.state["approval_state"]["history"] == approval_history
    assert persisted.state["approval_state"]["provider_executed"] is False
    assert attempt["status"] == "failed"
    assert attempt["error"] == {"type": "RuntimeError", "message": "provider unavailable"}
    assert runtime.list_artifacts("LeekParty", task.task_id) == ()
    assert (
        tmp_path
        / "projects"
        / "LeekParty"
        / "runs"
        / task.task_id
        / "executions.json"
    ).is_file()
