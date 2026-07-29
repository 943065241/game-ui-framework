from __future__ import annotations

from pathlib import Path

from guif.core import init_project, record_memory
from guif.runtime.context import load_runtime_context


def test_runtime_context_loads_markdown_memory_records(tmp_path: Path) -> None:
    init_project(tmp_path, "Demo")
    memory_path = record_memory(
        tmp_path,
        "Demo",
        "decision",
        "Use a twelve-column layout grid for the fictional interface fixture.",
    )

    context = load_runtime_context(tmp_path, "Demo")

    assert len(context.memory) == 1
    assert context.memory[0]["path"] == str(memory_path.relative_to(tmp_path / "projects" / "Demo"))
    assert context.memory[0]["type"] == "decisions"
    assert "twelve-column layout grid" in context.memory[0]["content"]
