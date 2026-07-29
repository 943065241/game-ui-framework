from __future__ import annotations

import json
from pathlib import Path

import pytest

from guif.core import init_project
from guif.runtime import Runtime, RuntimeContext, Task, TaskStore, ThemeResolutionRequired
from guif.runtime.context import load_runtime_context


THEME_CONTENT = {
    "description": "A fully fictional abstract arcade fixture.",
    "palette": ["#112233", "#ddeeff"],
    "materials": ["matte polymer"],
    "lighting": "flat studio light",
    "must_include": ["hexagonal navigation"],
    "avoid": ["real brands"],
}


def test_private_theme_versioning_and_conversation_binding(tmp_path: Path) -> None:
    init_project(tmp_path, "SampleGame")
    runtime = Runtime(tmp_path)

    unresolved = runtime.prepare_conversation_theme("conversation-1", project="SampleGame")
    assert unresolved["status"] == "confirmation-required"

    created = runtime.create_private_theme(
        "Fictional Arcade",
        THEME_CONTENT,
        actor="test-host",
        conversation_id="conversation-1",
        project="SampleGame",
    )
    assert created["version"] == 1
    assert created["privacy"] == "private"
    assert not str(runtime.theme_store.root).startswith(str(tmp_path.resolve()))

    selected = runtime.prepare_conversation_theme("conversation-1", project="SampleGame")
    assert selected["status"] == "selected"
    assert selected["selected_theme"]["theme_id"] == created["theme_id"]
    assert "description" not in selected["selected_theme"]

    derived = runtime.derive_private_theme(
        created["theme_id"],
        {"lighting": "soft top light"},
        actor="test-host",
        conversation_id="conversation-1",
        from_version=1,
    )
    assert derived["version"] == 2
    assert derived["parent_version"] == 1
    assert runtime.get_private_theme(created["theme_id"], 1)["content"]["lighting"] == "flat studio light"
    assert runtime.get_private_theme(created["theme_id"], 2)["content"]["lighting"] == "soft top light"


def test_context_and_task_persistence_redact_private_theme_content(tmp_path: Path) -> None:
    root = init_project(tmp_path, "SampleGame")
    runtime = Runtime(tmp_path)
    record = runtime.create_private_theme(
        "Synthetic Theme",
        THEME_CONTENT,
        project="SampleGame",
        actor="test-host",
    )

    context = load_runtime_context(tmp_path, "SampleGame")
    assert context.active_theme is not None
    assert context.active_theme["description"] == THEME_CONTENT["description"]
    serialized_context = context.to_dict()
    assert serialized_context["active_theme"] is None
    assert serialized_context["active_theme_ref"]["theme_id"] == record["theme_id"]
    assert THEME_CONTENT["description"] not in json.dumps(serialized_context)

    task = Task(
        project="SampleGame",
        requirement="Create a fictional menu",
        pipeline="ui-production",
        context=context,
    )
    task.complete()
    store = TaskStore(tmp_path)
    run_dir = store.save(task)
    persisted = (run_dir / "task.json").read_text(encoding="utf-8")
    assert not str(run_dir).startswith(str(root))
    assert THEME_CONTENT["description"] not in persisted
    assert record["theme_id"] in persisted

    loaded = store.load("SampleGame", task.task_id)
    assert isinstance(loaded.context, RuntimeContext)
    assert loaded.context.active_theme is not None
    assert loaded.context.active_theme["lighting"] == "flat studio light"


def test_new_conversation_requires_explicit_theme_resolution(tmp_path: Path) -> None:
    init_project(tmp_path, "SampleGame")
    runtime = Runtime(tmp_path)
    with pytest.raises(ThemeResolutionRequired) as exc_info:
        runtime.run(
            "SampleGame",
            "Create a fictional screen",
            conversation_id="conversation-new",
        )
    assert exc_info.value.resolution["status"] == "confirmation-required"


def test_legacy_project_theme_migrates_to_private_storage(tmp_path: Path) -> None:
    root = init_project(tmp_path, "SampleGame")
    themes = root / "themes"
    themes.mkdir()
    legacy = {"schema_version": 1, "name": "Legacy Fixture", **THEME_CONTENT}
    (themes / "legacy-fixture.json").write_text(
        json.dumps(legacy, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    config_path = root / "project.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["current_theme"] = "legacy-fixture"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    runtime = Runtime(tmp_path)
    before = runtime.audit_privacy(persist=False)
    assert before["status"] == "blocked"

    report = runtime.migrate_legacy_project_themes("SampleGame", actor="migration-test")
    assert len(report["imported"]) == 1
    assert report["selected_theme"] is not None
    assert not (themes / "legacy-fixture.json").exists()
    cleaned = json.loads(config_path.read_text(encoding="utf-8"))
    assert "current_theme" not in cleaned
    assert "theme_binding" not in cleaned
    assert runtime.audit_privacy(persist=False)["status"] == "passed"
    resolved = load_runtime_context(tmp_path, "SampleGame")
    assert resolved.active_theme is not None
    assert resolved.active_theme["name"] == "Legacy Fixture"
