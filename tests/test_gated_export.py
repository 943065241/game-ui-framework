from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from guif.core import init_project
from guif.runtime import GatedExportError, Runtime, RuntimeContext, Task, TaskStore


def _png(path: Path, size: tuple[int, int] = (16, 12)) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", size, (160, 120, 40, 255)).save(path, format="PNG")
    return path.read_bytes()


def _ready_task(tmp_path: Path, *, export_allowed: bool = True, unresolved_revision: bool = False) -> Task:
    root = init_project(tmp_path, "Demo")
    context = RuntimeContext(
        project_root=str(root),
        project_config=json.loads((root / "project.json").read_text(encoding="utf-8")),
        active_theme=None,
        workflows=(),
        resources=(),
        memory=(),
    )
    task = Task(
        project="Demo",
        requirement="Create a production icon for Unity",
        pipeline="ui-production",
        context=context,
    )
    store = TaskStore(tmp_path)
    run_dir = store.run_dir("Demo", task.task_id)
    artifact_path = run_dir / "artifacts" / "artifact-icon.png"
    content = _png(artifact_path)
    digest = hashlib.sha256(content).hexdigest()
    manifest = {
        "schema_version": 1,
        "id": "trade-icon",
        "type": "icon",
        "width": 16,
        "height": 12,
        "format": "png",
        "alpha_required": True,
        "target_engine": "unity",
        "output_name": "trade-icon.png",
        "source": None,
        "import_settings": {"spriteMode": "Single", "mipmapEnabled": False},
    }
    artifact = {
        "schema_version": 1,
        "artifact_id": "artifact-trade-icon",
        "task_id": task.task_id,
        "project": "Demo",
        "job_id": "trade-icon",
        "artifact_kind": "production-asset",
        "operation": "generate",
        "status": "registered",
        "provider": {"provider_id": "chatgpt-image"},
        "file": {
            "path": "artifacts/artifact-icon.png",
            "sha256": digest,
            "mime_type": "image/png",
            "size_bytes": len(content),
            "width": 16,
            "height": 12,
        },
        "simulation": False,
        "visual": True,
        "output_contract": dict(manifest),
        "references": [],
        "provenance": {"execution_id": "exec-1"},
        "qa": {
            "status": "passed",
            "review_id": "review-1",
            "metadata_status": "passed",
            "semantic_status": "passed",
        },
        "created_at": "2026-07-29T00:00:00+00:00",
    }
    task.state.update(
        {
            "plan": {"target_engine": "unity"},
            "approval_state": {
                "status": "approved",
                "required_ids": ["resource-manifests"],
                "approved_ids": ["resource-manifests"],
                "pending_ids": [],
            },
            "qa_report": {
                "status": "passed",
                "artifact_review": {"status": "passed" if export_allowed else "not-run"},
                "export_gate": {"allowed": export_allowed, "reasons": []},
            },
            "resource_contracts": {
                "status": "review-required",
                "target_engine": "unity",
                "manifest_candidates": [
                    {
                        "resource_id": "trade-icon",
                        "status": "review-required",
                        "dimension_source": "plan",
                        "manifest": manifest,
                    }
                ],
            },
            "artifact_registry": {
                "schema_version": 1,
                "task_id": task.task_id,
                "project": "Demo",
                "records": [artifact],
            },
            "revision_plans": {
                "schema_version": 1,
                "task_id": task.task_id,
                "project": "Demo",
                "records": (
                    [
                        {
                            "revision_id": "revision-open",
                            "status": "proposed",
                            "source_artifact_id": artifact["artifact_id"],
                        }
                    ]
                    if unresolved_revision
                    else []
                ),
            },
        }
    )
    task.complete()
    store.save(task)
    return task


def test_export_plan_is_reviewable_and_does_not_mutate_project_truth(tmp_path: Path) -> None:
    task = _ready_task(tmp_path)
    runtime = Runtime(tmp_path)

    plan = runtime.prepare_gated_export("Demo", task.task_id)

    root = tmp_path / "projects" / "Demo"
    assert plan["status"] == "ready"
    assert plan["project_truth"]["mutated"] is False
    assert not (root / "production-assets" / "files" / "trade-icon.png").exists()
    assert not (root / "production-assets" / "trade-icon.resource.json").exists()
    assert (runtime.store.run_dir("Demo", task.task_id) / "gated-exports.json").is_file()


