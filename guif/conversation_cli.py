from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from guif.conversation_workflow import ConversationWorkflowService
from guif.runtime import Runtime


def _json_object(value: str, *, label: str) -> dict[str, Any]:
    source = value
    if value.startswith("@"):
        source = Path(value[1:]).read_text(encoding="utf-8")
    try:
        parsed = json.loads(source)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be a JSON object or @path") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} must be a JSON object")
    return parsed


def _print(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def _service(args: argparse.Namespace) -> ConversationWorkflowService:
    workspace = args.workspace.resolve()
    runtime = Runtime(workspace)
    token = os.environ.get("GUIF_HOST_TOKEN")
    return ConversationWorkflowService(
        workspace,
        runtime=runtime,
        bearer_token=token,
    )


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--project", required=True)
    parser.add_argument("--conversation", required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="guif-conversation",
        description=(
            "Use GUIF through a private conversation-first workflow without manually handling "
            "Task IDs, etags, leases, claims, handoffs, or callbacks"
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    open_parser = sub.add_parser("open", help="Open or reconcile a conversation")
    _common(open_parser)
    open_parser.add_argument("--diagnostics", action="store_true")

    status = sub.add_parser("status", help="Show the current user-facing stage")
    _common(status)
    status.add_argument("--diagnostics", action="store_true")

    theme_list = sub.add_parser("theme-list", help="List private Theme choices")
    _common(theme_list)

    theme_select = sub.add_parser("theme-select", help="Select a historical private Theme")
    _common(theme_select)
    theme_select.add_argument("theme_id")
    theme_select.add_argument("--version", type=int)
    theme_select.add_argument("--actor", default="conversation-user")

    theme_create = sub.add_parser("theme-create", help="Create and select a private Theme")
    _common(theme_create)
    theme_create.add_argument("name")
    theme_create.add_argument("content", help="JSON object or @path")
    theme_create.add_argument("--actor", default="conversation-user")

    theme_derive = sub.add_parser("theme-derive", help="Derive and select a new Theme version")
    _common(theme_derive)
    theme_derive.add_argument("theme_id")
    theme_derive.add_argument("updates", help="JSON object or @path")
    theme_derive.add_argument("--from-version", type=int)
    theme_derive.add_argument("--name")
    theme_derive.add_argument("--actor", default="conversation-user")

    unbound = sub.add_parser("theme-unbound", help="Explicitly continue without a Theme")
    _common(unbound)

    submit = sub.add_parser("submit", help="Submit a natural-language design request")
    _common(submit)
    submit.add_argument("requirement")
    submit.add_argument("--pipeline", default="ui-production")
    submit.add_argument("--request-key")

    for name, help_text in (
        ("approve", "Approve the current initial or revision gate and continue"),
        ("request-changes", "Request changes at the current approval gate"),
        ("reject", "Reject the current approval gate"),
    ):
        decision = sub.add_parser(name, help=help_text)
        _common(decision)
        decision.add_argument("--comment")

    continue_parser = sub.add_parser("continue", help="Continue the next approved production step")
    _common(continue_parser)

    export = sub.add_parser("export", help="Execute the final gated export")
    _common(export)
    export.add_argument("--target-engine")

    recover = sub.add_parser("recover", help="Reconcile private conversation state")
    _common(recover)

    retry = sub.add_parser("retry", help="Retry from a persisted failure or Tool wait")
    _common(retry)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        service = _service(args)
        project = args.project
        conversation = args.conversation
        command = args.command

        if command == "open":
            result = service.open(
                project,
                conversation,
                include_diagnostics=args.diagnostics,
            )
        elif command == "status":
            result = service.status(
                project,
                conversation,
                include_diagnostics=args.diagnostics,
            )
        elif command == "theme-list":
            result = {
                "schema_version": 1,
                "project": project,
                "conversation_id": conversation,
                "themes": [
                    {
                        "choice_id": item.get("theme_id"),
                        "name": item.get("name"),
                        "version": item.get("latest_version"),
                        "status": item.get("status"),
                        "updated_at": item.get("updated_at"),
                    }
                    for item in service.runtime.list_private_themes()
                ],
            }
        elif command == "theme-select":
            result = service.select_theme(
                project,
                conversation,
                args.theme_id,
                version=args.version,
                actor=args.actor,
            )
        elif command == "theme-create":
            result = service.create_theme(
                project,
                conversation,
                args.name,
                _json_object(args.content, label="Theme content"),
                actor=args.actor,
            )
        elif command == "theme-derive":
            result = service.derive_theme(
                project,
                conversation,
                args.theme_id,
                _json_object(args.updates, label="Theme updates"),
                from_version=args.from_version,
                name=args.name,
                actor=args.actor,
            )
        elif command == "theme-unbound":
            result = service.continue_unbound(project, conversation)
        elif command == "submit":
            result = service.submit(
                project,
                conversation,
                args.requirement,
                pipeline=args.pipeline,
                request_key=args.request_key,
            )
        elif command == "approve":
            result = service.approve(project, conversation, comment=args.comment)
        elif command == "request-changes":
            result = service.request_changes(project, conversation, comment=args.comment)
        elif command == "reject":
            result = service.reject(project, conversation, comment=args.comment)
        elif command == "continue":
            result = service.continue_work(project, conversation)
        elif command == "export":
            result = service.export(
                project,
                conversation,
                target_engine=args.target_engine,
            )
        elif command == "recover":
            result = service.recover(project, conversation)
        elif command == "retry":
            result = service.retry(project, conversation)
        else:
            raise ValueError(f"Unknown command: {command}")
        _print(result)
        return 0
    except (FileNotFoundError, RuntimeError, ValueError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
