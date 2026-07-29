from __future__ import annotations

import argparse
import json
from pathlib import Path

from guif.runtime import Runtime


def _print(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="guif-ledger",
        description="Inspect and verify the private GUIF operation ledger",
    )
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("descriptor")
    sub.add_parser("verify")
    listing = sub.add_parser("list")
    listing.add_argument("--limit", type=int, default=100)
    listing.add_argument("--operation", action="append", default=[])
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runtime = Runtime(args.workspace.resolve())
    if args.command == "descriptor":
        _print(runtime.operation_ledger_descriptor())
        return 0
    if args.command == "verify":
        report = runtime.verify_operation_ledger()
        _print(report)
        return 0 if report.get("valid") is True else 1
    if args.command == "list":
        _print(
            {
                "schema_version": 1,
                "entries": list(
                    runtime.list_operation_ledger(
                        limit=args.limit,
                        operations=tuple(args.operation),
                    )
                ),
            }
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
