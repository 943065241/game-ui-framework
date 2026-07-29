from pathlib import Path

from guif.core import create_plan, init_project, record_memory, route_requirement, validate_project


def test_init_plan_validate_and_record(tmp_path: Path) -> None:
    root = init_project(tmp_path, "SampleGame")
    assert (root / "project.json").is_file()
    assert validate_project(tmp_path, "SampleGame") == []

    plan = create_plan(tmp_path, "SampleGame", "Create a fictional geometric arcade menu style guide")
    assert plan.is_file()
    assert not str(plan).startswith(str(root))
    assert route_requirement("Create a fictional arcade theme direction").manager == "Theme Manager"

    memory = record_memory(tmp_path, "SampleGame", "decision", "Use a twelve-column layout grid.")
    assert memory.is_file()
    assert "twelve-column" in memory.read_text(encoding="utf-8")


def test_resource_and_qa_routes() -> None:
    assert route_requirement("切UI并导出透明通道图集").manager == "Resource Manager"
    assert route_requirement("检查遮罩外像素是否偏移").manager == "QA Manager"
