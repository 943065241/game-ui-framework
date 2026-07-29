from __future__ import annotations

import hashlib
import io
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from guif.auth import AuthenticationError
from guif.concurrency import ConcurrencyError, LeaseError
from guif.core import init_project
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
    Image.new("RGBA", (width, height), (100, 120, 140, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


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


def _ready_task(runtime: Runtime):
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
    return task


def test_private_host_credentials_authenticate_and_revoke(tmp_path: Path) -> None:
    runtime = Runtime(tmp_path)
    issued = runtime.register_host_credential(
        "host-operator",
        "chatgpt",
        ("task:lease", "tool-result:submit"),
        roles=("operator",),
        created_by="local-test-admin",
    )
    token = issued["bearer_token"]
    actor = runtime.authenticate_actor(token, required_capabilities=("task:lease",))

    assert actor.actor_id == "host-operator"
    assert actor.host_id == "chatgpt"
    assert "secret_hash" not in issued["credential"]
    with pytest.raises(AuthenticationError):
        runtime.authenticate_actor(token + "tampered")

    credential_id = issued["credential"]["credential_id"]
    revoked = runtime.revoke_host_credential(
        credential_id,
        actor="local-test-admin",
        reason="test revocation",
    )
    assert revoked["status"] == "revoked"
    with pytest.raises(AuthenticationError):
        runtime.authenticate_actor(token)


def test_task_lease_enforces_etag_and_single_owner(tmp_path: Path) -> None:
    init_project(tmp_path, PROJECT)
    runtime = Runtime(tmp_path)
    task = Task(project=PROJECT, requirement="Synthetic task", pipeline="ui-production", context={})
    task.complete()
    runtime.store.save(task)
    issued = runtime.register_host_credential(
        "lease-owner",
        "local-host",
        ("task:lease",),
    )
    token = issued["bearer_token"]
    etag = runtime.get_task_etag(PROJECT, task.task_id)
    acquired = runtime.acquire_task_lease(
        PROJECT,
        task.task_id,
        bearer_token=token,
        expected_task_etag=etag,
        ttl_seconds=60,
    )

    assert acquired["lease"]["base_task_etag"] == etag
    with pytest.raises(LeaseError):
        runtime.acquire_task_lease(
            PROJECT,
            task.task_id,
            bearer_token=token,
            expected_task_etag=etag,
        )
    with pytest.raises(ConcurrencyError):
        runtime.task_leases.validate(
            PROJECT,
            task.task_id,
            acquired["lease_token"],
            runtime.authenticate_actor(token),
            expected_task_etag="task-sha256:stale",
        )

    released = runtime.release_task_lease(
        PROJECT,
        task.task_id,
        bearer_token=token,
        lease_token=acquired["lease_token"],
        reason="test complete",
    )
    assert released["status"] == "released"


def test_authenticated_approval_records_actor_and_consumes_lease(tmp_path: Path) -> None:
    runtime = _create_ready_project(tmp_path)
    task = runtime.run(
        PROJECT,
        "Create a 1080x2340 fictional geometric shop page and export Unity",
    )
    approval_id = task.state["approval_state"]["required_ids"][0]
    issued = runtime.register_host_credential(
        "reviewer-1",
        "review-host",
        ("task:lease", "approval:decide"),
    )
    token = issued["bearer_token"]
    etag = runtime.get_task_etag(PROJECT, task.task_id)
    lease = runtime.acquire_task_lease(
        PROJECT,
        task.task_id,
        bearer_token=token,
        expected_task_etag=etag,
        purpose="approval-decision",
    )

    task = runtime.decide_approval_authenticated(
        PROJECT,
        task.task_id,
        approval_id,
        "approved",
        bearer_token=token,
        lease_token=lease["lease_token"],
        expected_task_etag=etag,
        comment="Reviewed synthetic fixture.",
    )

    record = task.state["approval_state"]["records"][approval_id]
    assert record["authenticated_actor"]["actor_id"] == "reviewer-1"
    assert record["authenticated_actor"]["authenticated"] is True
    assert runtime.get_task_lease(PROJECT, task.task_id)["status"] == "consumed"


def test_authenticated_host_callback_registers_artifact_and_audit(tmp_path: Path) -> None:
    runtime = _create_ready_project(tmp_path)
    task = _ready_task(runtime)
    job_id = task.state["prompt_ir"]["jobs"][0]["id"]
    task = runtime.execute_job(PROJECT, task.task_id, job_id)
    handoff = runtime.list_tool_handoffs(PROJECT, task.task_id)[0]
    issued = runtime.register_host_credential(
        "chatgpt-callback",
        handoff["host_id"],
        ("task:lease", "tool-result:submit"),
    )
    token = issued["bearer_token"]
    etag = runtime.get_task_etag(PROJECT, task.task_id)
    lease = runtime.acquire_task_lease(
        PROJECT,
        task.task_id,
        bearer_token=token,
        expected_task_etag=etag,
        purpose="host-result-callback",
    )
    content = _png_bytes()

    task = runtime.submit_authenticated_tool_result(
        PROJECT,
        task.task_id,
        handoff["handoff_id"],
        bearer_token=token,
        lease_token=lease["lease_token"],
        expected_task_etag=etag,
        content=content,
        content_sha256=hashlib.sha256(content).hexdigest(),
        filename="synthetic-shop.png",
        mime_type="image/png",
        width=8,
        height=8,
        model_id="fictional-image-model",
    )

    callbacks = runtime.list_host_callbacks(PROJECT, task.task_id)
    artifacts = runtime.list_artifacts(PROJECT, task.task_id)
    assert task.status == "completed"
    assert len(callbacks) == 1
    assert callbacks[0]["actor"]["actor_id"] == "chatgpt-callback"
    assert callbacks[0]["artifact_id"] == artifacts[0]["artifact_id"]
    assert artifacts[0]["provider"]["metadata"]["authenticated_actor"]["authenticated"] is True
    assert runtime.get_task_lease(PROJECT, task.task_id)["status"] == "consumed"


def test_authenticated_callback_rejects_stale_task_etag(tmp_path: Path) -> None:
    runtime = _create_ready_project(tmp_path)
    task = _ready_task(runtime)
    job_id = task.state["prompt_ir"]["jobs"][0]["id"]
    task = runtime.execute_job(PROJECT, task.task_id, job_id)
    handoff = runtime.list_tool_handoffs(PROJECT, task.task_id)[0]
    issued = runtime.register_host_credential(
        "stale-callback",
        handoff["host_id"],
        ("task:lease", "tool-result:submit"),
    )
    token = issued["bearer_token"]
    etag = runtime.get_task_etag(PROJECT, task.task_id)
    lease = runtime.acquire_task_lease(
        PROJECT,
        task.task_id,
        bearer_token=token,
        expected_task_etag=etag,
    )
    changed = runtime.load_task(PROJECT, task.task_id)
    changed.record("test", "changed", "Simulate a concurrent Task update.")
    runtime.store.save(changed)

    with pytest.raises(ConcurrencyError):
        runtime.submit_authenticated_tool_result(
            PROJECT,
            task.task_id,
            handoff["handoff_id"],
            bearer_token=token,
            lease_token=lease["lease_token"],
            expected_task_etag=etag,
            content=_png_bytes(),
            filename="stale.png",
            mime_type="image/png",
        )


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


@pytest.mark.skipif(shutil.which("git") is None, reason="Git is required")
def test_export_git_change_set_commits_and_reverts(tmp_path: Path) -> None:
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.email", "guif-test@example.invalid")
    _git(tmp_path, "config", "user.name", "GUIF Test")
    root = init_project(tmp_path, PROJECT)
    asset = root / "production-assets" / "files" / "menu.txt"
    asset.parent.mkdir(parents=True)
    asset.write_text("old\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "test: initial project")

    asset.write_text("new\n", encoding="utf-8")
    export_id = "export-fictional"
    engine_dir = root / "exports" / "generic" / export_id
    engine_dir.mkdir(parents=True)
    (engine_dir / "menu.txt").write_text("new\n", encoding="utf-8")
    history_dir = root / "export-history" / export_id
    history_dir.mkdir(parents=True)
    transaction_path = history_dir / "transaction.json"
    transaction = {
        "schema_version": 1,
        "export_id": export_id,
        "project": PROJECT,
        "task_id": "pending",
        "status": "completed",
        "mutations": [
            {
                "path": "production-assets/files/menu.txt",
                "before_exists": True,
                "before_sha256": hashlib.sha256(b"old\n").hexdigest(),
                "after_sha256": hashlib.sha256(b"new\n").hexdigest(),
                "backup_path": None,
            }
        ],
    }
    transaction_path.write_text(json.dumps(transaction, indent=2) + "\n", encoding="utf-8")

    runtime = Runtime(tmp_path)
    task = Task(project=PROJECT, requirement="Synthetic export", pipeline="ui-production", context={})
    task.complete()
    transaction["task_id"] = task.task_id
    transaction_path.write_text(json.dumps(transaction, indent=2) + "\n", encoding="utf-8")
    task.state["gated_exports"] = {
        "schema_version": 1,
        "task_id": task.task_id,
        "project": PROJECT,
        "records": [
            {
                "schema_version": 1,
                "export_id": export_id,
                "task_id": task.task_id,
                "project": PROJECT,
                "target_engine": "generic",
                "status": "completed",
                "engine_output_dir": f"exports/generic/{export_id}",
                "transaction": f"export-history/{export_id}/transaction.json",
                "updated_at": task.updated_at,
            }
        ],
        "latest_by_target": {"generic": export_id},
        "updated_at": task.updated_at,
    }
    runtime.store.save(task)
    issued = runtime.register_host_credential(
        "git-operator",
        "local-host",
        ("task:lease", "git:prepare", "git:commit", "git:revert"),
    )
    token = issued["bearer_token"]

    etag = runtime.get_task_etag(PROJECT, task.task_id)
    change = runtime.prepare_export_git_change(
        PROJECT,
        task.task_id,
        export_id,
        bearer_token=token,
        expected_task_etag=etag,
        branch_name="guif/test-export",
    )
    assert change["status"] == "ready"
    diff = runtime.diff_git_change(PROJECT, task.task_id, change["change_set_id"])
    assert "menu.txt" in diff["diff"]

    etag = runtime.get_task_etag(PROJECT, task.task_id)
    lease = runtime.acquire_task_lease(
        PROJECT,
        task.task_id,
        bearer_token=token,
        expected_task_etag=etag,
        purpose="git-commit",
    )
    committed = runtime.execute_git_change(
        PROJECT,
        task.task_id,
        change["change_set_id"],
        bearer_token=token,
        lease_token=lease["lease_token"],
        expected_task_etag=etag,
    )
    assert committed["status"] == "committed"
    assert _git(tmp_path, "branch", "--show-current") == "guif/test-export"
    assert _git(tmp_path, "rev-parse", "HEAD") == committed["commit"]["sha"]

    etag = runtime.get_task_etag(PROJECT, task.task_id)
    lease = runtime.acquire_task_lease(
        PROJECT,
        task.task_id,
        bearer_token=token,
        expected_task_etag=etag,
        purpose="git-revert",
    )
    reverted = runtime.revert_git_change(
        PROJECT,
        task.task_id,
        change["change_set_id"],
        bearer_token=token,
        lease_token=lease["lease_token"],
        expected_task_etag=etag,
        reason="Synthetic rollback test",
    )
    assert reverted["status"] == "reverted"
    assert asset.read_text(encoding="utf-8") == "old\n"
    assert _git(tmp_path, "rev-parse", "HEAD") == reverted["revert"]["sha"]
