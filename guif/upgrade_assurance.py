from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from guif.compatibility import compatibility_contract
from guif.private_data import PrivateDataLayout
from guif.private_migration import PrivateSchemaMigrator

BETA_RELEASE = "1.0.0-beta.1"
SUPPORTED_ALPHA_SOURCES = (
    "1.0.0-alpha.27",
    "1.0.0-alpha.28",
)


class UpgradeAssuranceError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    try:
        os.chmod(temporary, 0o600)
    except OSError:
        pass
    temporary.replace(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


class UpgradeAssuranceService:
    """Plan and record supported alpha-to-beta private-data upgrades.

    The service does not infer a source release from file timestamps. The owner
    supplies the installed source release explicitly, then GUIF checks backup
    readiness, private schema compatibility, and the frozen public contract.
    """

    def __init__(self, workspace: Path, *, data_root: Path | None = None) -> None:
        self.workspace = workspace.resolve()
        self.layout = PrivateDataLayout(self.workspace, data_root)
        self.migrator = PrivateSchemaMigrator(self.workspace, data_root=data_root)

    def plan(
        self,
        source_release: str,
        *,
        require_backup: bool = True,
    ) -> dict[str, Any]:
        source = source_release.strip()
        supported = source in SUPPORTED_ALPHA_SOURCES
        backup_count = (
            len(tuple(self.layout.backups.glob("*.guif-private.zip")))
            if self.layout.backups.is_dir()
            else 0
        )
        migration = self.migrator.scan()
        reasons: list[str] = []
        if not supported:
            reasons.append("unsupported-source-release")
        if require_backup and backup_count == 0:
            reasons.append("portable-backup-required")
        if migration["status"] == "blocked":
            reasons.append("private-schema-blocked")
        actions: list[str] = []
        if require_backup and backup_count == 0:
            actions.append("create-portable-backup")
        if migration["status"] == "migration-required":
            actions.append("apply-private-migration")
        if migration["status"] == "blocked":
            actions.append("inspect-private-records")
        if not supported:
            actions.append("install-supported-alpha-or-use-manual-migration")
        status = "blocked" if reasons else (
            "action-required" if actions else "ready"
        )
        return {
            "schema_version": 1,
            "status": status,
            "source_release": source,
            "target_release": BETA_RELEASE,
            "source_supported": supported,
            "supported_sources": list(SUPPORTED_ALPHA_SOURCES),
            "portable_backup_required": require_backup,
            "portable_backup_count": backup_count,
            "private_schema_status": migration["status"],
            "migration_required_count": migration["migration_required_count"],
            "migration_blocked_count": migration["blocked_count"],
            "blocking_reasons": reasons,
            "actions": actions,
            "public_api_preserved": compatibility_contract()["public_api_version"] == 1,
            "planned_at": _now(),
        }

    def run(
        self,
        source_release: str,
        *,
        apply: bool = False,
        require_backup: bool = True,
        actor: str = "upgrade-assurance",
    ) -> dict[str, Any]:
        plan = self.plan(source_release, require_backup=require_backup)
        if not apply:
            return {**plan, "apply_required": plan["status"] != "ready"}
        if not plan["source_supported"]:
            raise UpgradeAssuranceError(
                f"Unsupported upgrade source: {plan['source_release']}"
            )
        if "portable-backup-required" in plan["blocking_reasons"]:
            raise UpgradeAssuranceError(
                "A verified-location portable backup is required before beta upgrade"
            )
        if "private-schema-blocked" in plan["blocking_reasons"]:
            raise UpgradeAssuranceError(
                "Private schema upgrade is blocked and requires manual inspection"
            )
        migration_result: dict[str, Any] | None = None
        if plan["private_schema_status"] == "migration-required":
            migration_result = self.migrator.apply(actor=actor)
        post_scan = self.migrator.scan()
        if post_scan["status"] != "current":
            raise UpgradeAssuranceError(
                f"Private schemas are not current after upgrade: {post_scan['status']}"
            )
        result = {
            "schema_version": 1,
            "status": "verified",
            "source_release": plan["source_release"],
            "target_release": BETA_RELEASE,
            "portable_backup_count": plan["portable_backup_count"],
            "migration": migration_result,
            "private_schema_status": post_scan["status"],
            "public_api_version": compatibility_contract()["public_api_version"],
            "public_api_preserved": True,
            "actor": actor.strip() or "upgrade-assurance",
            "completed_at": _now(),
        }
        report_path = (
            self.layout.upgrade_reports
            / f"upgrade-{_timestamp()}-{plan['source_release'].replace('.', '-')}.json"
        )
        _write_json(report_path, result)
        return {**result, "private_report_written": True}


__all__ = [
    "BETA_RELEASE",
    "SUPPORTED_ALPHA_SOURCES",
    "UpgradeAssuranceError",
    "UpgradeAssuranceService",
]
