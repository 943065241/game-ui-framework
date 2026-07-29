from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from guif.backup_protection import (
    BackupProtectionError,
    BackupProtectionService,
    ExternalCommandProtectionAdapter,
    external_adapter_from_env,
)
from guif.beta_readiness import bootstrap_workspace
from guif.compatibility import compatibility_contract
from guif.fault_injection import FaultInjectionDisabled, FaultInjector, InjectedFault
from guif.hardening import HardeningService
from guif.private_backup import PrivateBackupService
from guif.private_data import PrivateDataLayout
from guif.private_migration import PrivateSchemaMigrator
from guif.support_policy import support_contract
from guif.upgrade_assurance import UpgradeAssuranceError, UpgradeAssuranceService

PROJECT = "SampleGame"
CONVERSATION = "conversation-beta1-fictional"


def _private_fixture(workspace: Path) -> Path:
    path = (
        PrivateDataLayout(workspace).themes
        / "fictional-hardening-theme"
        / "versions"
        / "1.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "theme_id": "fictional-hardening-theme",
                "version": 1,
                "name": "Fictional Hardening Theme",
                "content": {
                    "description": "A generic test-only observatory interface.",
                    "palette": ["test blue", "test gray"],
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def _portable_backup(workspace: Path, destination: Path | None = None) -> Path:
    _private_fixture(workspace)
    archive = destination or (
        PrivateDataLayout(workspace).backups / "before-beta1.guif-private.zip"
    )
    PrivateBackupService(workspace).create(archive)
    return archive


def _reversing_adapter(tmp_path: Path) -> ExternalCommandProtectionAdapter:
    script = tmp_path / "reverse-bytes.py"
    script.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "Path(sys.argv[2]).write_bytes(Path(sys.argv[1]).read_bytes()[::-1])\n",
        encoding="utf-8",
    )
    argv = (sys.executable, str(script), "{input}", "{output}")
    return ExternalCommandProtectionAdapter(
        adapter_id="test-external-protector",
        protect_argv=argv,
        unprotect_argv=argv,
        timeout_seconds=30,
    )


def test_external_backup_protection_round_trip_persists_no_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    archive = _portable_backup(workspace, tmp_path / "portable.guif-private.zip")
    protected = tmp_path / "portable.guif-private.zip.protected"
    recovered = tmp_path / "recovered.guif-private.zip"
    monkeypatch.setenv("GUIF_TEST_BACKUP_SECRET", "must-never-be-persisted")
    service = BackupProtectionService(_reversing_adapter(tmp_path))

    result = service.protect(archive, protected)
    assert result["status"] == "protected"
    assert service.verify(protected)["status"] == "verified"
    recovered_result = service.unprotect(protected, recovered)
    assert recovered_result["status"] == "recovered"
    assert recovered.read_bytes() == archive.read_bytes()
    assert PrivateBackupService(workspace).verify(recovered)["status"] == "verified"

    receipt = Path(result["receipt_path"]).read_text(encoding="utf-8")
    assert "must-never-be-persisted" not in receipt
    assert "reverse-bytes.py" not in receipt
    assert json.loads(receipt)["secret_material_persisted"] is False


def test_backup_protection_fault_is_atomic_and_cleans_temporary_output(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    archive = _portable_backup(workspace, tmp_path / "portable.guif-private.zip")
    protected = tmp_path / "portable.protected"
    service = BackupProtectionService(
        _reversing_adapter(tmp_path),
        fault_injector=FaultInjector.explicit("backup-protection.before-publish"),
    )

    with pytest.raises(InjectedFault):
        service.protect(archive, protected)

    assert not protected.exists()
    assert not protected.with_suffix(protected.suffix + ".protect.tmp").exists()
    assert archive.is_file()
    assert PrivateBackupService(workspace).verify(archive)["status"] == "verified"


def test_protected_backup_tampering_fails_closed(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    archive = _portable_backup(workspace, tmp_path / "portable.guif-private.zip")
    protected = tmp_path / "portable.protected"
    service = BackupProtectionService(_reversing_adapter(tmp_path))
    service.protect(archive, protected)
    protected.write_bytes(protected.read_bytes() + b"tampered")

    with pytest.raises(BackupProtectionError):
        service.verify(protected)


def test_external_protection_configuration_is_explicit_and_no_shell_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GUIF_BACKUP_PROTECT_COMMAND_JSON", raising=False)
    monkeypatch.delenv("GUIF_BACKUP_UNPROTECT_COMMAND_JSON", raising=False)
    with pytest.raises(BackupProtectionError):
        external_adapter_from_env()


def test_fault_injection_environment_requires_double_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GUIF_FAULT_POINTS", "backup-protection.before-publish")
    monkeypatch.delenv("GUIF_ALLOW_FAULT_INJECTION", raising=False)
    with pytest.raises(FaultInjectionDisabled):
        FaultInjector.from_env()

    monkeypatch.setenv("GUIF_ALLOW_FAULT_INJECTION", "1")
    injector = FaultInjector.from_env()
    with pytest.raises(InjectedFault):
        injector.hit("backup-protection.before-publish")


def test_alpha27_upgrade_requires_backup_then_repairs_private_record(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    layout = PrivateDataLayout(workspace)
    record = layout.conversation_workflows / PROJECT / "conversation-alpha27.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "project": PROJECT,
                "conversation_id": "alpha27-fixture",
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    service = UpgradeAssuranceService(workspace)

    blocked = service.plan("1.0.0-alpha.27")
    assert blocked["status"] == "blocked"
    assert "portable-backup-required" in blocked["blocking_reasons"]

    _portable_backup(workspace)
    result = service.run("1.0.0-alpha.27", apply=True, actor="beta1-test")
    assert result["status"] == "verified"
    assert result["public_api_preserved"] is True
    assert PrivateSchemaMigrator(workspace).scan()["status"] == "current"
    repaired = json.loads(record.read_text(encoding="utf-8"))
    assert repaired["privacy"]["raw_secrets_persisted"] is False
    assert repaired["compatibility"]["public_api_version"] == 1


def test_unknown_upgrade_source_fails_closed(tmp_path: Path) -> None:
    service = UpgradeAssuranceService(tmp_path)
    with pytest.raises(UpgradeAssuranceError):
        service.run("0.9.0-unknown", apply=True, require_backup=False)


def test_beta1_soak_repeats_read_only_contracts_without_runtime_ids(tmp_path: Path) -> None:
    boot = bootstrap_workspace(tmp_path, PROJECT, CONVERSATION)
    report = HardeningService(
        tmp_path,
        bearer_token=boot["bearer_token"],
    ).soak(
        PROJECT,
        conversation_id=CONVERSATION,
        iterations=10,
        max_p95_ms=5000,
        persist=False,
    )

    assert report["status"] == "passed"
    assert report["successful_iterations"] == 10
    assert report["mutating_operations_performed"] is False
    serialized = json.dumps(report)
    assert "task_id" not in serialized
    assert "lease_token" not in serialized
    assert "claim_token" not in serialized


def test_beta1_preserves_frozen_public_api_and_publishes_support_window() -> None:
    compatibility = compatibility_contract()
    support = support_contract()

    assert compatibility["release"] == "1.0.0-beta.1"
    assert compatibility["origin_release"] == "1.0.0-alpha.28"
    assert compatibility["public_api_version"] == 1
    assert compatibility["channel"] == "beta"
    assert "theme-confirmation" in compatibility["conversation"]["stages"]
    assert "ready-to-export" in compatibility["conversation"]["stages"]
    assert support["release"] == "1.0.0-beta.1"
    assert support["deprecation"]["migration_path_required"] is True
    assert set(support["supported_upgrade_sources"]) == {
        "1.0.0-alpha.27",
        "1.0.0-alpha.28",
    }
