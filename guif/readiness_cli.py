from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from guif.backup_protection import BackupProtectionService, external_adapter_from_env
from guif.beta_readiness import BetaReadinessService, bootstrap_workspace
from guif.compatibility import compatibility_contract
from guif.fault_injection import FaultInjector
from guif.hardening import HardeningService, SOAK_PROFILES
from guif.private_backup import PrivateBackupService
from guif.private_data import PrivateDataLayout
from guif.private_migration import PrivateSchemaMigrator
from guif.release_provenance import (
    DEFAULT_MANIFEST_NAME,
    generate_hash_provenance,
    verify_hash_provenance,
)
from guif.support_policy import support_contract
from guif.upgrade_assurance import UpgradeAssuranceService


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def _workspace(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workspace", type=Path, default=Path.cwd())


def _workspace_path(workspace: Path, value: Path) -> Path:
    return value if value.is_absolute() else workspace / value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="guif-ready",
        description=(
            "Bootstrap, diagnose, migrate, back up, upgrade, and harden the GUIF beta.2 MVP"
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="Initialize Project, Host credential, and Conversation")
    _workspace(start)
    start.add_argument("--project", required=True)
    start.add_argument("--conversation", required=True)
    start.add_argument("--actor", default="conversation-host")

    diagnose = sub.add_parser("diagnose", help="Run privacy-safe beta readiness diagnostics")
    _workspace(diagnose)
    diagnose.add_argument("--project", required=True)
    diagnose.add_argument("--conversation")
    diagnose.add_argument("--no-persist", action="store_true")

    migrate = sub.add_parser("migrate", help="Plan or apply private schema repairs")
    _workspace(migrate)
    migrate.add_argument("--apply", action="store_true")
    migrate.add_argument("--actor", default="private-schema-migrator")

    backup = sub.add_parser("backup", help="Create a verified private backup")
    _workspace(backup)
    backup.add_argument("--output", type=Path)
    backup.add_argument("--profile", choices=("portable", "full-local"), default="portable")
    backup.add_argument("--include-sensitive", action="store_true")

    verify = sub.add_parser("backup-verify", help="Verify a private backup before restore")
    _workspace(verify)
    verify.add_argument("archive", type=Path)

    restore = sub.add_parser("backup-restore", help="Plan or explicitly apply a verified restore")
    _workspace(restore)
    restore.add_argument("archive", type=Path)
    restore.add_argument("--target-root", type=Path)
    restore.add_argument("--conflict", choices=("fail", "skip", "replace"), default="fail")
    restore.add_argument("--apply", action="store_true")
    restore.add_argument("--no-pre-restore-backup", action="store_true")

    protect = sub.add_parser(
        "backup-protect",
        help="Protect a verified backup with a configured external encryption tool",
    )
    _workspace(protect)
    protect.add_argument("archive", type=Path)
    protect.add_argument("protected", type=Path)

    protection_verify = sub.add_parser(
        "backup-protection-verify",
        help="Verify a protected backup and its secret-free receipt",
    )
    _workspace(protection_verify)
    protection_verify.add_argument("protected", type=Path)

    unprotect = sub.add_parser(
        "backup-unprotect",
        help="Recover a verified GUIF backup through the configured external tool",
    )
    _workspace(unprotect)
    unprotect.add_argument("protected", type=Path)
    unprotect.add_argument("archive", type=Path)

    upgrade = sub.add_parser(
        "upgrade",
        help="Plan or record a supported alpha.27/alpha.28 to beta.2 upgrade",
    )
    _workspace(upgrade)
    upgrade.add_argument("--source-release", required=True)
    upgrade.add_argument("--apply", action="store_true")
    upgrade.add_argument("--actor", default="upgrade-assurance")
    upgrade.add_argument("--no-require-backup", action="store_true")

    soak = sub.add_parser(
        "soak",
        help="Run bounded repeatability and latency checks over read-only contracts",
    )
    _workspace(soak)
    soak.add_argument("--project", required=True)
    soak.add_argument("--conversation")
    soak.add_argument("--backup", type=Path)
    soak.add_argument("--profile", choices=tuple(SOAK_PROFILES), default="standard")
    soak.add_argument("--iterations", type=int)
    soak.add_argument("--max-p95-ms", type=float)
    soak.add_argument("--report", type=Path)
    soak.add_argument("--no-persist", action="store_true")

    provenance = sub.add_parser(
        "provenance",
        help="Generate or verify hash-only wheel and sdist provenance",
    )
    _workspace(provenance)
    provenance.add_argument("--dist", type=Path, default=Path("dist"))
    provenance.add_argument("--manifest", type=Path)
    provenance.add_argument("--git-commit")
    provenance.add_argument("--verify", action="store_true")

    acceptance = sub.add_parser("acceptance", help="Check the end-to-end MVP acceptance gate")
    _workspace(acceptance)
    acceptance.add_argument("--project", required=True)
    acceptance.add_argument("--conversation", required=True)
    acceptance.add_argument("--require-completed", action="store_true")

    contract = sub.add_parser("contract", help="Show the frozen beta compatibility contract")
    _workspace(contract)

    support = sub.add_parser("support", help="Show the beta support and deprecation contract")
    _workspace(support)

    return parser


def _protection_service() -> BackupProtectionService:
    return BackupProtectionService(
        external_adapter_from_env(),
        fault_injector=FaultInjector.from_env(),
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workspace = args.workspace.resolve()
    token = os.environ.get("GUIF_HOST_TOKEN")
    try:
        if args.command == "start":
            result = bootstrap_workspace(
                workspace,
                args.project,
                args.conversation,
                bearer_token=token,
                actor_id=args.actor,
            )
        elif args.command == "diagnose":
            result = BetaReadinessService(
                workspace,
                bearer_token=token,
            ).diagnose(
                args.project,
                conversation_id=args.conversation,
                persist=not args.no_persist,
            )
        elif args.command == "migrate":
            migrator = PrivateSchemaMigrator(workspace)
            result = migrator.apply(actor=args.actor) if args.apply else migrator.scan()
        elif args.command == "backup":
            destination = args.output
            if destination is None:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                destination = (
                    PrivateDataLayout(workspace).backups
                    / f"portable-{timestamp}.guif-private.zip"
                )
            result = PrivateBackupService(workspace).create(
                destination,
                profile=args.profile,
                include_sensitive=args.include_sensitive,
            )
        elif args.command == "backup-verify":
            result = PrivateBackupService(workspace).verify(args.archive)
        elif args.command == "backup-restore":
            result = PrivateBackupService(workspace).restore(
                args.archive,
                target_root=args.target_root,
                conflict=args.conflict,
                apply=args.apply,
                create_pre_restore_backup=not args.no_pre_restore_backup,
            )
        elif args.command == "backup-protect":
            PrivateBackupService(workspace).verify(args.archive)
            result = _protection_service().protect(args.archive, args.protected)
        elif args.command == "backup-protection-verify":
            result = _protection_service().verify(args.protected)
        elif args.command == "backup-unprotect":
            result = _protection_service().unprotect(args.protected, args.archive)
            result["backup_verification"] = PrivateBackupService(workspace).verify(args.archive)
        elif args.command == "upgrade":
            result = UpgradeAssuranceService(workspace).run(
                args.source_release,
                apply=args.apply,
                require_backup=not args.no_require_backup,
                actor=args.actor,
            )
        elif args.command == "soak":
            report_path = (
                _workspace_path(workspace, args.report) if args.report is not None else None
            )
            result = HardeningService(
                workspace,
                bearer_token=token,
            ).soak(
                args.project,
                conversation_id=args.conversation,
                backup_path=args.backup,
                profile=args.profile,
                iterations=args.iterations,
                max_p95_ms=args.max_p95_ms,
                persist=not args.no_persist,
                report_path=report_path,
            )
        elif args.command == "provenance":
            dist_dir = _workspace_path(workspace, args.dist).resolve()
            manifest = (
                _workspace_path(workspace, args.manifest).resolve()
                if args.manifest is not None
                else dist_dir / DEFAULT_MANIFEST_NAME
            )
            if args.verify:
                result = verify_hash_provenance(
                    manifest,
                    dist_dir=dist_dir,
                    expected_git_commit=args.git_commit,
                )
            else:
                if not args.git_commit:
                    raise ValueError("--git-commit is required when generating provenance")
                result = generate_hash_provenance(
                    dist_dir,
                    git_commit=args.git_commit,
                    output_path=manifest,
                )
        elif args.command == "acceptance":
            result = BetaReadinessService(
                workspace,
                bearer_token=token,
            ).acceptance(
                args.project,
                args.conversation,
                require_completed=args.require_completed,
            )
        elif args.command == "contract":
            result = compatibility_contract()
        elif args.command == "support":
            result = support_contract()
        else:
            raise ValueError(f"Unknown command: {args.command}")
        _print(result)
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
