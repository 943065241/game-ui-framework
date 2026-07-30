from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from guif.beta_readiness import bootstrap_workspace
from guif.improvement_cases import ImprovementCaseError, version_satisfies
from guif.improvement_workflow import ConversationWorkflowService
from guif.private_data import PrivateDataLayout
from guif.runtime import Runtime

PROJECT = "FictionalCandidateLab"
THEME = {
    "description": "A wholly fictional clean orbital market interface.",
    "palette": ["test indigo", "test silver"],
    "materials": ["matte composite", "clean alloy"],
    "lighting": "soft synthetic daylight",
    "must_include": ["circular market console"],
    "avoid": ["real brands", "photoreal people"],
}
PROPOSAL = {
    "summary": "Reduce unintended texture during protected fictional image edits.",
    "changes": [
        "Constrain edits to the approved region.",
        "Add negative constraints for grain and unnecessary highlights.",
        "Add semantic cleanliness review guidance.",
    ],
    "affected_layers": ["Skill", "Prompt IR", "Visual Review"],
    "validation_plan": [
        "Use the same fictional source and edit objective for stable and candidate results.",
        "Inspect real candidate pixels and require a separate user adoption decision.",
    ],
    "safety_constraints": [
        "Do not commit real user images.",
        "Do not merge before adoption approval.",
        "Do not substitute metadata for semantic review.",
    ],
    "public_fixture": "Use a fictional orbital market with flat clean surfaces.",
}


def _png(path: Path, *, value: int = 80) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (320, 180), (value, value + 10, value + 20, 255)).save(path)
    return path


def _service(tmp_path: Path, conversation: str) -> tuple[Runtime, ConversationWorkflowService]:
    boot = bootstrap_workspace(tmp_path, PROJECT, conversation)
    runtime = Runtime(tmp_path)
    service = ConversationWorkflowService(
        tmp_path,
        runtime=runtime,
        bearer_token=str(boot["bearer_token"]),
    )
    service.create_theme(
        PROJECT,
        conversation,
        "Fictional Clean Market",
        THEME,
    )
    submitted = service.submit(
        PROJECT,
        conversation,
        "Create a 1080x2340 fictional orbital market page and export Unity",
        request_key=f"candidate-source-{conversation}",
    )
    assert submitted["stage"] == "approval-required"
    return runtime, service


def test_code_candidate_requires_two_approvals_publish_refresh_and_regression(
    tmp_path: Path,
) -> None:
    conversation = "candidate-code-flow"
    runtime, service = _service(tmp_path, conversation)

    opened = service.open_improvement(
        PROJECT,
        conversation,
        change_type="skill-change",
        observed_behavior="Protected edits introduce unwanted fictional surface grain.",
        expected_behavior="Protected edits preserve clean non-target surfaces.",
        diagnosis="The Skill, Prompt IR, and semantic review need an isolated candidate trial.",
        proposal=PROPOSAL,
    )
    assert opened["stage"] == "improvement-trial-approval-required"
    assert opened["production"]["paused_for_improvement"] is True
    assert opened["production"]["stable_plugin_changed_by_trial"] is False

    trial = service.decide_improvement_trial(
        PROJECT,
        conversation,
        "approved",
        comment="Approve only the isolated fictional trial.",
    )
    assert trial["stage"] == "improvement-candidate-building"
    assert trial["improvement"]["trial_approval"]["decision"] == "approved"
    assert trial["improvement"]["candidate"]["development_bundle_ready"] is True

    linked = service.link_improvement_candidate(
        PROJECT,
        conversation,
        {
            "branch": "experiment/fictional-clean-edit",
            "commit": "candidate-fictional-001",
            "version": "1.0.0-beta.3-candidate.1",
        },
    )
    assert linked["stage"] == "improvement-candidate-ready"

    with pytest.raises(ImprovementCaseError, match="reviewed candidate results"):
        service.decide_improvement_adoption(
            PROJECT,
            conversation,
            "approved",
        )

    candidate_image = _png(tmp_path.parent / "private-fixtures" / "candidate.png")
    reviewed = service.record_improvement_result(
        PROJECT,
        conversation,
        group="candidate",
        summary="The fictional candidate preserved flat surfaces without added grain.",
        file_path=candidate_image,
        metadata={"semantic_pixels_inspected": True, "fictional_fixture": True},
    )
    assert reviewed["stage"] == "improvement-result-review-required"
    serialized = json.dumps(reviewed, ensure_ascii=False)
    assert str(candidate_image) not in serialized
    assert "sha256" not in serialized
    assert "task_id" not in serialized

    adopted = service.decide_improvement_adoption(
        PROJECT,
        conversation,
        "approved",
        comment="The real fictional candidate result is acceptable.",
    )
    assert adopted["stage"] == "improvement-publishing-required"

    published = service.mark_improvement_published(
        PROJECT,
        conversation,
        {
            "repository": "943065241/game-ui-framework",
            "branch": "feature/candidate-change-improvement-flow",
            "pull_request": 999,
            "merge_commit": "fictional-merged-commit",
            "minimum_plugin_version": "1.0.0-beta.3",
        },
    )
    assert published["stage"] == "plugin-refresh-required"

    refreshed = service.confirm_improvement_refresh(
        PROJECT,
        conversation,
        current_plugin_version="1.0.0-beta.3",
    )
    assert refreshed["stage"] == "regression-validation-required"

    passed = service.record_improvement_regression(
        PROJECT,
        conversation,
        passed=True,
        summary="The refreshed plugin passed the original fictional clean-edit scenario.",
    )
    assert passed["stage"] == "improvement-resolved"

    resumed = service.resume_after_improvement(PROJECT, conversation)
    assert resumed["stage"] == "approval-required"
    assert resumed["improvement"]["status"] == "not-active"

    private_root = PrivateDataLayout(tmp_path).improvement_cases
    assert private_root.is_dir()
    assert not private_root.is_relative_to(tmp_path.resolve())
    assert runtime.list_tasks(PROJECT)


