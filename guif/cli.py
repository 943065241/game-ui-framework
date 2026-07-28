from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from guif import __version__
from guif.core import create_plan, init_project, project_root, record_memory, validate_project


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="guif", description="Game UI Framework CLI")
    parser.add_argument("--version", action="version", version=f"GUIF {__version__}")
    parser.add_argument("--workspace", type=Path, default=Path.cwd(), help="Framework workspace root")
    sub = parser.add_subparsers(dest="command", required=True)

    init_cmd = sub.add_parser("init", help="Create a GUIF project")
    init_cmd.add_argument("project")

    inspect_cmd = sub.add_parser("inspect", help="Inspect framework or project state")
    inspect_cmd.add_argument("project", nargs="?")

    plan_cmd = sub.add_parser("plan", help="Create a routed plan from a requirement")
    plan_cmd.add_argument("requirement")
    plan_cmd.add_argument("--project", required=True)

    validate_cmd = sub.add_parser("validate", help="Validate a project workspace")
    validate_cmd.add_argument("project")

    record_cmd = sub.add_parser("record", help="Record reusable project memory")
    record_cmd.add_argument("memory_type", choices=("decision", "lesson", "mistake", "best-practice"))
    record_cmd.add_argument("message")
    record_cmd.add_argument("--project", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workspace = args.workspace.resolve()
    try:
        if args.command == "init":
            print(init_project(workspace, args.project))
            return 0
        if args.command == "inspect":
            if args.project:
                root = project_root(workspace, args.project)
                config_path = root / "project.json"
                if not config_path.exists():
                    raise FileNotFoundError(f"Unknown project: {args.project}")
                config = json.loads(config_path.read_text(encoding="utf-8"))
                plans = len(list((root / "plans").glob("*.json")))
                print(json.dumps({"root": str(root), "config": config, "plans": plans}, ensure_ascii=False, indent=2))
            else:
                projects_dir = workspace / "projects"
                projects = sorted(path.name for path in projects_dir.iterdir() if path.is_dir()) if projects_dir.exists() else []
                print(json.dumps({"version": __version__, "workspace": str(workspace), "projects": projects}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "plan":
            print(create_plan(workspace, args.project, args.requirement))
            return 0
        if args.command == "validate":
            errors = validate_project(workspace, args.project)
            if errors:
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print(f"OK: {args.project}")
            return 0
        if args.command == "record":
            print(record_memory(workspace, args.project, args.memory_type, args.message))
            return 0
    except (FileExistsError, FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
