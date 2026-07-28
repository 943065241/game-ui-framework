import json
from pathlib import Path

from guif.core import init_project, validate_project
from guif.project_schema import validate_project_config


def test_project_schema_rejects_invalid_fields() -> None:
    errors = validate_project_config(
        {
            "schema_version": 2,
            "name": "",
            "status": "unknown",
            "current_theme": 123,
            "created_at": "not-a-date",
        }
    )

    assert any("schema_version" in error for error in errors)
    assert any("name" in error for error in errors)
    assert any("status" in error for error in errors)
    assert any("current_theme" in error for error in errors)
    assert any("created_at" in error for error in errors)


def test_validate_project_checks_current_theme_exists(tmp_path: Path) -> None:
    root = init_project(tmp_path, "Demo")
    config_path = root / "project.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config["current_theme"] = "missing-theme"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    errors = validate_project(tmp_path, "Demo")

    assert "Current theme file does not exist: themes/missing-theme.json" in errors
