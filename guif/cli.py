from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from guif import __version__
from guif.asset_qa import validate_asset_against_manifest
from guif.compositor import compose_masked_edit
from guif.core import create_plan, init_project, project_root, record_memory, validate_project
from guif.exporter import export_project_assets
from guif.image_qa import compare_protected_pixels
from guif.resource import create_resource_manifest, load_resource_manifest, validate_resource_file
from guif.theme import create_theme, validate_theme_file
from guif.workflow import list_workflows, load_workflow, validate_workflow_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="guif", description="Game UI Framework CLI")
    parser.add_argument("--version", action="version", version=f"GUIF {__version__}")
    parser.add_argument("--workspace", type=Path, default=Path.cwd(), help="Framework workspace root")
    sub = parser.add_subparsers(dest="command", required=True)
    init_cmd = sub.add_parser("init", help="Create a GUIF project"); init_cmd.add_argument("project")
    inspect_cmd = sub.add_parser("inspect", help="Inspect framework or project state"); inspect_cmd.add_argument("project", nargs="?")
    plan_cmd = sub.add_parser("plan", help="Create a routed plan from a requirement"); plan_cmd.add_argument("requirement"); plan_cmd.add_argument("--project", required=True)
    validate_cmd = sub.add_parser("validate", help="Validate a project workspace"); validate_cmd.add_argument("project")
    record_cmd = sub.add_parser("record", help="Record reusable project memory"); record_cmd.add_argument("memory_type", choices=("decision", "lesson", "mistake", "best-practice")); record_cmd.add_argument("message"); record_cmd.add_argument("--project", required=True)
    theme_cmd = sub.add_parser("theme-create", help="Create and activate a project theme"); theme_cmd.add_argument("name"); theme_cmd.add_argument("description"); theme_cmd.add_argument("--project", required=True)
    theme_validate_cmd = sub.add_parser("theme-validate", help="Validate a theme JSON file"); theme_validate_cmd.add_argument("path", type=Path)
    workflow_list_cmd = sub.add_parser("workflow-list", help="List built-in and project workflow manifests"); workflow_list_cmd.add_argument("--project")
    workflow_show_cmd = sub.add_parser("workflow-show", help="Show the resolved workflow manifest"); workflow_show_cmd.add_argument("workflow_id"); workflow_show_cmd.add_argument("--project", required=True)
    workflow_validate_cmd = sub.add_parser("workflow-validate", help="Validate a workflow JSON file"); workflow_validate_cmd.add_argument("path", type=Path)
    resource_create_cmd = sub.add_parser("resource-create", help="Create a production resource manifest")
    resource_create_cmd.add_argument("resource_id"); resource_create_cmd.add_argument("resource_type"); resource_create_cmd.add_argument("width", type=int); resource_create_cmd.add_argument("height", type=int); resource_create_cmd.add_argument("file_format")
    resource_create_cmd.add_argument("--project", required=True); resource_create_cmd.add_argument("--target-engine", default="generic"); resource_create_cmd.add_argument("--output-name"); resource_create_cmd.add_argument("--source"); resource_create_cmd.add_argument("--alpha", action=argparse.BooleanOptionalAction, default=True)
    resource_create_cmd.add_argument("--import-settings", default="{}", help="JSON object with engine-specific import hints")
    resource_validate_cmd = sub.add_parser("resource-validate", help="Validate a production resource manifest"); resource_validate_cmd.add_argument("path", type=Path)
    resource_show_cmd = sub.add_parser("resource-show", help="Show a normalized production resource manifest"); resource_show_cmd.add_argument("path", type=Path)
    asset_validate_cmd = sub.add_parser("asset-validate", help="Validate an image asset against a resource manifest"); asset_validate_cmd.add_argument("manifest", type=Path); asset_validate_cmd.add_argument("asset", type=Path)
    export_cmd = sub.add_parser("export", help="Validate and export project assets deterministically"); export_cmd.add_argument("project"); export_cmd.add_argument("--target", default="generic"); export_cmd.add_argument("--output", type=Path); export_cmd.add_argument("--clean", action=argparse.BooleanOptionalAction, default=True)
    pixel_cmd = sub.add_parser("qa-pixels", help="Verify that protected pixels did not change"); pixel_cmd.add_argument("original", type=Path); pixel_cmd.add_argument("edited", type=Path); pixel_cmd.add_argument("mask", type=Path); pixel_cmd.add_argument("--tolerance", type=int, default=0)
    composite_cmd = sub.add_parser("compose-edit", help="Compose generated pixels through a mask while preserving protected pixels"); composite_cmd.add_argument("original", type=Path); composite_cmd.add_argument("generated", type=Path); composite_cmd.add_argument("mask", type=Path); composite_cmd.add_argument("output", type=Path); composite_cmd.add_argument("--feather", type=float, default=0.0); composite_cmd.add_argument("--threshold", type=int, default=1); composite_cmd.add_argument("--verify", action=argparse.BooleanOptionalAction, default=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv); workspace = args.workspace.resolve()
    try:
        if args.command == "init": print(init_project(workspace, args.project)); return 0
        if args.command == "inspect":
            if args.project:
                root = project_root(workspace, args.project); config_path = root / "project.json"
                if not config_path.exists(): raise FileNotFoundError(f"Unknown project: {args.project}")
                payload = {"root": str(root), "config": json.loads(config_path.read_text(encoding="utf-8")), "plans": len(list((root / "plans").glob("*.json"))), "themes": sorted(path.stem for path in (root / "themes").glob("*.json")), "resources": sorted(path.name for path in (root / "production-assets").glob("*.resource.json")), "workflows": list_workflows(workspace, args.project)}
            else:
                projects_dir = workspace / "projects"; payload = {"version": __version__, "workspace": str(workspace), "projects": sorted(path.name for path in projects_dir.iterdir() if path.is_dir()) if projects_dir.exists() else [], "workflows": list_workflows(workspace)}
            print(json.dumps(payload, ensure_ascii=False, indent=2)); return 0
        if args.command == "plan": print(create_plan(workspace, args.project, args.requirement)); return 0
        if args.command == "validate":
            errors = validate_project(workspace, args.project)
            if errors:
                for error in errors: print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print(f"OK: {args.project}"); return 0
        if args.command == "record": print(record_memory(workspace, args.project, args.memory_type, args.message)); return 0
        if args.command == "theme-create": print(create_theme(workspace, args.project, args.name, args.description)); return 0
        if args.command == "theme-validate":
            errors = validate_theme_file(args.path)
            if errors:
                for error in errors: print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print(f"OK: {args.path}"); return 0
        if args.command == "workflow-list": print(json.dumps(list_workflows(workspace, args.project), ensure_ascii=False, indent=2)); return 0
        if args.command == "workflow-show": print(json.dumps(load_workflow(workspace, args.project, args.workflow_id).to_dict(), ensure_ascii=False, indent=2)); return 0
        if args.command == "workflow-validate":
            errors = validate_workflow_file(args.path)
            if errors:
                for error in errors: print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print(f"OK: {args.path}"); return 0
        if args.command == "resource-create":
            import_settings = json.loads(args.import_settings)
            if not isinstance(import_settings, dict): raise ValueError("--import-settings must decode to a JSON object")
            print(create_resource_manifest(workspace, args.project, args.resource_id, args.resource_type, args.width, args.height, args.file_format, alpha_required=args.alpha, target_engine=args.target_engine, output_name=args.output_name, source=args.source, import_settings=import_settings)); return 0
        if args.command == "resource-validate":
            errors = validate_resource_file(args.path)
            if errors:
                for error in errors: print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print(f"OK: {args.path}"); return 0
        if args.command == "resource-show": print(json.dumps(load_resource_manifest(args.path).to_dict(), ensure_ascii=False, indent=2)); return 0
        if args.command == "asset-validate":
            report = validate_asset_against_manifest(args.manifest, args.asset); print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2)); return 0 if report.passed else 1
        if args.command == "export":
            report = export_project_assets(workspace, args.project, target_engine=args.target, output_dir=args.output, clean=args.clean); print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2)); return 0 if report.passed else 1
        if args.command == "qa-pixels":
            report = compare_protected_pixels(args.original, args.edited, args.mask, args.tolerance); print(json.dumps(report.to_dict(), indent=2)); return 0 if report.passed else 1
        if args.command == "compose-edit":
            report = compose_masked_edit(args.original, args.generated, args.mask, args.output, feather_radius=args.feather, threshold=args.threshold); payload: dict[str, object] = {"composition": report.to_dict()}
            if args.verify:
                qa = compare_protected_pixels(args.original, args.output, args.mask, tolerance=0); payload["protected_pixel_qa"] = qa.to_dict(); print(json.dumps(payload, indent=2)); return 0 if qa.passed else 1
            print(json.dumps(payload, indent=2)); return 0
    except (FileExistsError, FileNotFoundError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 2
    return 0


if __name__ == "__main__": raise SystemExit(main())
