from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from guif.backup_protection import (
    BackupProtectionError,
    BackupProtectionService,
    ExternalCommandProtectionAdapter,
)
from guif.private_backup import PrivateBackupService
from guif.private_data import PrivateDataLayout
from guif.upgrade_assurance import UpgradeAssuranceService


def _archive(workspace: Path, destination: Path) -> Path:
    fixture = PrivateDataLayout(workspace).themes / "fictional-edge-theme" / "versions" / "1.json"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "theme_id": "fictional-edge-theme",
                "version": 1,
                "name": "Fictional Edge Theme",
                "content": {"description": "Test-only neutral UI fixture."},
            }
        ),
        encoding="utf-8",
    )
    PrivateBackupService(workspace).create(destination)
    return destination


def _adapter(tmp_path: Path) -> ExternalCommandProtectionAdapter:
    script = tmp_path / "copy-bytes.py"
    script.write_text(
        "from pathlib import Path\n"
        "import sys\n"
        "Path(sys.argv[2]).write_bytes(Path(sys.argv[1]).read_bytes())\n",
        encoding="utf-8",
    )
    argv = (sys.executable, str(script), "{input}", "{output}")
    return ExternalCommandProtectionAdapter(
        adapter_id="test-copy-protector",
        protect_argv=argv,
        unprotect_argv=argv,
        timeout_seconds=30,
    )


def test_backup_protection_refuses_existing_destination_without_mutation(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    archive = _archive(workspace, tmp_path / "portable.guif-private.zip")
    destination = tmp_path / "protected.bin"
    destination.write_bytes(b"existing-owner-data")
    service = BackupProtectionService(_adapter(tmp_path))

    with pytest.raises(BackupProtectionError):
        service.protect(archive, destination)

    assert destination.read_bytes() == b"existing-owner-data"
    assert not destination.with_suffix(destination.suffix + ".guif-protection.json").exists()


def test_upgrade_public_result_hides_private_paths_and_full_migration_evidence(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    layout = PrivateDataLayout(workspace)
    record = layout.conversation_workflows / "SampleGame" / "conversation-alpha28.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "project": "SampleGame",
                "conversation_id": "fictional-alpha28-upgrade",
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    _archive(workspace, layout.backups / "before-beta1.guif-private.zip")

    result = UpgradeAssuranceService(workspace).run(
        "1.0.0-alpha.28",
        apply=True,
        actor="privacy-test",
    )

    serialized = json.dumps(result)
    assert result["status"] == "verified"
    assert result["private_report_written"] is True
    assert "private_report" not in serialized
    assert "report" not in serialized
    assert str(layout.root) not in serialized
    assert result["migration"] == {
        "status": "applied",
        "applied_count": 1,
        "compatibility_preserved": True,
    }
