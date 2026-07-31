from __future__ import annotations

import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_FEATURE_ROOT = ROOT / "plugins" / "game-ui-framework"
SCRIPT = (
    PLUGIN_FEATURE_ROOT
    / "skills"
    / "game-ui-framework"
    / "scripts"
    / "guif_codex.py"
)


def _run(
    workspace: Path,
    plugin_data: Path,
    *arguments: str,
    project: str = "FictionalObservatory",
    conversation: str = "codex-fictional-001",
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
            project,
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


def _theme_file(plugin_data: Path) -> Path:
    path = plugin_data / "input" / "fictional-theme.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "description": "A wholly fictional orbital kiosk interface.",
                "palette": ["test violet", "test silver"],
                "materials": ["matte composite"],
                "lighting": "soft synthetic daylight",
                "must_include": ["circular menu"],
                "avoid": ["real brands"],
            }
        ),
        encoding="utf-8",
    )
    return path


def _source_image(plugin_data: Path, name: str = "fictional-source.png") -> Path:
    path = plugin_data / "input" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGBA", (1080, 2340), (70, 80, 100, 255)).save(path)
    return path


def test_codex_plugin_manifest_marketplace_and_bundled_runtime_contract() -> None:
    marketplace = json.loads(
        (ROOT / ".agents" / "plugins" / "marketplace.json").read_text(
            encoding="utf-8"
        )
    )
    assert marketplace["interface"]["displayName"] == "AIPG Framework"
    plugin = marketplace["plugins"][0]
    assert plugin["name"] == "aipg-framework"
    assert plugin["source"] == {"source": "local", "path": "."}
    assert plugin["policy"] == {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL",
    }
    assert plugin["category"] == "Productivity"

    manifest = json.loads(
        (ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert manifest["name"] == "aipg-framework"
    assert manifest["version"] == "1.1.0-beta.1"
    assert manifest["skills"] == "./plugins/game-ui-framework/skills/"
    assert manifest["repository"] == "https://github.com/943065241/game-ui-framework"
    assert manifest["interface"]["displayName"] == "AIPG Framework"
    assert "Read" in manifest["interface"]["capabilities"]
    assert "Write" in manifest["interface"]["capabilities"]

    assert (ROOT / "guif" / "__init__.py").is_file()
    assert SCRIPT.is_file()
    assert not (PLUGIN_FEATURE_ROOT / ".codex-plugin" / "plugin.json").exists()

    skill = (
        PLUGIN_FEATURE_ROOT / "skills" / "game-ui-framework" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert skill.startswith("---\nname: game-ui-framework\n")
    assert "Do not make the user install GUIF" in skill
    assert "Never fabricate pixels" in skill
    assert "Legacy ProviderAdapter" in skill
    assert "source-import-required" in skill
    assert "Do not choose silently" in skill
    assert "improvement-trial-approval-required" in skill
    assert "Trial approval never implies adoption" in skill
    assert "relative to this SKILL.md" in skill
    assert "$PLUGIN_ROOT/plugins/game-ui-framework" in skill

    aipg_skill = (
        PLUGIN_FEATURE_ROOT / "skills" / "aipg-framework" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert aipg_skill.startswith("---\nname: aipg-framework\n")
    assert "GUIF is its game UI and visual-production domain" in aipg_skill
    assert "Theme confirmation" in aipg_skill

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    assert version == "1.1.0-dev.11"

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert version in readme
    assert "Current implementation status" in readme
    assert "Workflow Runtime" in readme

    project_status = (ROOT / "docs" / "PROJECT_STATUS.md").read_text(
        encoding="utf-8"
    )
    assert version in project_status
    assert "Implemented runtime capabilities" in project_status
    assert "Explicit limitations" in project_status

    architecture = (ROOT / "docs" / "AIPG_ARCHITECTURE.md").read_text(
        encoding="utf-8"
    )
    assert "AIPG" in architecture
    assert "GUIF" in architecture
    assert "ToolRegistry" in architecture

    runtime = (ROOT / "docs" / "AIPG_WORKFLOW_RUNTIME.md").read_text(
        encoding="utf-8"
    )
    assert "RecoverableWorkflowEngine" in runtime
    assert "CheckpointStore" in runtime
    assert "ToolRegistry" in runtime

    contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert "VERSION" in contributing
    assert "main" in contributing

    roadmap = (ROOT / "ROADMAP.md").read_text(encoding="utf-8")
    assert version in roadmap
    assert "Provider Adapter" in roadmap


def test_codex_bridge_compiles() -> None:
    py_compile.compile(str(SCRIPT), doraise=True)


def test_codex_bridge_runs_private_natural_language_image_and_visual_loop(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "fictional-game-workspace"
    workspace.mkdir()
    plugin_data = tmp_path / "private-plugin-data"

    started = _run(workspace, plugin_data, "start")
    serialized = json.dumps(started, ensure_ascii=False)
    assert started["status"] == "ready"
    assert "bearer_token" not in serialized
    assert "guifh1." not in serialized
    assert started["privacy"] == {
        "credential": "stored-in-plugin-private-data",
        "framework_data": "outside-project-git",
        "source_images": "private-source-library-outside-project-git",
        "improvement_cases": "private-candidate-change-records-outside-project-git",
    }

    contexts = list((plugin_data / "workspaces").glob("*/context.json"))
    assert len(contexts) == 1
    private_context = json.loads(contexts[0].read_text(encoding="utf-8"))
    assert str(private_context["bearer_token"]).startswith("guifh1.")
    assert not any(
        "guifh1." in path.read_text(encoding="utf-8", errors="ignore")
        for path in workspace.rglob("*")
        if path.is_file()
    )

    theme_file = _theme_file(plugin_data)
    themed = _run(
        workspace,
        plugin_data,
        "theme-create",
        "--name",
        "Fictional Orbital Fixture",
        "--content-file",
        str(theme_file),
    )
    assert themed["stage"] == "ready-for-request"
    assert themed["theme"]["privacy"] == "private"

    request_file = plugin_data / "input" / "fictional-request.txt"
    request_file.write_text(
        "Create a 1080x2340 fictional orbital shop page and export Unity",
        encoding="utf-8",
    )
    submitted = _run(
        workspace,
        plugin_data,
        "submit",
        "--request-file",
        str(request_file),
    )
    assert submitted["stage"] == "approval-required"

    approved = _run(workspace, plugin_data, "approve")
    assert approved["stage"] == "image-production"

    image_work = _run(workspace, plugin_data, "host-prepare")
    assert image_work["status"] == "prepared"
    assert image_work["kind"] == "image-generation"
    assert image_work["completion_contract"].startswith("Submit a real image")
    assert "claim_token" not in json.dumps(image_work, ensure_ascii=False)
    assert "lease_token" not in json.dumps(image_work, ensure_ascii=False)

    image_path = plugin_data / "input" / "fictional-output.png"
    Image.new("RGBA", (1080, 2340), (80, 90, 120, 255)).save(image_path)
    image_completed = _run(
        workspace,
        plugin_data,
        "host-complete-image",
        "--session",
        str(image_work["host_session"]),
        "--image",
        str(image_path),
        "--model-id",
        "fictional-test-image-tool",
    )
    assert image_completed["status"] == "completed"
    assert image_completed["artifact_created"] is True

    visual_work = _run(workspace, plugin_data, "host-prepare")
    assert visual_work["status"] == "prepared"
    assert visual_work["kind"] == "visual-inspection"
    assert len(visual_work["attachments"]) == 1
    assert Path(str(visual_work["attachments"][0]["path"])).is_file()

    visual_result = plugin_data / "input" / "fictional-visual-result.json"
    visual_result.write_text(
        json.dumps(
            {
                "status": "passed",
                "summary": "The fictional test artifact satisfies the fixture dimensions.",
                "findings": [],
            }
        ),
        encoding="utf-8",
    )
    visual_completed = _run(
        workspace,
        plugin_data,
        "host-complete-visual",
        "--session",
        str(visual_work["host_session"]),
        "--result-file",
        str(visual_result),
        "--inspector-id",
        "fictional-test-vision-tool",
    )
    assert visual_completed["status"] == "completed"
    assert visual_completed["conversation"]["stage"] == "ready-to-export"
    assert visual_completed["conversation"]["artifacts"][-1]["review_status"] == "passed"


def test_unregistered_edit_proposes_choices_then_imports_protected_source(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "edit-workspace"
    workspace.mkdir()
    plugin_data = tmp_path / "edit-plugin-data"
    _run(workspace, plugin_data, "start", conversation="edit-conversation")
    theme_file = _theme_file(plugin_data)
    _run(
        workspace,
        plugin_data,
        "theme-create",
        "--name",
        "Fictional Edit Theme",
        "--content-file",
        str(theme_file),
        conversation="edit-conversation",
    )

    request_file = plugin_data / "input" / "edit-request.txt"
    request_file.write_text(
        "Modify the 1080x2340 fictional orbital homepage, preserve non-target pixels, and export Unity",
        encoding="utf-8",
    )
    blocked = _run(
        workspace,
        plugin_data,
        "submit",
        "--request-file",
        str(request_file),
        conversation="edit-conversation",
    )
    assert blocked["stage"] == "source-import-required"
    action_ids = {item["action"] for item in blocked["actions"]}
    assert action_ids == {
        "import-source-and-continue",
        "import-as-theme-reference",
        "import-as-master-reference",
        "continue-outside-guif",
    }
    assert blocked["source"]["status"] == "required"

    source = _source_image(plugin_data)
    imported = _run(
        workspace,
        plugin_data,
        "source-import",
        "--source-file",
        str(source),
        "--source-kind",
        "conversation-temporary-image",
        "--source-usage",
        "editable-source",
        conversation="edit-conversation",
    )
    assert imported["stage"] == "approval-required"
    assert imported["source"]["status"] == "registered"
    assert imported["source"]["selected"][0]["privacy"] == "private"
    serialized = json.dumps(imported, ensure_ascii=False)
    assert str(source) not in serialized
    assert "sha256" not in serialized

    approved = _run(
        workspace,
        plugin_data,
        "approve",
        conversation="edit-conversation",
    )
    assert approved["stage"] == "image-production"
    work = _run(
        workspace,
        plugin_data,
        "host-prepare",
        conversation="edit-conversation",
    )
    assert work["kind"] == "image-editing"
    assert len(work["attachments"]) == 1
    assert Path(str(work["attachments"][0]["path"])).is_file()
    assert work["attachments"][0]["sha256"]
    _run(
        workspace,
        plugin_data,
        "host-abort",
        "--session",
        str(work["host_session"]),
        conversation="edit-conversation",
    )
    assert not any(path.name == source.name for path in workspace.rglob("*"))


def test_theme_master_image_is_auto_registered_and_reused_for_edit(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "master-workspace"
    workspace.mkdir()
    plugin_data = tmp_path / "master-plugin-data"
    conversation = "master-conversation"
    _run(workspace, plugin_data, "start", conversation=conversation)
    theme_file = _theme_file(plugin_data)
    master = _source_image(plugin_data, "fictional-master.png")
    themed = _run(
        workspace,
        plugin_data,
        "theme-create",
        "--name",
        "Fictional Master Theme",
        "--content-file",
        str(theme_file),
        "--source-file",
        str(master),
        "--source-kind",
        "user-upload",
        conversation=conversation,
    )
    assert themed["stage"] == "ready-for-request"
    assert "master-reference" in themed["source"]["selected"][0]["usages"]

    request_file = plugin_data / "input" / "master-edit-request.txt"
    request_file.write_text(
        "Adjust the 1080x2340 fictional master homepage while preserving the approved composition and export Unity",
        encoding="utf-8",
    )
    submitted = _run(
        workspace,
        plugin_data,
        "submit",
        "--request-file",
        str(request_file),
        conversation=conversation,
    )
    assert submitted["stage"] == "approval-required"
    assert submitted["stage"] != "source-import-required"
    approved = _run(workspace, plugin_data, "approve", conversation=conversation)
    assert approved["stage"] == "image-production"
    work = _run(workspace, plugin_data, "host-prepare", conversation=conversation)
    assert work["kind"] == "image-editing"
    assert len(work["attachments"]) == 1
    _run(
        workspace,
        plugin_data,
        "host-abort",
        "--session",
        str(work["host_session"]),
        conversation=conversation,
    )


def test_user_can_explicitly_leave_formal_guif_edit_chain(tmp_path: Path) -> None:
    workspace = tmp_path / "external-workspace"
    workspace.mkdir()
    plugin_data = tmp_path / "external-plugin-data"
    conversation = "external-conversation"
    _run(workspace, plugin_data, "start", conversation=conversation)
    theme_file = _theme_file(plugin_data)
    _run(
        workspace,
        plugin_data,
        "theme-create",
        "--name",
        "Fictional External Edit Theme",
        "--content-file",
        str(theme_file),
        conversation=conversation,
    )
    request_file = plugin_data / "input" / "external-request.txt"
    request_file.write_text(
        "Modify the 1080x2340 fictional homepage and export Unity",
        encoding="utf-8",
    )
    blocked = _run(
        workspace,
        plugin_data,
        "submit",
        "--request-file",
        str(request_file),
        conversation=conversation,
    )
    assert blocked["stage"] == "source-import-required"
    external = _run(
        workspace,
        plugin_data,
        "source-external-edit",
        conversation=conversation,
    )
    assert external["stage"] == "external-edit-selected"
    assert external["source"]["status"] == "external-edit-selected"
