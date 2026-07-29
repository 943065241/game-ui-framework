from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from pathlib import Path
from typing import Any

from guif import __version__
from guif.asset_qa import validate_asset_against_manifest
from guif.compositor import compose_masked_edit
from guif.core import create_plan, init_project, project_root, record_memory, validate_project
from guif.exporter import export_project_assets
from guif.image_qa import compare_protected_pixels
from guif.resource import create_resource_manifest, load_resource_manifest, validate_resource_file
from guif.revision_review import RevisionReviewService
from guif.runtime import Runtime, ThemeResolutionRequired
from guif.theme import validate_theme_file
from guif.workflow import list_workflows, load_workflow, validate_workflow_file


def _json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def _object(value: str, *, option: str) -> dict[str, Any]:
    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise ValueError(f"{option} must decode to a JSON object")
    return payload


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
    inspect_cmd = sub.add_parser("inspect", help="Inspect framework or project state without revealing private Theme content"); inspect_cmd.add_argument("project", nargs="?")
    plan_cmd = sub.add_parser("plan", help="Create a private routed plan from a requirement"); plan_cmd.add_argument("requirement"); plan_cmd.add_argument("--project", required=True)
    run_cmd = sub.add_parser("run", help="Execute and privately persist a requirement through the GUIF runtime"); run_cmd.add_argument("requirement"); run_cmd.add_argument("--project", required=True); run_cmd.add_argument("--pipeline", default="ui-production"); run_cmd.add_argument("--conversation-id"); run_cmd.add_argument("--continue-unbound", action="store_true")
    run_list_cmd = sub.add_parser("run-list", help="List persisted private runtime task runs"); run_list_cmd.add_argument("--project", required=True)
    run_show_cmd = sub.add_parser("run-show", help="Show a persisted runtime task"); run_show_cmd.add_argument("task_id"); run_show_cmd.add_argument("--project", required=True)
    run_resume_cmd = sub.add_parser("run-resume", help="Resume a failed or interrupted runtime task"); run_resume_cmd.add_argument("task_id"); run_resume_cmd.add_argument("--project", required=True)
    approval_list_cmd = sub.add_parser("run-approval-list", help="Show persisted approval state for a task"); approval_list_cmd.add_argument("task_id"); approval_list_cmd.add_argument("--project", required=True)
    _approval_command(sub, "run-approve", "Approve one required task approval point")
    _approval_command(sub, "run-reject", "Reject one required task approval point")
    _approval_command(sub, "run-request-changes", "Request changes for one required task approval point")

    theme_list = sub.add_parser("theme-list", help="List private Theme metadata without full Theme content"); theme_list.add_argument("--include-archived", action="store_true")
    theme_show = sub.add_parser("theme-show", help="Show one private Theme version"); theme_show.add_argument("theme_id"); theme_show.add_argument("--version", type=int)
    theme_create = sub.add_parser("theme-create", help="Create a private Theme and optionally bind it"); theme_create.add_argument("name"); theme_create.add_argument("description"); theme_create.add_argument("--content-json", default="{}"); theme_create.add_argument("--project"); theme_create.add_argument("--conversation-id"); theme_create.add_argument("--actor", default="host"); theme_create.add_argument("--status", choices=("draft", "published", "archived"), default="published")
    theme_derive = sub.add_parser("theme-derive", help="Create an immutable private Theme version"); theme_derive.add_argument("theme_id"); theme_derive.add_argument("updates_json"); theme_derive.add_argument("--from-version", type=int); theme_derive.add_argument("--project"); theme_derive.add_argument("--conversation-id"); theme_derive.add_argument("--actor", default="host"); theme_derive.add_argument("--name"); theme_derive.add_argument("--status", choices=("draft", "published", "archived"), default="published")
    theme_bind = sub.add_parser("theme-bind", help="Bind a private Theme to a conversation or project"); theme_bind.add_argument("theme_id"); theme_bind.add_argument("--version", type=int); theme_bind.add_argument("--project"); theme_bind.add_argument("--conversation-id"); theme_bind.add_argument("--actor", default="host")
    conversation_theme = sub.add_parser("conversation-theme-resolve", help="Resolve or request Theme confirmation for a conversation"); conversation_theme.add_argument("conversation_id"); conversation_theme.add_argument("--project")
    theme_migrate = sub.add_parser("theme-migrate-private", help="Migrate legacy project-local Theme files to private storage"); theme_migrate.add_argument("project"); theme_migrate.add_argument("--actor", default="migration")
    theme_validate = sub.add_parser("theme-validate", help="Validate a Theme JSON file"); theme_validate.add_argument("path", type=Path)
    privacy_audit = sub.add_parser("privacy-audit", help="Audit the current working tree for private GUIF data"); privacy_audit.add_argument("--sensitive-term", action="append", default=[]); privacy_audit.add_argument("--no-persist", action="store_true")

    sub.add_parser("host-show", help="Show the active Host profile")
    sub.add_parser("host-discover", help="Run the Host capability discovery protocol")
    sub.add_parser("tool-list", help="List registered Tools and manifests")
    tool_discover = sub.add_parser("tool-discover", help="Discover registered, available, and installable Tools"); tool_discover.add_argument("--project"); tool_discover.add_argument("--mode", choices=("production", "development", "ci"))
    tool_health = sub.add_parser("tool-health", help="Run a Tool health check"); tool_health.add_argument("tool_id"); tool_health.add_argument("--project"); tool_health.add_argument("--mode", choices=("production", "development", "ci")); tool_health.add_argument("--explicit", action="store_true")
    health_retry = sub.add_parser("tool-health-retry", help="Persist a Tool health retry"); health_retry.add_argument("tool_id"); health_retry.add_argument("--project", required=True)
    contract_test = sub.add_parser("tool-contract-test", help="Run side-effect-free Tool Adapter contract tests"); contract_test.add_argument("tool_id"); contract_test.add_argument("--mode", choices=("production", "development", "ci"), default="production")
    tool_bind = sub.add_parser("tool-bind", help="Bind a registered Tool to one Project capability"); tool_bind.add_argument("capability"); tool_bind.add_argument("tool_id"); tool_bind.add_argument("--project", required=True)
    tool_scaffold = sub.add_parser("tool-scaffold", help="Create an unimplemented Tool Adapter scaffold"); tool_scaffold.add_argument("tool_id"); tool_scaffold.add_argument("capabilities", nargs="+"); tool_scaffold.add_argument("--execution-mode", choices=("direct", "external-callback"), default="external-callback")
    connect_request = sub.add_parser("tool-connect-request", help="Create a reviewable Tool connection request"); connect_request.add_argument("capability"); connect_request.add_argument("tool_id", nargs="?"); connect_request.add_argument("--project", required=True); connect_request.add_argument("--requested-by", default="host"); connect_request.add_argument("--reason"); connect_request.add_argument("--requires", nargs="*", default=[])
    connect_list = sub.add_parser("tool-connect-list", help="List persisted Tool connection requests"); connect_list.add_argument("--project", required=True)
    connect_approve = sub.add_parser("tool-connect-approve", help="Approve a Tool connection"); connect_approve.add_argument("request_id"); connect_approve.add_argument("--project", required=True); connect_approve.add_argument("--actor", required=True); connect_approve.add_argument("--comment"); connect_approve.add_argument("--credential-ref")
    connect_reject = sub.add_parser("tool-connect-reject", help="Reject a Tool connection"); connect_reject.add_argument("request_id"); connect_reject.add_argument("--project", required=True); connect_reject.add_argument("--actor", required=True); connect_reject.add_argument("--comment")

    sub.add_parser("provider-list", help="List legacy Provider adapters and capabilities")
    execute = sub.add_parser("run-execute", help="Execute one approved Prompt or Revision job"); execute.add_argument("task_id"); execute.add_argument("job_id"); execute.add_argument("--project", required=True); execute.add_argument("--tool"); execute.add_argument("--provider")
    resolution = sub.add_parser("run-tool-resolution", help="Show persisted Tool resolution state"); resolution.add_argument("task_id"); resolution.add_argument("--project", required=True)
    handoff_list = sub.add_parser("run-tool-handoff-list", help="List persisted external Tool handoffs"); handoff_list.add_argument("task_id"); handoff_list.add_argument("--project", required=True)
    submit = sub.add_parser("run-tool-submit", help="Submit an external Host Tool result file"); submit.add_argument("task_id"); submit.add_argument("handoff_id"); submit.add_argument("file", type=Path); submit.add_argument("--project", required=True); submit.add_argument("--tool"); submit.add_argument("--mime-type"); submit.add_argument("--width", type=int); submit.add_argument("--height", type=int); submit.add_argument("--model-id")
    cancel_tool = sub.add_parser("run-tool-cancel", help="Cancel a Task waiting for Tool configuration or result"); cancel_tool.add_argument("task_id"); cancel_tool.add_argument("--project", required=True); cancel_tool.add_argument("--reason", required=True)

    artifact_list = sub.add_parser("run-artifact-list", help="List Artifact records for a task"); artifact_list.add_argument("task_id"); artifact_list.add_argument("--project", required=True)
    artifact_show = sub.add_parser("run-artifact-show", help="Show one Artifact record"); artifact_show.add_argument("task_id"); artifact_show.add_argument("artifact_id"); artifact_show.add_argument("--project", required=True)
    sub.add_parser("visual-inspector-list", help="List registered Visual Inspection adapters")
    review = sub.add_parser("run-artifact-review", help="Run metadata and optional semantic Visual review"); review.add_argument("task_id"); review.add_argument("artifact_id"); review.add_argument("--project", required=True); review.add_argument("--inspector")
    review_list = sub.add_parser("run-visual-review-list", help="List persisted Visual Review records"); review_list.add_argument("task_id"); review_list.add_argument("--project", required=True)
    revision_list = sub.add_parser("run-revision-list", help="List persisted Revision Plans"); revision_list.add_argument("task_id"); revision_list.add_argument("--project", required=True)
    revision_create = sub.add_parser("run-revision-create", help="Construct an edit Job from one Revision Plan"); revision_create.add_argument("task_id"); revision_create.add_argument("revision_id"); revision_create.add_argument("--project", required=True)
    revision_job_list = sub.add_parser("run-revision-job-list", help="List constructed Revision Jobs"); revision_job_list.add_argument("task_id"); revision_job_list.add_argument("--project", required=True)
    revision_approval = sub.add_parser("run-revision-approval", help="Show one Revision approval gate"); revision_approval.add_argument("task_id"); revision_approval.add_argument("revision_id"); revision_approval.add_argument("--project", required=True)
    _revision_decision_command(sub, "run-revision-approve", "Approve one constructed Revision Job")
    _revision_decision_command(sub, "run-revision-reject", "Reject one constructed Revision Job")
    _revision_decision_command(sub, "run-revision-request-changes", "Request changes for one constructed Revision Job")
    revision_execute = sub.add_parser("run-revision-execute", help="Execute an approved Revision Job"); revision_execute.add_argument("task_id"); revision_execute.add_argument("revision_id"); revision_execute.add_argument("--project", required=True); revision_execute.add_argument("--tool")
    supersede = sub.add_parser("run-artifact-supersede", help="Explicitly supersede an older Artifact"); supersede.add_argument("task_id"); supersede.add_argument("old_artifact_id"); supersede.add_argument("new_artifact_id"); supersede.add_argument("--project", required=True)

    gated_plan = sub.add_parser("run-export-plan", help="Evaluate production Export Gate without mutation"); gated_plan.add_argument("task_id"); gated_plan.add_argument("--project", required=True); gated_plan.add_argument("--target")
    gated_execute = sub.add_parser("run-export-execute", help="Materialize reviewed production Artifacts"); gated_execute.add_argument("task_id"); gated_execute.add_argument("--project", required=True); gated_execute.add_argument("--target"); gated_execute.add_argument("--actor", required=True)
    gated_list = sub.add_parser("run-export-list", help="List gated Export records"); gated_list.add_argument("task_id"); gated_list.add_argument("--project", required=True)
    gated_show = sub.add_parser("run-export-show", help="Show one gated Export record"); gated_show.add_argument("task_id"); gated_show.add_argument("export_id"); gated_show.add_argument("--project", required=True)
    gated_rollback = sub.add_parser("run-export-rollback", help="Rollback one completed gated Export"); gated_rollback.add_argument("task_id"); gated_rollback.add_argument("export_id"); gated_rollback.add_argument("--project", required=True); gated_rollback.add_argument("--actor", required=True); gated_rollback.add_argument("--reason", required=True); gated_rollback.add_argument("--force", action="store_true")

    validate = sub.add_parser("validate", help="Validate a project workspace"); validate.add_argument("project")
    record = sub.add_parser("record", help="Record reusable project memory"); record.add_argument("memory_type", choices=("decision", "lesson", "mistake", "best-practice")); record.add_argument("message"); record.add_argument("--project", required=True)
    workflow_list = sub.add_parser("workflow-list", help="List built-in and project workflows"); workflow_list.add_argument("--project")
    workflow_show = sub.add_parser("workflow-show", help="Show a workflow manifest"); workflow_show.add_argument("workflow_id"); workflow_show.add_argument("--project", required=True)
    workflow_validate = sub.add_parser("workflow-validate", help="Validate a workflow JSON file"); workflow_validate.add_argument("path", type=Path)
    resource_create = sub.add_parser("resource-create", help="Create a production resource manifest"); resource_create.add_argument("resource_id"); resource_create.add_argument("resource_type"); resource_create.add_argument("width", type=int); resource_create.add_argument("height", type=int); resource_create.add_argument("file_format"); resource_create.add_argument("--project", required=True); resource_create.add_argument("--target-engine", default="generic"); resource_create.add_argument("--output-name"); resource_create.add_argument("--source"); resource_create.add_argument("--alpha", action=argparse.BooleanOptionalAction, default=True); resource_create.add_argument("--import-settings", default="{}")
    resource_validate = sub.add_parser("resource-validate", help="Validate a production resource manifest"); resource_validate.add_argument("path", type=Path)
    resource_show = sub.add_parser("resource-show", help="Show a normalized resource manifest"); resource_show.add_argument("path", type=Path)
    asset_validate = sub.add_parser("asset-validate", help="Validate an image asset against a resource manifest"); asset_validate.add_argument("manifest", type=Path); asset_validate.add_argument("asset", type=Path)
    export = sub.add_parser("export", help="Export existing Project Resource files"); export.add_argument("project"); export.add_argument("--target", default="generic"); export.add_argument("--output", type=Path); export.add_argument("--clean", action=argparse.BooleanOptionalAction, default=True)
    pixel = sub.add_parser("qa-pixels", help="Verify protected pixels"); pixel.add_argument("original", type=Path); pixel.add_argument("edited", type=Path); pixel.add_argument("mask", type=Path); pixel.add_argument("--tolerance", type=int, default=0)
    composite = sub.add_parser("compose-edit", help="Compose generated pixels through a mask"); composite.add_argument("original", type=Path); composite.add_argument("generated", type=Path); composite.add_argument("mask", type=Path); composite.add_argument("output", type=Path); composite.add_argument("--feather", type=float, default=0.0); composite.add_argument("--threshold", type=int, default=1); composite.add_argument("--verify", action=argparse.BooleanOptionalAction, default=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workspace = args.workspace.resolve()
    runtime = Runtime(workspace)
    try:
        if args.command == "init": print(init_project(workspace, args.project)); return 0
        if args.command == "inspect":
            if args.project:
                root = project_root(workspace, args.project); config_path = root / "project.json"
                if not config_path.exists(): raise FileNotFoundError(f"Unknown project: {args.project}")
                payload = {"root": str(root), "private_data_root": str(runtime.store.private_root()), "config": json.loads(config_path.read_text(encoding="utf-8")), "run_count": len(runtime.list_runs(args.project)), "private_theme_binding": runtime.theme_store.get_binding("project", args.project), "resources": sorted(path.name for path in (root / "production-assets").glob("*.resource.json")), "workflows": list_workflows(workspace, args.project)}
            else:
                projects_dir = workspace / "projects"; payload = {"version": __version__, "workspace": str(workspace), "private_data_root": str(runtime.store.private_root()), "projects": sorted(path.name for path in projects_dir.iterdir() if path.is_dir()) if projects_dir.exists() else [], "workflows": list_workflows(workspace)}
            _json(payload); return 0
        if args.command == "plan": print(create_plan(workspace, args.project, args.requirement)); return 0
        if args.command == "run": _json(runtime.run(args.project, args.requirement, pipeline=args.pipeline, conversation_id=args.conversation_id, continue_unbound=args.continue_unbound).to_dict()); return 0
        if args.command == "run-list": _json(runtime.list_runs(args.project)); return 0
        if args.command == "run-show": _json(runtime.load_task(args.project, args.task_id).to_dict()); return 0
        if args.command == "run-resume": _json(runtime.resume(args.project, args.task_id).to_dict()); return 0
        if args.command == "run-approval-list": _json(runtime.get_approvals(args.project, args.task_id)); return 0
        if args.command in {"run-approve", "run-reject", "run-request-changes"}:
            method = {"run-approve": runtime.approve, "run-reject": runtime.reject, "run-request-changes": runtime.request_changes}[args.command]; _json(method(args.project, args.task_id, args.approval_id, actor=args.actor, comment=args.comment).to_dict()); return 0

        if args.command == "theme-list": _json(runtime.list_private_themes(include_archived=args.include_archived)); return 0
        if args.command == "theme-show": _json(runtime.get_private_theme(args.theme_id, args.version)); return 0
        if args.command == "theme-create":
            content = _object(args.content_json, option="--content-json"); content["description"] = args.description
            _json(runtime.create_private_theme(args.name, content, actor=args.actor, conversation_id=args.conversation_id, project=args.project, status=args.status)); return 0
        if args.command == "theme-derive": _json(runtime.derive_private_theme(args.theme_id, _object(args.updates_json, option="updates_json"), from_version=args.from_version, actor=args.actor, conversation_id=args.conversation_id, project=args.project, name=args.name, status=args.status)); return 0
        if args.command == "theme-bind":
            if not args.project and not args.conversation_id: raise ValueError("theme-bind requires --project or --conversation-id")
            payload: dict[str, Any] = {}
            if args.project: payload["project"] = runtime.bind_project_theme(args.project, args.theme_id, version=args.version, actor=args.actor)
            if args.conversation_id: payload["conversation"] = runtime.bind_conversation_theme(args.conversation_id, args.theme_id, version=args.version, actor=args.actor)
            _json(payload); return 0
        if args.command == "conversation-theme-resolve": _json(runtime.prepare_conversation_theme(args.conversation_id, project=args.project)); return 0
        if args.command == "theme-migrate-private": _json(runtime.migrate_legacy_project_themes(args.project, actor=args.actor)); return 0
        if args.command == "theme-validate":
            errors = validate_theme_file(args.path)
            if errors:
                for error in errors: print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print(f"OK: {args.path}"); return 0
        if args.command == "privacy-audit":
            report = runtime.audit_privacy(sensitive_terms=tuple(args.sensitive_term), persist=not args.no_persist); _json(report); return 0 if report["status"] == "passed" else 1

        if args.command == "host-show": _json(runtime.get_host_profile()); return 0
        if args.command == "host-discover": _json(runtime.discover_host()); return 0
        if args.command == "tool-list": _json(runtime.list_tools()); return 0
        if args.command == "tool-discover": _json(runtime.discover_tools(project=args.project, mode=args.mode)); return 0
        if args.command == "tool-health": _json(runtime.tool_health(args.tool_id, project=args.project, mode=args.mode, explicit=args.explicit)); return 0
        if args.command == "tool-health-retry": _json(runtime.retry_tool_health(args.project, args.tool_id)); return 0
        if args.command == "tool-contract-test": _json(runtime.run_tool_contract_tests(args.tool_id, mode=args.mode)); return 0
        if args.command == "tool-bind": print(runtime.bind_project_tool(args.project, args.capability, args.tool_id)); return 0
        if args.command == "tool-scaffold": print(runtime.scaffold_tool(args.tool_id, tuple(args.capabilities), execution_mode=args.execution_mode)); return 0
        if args.command == "tool-connect-request": _json(runtime.request_tool_connection(args.project, args.capability, args.tool_id, requested_by=args.requested_by, reason=args.reason, required_capabilities=tuple(args.requires))); return 0
        if args.command == "tool-connect-list": _json(runtime.list_tool_connections(args.project)); return 0
        if args.command == "tool-connect-approve": _json(runtime.approve_tool_connection(args.project, args.request_id, actor=args.actor, comment=args.comment, credential_ref=args.credential_ref)); return 0
        if args.command == "tool-connect-reject": _json(runtime.reject_tool_connection(args.project, args.request_id, actor=args.actor, comment=args.comment)); return 0
        if args.command == "provider-list": _json(runtime.list_providers()); return 0
        if args.command == "run-execute": _json(runtime.execute_job(args.project, args.task_id, args.job_id, tool_id=args.tool, provider_id=args.provider).to_dict()); return 0
        if args.command == "run-tool-resolution": _json(runtime.get_tool_resolution(args.project, args.task_id)); return 0
        if args.command == "run-tool-handoff-list": _json(runtime.list_tool_handoffs(args.project, args.task_id)); return 0
        if args.command == "run-tool-submit":
            if not args.file.is_file(): raise FileNotFoundError(f"Tool result file does not exist: {args.file}")
            mime_type = args.mime_type or mimetypes.guess_type(args.file.name)[0] or "application/octet-stream"
            _json(runtime.submit_tool_result(args.project, args.task_id, args.handoff_id, content=args.file.read_bytes(), filename=args.file.name, mime_type=mime_type, width=args.width, height=args.height, model_id=args.model_id, tool_id=args.tool).to_dict()); return 0
        if args.command == "run-tool-cancel": _json(runtime.cancel_tool_wait(args.project, args.task_id, reason=args.reason).to_dict()); return 0
        if args.command == "run-artifact-list": _json(runtime.list_artifacts(args.project, args.task_id)); return 0
        if args.command == "run-artifact-show": _json(runtime.get_artifact(args.project, args.task_id, args.artifact_id)); return 0
        if args.command == "visual-inspector-list": _json(RevisionReviewService(workspace).list_inspectors()); return 0
        if args.command == "run-artifact-review": _json(RevisionReviewService(workspace).review(args.project, args.task_id, args.artifact_id, inspector_id=args.inspector).to_dict()); return 0
        if args.command == "run-visual-review-list": _json(RevisionReviewService(workspace).list_reviews(args.project, args.task_id)); return 0
        if args.command == "run-revision-list": _json(RevisionReviewService(workspace).list_revision_plans(args.project, args.task_id)); return 0
        if args.command == "run-revision-create": _json(runtime.create_revision_job(args.project, args.task_id, args.revision_id).to_dict()); return 0
        if args.command == "run-revision-job-list": _json(runtime.list_revision_jobs(args.project, args.task_id)); return 0
        if args.command == "run-revision-approval": _json(runtime.get_revision_approval(args.project, args.task_id, args.revision_id)); return 0
        if args.command in {"run-revision-approve", "run-revision-reject", "run-revision-request-changes"}:
            method = {"run-revision-approve": runtime.approve_revision, "run-revision-reject": runtime.reject_revision, "run-revision-request-changes": runtime.request_revision_changes}[args.command]; _json(method(args.project, args.task_id, args.revision_id, actor=args.actor, comment=args.comment).to_dict()); return 0
        if args.command == "run-revision-execute": _json(runtime.execute_revision(args.project, args.task_id, args.revision_id, tool_id=args.tool).to_dict()); return 0
        if args.command == "run-artifact-supersede": _json(RevisionReviewService(workspace).supersede(args.project, args.task_id, args.old_artifact_id, args.new_artifact_id).to_dict()); return 0
        if args.command == "run-export-plan": _json(runtime.prepare_gated_export(args.project, args.task_id, target_engine=args.target)); return 0
        if args.command == "run-export-execute": _json(runtime.execute_gated_export(args.project, args.task_id, target_engine=args.target, actor=args.actor)); return 0
        if args.command == "run-export-list": _json(runtime.list_gated_exports(args.project, args.task_id)); return 0
        if args.command == "run-export-show": _json(runtime.get_gated_export(args.project, args.task_id, args.export_id)); return 0
        if args.command == "run-export-rollback": _json(runtime.rollback_gated_export(args.project, args.task_id, args.export_id, actor=args.actor, reason=args.reason, force=args.force)); return 0
        if args.command == "validate":
            errors = validate_project(workspace, args.project)
            if errors:
                for error in errors: print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print(f"OK: {args.project}"); return 0
        if args.command == "record": print(record_memory(workspace, args.project, args.memory_type, args.message)); return 0
        if args.command == "workflow-list": _json(list_workflows(workspace, args.project)); return 0
        if args.command == "workflow-show": _json(load_workflow(workspace, args.project, args.workflow_id).to_dict()); return 0
        if args.command == "workflow-validate":
            errors = validate_workflow_file(args.path)
            if errors:
                for error in errors: print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print(f"OK: {args.path}"); return 0
        if args.command == "resource-create": print(create_resource_manifest(workspace, args.project, args.resource_id, args.resource_type, args.width, args.height, args.file_format, alpha_required=args.alpha, target_engine=args.target_engine, output_name=args.output_name, source=args.source, import_settings=_object(args.import_settings, option="--import-settings"))); return 0
        if args.command == "resource-validate":
            errors = validate_resource_file(args.path)
            if errors:
                for error in errors: print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print(f"OK: {args.path}"); return 0
        if args.command == "resource-show": _json(load_resource_manifest(args.path).to_dict()); return 0
        if args.command == "asset-validate":
            report = validate_asset_against_manifest(args.manifest, args.asset); _json(report.to_dict()); return 0 if report.passed else 1
        if args.command == "export":
            report = export_project_assets(workspace, args.project, target_engine=args.target, output_dir=args.output, clean=args.clean); _json(report.to_dict()); return 0 if report.passed else 1
        if args.command == "qa-pixels":
            report = compare_protected_pixels(args.original, args.edited, args.mask, args.tolerance); _json(report.to_dict()); return 0 if report.passed else 1
        if args.command == "compose-edit":
            report = compose_masked_edit(args.original, args.generated, args.mask, args.output, feather_radius=args.feather, threshold=args.threshold); payload: dict[str, object] = {"composition": report.to_dict()}
            if args.verify:
                qa = compare_protected_pixels(args.original, args.output, args.mask, tolerance=0); payload["protected_pixel_qa"] = qa.to_dict(); _json(payload); return 0 if qa.passed else 1
            _json(payload); return 0
    except ThemeResolutionRequired as exc:
        _json(exc.resolution)
        return 3
    except (FileExistsError, FileNotFoundError, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
