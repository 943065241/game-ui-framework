from __future__ import annotations

from pathlib import Path

import pytest

from guif.agents.base import ContractAgent
from guif.core import init_project
from guif.runtime import AgentRegistry, Pipeline, Runtime


def test_runtime_loads_context_and_executes_default_pipeline(tmp_path: Path) -> None:
    init_project(tmp_path, "demo")

    task = Runtime(tmp_path).run("demo", "Create a medieval shop page")

    assert task.completed_at is not None
    assert task.project == "demo"
    assert task.pipeline == "ui-production"
    assert task.context.project_config["name"] == "demo"
    assert tuple(task.state["agents"]) == (
        "planner",
        "director",
        "theme",
        "resource",
        "prompt",
        "qa",
        "export",
    )
    assert task.events[0].agent == "runtime"
    assert task.events[-1].status == "completed"


def test_runtime_supports_custom_registry_and_pipeline(tmp_path: Path) -> None:
    init_project(tmp_path, "demo")
    registry = AgentRegistry((ContractAgent("custom", "Test custom execution."),))
    pipelines = {"custom-flow": Pipeline("custom-flow", ("custom",))}

    task = Runtime(tmp_path, registry=registry, pipelines=pipelines).run(
        "demo",
        "Run a custom task",
        pipeline="custom-flow",
    )

    assert task.state["agents"]["custom"]["status"] == "contract-ready"


def test_runtime_rejects_unknown_pipeline_and_empty_requirement(tmp_path: Path) -> None:
    init_project(tmp_path, "demo")
    runtime = Runtime(tmp_path)

    with pytest.raises(ValueError, match="Unknown pipeline"):
        runtime.run("demo", "Create UI", pipeline="missing")
    with pytest.raises(ValueError, match="Requirement must not be empty"):
        runtime.run("demo", "   ")


def test_registry_rejects_duplicate_agent_names() -> None:
    with pytest.raises(ValueError, match="already registered"):
        AgentRegistry((ContractAgent("same", "One"), ContractAgent("same", "Two")))
