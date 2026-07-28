from __future__ import annotations

import importlib


def test_core_and_theme_import_without_cycle() -> None:
    core = importlib.import_module("guif.core")
    theme = importlib.import_module("guif.theme")
    paths = importlib.import_module("guif.paths")

    assert callable(core.init_project)
    assert callable(theme.create_theme)
    assert callable(paths.project_root)
