from pathlib import Path

from guif.core import create_plan, init_project, record_memory, route_requirement, validate_project


def test_init_plan_validate_and_record(tmp_path: Path) -> None:
    root = init_project(tmp_path, "LeekParty")
    assert (root / "project.json").is_file()
    assert validate_project(tmp_path, "LeekParty") == []

    plan = create_plan(tmp_path, "LeekParty", "中世纪商城主题效果图")
    assert plan.is_file()
    assert route_requirement("中世纪商城主题效果图").manager == "Theme Manager"

    memory = record_memory(tmp_path, "LeekParty", "decision", "Use warm sunset lighting.")
    assert memory.is_file()
    assert "warm sunset" in memory.read_text(encoding="utf-8")


def test_resource_and_qa_routes() -> None:
    assert route_requirement("切UI并导出透明通道图集").manager == "Resource Manager"
    assert route_requirement("检查遮罩外像素是否偏移").manager == "QA Manager"
