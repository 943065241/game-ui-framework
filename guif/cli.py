from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from pathlib import Path

from guif import __version__
from guif.asset_qa import validate_asset_against_manifest
from guif.compositor import compose_masked_edit
from guif.core import create_plan, init_project, project_root, record_memory, validate_project
from guif.exporter import export_project_assets
from guif.image_qa import compare_protected_pixels
from guif.resource import create_resource_manifest, load_resource_manifest, validate_resource_file
from guif.revision_review import RevisionReviewService
from guif.runtime import Runtime
from guif.theme import create_theme, validate_theme_file
from guif.workflow import list_workflows, load_workflow, validate_workflow_file


def _approval_command(sub: argparse._SubParsersAction, name: str, help_text: str) -> None:
    command = sub.add_parser(name, help=help_text)
    command.add_argument("task_id")
    command.add_argument("approval_id")
    command.add_argument("--project", required=True)
    command.add_argument("--actor", required=True)
    command.add_argument("--comment")


def _revision_decision_command(sub: argparse._SubParsersAction, name: str, help_text: str) -> None:
    command = sub.add_parser(name, help=help_text)
    command.add_argument("task_id")
    command.add_argument("revision_id")
    command.add_argument("--project", required=True)
    command.add_argument("--actor", required=True)
    command.add_argument("--comment")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="guif", description="Game UI Framework CLI")
    parser.add_argument("--version", action="version", version=f"GUIF {__version__}")
    parser.add_argument("--workspace", type=Path, default=Path.cwd(), help="Framework workspace root")
    sub = parser.add_subparsers(dest="command", required=True)
    init_cmd = sub.add_parser("init", help="Create a GUIF project"); init_cmd.add_argument("project")
    inspect_cmd = sub.add_parser("inspect", help="Inspect framework or project state"); inspect_cmd.add_argument("project", nargs="?")
    plan_cmd = sub.add_parser("plan", help="Create a routed plan from a requirement"); plan_cmd.add_argument("requirement"); plan_cmd.add_argument("--project", required=True)
    run_cmd = sub.add_parser("run", help="Execute and persist a requirement through the GUIF runtime"); run_cmd.add_argument("requirement"); run_cmd.add_argument("--project", required=True); run_cmd.add_argument("--pipeline", default="ui-production")
    run_list_cmd = sub.add_parser("run-list", help="List persisted runtime task runs"); run_list_cmd.add_argument("--project", required=True)
    run_show_cmd = sub.add_parser("run-show", help="Show a persisted runtime task"); run_show_cmd.add_argument("task_id"); run_show_cmd.add_argument("--project", required=True)
    run_resume_cmd = sub.add_parser("run-resume", help="Resume a failed or interrupted runtime task"); run_resume_cmd.add_argument("task_id"); run_resume_cmd.add_argument("--project", required=True)
    approval_list_cmd = sub.add_parser("run-approval-list", help="Show persisted approval state for a task"); approval_list_cmd.add_argument("task_id"); approval_list_cmd.add_argument("--project", required=True)
    _approval_command(sub, "run-approve", "Approve one required task approval point")
    _approval_command(sub, "run-reject", "Reject one required task approval point")
    _approval_command(sub, "run-request-changes", "Request changes for one required task approval point")

    sub.add_parser("host-show", help="Show the active Host profile")
    sub.add_parser("host-discover", help="Run the Host capability discovery protocol")
    sub.add_parser("tool-list", help="List registered Tools and manifests")
    tool_discover_cmd = sub.add_parser("tool-discover", help="Discover registered, available, and installable Tools"); tool_discover_cmd.add_argument("--project"); tool_discover_cmd.add_argument("--mode", choices=("production", "development", "ci"))
    tool_health_cmd = sub.add_parser("tool-health", help="Run a Tool health check"); tool_health_cmd.add_argument("tool_id"); tool_health_cmd.add_argument("--project"); tool_health_cmd.add_argument("--mode", choices=("production", "development", "ci")); tool_health_cmd.add_argument("--explicit", action="store_true")
    health_retry_cmd = sub.add_parser("tool-health-retry", help="Persist a Tool health retry and resume approved connections when ready"); health_retry_cmd.add_argument("tool_id"); health_retry_cmd.add_argument("--project", required=True)
    contract_test_cmd = sub.add_parser("tool-contract-test", help="Run side-effect-free Tool Adapter contract tests"); contract_test_cmd.add_argument("tool_id"); contract_test_cmd.add_argument("--mode", choices=("production", "development", "ci"), default="production")
    tool_bind_cmd = sub.add_parser("tool-bind", help="Bind a registered Tool to one Project capability"); tool_bind_cmd.add_argument("capability"); tool_bind_cmd.add_argument("tool_id"); tool_bind_cmd.add_argument("--project", required=True)
    tool_scaffold_cmd = sub.add_parser("tool-scaffold", help="Create an unimplemented Tool Adapter scaffold"); tool_scaffold_cmd.add_argument("tool_id"); tool_scaffold_cmd.add_argument("capabilities", nargs="+"); tool_scaffold_cmd.add_argument("--execution-mode", choices=("direct", "external-callback"), default="external-callback")
    connect_request_cmd = sub.add_parser("tool-connect-request", help="Create a reviewable Tool connection request"); connect_request_cmd.add_argument("capability"); connect_request_cmd.add_argument("tool_id", nargs="?"); connect_request_cmd.add_argument("--project", required=True); connect_request_cmd.add_argument("--requested-by", default="host"); connect_request_cmd.add_argument("--reason"); connect_request_cmd.add_argument("--requires", nargs="*", default=[])
    connect_list_cmd = sub.add_parser("tool-connect-list", help="List persisted Tool connection requests"); connect_list_cmd.add_argument("--project", required=True)
    connect_approve_cmd = sub.add_parser("tool-connect-approve", help="Approve a Tool connection after reviewing disclosures"); connect_approve_cmd.add_argument("request_id"); connect_approve_cmd.add_argument("--project", required=True); connect_approve_cmd.add_argument("--actor", required=True); connect_approve_cmd.add_argument("--comment"); connect_approve_cmd.add_argument("--credential-ref")
    connect_reject_cmd = sub.add_parser("tool-connect-reject", help="Reject a Tool connection request"); connect_reject_cmd.add_argument("request_id"); connect_reject_cmd.add_argument("--project", required=True); connect_reject_cmd.add_argument("--actor", required=True); connect_reject_cmd.add_argument("--comment")

    sub.add_parser("provider-list", help="List legacy Provider adapters and capabilities")
    execute_cmd = sub.add_parser("run-execute", help="Resolve and execute one approved Prompt or Revision job through a configured Tool"); execute_cmd.add_argument("task_id"); execute_cmd.add_argument("job_id"); execute_cmd.add_argument("--project", required=True); execute_cmd.add_argument("--tool"); execute_cmd.add_argument("--provider", help="Legacy explicit Provider path")
    resolution_cmd = sub.add_parser("run-tool-resolution", help="Show persisted Tool resolution state"); resolution_cmd.add_argument("task_id"); resolution_cmd.add_argument("--project", required=True)
    handoff_list_cmd = sub.add_parser("run-tool-handoff-list", help="List persisted external Tool handoffs"); handoff_list_cmd.add_argument("task_id"); handoff_list_cmd.add_argument("--project", required=True)
    submit_cmd = sub.add_parser("run-tool-submit", help="Submit an external Host Tool result file"); submit_cmd.add_argument("task_id"); submit_cmd.add_argument("handoff_id"); submit_cmd.add_argument("file", type=Path); submit_cmd.add_argument("--project", required=True); submit_cmd.add_argument("--tool"); submit_cmd.add_argument("--mime-type"); submit_cmd.add_argument("--width", type=int); submit_cmd.add_argument("--height", type=int); submit_cmd.add_argument("--model-id")
    cancel_tool_cmd = sub.add_parser("run-tool-cancel", help="Cancel a Task waiting for Tool configuration or result"); cancel_tool_cmd.add_argument("task_id"); cancel_tool_cmd.add_argument("--project", required=True); cancel_tool_cmd.add_argument("--reason", required=True)

    artifact_list_cmd = sub.add_parser("run-artifact-list", help="List Artifact records for a task"); artifact_list_cmd.add_argument("task_id"); artifact_list_cmd.add_argument("--project", required=True)
    artifact_show_cmd = sub.add_parser("run-artifact-show", help="Show one Artifact record"); artifact_show_cmd.add_argument("task_id"); artifact_show_cmd.add_argument("artifact_id"); artifact_show_cmd.add_argument("--project", required=True)
    sub.add_parser("visual-inspector-list", help="List registered Visual Inspection adapters")
    review_cmd = sub.add_parser("run-artifact-review", help="Run eligibility, image metadata, and optional semantic Visual review"); review_cmd.add_argument("task_id"); review_cmd.add_argument("artifact_id"); review_cmd.add_argument("--project", required=True); review_cmd.add_argument("--inspector")
    review_list_cmd = sub.add_parser("run-visual-review-list", help="List persisted Visual Review records"); review_list_cmd.add_argument("task_id"); review_list_cmd.add_argument("--project", required=True)
    revision_list_cmd = sub.add_parser("run-revision-list", help="List persisted Revision Plans"); revision_list_cmd.add_argument("task_id"); revision_list_cmd.add_argument("--project", required=True)
    revision_create_cmd = sub.add_parser("run-revision-create", help="Construct a versioned edit Job from one Revision Plan"); revision_create_cmd.add_argument("task_id"); revision_create_cmd.add_argument("revision_id"); revision_create_cmd.add_argument("--project", required=True)
    revision_job_list_cmd = sub.add_parser("run-revision-job-list", help="List constructed Revision Jobs"); revision_job_list_cmd.add_argument("task_id"); revision_job_list_cmd.add_argument("--project", required=True)
    revision_approval_cmd = sub.add_parser("run-revision-approval", help="Show one Revision approval gate"); revision_approval_cmd.add_argument("task_id"); revision_approval_cmd.add_argument("revision_id"); revision_approval_cmd.add_argument("--project", required=True)
    _revision_decision_command(sub, "run-revision-approve", "Approve one constructed Revision Job")
    _revision_decision_command(sub, "run-revision-reject", "Reject one constructed Revision Job")
    _revision_decision_command(sub, "run-revision-request-changes", "Request changes for one constructed Revision Job")
    revision_execute_cmd = sub.add_parser("run-revision-execute", help="Execute an approved Revision Job through Tool routing"); revision_execute_cmd.add_argument("task_id"); revision_execute_cmd.add_argument("revision_id"); revision_execute_cmd.add_argument("--project", required=True); revision_execute_cmd.add_argument("--tool")
    supersede_cmd = sub.add_parser("run-artifact-supersede", help="Explicitly supersede an older Artifact with a compatible replacement"); supersede_cmd.add_argument("task_id"); supersede_cmd.add_argument("old_artifact_id"); supersede_cmd.add_argument("new_artifact_id"); supersede_cmd.add_argument("--project", required=True)

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
                payload = {"root": str(root), "config": json.loads(config_path.read_text(encoding="utf-8")), "plans": len(list((root / "plans").glob("*.json"))), "runs": len(list((root / "runs").glob("*/task.json"))) if (root / "runs").exists() else 0, "themes": sorted(path.stem for path in (root / "themes").glob("*.json")), "resources": sorted(path.name for path in (root / "production-assets").glob("*.resource.json")), "workflows": list_workflows(workspace, args.project)}
            else:
                projects_dir = workspace / "projects"; payload = {"version": __version__, "workspace": str(workspace), "projects": sorted(path.name for path in projects_dir.iterdir() if path.is_dir()) if projects_dir.exists() else [], "workflows": list_workflows(workspace)}
            print(json.dumps(payload, ensure_ascii=False, indent=2)); return 0
        if args.command == "plan": print(create_plan(workspace, args.project, args.requirement)); return 0
        if args.command == "run": print(json.dumps(Runtime(workspace).run(args.project, args.requirement, pipeline=args.pipeline).to_dict(), ensure_ascii=False, indent=2)); return 0
        if args.command == "run-list": print(json.dumps(Runtime(workspace).list_runs(args.project), ensure_ascii=False, indent=2)); return 0
        if args.command == "run-show": print(json.dumps(Runtime(workspace).load_task(args.project, args.task_id).to_dict(), ensure_ascii=False, indent=2)); return 0
        if args.command == "run-resume": print(json.dumps(Runtime(workspace).resume(args.project, args.task_id).to_dict(), ensure_ascii=False, indent=2)); return 0
        if args.command == "run-approval-list": print(json.dumps(Runtime(workspace).get_approvals(args.project, args.task_id), ensure_ascii=False, indent=2)); return 0
        if args.command in {"run-approve", "run-reject", "run-request-changes"}:
            runtime = Runtime(workspace); method = {"run-approve": runtime.approve, "run-reject": runtime.reject, "run-request-changes": runtime.request_changes}[args.command]
            print(json.dumps(method(args.project, args.task_id, args.approval_id, actor=args.actor, comment=args.comment).to_dict(), ensure_ascii=False, indent=2)); return 0
        if args.command == "host-show": print(json.dumps(Runtime(workspace).get_host_profile(), ensure_ascii=False, indent=2)); return 0
        if args.command == "host-discover": print(json.dumps(Runtime(workspace).discover_host(), ensure_ascii=False, indent=2)); return 0
        if args.command == "tool-list": print(json.dumps(Runtime(workspace).list_tools(), ensure_ascii=False, indent=2)); return 0
        if args.command == "tool-discover": print(json.dumps(Runtime(workspace).discover_tools(project=args.project, mode=args.mode), ensure_ascii=False, indent=2)); return 0
        if args.command == "tool-health": print(json.dumps(Runtime(workspace).tool_health(args.tool_id, project=args.project, mode=args.mode, explicit=args.explicit), ensure_ascii=False, indent=2)); return 0
        if args.command == "tool-health-retry": print(json.dumps(Runtime(workspace).retry_tool_health(args.project, args.tool_id), ensure_ascii=False, indent=2)); return 0
        if args.command == "tool-contract-test": print(json.dumps(Runtime(workspace).run_tool_contract_tests(args.tool_id, mode=args.mode), ensure_ascii=False, indent=2)); return 0
        if args.command == "tool-bind": print(Runtime(workspace).bind_project_tool(args.project, args.capability, args.tool_id)); return 0
        if args.command == "tool-scaffold": print(Runtime(workspace).scaffold_tool(args.tool_id, tuple(args.capabilities), execution_mode=args.execution_mode)); return 0
        if args.command == "tool-connect-request": print(json.dumps(Runtime(workspace).request_tool_connection(args.project, args.capability, args.tool_id, requested_by=args.requested_by, reason=args.reason, required_capabilities=tuple(args.requires)), ensure_ascii=False, indent=2)); return 0
        if args.command == "tool-connect-list": print(json.dumps(Runtime(workspace).list_tool_connections(args.project), ensure_ascii=False, indent=2)); return 0
        if args.command == "tool-connect-approve": print(json.dumps(Runtime(workspace).approve_tool_connection(args.project, args.request_id, actor=args.actor, comment=args.comment, credential_ref=args.credential_ref), ensure_ascii=False, indent=2)); return 0
        if args.command == "tool-connect-reject": print(json.dumps(Runtime(workspace).reject_tool_connection(args.project, args.request_id, actor=args.actor, comment=args.comment), ensure_ascii=False, indent=2)); return 0
        if args.command == "provider-list": print(json.dumps(Runtime(workspace).list_providers(), ensure_ascii=False, indent=2)); return 0
        if args.command == "run-execute": print(json.dumps(Runtime(workspace).execute_job(args.project, args.task_id, args.job_id, tool_id=args.tool, provider_id=args.provider).to_dict(), ensure_ascii=False, indent=2)); return 0
        if args.command == "run-tool-resolution": print(json.dumps(Runtime(workspace).get_tool_resolution(args.project, args.task_id), ensure_ascii=False, indent=2)); return 0
        if args.command == "run-tool-handoff-list": print(json.dumps(Runtime(workspace).list_tool_handoffs(args.project, args.task_id), ensure_ascii=False, indent=2)); return 0
        if args.command == "run-tool-submit":
            if not args.file.is_file(): raise FileNotFoundError(f"Tool result file does not exist: {args.file}")
            mime_type = args.mime_type or mimetypes.guess_type(args.file.name)[0] or "application/octet-stream"
            task = Runtime(workspace).submit_tool_result(args.project, args.task_id, args.handoff_id, content=args.file.read_bytes(), filename=args.file.name, mime_type=mime_type, width=args.width, height=args.height, model_id=args.model_id, tool_id=args.tool)
            print(json.dumps(task.to_dict(), ensure_ascii=False, indent=2)); return 0
        if args.command == "run-tool-cancel": print(json.dumps(Runtime(workspace).cancel_tool_wait(args.project, args.task_id, reason=args.reason).to_dict(), ensure_ascii=False, indent=2)); return 0
        if args.command == "run-artifact-list": print(json.dumps(Runtime(workspace).list_artifacts(args.project, args.task_id), ensure_ascii=False, indent=2)); return 0
        if args.command == "run-artifact-show": print(json.dumps(Runtime(workspace).get_artifact(args.project, args.task_id, args.artifact_id), ensure_ascii=False, indent=2)); return 0
        if args.command == "visual-inspector-list": print(json.dumps(RevisionReviewService(workspace).list_inspectors(), ensure_ascii=False, indent=2)); return 0
        if args.command == "run-artifact-review": print(json.dumps(RevisionReviewService(workspace).review(args.project, args.task_id, args.artifact_id, inspector_id=args.inspector).to_dict(), ensure_ascii=False, indent=2)); return 0
        if args.command == "run-visual-review-list": print(json.dumps(RevisionReviewService(workspace).list_reviews(args.project, args.task_id), ensure_ascii=False, indent=2)); return 0
        if args.command == "run-revision-list": print(json.dumps(RevisionReviewService(workspace).list_revision_plans(args.project, args.task_id), ensure_ascii=False, indent=2)); return 0
        if args.command == "run-revision-create": print(json.dumps(Runtime(workspace).create_revision_job(args.project, args.task_id, args.revision_id).to_dict(), ensure_ascii=False, indent=2)); return 0
        if args.command == "run-revision-job-list": print(json.dumps(Runtime(workspace).list_revision_jobs(args.project, args.task_id), ensure_ascii=False, indent=2)); return 0
        if args.command == "run-revision-approval": print(json.dumps(Runtime(workspace).get_revision_approval(args.project, args.task_id, args.revision_id), ensure_ascii=False, indent=2)); return 0
        if args.command in {"run-revision-approve", "run-revision-reject", "run-revision-request-changes"}:
            runtime = Runtime(workspace); method = {"run-revision-approve": runtime.approve_revision, "run-revision-reject": runtime.reject_revision, "run-revision-request-changes": runtime.request_revision_changes}[args.command]
            print(json.dumps(method(args.project, args.task_id, args.revision_id, actor=args.actor, comment=args.comment).to_dict(), ensure_ascii=False, indent=2)); return 0
        if args.command == "run-revision-execute": print(json.dumps(Runtime(workspace).execute_revision(args.project, args.task_id, args.revision_id, tool_id=args.tool).to_dict(), ensure_ascii=False, indent=2)); return 0
        if args.command == "run-artifact-supersede": print(json.dumps(RevisionReviewService(workspace).supersede(args.project, args.task_id, args.old_artifact_id, args.new_artifact_id).to_dict(), ensure_ascii=False, indent=2)); return 0
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
    except (FileExistsError, FileNotFoundError, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return 2
    return 0


if __name__ == "__main__": raise SystemExit(main())
