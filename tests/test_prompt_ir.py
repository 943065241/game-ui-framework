from __future__ import annotations

from pathlib import Path

from guif.core import init_project, record_memory
from guif.prompt_ir import validate_prompt_ir
from guif.resource import create_resource_manifest, validate_resource_data
from guif.runtime import Runtime

PROJECT = "SampleGame"


def _create_project_theme(tmp_path: Path) -> None:
    Runtime(tmp_path).create_private_theme(
        "Fictional Geometric Arcade",
        {
            "description": "Synthetic abstract arcade UI direction for tests.",
            "palette": ["test blue", "test gray"],
            "materials": ["matte polymer", "brushed alloy"],
            "lighting": "flat studio light",
            "must_include": ["hexagonal navigation", "abstract tokens"],
            "avoid": ["real brands", "photoreal people"],
        },
        project=PROJECT,
        actor="test-host",
    )


def test_prompt_agent_builds_provider_neutral_jobs_and_provenance(tmp_path: Path) -> None:
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

    prompt_ir = task.state["prompt_ir"]
    assert not validate_prompt_ir(prompt_ir)
    assert prompt_ir["status"] == "review-required"
    assert prompt_ir["provider"] == {
        "mode": "model-neutral",
        "provider_id": None,
        "model_id": None,
        "selection": "agent-host-or-adapter",
        "must_preserve_fields": [
            "instructions",
            "negative_constraints",
            "references",
            "output_contract",
            "acceptance_criteria",
        ],
    }
    assert prompt_ir["provenance"]["plan_output"] == "ui-production-plan"
    assert prompt_ir["provenance"]["theme_output"] == "resolved-theme-contract"
    assert prompt_ir["global_contract"]["page"] == {
        "type": "shop",
        "orientation": "portrait",
        "width": 1080,
        "height": 2340,
    }
    assert "photoreal people" in prompt_ir["global_contract"]["negative_constraints"]
    assert any(
        "bottom tab navigation" in value
        for value in prompt_ir["global_contract"]["negative_constraints"]
    )

    jobs = {job["id"]: job for job in prompt_ir["jobs"]}
    effect_job = jobs["shop-effect-image"]
    assert effect_job["operation"] == "generate"
    assert effect_job["canvas"]["width"] == 1080
    assert effect_job["references"][0]["resource_id"] == "action-button"
    assert effect_job["executable"] is False

    background_job = jobs["shop-background"]
    assert background_job["artifact_kind"] == "production-asset"
    assert background_job["output_contract"]["width"] == 1080
    assert background_job["output_contract"]["height"] == 2340
    assert not validate_resource_data(background_job["output_contract"])
    assert all(job["executable"] is False for job in prompt_ir["jobs"])
    assert "transparent-output" in prompt_ir["capability_requirements"]
    assert [output["type"] for output in task.outputs[:5]] == [
        "ui-production-plan",
        "art-direction-review",
        "resolved-theme-contract",
        "resource-contract-bundle",
        "model-neutral-prompt-ir",
    ]
    assert task.state["agents"]["prompt"]["implementation"] == "model-neutral-prompt-ir"


def test_prompt_agent_blocks_edit_without_approved_reference(tmp_path: Path) -> None:
    init_project(tmp_path, PROJECT)
    _create_project_theme(tmp_path)

    task = Runtime(tmp_path).run(
        PROJECT,
        "Edit the 1080x2340 portrait fictional arcade shop page and replace the product area",
        pipeline="ui-production",
    )

    prompt_ir = task.state["prompt_ir"]
    assert prompt_ir["status"] == "blocked"
    assert {item["code"] for item in prompt_ir["blockers"]} >= {"missing-edit-reference"}
    assert "image-editing" in prompt_ir["capability_requirements"]
    assert "protected-region-editing" in prompt_ir["capability_requirements"]
    assert all(job["executable"] is False for job in prompt_ir["jobs"])


def test_prompt_agent_preserves_unknown_theme_and_canvas_as_blockers(tmp_path: Path) -> None:
    init_project(tmp_path, "Demo")

    task = Runtime(tmp_path).run(
        "Demo",
        "Create a generic UI page",
        pipeline="ui-production",
    )

    prompt_ir = task.state["prompt_ir"]
    assert prompt_ir["status"] == "blocked"
    assert {item["code"] for item in prompt_ir["blockers"]} >= {
        "missing-theme",
        "missing-canvas",
        "theme-contract-blocked",
        "dimension-unresolved",
    }
    assert prompt_ir["jobs"][0]["artifact_kind"] == "effect-image"
    assert prompt_ir["jobs"][0]["canvas"]["width"] is None
    assert all(job["executable"] is False for job in prompt_ir["jobs"])
