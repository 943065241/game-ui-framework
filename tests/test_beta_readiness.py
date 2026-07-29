from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest
from PIL import Image

from guif.beta_readiness import BetaReadinessService, bootstrap_workspace
from guif.compatibility import compatibility_contract
from guif.conversation_workflow import ConversationWorkflowService
from guif.private_backup import PrivateBackupError, PrivateBackupService
from guif.private_data import PrivateDataLayout
from guif.private_migration import PrivateMigrationError, PrivateSchemaMigrator
from guif.runtime import Runtime

PROJECT = "SampleGame"
CONVERSATION = "conversation-alpha28-fictional"
THEME = {
    "description": "A wholly fictional crystalline observatory interface.",
    "palette": ["test cyan", "test charcoal"],
    "materials": ["matte crystal"],
    "lighting": "soft artificial starlight",
    "must_include": ["radial navigation"],
    "avoid": ["real brands"],
}


def _png_bytes(width: int = 1080, height: int = 2340) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", (width, height), (70, 100, 130, 255)).save(buffer, format="PNG")
    return buffer.getvalue()


def _boot(workspace: Path) -> tuple[Runtime, ConversationWorkflowService, str]:
    result = bootstrap_workspace(workspace, PROJECT, CONVERSATION)
    token = result["bearer_token"]
    runtime = Runtime(workspace)
    return runtime, ConversationWorkflowService(
        workspace,
        runtime=runtime,
        bearer_token=token,
    ), token


def test_one_command_bootstrap_keeps_secret_out_of_private_conversation_record(tmp_path: Path) -> None:
    result = bootstrap_workspace(tmp_path, PROJECT, CONVERSATION)

    assert result["project_created"] is True
    assert result["credential_created"] is True
    assert result["credential_secret_visible_once"] is True
    assert result["bearer_token"].startswith("guifh1.")
    assert result["conversation"]["stage"] == "theme-confirmation"
    assert (tmp_path / "projects" / PROJECT / "project.json").is_file()

    record_path = next(
        PrivateDataLayout(tmp_path).conversation_workflows.glob(
            f"{PROJECT}/conversation-*.json"
        )
    )
    persisted = record_path.read_text(encoding="utf-8")
    assert result["bearer_token"] not in persisted
    assert "lease_token" not in persisted
    assert "claim_token" not in persisted


def test_current_conversation_record_does_not_require_legacy_migration(tmp_path: Path) -> None:
    _boot(tmp_path)

    scan = PrivateSchemaMigrator(tmp_path).scan()

    assert scan["status"] == "current"
    assert scan["migration_required_count"] == 0
    assert scan["blocked_count"] == 0


def test_portable_backup_is_verified_and_excludes_authentication_material(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    runtime, conversation, token = _boot(workspace)
    conversation.create_theme(PROJECT, CONVERSATION, "Fictional Observatory", THEME)
    destination = tmp_path / "portable.guif-private.zip"

    created = PrivateBackupService(workspace).create(destination)

    assert created["status"] == "created"
    assert created["verification"]["status"] == "verified"
    with zipfile.ZipFile(destination, "r") as archive:
        names = archive.namelist()
    assert any(name.startswith("data/themes/") for name in names)
    assert any(name.startswith("data/conversation-workflows/") for name in names)
    assert not any(name.startswith("data/host-credentials/") for name in names)
    assert not any(name.startswith("data/operation-ledger/") for name in names)


def test_full_local_backup_requires_explicit_sensitive_material_decision(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    _boot(workspace)

    with pytest.raises(PrivateBackupError):
        PrivateBackupService(workspace).create(
            tmp_path / "full.guif-private.zip",
            profile="full-local",
        )


def test_restore_is_plan_first_and_preserves_verified_private_files(tmp_path: Path) -> None:
    source = tmp_path / "source"
    runtime, conversation, token = _boot(source)
    conversation.create_theme(PROJECT, CONVERSATION, "Fictional Observatory", THEME)
    archive = tmp_path / "portable.guif-private.zip"
    PrivateBackupService(source).create(archive)

    target_workspace = tmp_path / "target-workspace"
    target_root = tmp_path / "restored-private"
    restore = PrivateBackupService(target_workspace, data_root=target_root)
    plan = restore.restore(archive, target_root=target_root)
    assert plan["status"] == "planned"
    assert not target_root.exists()

    applied = restore.restore(
        archive,
        target_root=target_root,
        apply=True,
    )
    assert applied["status"] == "restored"
    assert any((target_root / item["path"]).is_file() for item in applied["applied"])
    assert tuple((target_root / "themes").glob("*/versions/1.json"))


def test_restore_rejects_a_target_inside_framework_workspace(tmp_path: Path) -> None:
    source = tmp_path / "source"
    runtime, conversation, token = _boot(source)
    conversation.create_theme(PROJECT, CONVERSATION, "Fictional Observatory", THEME)
    archive = tmp_path / "portable.guif-private.zip"
    PrivateBackupService(source).create(archive)

    target_workspace = tmp_path / "target-workspace"
    target_workspace.mkdir()
    service = PrivateBackupService(target_workspace)

    with pytest.raises(PrivateBackupError):
        service.restore(
            archive,
            target_root=target_workspace / "private-data",
        )


def test_backup_verification_rejects_tampered_member(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    runtime, conversation, token = _boot(workspace)
    conversation.create_theme(PROJECT, CONVERSATION, "Fictional Observatory", THEME)
    original = tmp_path / "original.guif-private.zip"
    tampered = tmp_path / "tampered.guif-private.zip"
    service = PrivateBackupService(workspace)
    service.create(original)

    with zipfile.ZipFile(original, "r") as source, zipfile.ZipFile(
        tampered,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as target:
        changed = False
        for info in source.infolist():
            content = source.read(info.filename)
            if not changed and info.filename.startswith("data/"):
                content += b"tampered"
                changed = True
            target.writestr(info.filename, content)

    with pytest.raises(PrivateBackupError):
        service.verify(tampered)


def test_backup_verification_rejects_unmanifested_directory_member(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    runtime, conversation, token = _boot(workspace)
    conversation.create_theme(PROJECT, CONVERSATION, "Fictional Observatory", THEME)
    original = tmp_path / "original.guif-private.zip"
    unexpected = tmp_path / "unexpected-directory.guif-private.zip"
    service = PrivateBackupService(workspace)
    service.create(original)

    with zipfile.ZipFile(original, "r") as source, zipfile.ZipFile(
        unexpected,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as target:
        for info in source.infolist():
            target.writestr(info.filename, source.read(info.filename))
        target.writestr("unexpected/", b"")

    with pytest.raises(PrivateBackupError):
        service.verify(unexpected)


def test_private_schema_migration_repairs_v1_record_and_records_history(tmp_path: Path) -> None:
    layout = PrivateDataLayout(tmp_path)
    path = layout.conversation_workflows / PROJECT / "conversation-legacy.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "conversation_id": "legacy",
                "project": PROJECT,
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
            }
        ),
        encoding="utf-8",
    )
    migrator = PrivateSchemaMigrator(tmp_path)

    scan = migrator.scan()
    assert scan["status"] == "migration-required"
    applied = migrator.apply(actor="test-migrator")
    assert applied["applied_count"] == 1

    repaired = json.loads(path.read_text(encoding="utf-8"))
    assert repaired["schema_version"] == 1
    assert repaired["request_records"] == {}
    assert repaired["privacy"]["raw_secrets_persisted"] is False
    assert repaired["compatibility"]["public_api_version"] == 1
    assert repaired["migration_history"][-1]["actor"] == "test-migrator"
    assert migrator.scan()["status"] == "current"


def test_private_schema_migration_blocks_raw_secret_fields(tmp_path: Path) -> None:
    layout = PrivateDataLayout(tmp_path)
    path = layout.conversation_workflows / PROJECT / "conversation-unsafe.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "conversation_id": "unsafe",
                "project": PROJECT,
                "bearer_token": "must-not-be-migrated",
            }
        ),
        encoding="utf-8",
    )
    migrator = PrivateSchemaMigrator(tmp_path)

    assert migrator.scan()["status"] == "blocked"
    with pytest.raises(PrivateMigrationError):
        migrator.apply()


