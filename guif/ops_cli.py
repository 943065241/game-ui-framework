from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from pathlib import Path
from typing import Any

from guif.runtime import Runtime

DEFAULT_TOKEN_ENV = "GUIF_HOST_TOKEN"
DEFAULT_LEASE_ENV = "GUIF_TASK_LEASE"


def _json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _secret_from_env(name: str) -> str:
    value = os.environ.get(name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Required secret environment variable is not set: {name}")
    return value.strip()


def _token_options(command: argparse.ArgumentParser, *, lease: bool = False) -> None:
    command.add_argument(
        "--token-env",
        default=DEFAULT_TOKEN_ENV,
        help=f"Environment variable containing the Host bearer token (default: {DEFAULT_TOKEN_ENV})",
    )
    if lease:
        command.add_argument(
            "--lease-env",
            default=DEFAULT_LEASE_ENV,
            help=f"Environment variable containing the Task lease token (default: {DEFAULT_LEASE_ENV})",
        )


def _task_command(sub: argparse._SubParsersAction, name: str, help_text: str) -> argparse.ArgumentParser:
    command = sub.add_parser(name, help=help_text)
    command.add_argument("task_id")
    command.add_argument("--project", required=True)
    return command


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="guif-ops",
        description="GUIF authenticated Host, concurrency, callback, and Git operations",
    )
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)

    credential_create = sub.add_parser("credential-create", help="Create a private Host credential")
    credential_create.add_argument("actor_id")
    credential_create.add_argument("host_id")
    credential_create.add_argument("capabilities", nargs="+")
    credential_create.add_argument("--role", action="append", default=[])
    credential_create.add_argument("--created-by", default="local-admin")
    credential_create.add_argument("--expires-at")

    credential_list = sub.add_parser("credential-list", help="List private Host credential metadata")
    credential_list.add_argument("--include-revoked", action="store_true")

    credential_revoke = sub.add_parser("credential-revoke", help="Revoke a Host credential")
    credential_revoke.add_argument("credential_id")
    credential_revoke.add_argument("--actor", required=True)
    credential_revoke.add_argument("--reason", required=True)

    credential_rotate = sub.add_parser("credential-rotate", help="Rotate a Host credential")
    credential_rotate.add_argument("credential_id")
    credential_rotate.add_argument("--actor", required=True)
    credential_rotate.add_argument("--reason", default="credential rotation")

    _task_command(sub, "task-etag", "Show the current optimistic Task etag")
    _task_command(sub, "lease-show", "Show the current Task lease")

    lease_acquire = _task_command(sub, "lease-acquire", "Acquire an exclusive Task lease")
    lease_acquire.add_argument("--expected-etag")
    lease_acquire.add_argument("--ttl", type=int, default=300)
    lease_acquire.add_argument("--purpose", default="exclusive-task-operation")
    _token_options(lease_acquire)

    lease_renew = _task_command(sub, "lease-renew", "Renew an active Task lease")
    lease_renew.add_argument("--expected-etag", required=True)
    lease_renew.add_argument("--ttl", type=int, default=300)
    _token_options(lease_renew, lease=True)

    lease_release = _task_command(sub, "lease-release", "Release a Task lease")
    lease_release.add_argument("--reason", default="released")
    _token_options(lease_release, lease=True)

    callback_submit = _task_command(sub, "callback-submit", "Submit an authenticated external Tool result")
    callback_submit.add_argument("handoff_id")
    callback_submit.add_argument("file", type=Path)
    callback_submit.add_argument("--expected-etag", required=True)
    callback_submit.add_argument("--mime-type")
    callback_submit.add_argument("--width", type=int)
    callback_submit.add_argument("--height", type=int)
    callback_submit.add_argument("--model-id")
    callback_submit.add_argument("--tool")
    callback_submit.add_argument("--request-id")
    _token_options(callback_submit, lease=True)

    callback_list = _task_command(sub, "callback-list", "List authenticated Host callbacks")
    callback_show = _task_command(sub, "callback-show", "Show one authenticated Host callback")
    callback_show.add_argument("callback_id")

    approval = _task_command(sub, "approval-decide", "Make an authenticated Approval decision")
    approval.add_argument("approval_id")
    approval.add_argument("decision", choices=("approved", "rejected", "changes-requested"))
    approval.add_argument("--expected-etag", required=True)
    approval.add_argument("--comment")
    _token_options(approval, lease=True)

    export_execute = _task_command(sub, "export-execute", "Execute Gated Export as an authenticated actor")
    export_execute.add_argument("--expected-etag", required=True)
    export_execute.add_argument("--target")
    _token_options(export_execute, lease=True)

    export_rollback = _task_command(sub, "export-rollback", "Rollback Gated Export as an authenticated actor")
    export_rollback.add_argument("export_id")
    export_rollback.add_argument("--expected-etag", required=True)
    export_rollback.add_argument("--reason", required=True)
    export_rollback.add_argument("--force", action="store_true")
    _token_options(export_rollback, lease=True)

    git_plan = _task_command(sub, "git-plan", "Prepare a Task-bound Git Change Set from a completed Export")
    git_plan.add_argument("export_id")
    git_plan.add_argument("--expected-etag", required=True)
    git_plan.add_argument("--branch")
    git_plan.add_argument("--message")
    _token_options(git_plan)

    _task_command(sub, "git-list", "List Task-bound Git Change Sets")
    git_show = _task_command(sub, "git-show", "Show one Git Change Set")
    git_show.add_argument("change_set_id")
    git_diff = _task_command(sub, "git-diff", "Show one Git Change Set diff")
    git_diff.add_argument("change_set_id")

    git_commit = _task_command(sub, "git-commit", "Commit a ready Git Change Set on its dedicated branch")
    git_commit.add_argument("change_set_id")
    git_commit.add_argument("--expected-etag", required=True)
    _token_options(git_commit, lease=True)

    git_revert = _task_command(sub, "git-revert", "Create a revert commit for a committed Git Change Set")
    git_revert.add_argument("change_set_id")
    git_revert.add_argument("--expected-etag", required=True)
    git_revert.add_argument("--reason", required=True)
    _token_options(git_revert, lease=True)

    _task_command(sub, "summary", "Show authenticated operation summary for a Task")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runtime = Runtime(args.workspace.resolve())
    try:
        if args.command == "credential-create":
            _json(runtime.register_host_credential(
                args.actor_id,
                args.host_id,
                tuple(args.capabilities),
                roles=tuple(args.role),
                created_by=args.created_by,
                expires_at=args.expires_at,
            ))
        elif args.command == "credential-list":
            _json(runtime.list_host_credentials(include_revoked=args.include_revoked))
        elif args.command == "credential-revoke":
            _json(runtime.revoke_host_credential(args.credential_id, actor=args.actor, reason=args.reason))
        elif args.command == "credential-rotate":
            _json(runtime.rotate_host_credential(args.credential_id, actor=args.actor, reason=args.reason))
        elif args.command == "task-etag":
            print(runtime.get_task_etag(args.project, args.task_id))
        elif args.command == "lease-show":
            _json(runtime.get_task_lease(args.project, args.task_id))
        elif args.command == "lease-acquire":
            _json(runtime.acquire_task_lease(
                args.project,
                args.task_id,
                bearer_token=_secret_from_env(args.token_env),
                expected_task_etag=args.expected_etag,
                ttl_seconds=args.ttl,
                purpose=args.purpose,
            ))
        elif args.command == "lease-renew":
            _json(runtime.renew_task_lease(
                args.project,
                args.task_id,
                bearer_token=_secret_from_env(args.token_env),
                lease_token=_secret_from_env(args.lease_env),
                expected_task_etag=args.expected_etag,
                ttl_seconds=args.ttl,
            ))
        elif args.command == "lease-release":
            _json(runtime.release_task_lease(
                args.project,
                args.task_id,
                bearer_token=_secret_from_env(args.token_env),
                lease_token=_secret_from_env(args.lease_env),
                reason=args.reason,
            ))
        elif args.command == "callback-submit":
            if not args.file.is_file():
                raise FileNotFoundError(f"Host result file does not exist: {args.file}")
            mime_type = args.mime_type or mimetypes.guess_type(args.file.name)[0] or "application/octet-stream"
            _json(runtime.submit_authenticated_tool_result(
                args.project,
                args.task_id,
                args.handoff_id,
                bearer_token=_secret_from_env(args.token_env),
                lease_token=_secret_from_env(args.lease_env),
                expected_task_etag=args.expected_etag,
                content=args.file.read_bytes(),
                filename=args.file.name,
                mime_type=mime_type,
                width=args.width,
                height=args.height,
                model_id=args.model_id,
                tool_id=args.tool,
                request_id=args.request_id,
            ).to_dict())
        elif args.command == "callback-list":
            _json(runtime.list_host_callbacks(args.project, args.task_id))
        elif args.command == "callback-show":
            _json(runtime.get_host_callback(args.project, args.task_id, args.callback_id))
        elif args.command == "approval-decide":
            _json(runtime.decide_approval_authenticated(
                args.project,
                args.task_id,
                args.approval_id,
                args.decision,
                bearer_token=_secret_from_env(args.token_env),
                lease_token=_secret_from_env(args.lease_env),
                expected_task_etag=args.expected_etag,
                comment=args.comment,
            ).to_dict())
        elif args.command == "export-execute":
            _json(runtime.execute_gated_export_authenticated(
                args.project,
                args.task_id,
                bearer_token=_secret_from_env(args.token_env),
                lease_token=_secret_from_env(args.lease_env),
                expected_task_etag=args.expected_etag,
                target_engine=args.target,
            ))
        elif args.command == "export-rollback":
            _json(runtime.rollback_gated_export_authenticated(
                args.project,
                args.task_id,
                args.export_id,
                bearer_token=_secret_from_env(args.token_env),
                lease_token=_secret_from_env(args.lease_env),
                expected_task_etag=args.expected_etag,
                reason=args.reason,
                force=args.force,
            ))
        elif args.command == "git-plan":
            _json(runtime.prepare_export_git_change(
                args.project,
                args.task_id,
                args.export_id,
                bearer_token=_secret_from_env(args.token_env),
                expected_task_etag=args.expected_etag,
                branch_name=args.branch,
                message=args.message,
            ))
        elif args.command == "git-list":
            _json(runtime.list_git_changes(args.project, args.task_id))
        elif args.command == "git-show":
            _json(runtime.get_git_change(args.project, args.task_id, args.change_set_id))
        elif args.command == "git-diff":
            _json(runtime.diff_git_change(args.project, args.task_id, args.change_set_id))
        elif args.command == "git-commit":
            _json(runtime.execute_git_change(
                args.project,
                args.task_id,
                args.change_set_id,
                bearer_token=_secret_from_env(args.token_env),
                lease_token=_secret_from_env(args.lease_env),
                expected_task_etag=args.expected_etag,
            ))
        elif args.command == "git-revert":
            _json(runtime.revert_git_change(
                args.project,
                args.task_id,
                args.change_set_id,
                bearer_token=_secret_from_env(args.token_env),
                lease_token=_secret_from_env(args.lease_env),
                expected_task_etag=args.expected_etag,
                reason=args.reason,
            ))
        elif args.command == "summary":
            _json(runtime.operation_summary(args.project, args.task_id))
        else:
            raise ValueError(f"Unsupported operational command: {args.command}")
    except (FileNotFoundError, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
