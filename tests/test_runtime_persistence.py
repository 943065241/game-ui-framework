from __future__ import annotations

from pathlib import Path

import pytest

from guif.agents.base import Agent
from guif.core import init_project
from guif.runtime import AgentRegistry, Pipeline, Runtime, RuntimeExecutionError


class FlakyAgent(Agent):
    name = "flaky"

    def __init__(self) -> None:
        self.attempts = 0

    def execute(self, task):
        self.attempts += 1
        if self.attempts == 1:
            raise ValueError("boom")
        task.add_output("result", {"ok": True}, agent=self.name)
        task.record(self.name, "completed", "Recovered after retry")
        return task


def test_runtime_persists_loads_and_lists_runs(tmp_path: Path) -> None:
    root = init_project(tmp_path, "demo")
    runtime = Runtime(tmp_path)

    task = runtime.run("demo", "Create a fictional abstract menu page")
    run_dir = runtime.store.run_dir("demo", task.task_id)

    assert not str(run_dir).startswith(str(root))
    assert {path.name for path in run_dir.iterdir()} == {
        "approvals.json",
        "context.json",
        "events.jsonl",
        "outputs.json",
        "task.json",
    }
    assert runtime.load_task("demo", task.task_id).to_dict() == task.to_dict()
    summary = runtime.list_runs("demo")[0]
    assert summary["status"] == "completed"
    assert summary["private_storage"] is True
    assert summary["approval_status"] in {"pending", "rejected", "changes-requested"}
    assert summary["pending_approval_count"] >= 0


def test_runtime_persists_failure_and_resumes_from_failed_agent(tmp_path: Path) -> None:
    init_project(tmp_path, "demo")
    flaky = FlakyAgent()
    runtime = Runtime(
        tmp_path,
        registry=AgentRegistry((flaky,)),
        pipelines={"flaky-flow": Pipeline("flaky-flow", ("flaky",))},
    )

    with pytest.raises(RuntimeExecutionError, match="flaky"):
        runtime.run("demo", "Run flaky work", pipeline="flaky-flow")

    task_id = runtime.list_runs("demo")[0]["task_id"]
    failed = runtime.load_task("demo", task_id)
    run_dir = runtime.store.run_dir("demo", task_id)

    assert failed.status == "failed"
    assert failed.current_agent == "flaky"
    assert failed.next_agent_index == 0
    assert failed.error == {"agent": "flaky", "type": "ValueError", "message": "boom"}
    assert (run_dir / "error.json").is_file()

    resumed = runtime.resume("demo", task_id)

    assert resumed.status == "completed"
    assert resumed.next_agent_index == 1
    assert resumed.outputs[-1]["value"] == {"ok": True}
    assert flaky.attempts == 2
    assert not (run_dir / "error.json").exists()


def test_runtime_rejects_resuming_completed_task(tmp_path: Path) -> None:
    init_project(tmp_path, "demo")
    runtime = Runtime(tmp_path)
    task = runtime.run("demo", "Create a fictional UI fixture")

    with pytest.raises(ValueError, match="already completed"):
        runtime.resume("demo", task.task_id)
