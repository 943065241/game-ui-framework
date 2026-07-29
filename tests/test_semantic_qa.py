from __future__ import annotations

from pathlib import Path

from guif.core import init_project, record_memory
from guif.resource import create_resource_manifest
from guif.runtime import Runtime
from guif.semantic_qa import build_semantic_qa_report, validate_semantic_qa_report

PROJECT = "SampleGame"


def _create_project_theme(tmp_path: Path) -> None:
    Runtime(tmp_path).create_private_theme(
        "Fictional Geometric Arcade",
        {
            "description": "Synthetic abstract arcade UI direction for semantic QA tests.",
            "palette": ["test blue", "test gray"],
            "materials": ["matte polymer", "brushed alloy"],
            "lighting": "flat studio light",
            "must_include": ["hexagonal navigation", "abstract tokens"],
            "avoid": ["real brands", "photoreal people"],
        },
        project=PROJECT,
        actor="test-host",
    )


def test_semantic_qa_reviews_contracts_without_claiming_visual_results(tmp_path: Path) -> None:
    init_project(tmp_path, PROJECT)
    _create_project_theme(tmp_path)
    record_memory(
        tmp_path,
        PROJECT,
        "decision",
        "The fictional shop page must keep hexagonal navigation and must not include bottom tab navigation.",
    )
    create_resource_manifest(
        tmp_path,
        PROJECT,
        "action-button",
        "button",
        264,
        134,
        "png",
        target_engine="unity",
    )

    task = Runtime(tmp_path).run(
        PROJECT,
        "Create a 1080x2340 portrait fictional geometric arcade shop page, reuse the action button, and export Unity",
        pipeline="ui-production",
    )

    report = task.state["qa_report"]
    assert not validate_semantic_qa_report(report)
    assert report["status"] == "review-required"
    assert report["scope"] == "contract-only"
    assert report["summary"]["failed_check_count"] == 0
    assert report["artifact_review"]["status"] == "not-run"
    assert "does not claim visual quality results" in report["artifact_review"]["reason"]
    assert report["export_gate"]["allowed"] is False
    assert report["revision_request"]["required"] is False
    assert {check["id"] for check in report["checks"]} >= {
        "prompt-ir-schema",
        "provenance-chain",
        "page-contract-consistency",
        "theme-constraint-preservation",
        "resource-job-coverage",
        "reference-approval",
        "execution-gate",
        "capability-contract",
    }
    assert [output["type"] for output in task.outputs[:6]] == [
        "ui-production-plan",
        "art-direction-review",
        "resolved-theme-contract",
        "resource-contract-bundle",
        "model-neutral-prompt-ir",
        "semantic-qa-report",
    ]
    assert task.state["agents"]["qa"]["implementation"] == "semantic-contract-qa"
    assert task.state["agents"]["qa"]["export_allowed"] is False


def test_semantic_qa_preserves_upstream_blockers(tmp_path: Path) -> None:
    init_project(tmp_path, "Demo")

    task = Runtime(tmp_path).run(
        "Demo",
        "Create a generic UI page",
        pipeline="ui-production",
    )

    report = task.state["qa_report"]
    assert report["status"] == "blocked"
    assert report["revision_request"]["required"] is True
    codes = {finding["code"] for finding in report["findings"]}
    assert codes >= {
        "missing-theme",
        "missing-canvas",
        "theme-contract-blocked",
        "dimension-unresolved",
        "artifact-review-not-run",
    }
    assert report["export_gate"]["allowed"] is False


def test_semantic_qa_blocks_unsafe_executable_job(tmp_path: Path) -> None:
    init_project(tmp_path, PROJECT)
    _create_project_theme(tmp_path)

    task = Runtime(tmp_path).run(
        PROJECT,
        "Create a 1080x2340 portrait fictional geometric arcade shop page for Unity",
        pipeline="ui-production",
    )
    assert task.state["prompt_ir"]["status"] == "review-required"
    task.state["prompt_ir"]["jobs"][0]["executable"] = True

    report = build_semantic_qa_report(task)

    assert report["status"] == "blocked"
    assert any(
        finding["code"] == "unsafe-executable-job" and finding["severity"] == "blocking"
        for finding in report["findings"]
    )
    execution_check = next(check for check in report["checks"] if check["id"] == "execution-gate")
    assert execution_check["status"] == "failed"
    assert report["export_gate"]["allowed"] is False