def test_execute_materializes_approved_asset_and_engine_manifest(tmp_path: Path) -> None:
    task = _ready_task(tmp_path)
    runtime = Runtime(tmp_path)

    record = runtime.execute_gated_export(
        "Demo",
        task.task_id,
        actor="project-owner@example.com",
    )

    root = tmp_path / "projects" / "Demo"
    truth_asset = root / "production-assets" / "files" / "trade-icon.png"
    truth_manifest = root / "production-assets" / "trade-icon.resource.json"
    export_dir = root / record["engine_output_dir"]
    manifest = json.loads(truth_manifest.read_text(encoding="utf-8"))
    assert record["status"] == "completed"
    assert record["project_truth"]["mutated"] is True
    assert truth_asset.is_file()
    assert manifest["source"] == "production-assets/files/trade-icon.png"
    assert (export_dir / "trade-icon.png").is_file()
    assert (export_dir / "trade-icon.png.guif-unity.json").is_file()
    assert (export_dir / "export-manifest.json").is_file()
    assert (root / record["transaction"]).is_file()
    summary = runtime.list_runs("Demo")[0]
    assert summary["gated_export_count"] == 1
    assert summary["completed_export_count"] == 1
    assert summary["latest_export_status"] == "completed"


def test_export_fails_closed_when_visual_gate_or_revision_is_unresolved(tmp_path: Path) -> None:
    task = _ready_task(tmp_path, export_allowed=False)
    runtime = Runtime(tmp_path)

    with pytest.raises(GatedExportError, match="blocked"):
        runtime.execute_gated_export("Demo", task.task_id, actor="Owner")

    root = tmp_path / "projects" / "Demo"
    assert not (root / "production-assets" / "files" / "trade-icon.png").exists()
    blocked = runtime.list_gated_exports("Demo", task.task_id)[0]
    assert blocked["status"] == "blocked"
    assert any(item["id"] == "visual-export-gate" for item in blocked["blockers"])

    task2 = _ready_task(tmp_path / "second", unresolved_revision=True)
    runtime2 = Runtime(tmp_path / "second")
    plan = runtime2.prepare_gated_export("Demo", task2.task_id)
    assert plan["status"] == "blocked"
    assert any(item["id"] == "revision-resolution" for item in plan["blockers"])


def test_rollback_restores_previous_project_truth_and_removes_engine_output(tmp_path: Path) -> None:
    task = _ready_task(tmp_path)
    root = tmp_path / "projects" / "Demo"
    previous_asset = root / "production-assets" / "files" / "trade-icon.png"
    previous_manifest = root / "production-assets" / "trade-icon.resource.json"
    previous_asset.parent.mkdir(parents=True, exist_ok=True)
    previous_asset.write_bytes(b"previous-asset")
    previous_manifest.write_text('{"previous": true}\n', encoding="utf-8")
    runtime = Runtime(tmp_path)
    record = runtime.execute_gated_export("Demo", task.task_id, actor="Owner")
    assert previous_asset.read_bytes() != b"previous-asset"

    rolled_back = runtime.rollback_gated_export(
        "Demo",
        task.task_id,
        record["export_id"],
        actor="Owner",
        reason="Restore the previous production set.",
    )

    assert rolled_back["status"] == "rolled-back"
    assert previous_asset.read_bytes() == b"previous-asset"
    assert previous_manifest.read_text(encoding="utf-8") == '{"previous": true}\n'
    assert not (root / record["engine_output_dir"]).exists()


def test_rollback_detects_post_export_changes_unless_forced(tmp_path: Path) -> None:
    task = _ready_task(tmp_path)
    runtime = Runtime(tmp_path)
    record = runtime.execute_gated_export("Demo", task.task_id, actor="Owner")
    root = tmp_path / "projects" / "Demo"
    truth_asset = root / "production-assets" / "files" / "trade-icon.png"
    truth_asset.write_bytes(b"newer-project-change")

    with pytest.raises(GatedExportError, match="after export"):
        runtime.rollback_gated_export(
            "Demo",
            task.task_id,
            record["export_id"],
            actor="Owner",
            reason="Unsafe rollback attempt.",
        )

    rolled_back = runtime.rollback_gated_export(
        "Demo",
        task.task_id,
        record["export_id"],
        actor="Owner",
        reason="Force restoration after explicit review.",
        force=True,
    )
    assert rolled_back["status"] == "rolled-back"
    assert not truth_asset.exists()
