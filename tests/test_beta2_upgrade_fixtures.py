from __future__ import annotations

import json
from pathlib import Path

import pytest

from guif.private_backup import PrivateBackupService
from guif.private_data import PrivateDataLayout
from guif.private_migration import PrivateSchemaMigrator
from guif.upgrade_assurance import UpgradeAssuranceService

PROJECT = "FictionalUpgradeGame"


def _record_path(workspace: Path, name: str) -> Path:
    path = PrivateDataLayout(workspace).conversation_workflows / PROJECT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _current_record(conversation_id: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "project": PROJECT,
        "conversation_id": conversation_id,
        "status": "active",
        "continue_unbound": False,
        "active_task_id": None,
        "request_records": {},
        "checkpoint": None,
        "history": [],
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }


def _migration_required_record(conversation_id: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "project": PROJECT,
        "conversation_id": conversation_id,
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    }


def _write_record(workspace: Path, payload: dict[str, object], name: str) -> Path:
    path = _record_path(workspace, name)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _backup(workspace: Path) -> Path:
    destination = PrivateDataLayout(workspace).backups / "fictional-before-beta2.guif-private.zip"
    PrivateBackupService(workspace).create(destination)
    return destination


@pytest.mark.parametrize("source_release", ["1.0.0-alpha.27", "1.0.0-alpha.28"])
def test_current_alpha_fixture_upgrades_without_schema_mutation(
    tmp_path: Path,
    source_release: str,
) -> None:
    _write_record(
        tmp_path,
        _current_record(f"current-{source_release}"),
        "conversation-current.json",
    )
    _backup(tmp_path)
    service = UpgradeAssuranceService(tmp_path)

    plan = service.plan(source_release)
    assert plan["status"] == "ready"
    assert plan["private_schema_status"] == "current"
    assert plan["target_release"] == "1.0.0-beta.2"

    result = service.run(source_release, apply=True, actor="fictional-upgrade-test")
    assert result["status"] == "verified"
    assert result["migration"] is None
    assert result["public_api_version"] == 1


@pytest.mark.parametrize("source_release", ["1.0.0-alpha.27", "1.0.0-alpha.28"])
def test_migration_required_alpha_fixture_is_recorded_and_repaired(
    tmp_path: Path,
    source_release: str,
) -> None:
    record = _write_record(
        tmp_path,
        _migration_required_record(f"migration-{source_release}"),
        "conversation-migration.json",
    )
    _backup(tmp_path)
    service = UpgradeAssuranceService(tmp_path)

    plan = service.plan(source_release)
    assert plan["status"] == "action-required"
    assert "apply-private-migration" in plan["actions"]

    result = service.run(source_release, apply=True, actor="fictional-upgrade-test")
    assert result["status"] == "verified"
    assert result["migration"] == {
        "status": "applied",
        "applied_count": 1,
        "compatibility_preserved": True,
    }
    repaired = json.loads(record.read_text(encoding="utf-8"))
    assert repaired["privacy"]["raw_secrets_persisted"] is False
    assert repaired["compatibility"]["public_api_version"] == 1
    assert repaired["migration_history"]


def test_upgrade_fixture_without_backup_fails_closed(tmp_path: Path) -> None:
    _write_record(
        tmp_path,
        _current_record("backup-missing"),
        "conversation-backup-missing.json",
    )
    plan = UpgradeAssuranceService(tmp_path).plan("1.0.0-alpha.28")
    assert plan["status"] == "blocked"
    assert "portable-backup-required" in plan["blocking_reasons"]


def test_upgrade_fixture_with_backup_is_ready(tmp_path: Path) -> None:
    _write_record(
        tmp_path,
        _current_record("backup-present"),
        "conversation-backup-present.json",
    )
    _backup(tmp_path)
    plan = UpgradeAssuranceService(tmp_path).plan("1.0.0-alpha.28")
    assert plan["status"] == "ready"
    assert plan["portable_backup_count"] == 1


def test_unknown_future_schema_fixture_is_blocked(tmp_path: Path) -> None:
    payload = _current_record("future-schema")
    payload["schema_version"] = 999
    _write_record(tmp_path, payload, "conversation-future.json")

    scan = PrivateSchemaMigrator(tmp_path).scan()
    assert scan["status"] == "blocked"
    assert scan["blocked_count"] == 1
    assert "unsupported schema_version" in scan["records"][0]["reason"]


def test_invalid_json_fixture_is_blocked(tmp_path: Path) -> None:
    _record_path(tmp_path, "conversation-invalid.json").write_text(
        "{not valid json",
        encoding="utf-8",
    )

    scan = PrivateSchemaMigrator(tmp_path).scan()
    assert scan["status"] == "blocked"
    assert scan["blocked_count"] == 1
    assert "Invalid private JSON record" in scan["records"][0]["reason"]


def test_secret_like_field_fixture_is_blocked_without_echoing_value(tmp_path: Path) -> None:
    payload = _current_record("secret-like")
    payload["raw_secret"] = "fictional-secret-value-must-not-be-echoed"
    _write_record(tmp_path, payload, "conversation-secret.json")

    scan = PrivateSchemaMigrator(tmp_path).scan()
    serialized = json.dumps(scan)
    assert scan["status"] == "blocked"
    assert scan["records"][0]["secret_fields"] == ["raw_secret"]
    assert "fictional-secret-value-must-not-be-echoed" not in serialized