def test_readiness_diagnostics_are_privacy_safe_by_default(tmp_path: Path) -> None:
    runtime, conversation, token = _boot(tmp_path)
    report = BetaReadinessService(
        tmp_path,
        runtime=runtime,
        bearer_token=token,
    ).diagnose(
        PROJECT,
        conversation_id=CONVERSATION,
        persist=False,
    )

    serialized = json.dumps(report)
    assert report["status"] in {"ready", "action-required"}
    assert "bearer_token" not in serialized
    assert "lease_token" not in serialized
    assert "claim_token" not in serialized
    assert "task_id" not in serialized
    assert "private_storage_root" not in serialized


def test_end_to_end_acceptance_reaches_ready_to_export_without_manual_runtime_ids(
    tmp_path: Path,
) -> None:
    runtime, conversation, token = _boot(tmp_path)
    conversation.create_theme(PROJECT, CONVERSATION, "Fictional Observatory", THEME)
    submitted = conversation.submit(
        PROJECT,
        CONVERSATION,
        "Create a 1080x2340 fictional observatory page and export Unity",
        request_key="alpha28-e2e-001",
    )
    assert submitted["stage"] == "approval-required"
    conversation.approve(PROJECT, CONVERSATION)

    view = conversation.run_host_until_blocked(
        PROJECT,
        CONVERSATION,
        image_executor=lambda work, attachments: {
            "content": _png_bytes(),
            "filename": "fictional-observatory.png",
            "mime_type": "image/png",
            "width": 1080,
            "height": 2340,
            "model_id": "chatgpt-image",
            "metadata": {"fictional_fixture": True},
        },
        visual_inspector=lambda work, attachments: {
            "inspector_id": "chatgpt-vision",
            "status": "passed",
            "summary": "The fictional acceptance fixture satisfies every supplied review dimension.",
            "findings": [],
            "metadata": {"semantic_pixels_inspected": True},
        },
    )
    assert view["stage"] == "ready-to-export"

    acceptance = BetaReadinessService(
        tmp_path,
        runtime=runtime,
        bearer_token=token,
    ).acceptance(PROJECT, CONVERSATION)
    assert acceptance["status"] == "passed"
    assert acceptance["mvp_contract_frozen"] is True


def test_alpha28_compatibility_contract_freezes_public_stages_and_privacy() -> None:
    contract = compatibility_contract()

    assert contract["release"] == "1.0.0-alpha.28"
    assert contract["public_api_version"] == 1
    assert "theme-confirmation" in contract["conversation"]["stages"]
    assert "ready-to-export" in contract["conversation"]["stages"]
    assert contract["privacy"]["portable_backups_include_host_credentials"] is False
