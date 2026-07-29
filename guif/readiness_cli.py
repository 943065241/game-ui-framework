from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from guif.beta_readiness import BetaReadinessService, bootstrap_workspace
from guif.compatibility import compatibility_contract
from guif.private_backup import PrivateBackupService
from guif.private_data import PrivateDataLayout
from guif.private_migration import PrivateSchemaMigrator


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def _workspace(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workspace", type=Path, default=Path.cwd())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="guif-ready",
        description=(
            "Bootstrap, diagnose, migrate, back up, restore, and accept the frozen GUIF alpha.28 MVP"
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

    acceptance = sub.add_parser("acceptance", help="Check the end-to-end MVP acceptance gate")
    _workspace(acceptance)
    acceptance.add_argument("--project", required=True)
    acceptance.add_argument("--conversation", required=True)
    acceptance.add_argument("--require-completed", action="store_true")

    contract = sub.add_parser("contract", help="Show the frozen alpha.28 compatibility contract")
    _workspace(contract)

    return parser


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
        else:
            raise ValueError(f"Unknown command: {args.command}")
        _print(result)
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
