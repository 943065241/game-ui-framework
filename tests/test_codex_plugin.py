from __future__ import annotations

import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = ROOT / "plugins" / "game-ui-framework"
SCRIPT = (
    PLUGIN_ROOT
    / "skills"
    / "game-ui-framework"
    / "scripts"
    / "guif_codex.py"
)


def _run(
    workspace: Path,
    plugin_data: Path,
    *arguments: str,
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
            "FictionalObservatory",
            "--conversation",
            "codex-fictional-001",
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


def test_codex_plugin_manifest_marketplace_and_skill_contract() -> None:
    marketplace = json.loads(
        (ROOT / ".agents" / "plugins" / "marketplace.json").read_text(
            encoding="utf-8"
        )
    )
    assert marketplace["interface"]["displayName"] == "Game UI Framework"
    plugin = marketplace["plugins"][0]
    assert plugin["name"] == "game-ui-framework"
    assert plugin["source"] == {
        "source": "local",
        "path": "./plugins/game-ui-framework",
    }
    assert plugin["policy"] == {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL",
    }
    assert plugin["category"] == "Productivity"

    manifest = json.loads(
        (PLUGIN_ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert manifest["name"] == "game-ui-framework"
    assert manifest["version"] == "1.0.0-beta.2"
    assert manifest["skills"] == "./skills/"
    assert manifest["repository"] == "https://github.com/943065241/game-ui-framework"
    assert manifest["interface"]["displayName"] == "Game UI Framework"
    assert "Read" in manifest["interface"]["capabilities"]
    assert "Write" in manifest["interface"]["capabilities"]

    skill = (
        PLUGIN_ROOT / "skills" / "game-ui-framework" / "SKILL.md"
    ).read_text(encoding="utf-8")
    assert skill.startswith("---\nname: game-ui-framework\n")
    assert "Do not make the user install GUIF" in skill
    assert "Never fabricate pixels" in skill
    assert "Legacy ProviderAdapter" in skill
    assert "relative to this SKILL.md" in skill


def test_codex_bridge_compiles() -> None:
    py_compile.compile(str(SCRIPT), doraise=True)


def test_codex_bridge_bootstraps_privately_and_reaches_real_host_handoff(
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

    theme_file = plugin_data / "input" / "fictional-theme.json"
    theme_file.parent.mkdir(parents=True)
    theme_file.write_text(
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

    prepared = _run(workspace, plugin_data, "host-prepare")
    assert prepared["status"] == "prepared"
    assert prepared["kind"] == "image-generation"
    assert prepared["completion_contract"].startswith("Submit a real image")
    assert "claim_token" not in json.dumps(prepared, ensure_ascii=False)
    assert "lease_token" not in json.dumps(prepared, ensure_ascii=False)

    aborted = _run(
        workspace,
        plugin_data,
        "host-abort",
        "--session",
        str(prepared["host_session"]),
    )
    assert aborted["status"] == "aborted"