def test_unknown_figma_tool_becomes_integration_candidate_without_fake_trial(
    tmp_path: Path,
) -> None:
    conversation = "candidate-figma-integration"
    _, service = _service(tmp_path, conversation)
    project_file = tmp_path / "projects" / PROJECT / "project.json"
    before = project_file.read_text(encoding="utf-8")

    service.open_improvement(
        PROJECT,
        conversation,
        change_type="tool-change",
        observed_behavior="The current structured layout Tool is not suitable.",
        expected_behavior="Use Figma for editable structured layout only.",
        proposal=PROPOSAL,
        affected_tool_id="figma",
        capability="structured-ui-layout",
        adoption_scope="project",
    )
    assessed = service.decide_improvement_trial(
        PROJECT,
        conversation,
        "approved",
    )

    improvement = assessed["improvement"]
    assert assessed["stage"] == "improvement-candidate-building"
    assert improvement["change_type"] == "tool-integration-change"
    assert improvement["candidate"]["kind"] == "tool-integration"
    tool_trial = improvement["candidate"]["tool_trial"]
    assert tool_trial["tool_id"] == "figma"
    assert tool_trial["assessment"]["integration_required"] is True
    assert tool_trial["stable_configuration_changed"] is False
    assert project_file.read_text(encoding="utf-8") == before

    with pytest.raises(ImprovementCaseError, match="candidate-ready status"):
        service.start_improvement_candidate(PROJECT, conversation)


def test_supported_tool_trial_uses_task_override_until_scoped_adoption(
    tmp_path: Path,
) -> None:
    conversation = "candidate-supported-tool"
    runtime, service = _service(tmp_path, conversation)
    project_file = tmp_path / "projects" / PROJECT / "project.json"
    before = json.loads(project_file.read_text(encoding="utf-8"))

    service.open_improvement(
        PROJECT,
        conversation,
        change_type="tool-change",
        observed_behavior="The user wants to compare the currently available image Tool.",
        expected_behavior="Trial the available Tool without changing stable routing.",
        proposal=PROPOSAL,
        affected_tool_id="chatgpt-image",
        capability="image-generation",
        adoption_scope="project",
    )
    ready = service.decide_improvement_trial(
        PROJECT,
        conversation,
        "approved",
    )
    assert ready["stage"] == "improvement-candidate-ready"
    assert ready["improvement"]["candidate"]["kind"] == "tool-trial"
    assert ready["improvement"]["candidate"]["tool_trial"]["assessment"]["ready"] is True
    assert json.loads(project_file.read_text(encoding="utf-8")) == before

    running = service.start_improvement_candidate(PROJECT, conversation)
    assert running["stage"] == "approval-required"
    assert running["production"]["stable_plugin_changed_by_trial"] is False

    session = service._session(PROJECT, conversation)
    candidate = service._load_active_task(session)
    assert candidate is not None
    assert candidate.state["execution_overrides"]["tools"]["image-generation"] == {
        "primary": "chatgpt-image",
        "fallback": [],
    }
    assert json.loads(project_file.read_text(encoding="utf-8")) == before

    evidence = _png(tmp_path.parent / "private-fixtures" / "tool-candidate.png", value=95)
    reviewed = service.record_improvement_result(
        PROJECT,
        conversation,
        group="candidate",
        summary="The real fictional Tool trial produced an acceptable candidate image.",
        file_path=evidence,
        metadata={"tool_id": "chatgpt-image", "fictional_fixture": True},
    )
    assert reviewed["stage"] == "improvement-result-review-required"

    adopted = service.decide_improvement_adoption(
        PROJECT,
        conversation,
        "approved",
    )
    assert adopted["stage"] == "improvement-resolved"
    tool_trial = adopted["improvement"]["candidate"]["tool_trial"]
    assert tool_trial["stable_configuration_changed"] is True
    configured = json.loads(project_file.read_text(encoding="utf-8"))
    assert configured["execution"]["tools"]["image-generation"] == {
        "primary": "chatgpt-image",
        "fallback": [],
    }
    assert runtime.list_tasks(PROJECT)


def test_version_comparison_handles_plugin_prerelease_format() -> None:
    assert version_satisfies("1.0.0-beta.3", "1.0.0-beta.3") is True
    assert version_satisfies("1.0.0-beta.4", "1.0.0-beta.3") is True
    assert version_satisfies("1.0.0-beta.2", "1.0.0-beta.3") is False
