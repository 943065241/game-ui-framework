from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "plugins"
    / "game-ui-framework"
    / "skills"
    / "game-ui-framework"
    / "scripts"
    / "guif_codex.py"
)
PROJECT = "FictionalBridgeLab"
CONVERSATION = "candidate-bridge-001"


def _run(
    workspace: Path,
    plugin_data: Path,
    *arguments: str,
    conversation: str = CONVERSATION,
) -> dict[str, object]:
    env = dict(os.environ)
    env["GUIF_CODEX_PLUGIN_DATA"] = str(plugin_data)
    env["GUIF_DATA_HOME"] = str(plugin_data / "framework-data")
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--workspace",
            str(workspace),
            "--project",
            PROJECT,
            "--conversation",
            conversation,
            *arguments,
        ],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert completed.returncode == 0, completed.stderr
    value = json.loads(completed.stdout)
    assert isinstance(value, dict)
    return value


def _write_json(path: Path, value: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _write_text(path: Path, value: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")
    return path


def _prepare_production(workspace: Path, plugin_data: Path, *, conversation: str) -> None:
    _run(workspace, plugin_data, "start", conversation=conversation)
    theme = _write_json(
        plugin_data / "input" / f"{conversation}-theme.json",
        {
            "description": "A wholly fictional clean orbital interface.",
            "palette": ["test blue", "test silver"],
            "materials": ["matte composite"],
            "lighting": "soft synthetic light",
            "must_include": ["circular console"],
            "avoid": ["real brands"],
        },
    )
    _run(
        workspace,
        plugin_data,
        "theme-create",
        "--name",
        "Fictional Candidate Bridge Theme",
        "--content-file",
        str(theme),
        conversation=conversation,
    )
    request = _write_text(
        plugin_data / "input" / f"{conversation}-request.txt",
        "Create a 1080x2340 fictional orbital market page and export Unity",
    )
    submitted = _run(
        workspace,
        plugin_data,
        "submit",
        "--request-file",
        str(request),
        conversation=conversation,
    )
    assert submitted["stage"] == "approval-required"


def _proposal(plugin_data: Path, conversation: str) -> Path:
    return _write_json(
        plugin_data / "input" / f"{conversation}-proposal.json",
        {
            "summary": "Reduce unwanted fictional image texture through an isolated candidate.",
            "changes": [
                "Constrain the protected edit region.",
                "Add negative grain constraints.",
            ],
            "affected_layers": ["Skill", "Prompt IR"],
            "validation_plan": [
                "Generate a real fictional candidate image.",
                "Require a separate adoption decision after result review.",
            ],
            "safety_constraints": [
                "Do not merge before adoption.",
                "Do not commit private evidence.",
            ],
            "public_fixture": "Use a fictional orbital market fixture.",
        },
    )


def test_codex_bridge_runs_two_gate_candidate_change_publication_and_resume(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "bridge-workspace"
    workspace.mkdir()
    plugin_data = tmp_path / "bridge-private"
    _prepare_production(workspace, plugin_data, conversation=CONVERSATION)

    observed = _write_text(
        plugin_data / "input" / "observed.txt",
        "Protected edits introduce unwanted fictional grain.",
    )
    expected = _write_text(
        plugin_data / "input" / "expected.txt",
        "Protected edits preserve clean non-target surfaces.",
    )
    proposal = _proposal(plugin_data, CONVERSATION)
    opened = _run(
        workspace,
        plugin_data,
        "improvement-open",
        "--change-type",
        "skill-change",
        "--observed-file",
        str(observed),
        "--expected-file",
        str(expected),
        "--proposal-file",
        str(proposal),
    )
    assert opened["stage"] == "improvement-trial-approval-required"

    trial = _run(workspace, plugin_data, "improvement-trial-approve")
    assert trial["stage"] == "improvement-candidate-building"

    candidate_file = _write_json(
        plugin_data / "input" / "candidate.json",
        {
            "branch": "experiment/fictional-bridge-candidate",
            "commit": "fictional-candidate-commit",
            "version": "1.0.0-beta.3-candidate.1",
        },
    )
    linked = _run(
        workspace,
        plugin_data,
        "improvement-candidate-link",
        "--candidate-file",
        str(candidate_file),
    )
    assert linked["stage"] == "improvement-candidate-ready"

    result_summary = _write_text(
        plugin_data / "input" / "candidate-summary.txt",
        "The real fictional candidate preserved clean flat surfaces.",
    )
    result_image = plugin_data / "input" / "candidate-result.png"
    Image.new("RGBA", (320, 180), (70, 80, 100, 255)).save(result_image)
    reviewed = _run(
        workspace,
        plugin_data,
        "improvement-result",
        "--group",
        "candidate",
        "--summary-file",
        str(result_summary),
        "--artifact-file",
        str(result_image),
    )
    assert reviewed["stage"] == "improvement-result-review-required"
    serialized = json.dumps(reviewed, ensure_ascii=False)
    assert str(result_image) not in serialized
    assert "sha256" not in serialized

    adopted = _run(workspace, plugin_data, "improvement-adopt")
    assert adopted["stage"] == "improvement-publishing-required"

    delivery = _write_json(
        plugin_data / "input" / "delivery.json",
        {
            "repository": "943065241/game-ui-framework",
            "branch": "feature/candidate-change-improvement-flow",
            "pull_request": 999,
            "merge_commit": "fictional-merge-commit",
            "minimum_plugin_version": "1.0.0-beta.3",
        },
    )
    published = _run(
        workspace,
        plugin_data,
        "improvement-published",
        "--delivery-file",
        str(delivery),
    )
    assert published["stage"] == "plugin-refresh-required"

    refreshed = _run(
        workspace,
        plugin_data,
        "improvement-refresh-confirm",
    )
    assert refreshed["stage"] == "regression-validation-required"

    regression = _write_text(
        plugin_data / "input" / "regression.txt",
        "The refreshed plugin passed the original fictional scenario.",
    )
    passed = _run(
        workspace,
        plugin_data,
        "improvement-regression-pass",
        "--summary-file",
        str(regression),
    )
    assert passed["stage"] == "improvement-resolved"

    resumed = _run(workspace, plugin_data, "improvement-resume")
    assert resumed["stage"] == "approval-required"
    assert resumed["improvement"]["status"] == "not-active"


def test_codex_bridge_routes_unavailable_figma_to_tool_integration(
    tmp_path: Path,
) -> None:
    conversation = "candidate-bridge-figma"
    workspace = tmp_path / "figma-workspace"
    workspace.mkdir()
    plugin_data = tmp_path / "figma-private"
    _prepare_production(workspace, plugin_data, conversation=conversation)

    observed = _write_text(
        plugin_data / "input" / "figma-observed.txt",
        "The current structured layout Tool is unsuitable.",
    )
    expected = _write_text(
        plugin_data / "input" / "figma-expected.txt",
        "Trial Figma only for editable structured layout.",
    )
    opened = _run(
        workspace,
        plugin_data,
        "improvement-open",
        "--change-type",
        "tool-change",
        "--observed-file",
        str(observed),
        "--expected-file",
        str(expected),
        "--proposal-file",
        str(_proposal(plugin_data, conversation)),
        "--tool-id",
        "figma",
        "--capability",
        "structured-ui-layout",
        "--adoption-scope",
        "project",
        conversation=conversation,
    )
    assert opened["stage"] == "improvement-trial-approval-required"

    assessed = _run(
        workspace,
        plugin_data,
        "improvement-trial-approve",
        conversation=conversation,
    )
    assert assessed["stage"] == "improvement-candidate-building"
    assert assessed["improvement"]["change_type"] == "tool-integration-change"
    tool_trial = assessed["improvement"]["candidate"]["tool_trial"]
    assert tool_trial["assessment"]["integration_required"] is True
    assert tool_trial["stable_configuration_changed"] is False
