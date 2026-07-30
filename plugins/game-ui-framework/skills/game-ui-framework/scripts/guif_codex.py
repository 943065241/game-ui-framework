#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4


def _inject_framework_source() -> None:
    for parent in Path(__file__).resolve().parents:
        if (
            (parent / "guif" / "__init__.py").is_file()
            and (parent / "pyproject.toml").is_file()
        ):
            sys.path.insert(0, str(parent))
            return


_inject_framework_source()

from guif.beta_readiness import bootstrap_workspace  # noqa: E402
from guif.conversation_workflow import ConversationWorkflowError  # noqa: E402
from guif.improvement_cases import (  # noqa: E402
    CHANGE_TYPES,
    ImprovementCaseError,
    TOOL_ADOPTION_SCOPES,
)
from guif.improvement_workflow import ConversationWorkflowService  # noqa: E402
from guif.runtime import Runtime  # noqa: E402

SCHEMA_VERSION = 1
DEFAULT_CONVERSATION = "codex-main"
HOST_KINDS = {"image-generation", "image-editing", "visual-inspection"}
SOURCE_KINDS = (
    "conversation-temporary-image",
    "user-upload",
    "external-file",
    "guif-artifact",
)
SOURCE_USAGES = ("editable-source", "theme-reference", "master-reference")


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def _secure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass
    return path


def _secure_json(path: Path, value: dict[str, Any]) -> None:
    _secure_dir(path.parent)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(_dump(value) + "\n", encoding="utf-8")
    try:
        os.chmod(temporary, 0o600)
    except OSError:
        pass
    temporary.replace(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _read_object(path: Path, label: str) -> dict[str, Any]:
    value = json.loads(
        path.expanduser().resolve().read_text(encoding="utf-8")
    )
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{label} must be a non-empty JSON object")
    return value


def _read_text(path: Path, label: str) -> str:
    value = path.expanduser().resolve().read_text(encoding="utf-8")
    if not value.strip():
        raise ValueError(f"{label} must not be empty")
    return value


def _optional_text(path: Path | None, label: str) -> str | None:
    return _read_text(path, label) if path is not None else None


def _plugin_data() -> Path:
    configured = (
        os.environ.get("GUIF_CODEX_PLUGIN_DATA")
        or os.environ.get("PLUGIN_DATA")
    )
    root = (
        Path(configured).expanduser().resolve()
        if configured and configured.strip()
        else (Path.home() / ".guif" / "codex-plugin").resolve()
    )
    _secure_dir(root)
    os.environ.setdefault(
        "GUIF_DATA_HOME",
        str(root / "framework-data"),
    )
    return root


def _key(workspace: Path) -> str:
    return hashlib.sha256(
        str(workspace.resolve()).encode("utf-8")
    ).hexdigest()[:20]


def _state_root(workspace: Path) -> Path:
    return _secure_dir(_plugin_data() / "workspaces" / _key(workspace))


def _context_path(workspace: Path) -> Path:
    return _state_root(workspace) / "context.json"


def _claims_root(workspace: Path) -> Path:
    return _secure_dir(_state_root(workspace) / "host-claims")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _identity(value: str, fallback: str) -> str:
    cleaned = re.sub(
        r"[^A-Za-z0-9._-]+",
        "-",
        value.strip(),
    ).strip(".-")
    return cleaned or fallback


def _load_context(workspace: Path) -> dict[str, Any] | None:
    path = _context_path(workspace)
    return _read_json(path) if path.is_file() else None


def _ensure_context(
    workspace: Path,
    project: str | None,
    conversation: str | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    workspace = workspace.resolve()
    existing = _load_context(workspace) or {}
    resolved_project = _identity(
        project or str(existing.get("project") or workspace.name),
        "GameUIProject",
    )
    resolved_conversation = _identity(
        conversation
        or str(existing.get("conversation") or DEFAULT_CONVERSATION),
        DEFAULT_CONVERSATION,
    )
    token = str(existing.get("bearer_token") or "") or None
    bootstrap = bootstrap_workspace(
        workspace,
        resolved_project,
        resolved_conversation,
        bearer_token=token,
        actor_id="codex-plugin-host",
    )
    issued = bootstrap.get("bearer_token")
    if isinstance(issued, str) and issued.strip():
        token = issued
    if not isinstance(token, str) or not token.strip():
        raise RuntimeError(
            "GUIF did not provide a usable private Host credential"
        )
    context = {
        "schema_version": SCHEMA_VERSION,
        "workspace": str(workspace),
        "project": resolved_project,
        "conversation": resolved_conversation,
        "bearer_token": token,
    }
    _secure_json(_context_path(workspace), context)
    return context, bootstrap


def _service(
    workspace: Path,
    context: dict[str, Any],
) -> ConversationWorkflowService:
    return ConversationWorkflowService(
        workspace.resolve(),
        runtime=Runtime(workspace.resolve()),
        bearer_token=str(context["bearer_token"]),
    )


def _safe_start(
    result: dict[str, Any],
    service: ConversationWorkflowService,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": result.get("status"),
        "project_created": bool(result.get("project_created")),
        "project": result.get("project"),
        "conversation_id": result.get("conversation_id"),
        "conversation": service.status(
            str(result.get("project")),
            str(result.get("conversation_id")),
        ),
        "next_action": result.get("next_action"),
        "compatibility": result.get("compatibility"),
        "privacy": {
            "credential": "stored-in-plugin-private-data",
            "framework_data": "outside-project-git",
            "source_images": (
                "private-source-library-outside-project-git"
            ),
            "improvement_cases": (
                "private-candidate-change-records-outside-project-git"
            ),
        },
    }


def _context_summary(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "workspace": context["workspace"],
        "project": context["project"],
        "conversation": context["conversation"],
        "credential": "configured-private",
    }


def _active_task(
    context: dict[str, Any],
    service: ConversationWorkflowService,
) -> tuple[dict[str, Any], Any]:
    session = service._session(
        str(context["project"]),
        str(context["conversation"]),
    )
    task = service._load_active_task(session)
    if task is None:
        raise ConversationWorkflowError(
            "Conversation has no active production task"
        )
    return session, task


def _filename(value: str, fallback: str) -> str:
    cleaned = re.sub(
        r"[^A-Za-z0-9._-]+",
        "-",
        Path(value).name,
    ).strip(".-")
    return cleaned or fallback


def _dimensions(path: Path) -> tuple[int | None, int | None]:
    try:
        from PIL import Image

        with Image.open(path) as image:
            return int(image.width), int(image.height)
    except (ImportError, OSError, ValueError):
        return None, None


def _source_metadata(
    path: Path,
    args: argparse.Namespace,
) -> tuple[str | None, int | None, int | None]:
    resolved = path.expanduser().resolve(strict=True)
    width, height = _dimensions(resolved)
    return (
        args.mime_type or mimetypes.guess_type(resolved.name)[0],
        args.width if args.width is not None else width,
        args.height if args.height is not None else height,
    )


def _plugin_version() -> str:
    for parent in Path(__file__).resolve().parents:
        manifest = parent / ".codex-plugin" / "plugin.json"
        if not manifest.is_file():
            continue
        value = _read_json(manifest).get("version")
        if isinstance(value, str) and value.strip():
            return value.strip()
    raise RuntimeError("Unable to resolve installed GUIF plugin version")


def _prepare_host(
    workspace: Path,
    context: dict[str, Any],
    service: ConversationWorkflowService,
) -> dict[str, Any]:
    _, task = _active_task(context, service)
    runtime = service.runtime
    project = str(context["project"])
    candidates = runtime.list_host_work(
        project,
        statuses=("available",),
        limit=100,
    )
    work = next(
        (
            item
            for item in candidates
            if item.get("task_id") == task.task_id
            and item.get("kind") in HOST_KINDS
        ),
        None,
    )
    if not isinstance(work, dict):
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "blocked",
            "reason": "no-supported-host-work",
            "conversation": service.status(
                project,
                str(context["conversation"]),
            ),
        }

    etag = runtime.get_task_etag(project, task.task_id)
    lease = runtime.acquire_task_lease(
        project,
        task.task_id,
        bearer_token=str(context["bearer_token"]),
        expected_task_etag=etag,
        ttl_seconds=900,
        purpose=f"codex-plugin-host-work:{work['work_id']}",
    )
    try:
        claimed = runtime.claim_host_work(
            project,
            str(work["work_id"]),
            bearer_token=str(context["bearer_token"]),
            ttl_seconds=900,
        )
    except Exception:
        runtime.release_task_lease(
            project,
            task.task_id,
            bearer_token=str(context["bearer_token"]),
            lease_token=str(lease["lease_token"]),
            reason="Codex plugin Host claim failed",
        )
        raise

    claimed_work = claimed["work"]
    claim_token = str(claimed["claim_token"])
    session_id = uuid4().hex
    claim_root = _secure_dir(
        _claims_root(workspace) / session_id
    )
    attachments: list[dict[str, Any]] = []
    try:
        for index, descriptor in enumerate(
            claimed_work.get("attachments", []),
            start=1,
        ):
            if (
                not isinstance(descriptor, dict)
                or not descriptor.get("attachment_id")
            ):
                continue
            verified, content = runtime.get_host_work_attachment(
                project,
                str(claimed_work["work_id"]),
                str(descriptor["attachment_id"]),
                bearer_token=str(context["bearer_token"]),
                claim_token=claim_token,
            )
            name = _filename(
                str(
                    verified.get("filename")
                    or f"attachment-{index}.bin"
                ),
                f"attachment-{index}.bin",
            )
            path = claim_root / name
            path.write_bytes(content)
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
            attachments.append(
                {
                    "attachment_id": verified.get(
                        "attachment_id"
                    ),
                    "filename": name,
                    "mime_type": verified.get("mime_type"),
                    "sha256": verified.get("sha256"),
                    "path": str(path),
                }
            )
        _secure_json(
            claim_root / "claim.json",
            {
                "schema_version": SCHEMA_VERSION,
                "workspace": str(workspace.resolve()),
                "project": project,
                "conversation": context["conversation"],
                "task_id": task.task_id,
                "work_id": claimed_work["work_id"],
                "kind": claimed_work.get("kind"),
                "etag": etag,
                "lease_token": lease["lease_token"],
                "claim_token": claim_token,
            },
        )
    except Exception:
        current = runtime.get_task_lease(
            project,
            task.task_id,
        )
        if current.get("status") == "active":
            runtime.release_task_lease(
                project,
                task.task_id,
                bearer_token=str(context["bearer_token"]),
                lease_token=str(lease["lease_token"]),
                reason=(
                    "Codex plugin Host attachment "
                    "preparation failed"
                ),
            )
        shutil.rmtree(claim_root, ignore_errors=True)
        raise

    public_work = {
        key: value
        for key, value in claimed_work.items()
        if key
        not in {
            "claim_token",
            "lease_token",
            "bearer_token",
            "attachments",
        }
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "prepared",
        "host_session": session_id,
        "kind": claimed_work.get("kind"),
        "work": public_work,
        "attachments": attachments,
        "completion_contract": (
            "Submit a real image file with host-complete-image."
            if claimed_work.get("kind")
            in {"image-generation", "image-editing"}
            else (
                "Submit a real semantic inspection result "
                "with host-complete-visual."
            )
        ),
    }


def _claim(
    workspace: Path,
    session_id: str,
) -> tuple[Path, dict[str, Any]]:
    normalized = _identity(session_id, "")
    if not normalized or normalized != session_id:
        raise ValueError("Invalid Host session")
    root = _claims_root(workspace) / session_id
    path = root / "claim.json"
    if not path.is_file():
        raise FileNotFoundError(
            f"Unknown or expired Host session: {session_id}"
        )
    return root, _read_json(path)


def _complete_image(
    workspace: Path,
    context: dict[str, Any],
    service: ConversationWorkflowService,
    session_id: str,
    image_path: Path,
    model_id: str,
) -> dict[str, Any]:
    root, claim = _claim(workspace, session_id)
    if claim.get("kind") not in {
        "image-generation",
        "image-editing",
    }:
        raise ValueError(
            "Host session does not accept an image result"
        )
    path = image_path.expanduser().resolve()
    content = path.read_bytes()
    if not content:
        raise ValueError("Image result must not be empty")
    width, height = _dimensions(path)
    receipt = service.runtime.complete_host_image_work(
        str(claim["project"]),
        str(claim["work_id"]),
        bearer_token=str(context["bearer_token"]),
        claim_token=str(claim["claim_token"]),
        lease_token=str(claim["lease_token"]),
        expected_task_etag=str(claim["etag"]),
        content=content,
        filename=_filename(
            path.name,
            "generated-image.png",
        ),
        mime_type=(
            mimetypes.guess_type(path.name)[0]
            or "image/png"
        ),
        content_sha256=hashlib.sha256(content).hexdigest(),
        width=width,
        height=height,
        model_id=model_id,
        metadata={
            "host": "codex-plugin",
            "result_kind": "real-image",
        },
        request_id=str(claim["work_id"]),
    )
    shutil.rmtree(root, ignore_errors=True)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "completed",
        "kind": claim["kind"],
        "artifact_created": bool(receipt.get("artifact_id")),
        "conversation": service.status(
            str(claim["project"]),
            str(claim["conversation"]),
        ),
    }


def _complete_visual(
    workspace: Path,
    context: dict[str, Any],
    service: ConversationWorkflowService,
    session_id: str,
    result_path: Path,
    inspector_id: str,
) -> dict[str, Any]:
    root, claim = _claim(workspace, session_id)
    if claim.get("kind") != "visual-inspection":
        raise ValueError(
            "Host session does not accept a visual inspection result"
        )
    result = _read_object(
        result_path,
        "Visual inspection result",
    )
    findings = result.get("findings", [])
    if not isinstance(findings, list) or any(
        not isinstance(item, dict) for item in findings
    ):
        raise ValueError(
            "Visual inspection findings must be an array of objects"
        )
    status = str(result.get("status") or "").strip()
    if not status:
        raise ValueError(
            "Visual inspection status is required"
        )
    receipt = service.runtime.complete_host_visual_work(
        str(claim["project"]),
        str(claim["work_id"]),
        bearer_token=str(context["bearer_token"]),
        claim_token=str(claim["claim_token"]),
        lease_token=str(claim["lease_token"]),
        expected_task_etag=str(claim["etag"]),
        status=status,
        findings=tuple(findings),
        summary=str(result.get("summary") or ""),
        inspector_id=inspector_id,
        metadata={
            "host": "codex-plugin",
            "result_kind": "real-visual-inspection",
        },
    )
    shutil.rmtree(root, ignore_errors=True)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "completed",
        "kind": "visual-inspection",
        "revision_created": bool(
            receipt.get("revision_id")
        ),
        "conversation": service.status(
            str(claim["project"]),
            str(claim["conversation"]),
        ),
    }


def _abort(
    workspace: Path,
    context: dict[str, Any],
    service: ConversationWorkflowService,
    session_id: str,
) -> dict[str, Any]:
    root, claim = _claim(workspace, session_id)
    current = service.runtime.get_task_lease(
        str(claim["project"]),
        str(claim["task_id"]),
    )
    if current.get("status") == "active":
        service.runtime.release_task_lease(
            str(claim["project"]),
            str(claim["task_id"]),
            bearer_token=str(context["bearer_token"]),
            lease_token=str(claim["lease_token"]),
            reason="Codex plugin Host session aborted",
        )
    shutil.rmtree(root, ignore_errors=True)
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "aborted",
    }


def _add_source_arguments(
    parser: argparse.ArgumentParser,
    *,
    required: bool,
) -> None:
    parser.add_argument(
        "--source-file",
        type=Path,
        required=required,
    )
    parser.add_argument(
        "--source-kind",
        choices=SOURCE_KINDS,
        default="user-upload",
    )
    parser.add_argument(
        "--source-usage",
        choices=SOURCE_USAGES,
        default="editable-source",
    )
    parser.add_argument("--mime-type")
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)


def _add_comment_argument(
    parser: argparse.ArgumentParser,
) -> None:
    parser.add_argument("--comment-file", type=Path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="guif-codex",
        description=(
            "Private natural-language bridge used internally "
            "by the GUIF Codex plugin"
        ),
    )
    parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
    )
    parser.add_argument("--project")
    parser.add_argument("--conversation")
    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )
    sub.add_parser("start")
    sub.add_parser("status")
    sub.add_parser("context")

    create = sub.add_parser("theme-create")
    create.add_argument("--name", required=True)
    create.add_argument(
        "--content-file",
        type=Path,
        required=True,
    )
    _add_source_arguments(create, required=False)
    create.set_defaults(source_usage="master-reference")

    select = sub.add_parser("theme-select")
    select.add_argument("--theme-id", required=True)
    select.add_argument("--version", type=int)

    derive = sub.add_parser("theme-derive")
    derive.add_argument("--theme-id", required=True)
    derive.add_argument(
        "--updates-file",
        type=Path,
        required=True,
    )
    derive.add_argument("--from-version", type=int)
    derive.add_argument("--name")
    _add_source_arguments(derive, required=False)
    derive.set_defaults(source_usage="theme-reference")
    sub.add_parser("theme-unbound")

    source = sub.add_parser("source-import")
    _add_source_arguments(source, required=True)
    source.add_argument("--no-continue", action="store_true")
    sub.add_parser("source-external-edit")

    submit = sub.add_parser("submit")
    submit.add_argument(
        "--request-file",
        type=Path,
        required=True,
    )
    submit.add_argument("--request-key")
    submit.add_argument(
        "--pipeline",
        default="ui-production",
    )
    for name in (
        "approve",
        "request-changes",
        "reject",
    ):
        decision = sub.add_parser(name)
        _add_comment_argument(decision)
    sub.add_parser("continue")
    sub.add_parser("recover")
    sub.add_parser("retry")
    export = sub.add_parser("export")
    export.add_argument("--target-engine")

    improvement_open = sub.add_parser(
        "improvement-open"
    )
    improvement_open.add_argument(
        "--change-type",
        choices=sorted(CHANGE_TYPES),
        required=True,
    )
    improvement_open.add_argument(
        "--observed-file",
        type=Path,
        required=True,
    )
    improvement_open.add_argument(
        "--expected-file",
        type=Path,
        required=True,
    )
    improvement_open.add_argument(
        "--diagnosis-file",
        type=Path,
    )
    improvement_open.add_argument(
        "--proposal-file",
        type=Path,
    )
    improvement_open.add_argument("--tool-id")
    improvement_open.add_argument("--capability")
    improvement_open.add_argument(
        "--adoption-scope",
        choices=sorted(TOOL_ADOPTION_SCOPES),
        default="project",
    )
    sub.add_parser("improvement-status")

    improvement_propose = sub.add_parser(
        "improvement-propose"
    )
    improvement_propose.add_argument(
        "--proposal-file",
        type=Path,
        required=True,
    )

    for name in (
        "improvement-trial-approve",
        "improvement-trial-request-changes",
        "improvement-trial-reject",
        "improvement-adopt",
        "improvement-adoption-request-changes",
        "improvement-adoption-reject",
    ):
        decision = sub.add_parser(name)
        _add_comment_argument(decision)

    sub.add_parser("improvement-bundle")

    candidate_link = sub.add_parser(
        "improvement-candidate-link"
    )
    candidate_link.add_argument(
        "--candidate-file",
        type=Path,
        required=True,
    )
    sub.add_parser("improvement-candidate-run")

    result = sub.add_parser("improvement-result")
    result.add_argument(
        "--group",
        choices=("stable", "candidate"),
        required=True,
    )
    result.add_argument(
        "--summary-file",
        type=Path,
        required=True,
    )
    result.add_argument("--artifact-file", type=Path)
    result.add_argument("--metadata-file", type=Path)

    published = sub.add_parser(
        "improvement-published"
    )
    published.add_argument(
        "--delivery-file",
        type=Path,
        required=True,
    )

    refresh = sub.add_parser(
        "improvement-refresh-confirm"
    )
    refresh.add_argument("--current-version")

    for name in (
        "improvement-regression-pass",
        "improvement-regression-fail",
    ):
        regression = sub.add_parser(name)
        regression.add_argument(
            "--summary-file",
            type=Path,
            required=True,
        )
    sub.add_parser("improvement-resume")

    sub.add_parser("host-prepare")
    image = sub.add_parser("host-complete-image")
    image.add_argument("--session", required=True)
    image.add_argument(
        "--image",
        type=Path,
        required=True,
    )
    image.add_argument(
        "--model-id",
        default="chatgpt-image",
    )
    visual = sub.add_parser("host-complete-visual")
    visual.add_argument("--session", required=True)
    visual.add_argument(
        "--result-file",
        type=Path,
        required=True,
    )
    visual.add_argument(
        "--inspector-id",
        default="chatgpt-vision",
    )
    abort = sub.add_parser("host-abort")
    abort.add_argument("--session", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workspace = args.workspace.expanduser().resolve()
    try:
        context, bootstrap = _ensure_context(
            workspace,
            args.project,
            args.conversation,
        )
        service = _service(workspace, context)
        project = str(context["project"])
        conversation = str(context["conversation"])

        if args.command == "start":
            result = _safe_start(bootstrap, service)
        elif args.command == "context":
            result = _context_summary(context)
        elif args.command == "status":
            result = service.status(
                project,
                conversation,
            )
        elif args.command == "theme-create":
            source_options: dict[str, Any] = {}
            if args.source_file is not None:
                mime_type, width, height = _source_metadata(
                    args.source_file,
                    args,
                )
                source_options = {
                    "source_path": args.source_file,
                    "source_kind": args.source_kind,
                    "source_usage": args.source_usage,
                    "source_mime_type": mime_type,
                    "source_width": width,
                    "source_height": height,
                }
            result = service.create_theme(
                project,
                conversation,
                args.name,
                _read_object(
                    args.content_file,
                    "Theme content",
                ),
                actor="codex-plugin-user",
                **source_options,
            )
        elif args.command == "theme-select":
            result = service.select_theme(
                project,
                conversation,
                args.theme_id,
                version=args.version,
                actor="codex-plugin-user",
            )
        elif args.command == "theme-derive":
            source_options = {}
            if args.source_file is not None:
                mime_type, width, height = _source_metadata(
                    args.source_file,
                    args,
                )
                source_options = {
                    "source_path": args.source_file,
                    "source_kind": args.source_kind,
                    "source_usage": args.source_usage,
                    "source_mime_type": mime_type,
                    "source_width": width,
                    "source_height": height,
                }
            result = service.derive_theme(
                project,
                conversation,
                args.theme_id,
                _read_object(
                    args.updates_file,
                    "Theme updates",
                ),
                from_version=args.from_version,
                name=args.name,
                actor="codex-plugin-user",
                **source_options,
            )
        elif args.command == "theme-unbound":
            result = service.continue_unbound(
                project,
                conversation,
            )
        elif args.command == "source-import":
            mime_type, width, height = _source_metadata(
                args.source_file,
                args,
            )
            result = service.import_source(
                project,
                conversation,
                args.source_file,
                source_kind=args.source_kind,
                usage=args.source_usage,
                mime_type=mime_type,
                width=width,
                height=height,
                actor="codex-plugin-user",
                continue_after_import=not args.no_continue,
            )
        elif args.command == "source-external-edit":
            result = service.select_external_edit(
                project,
                conversation,
            )
        elif args.command == "submit":
            requirement = _read_text(
                args.request_file,
                "Design request",
            )
            request_key = args.request_key or (
                "codex-"
                + hashlib.sha256(
                    requirement.encode("utf-8")
                ).hexdigest()[:20]
            )
            result = service.submit(
                project,
                conversation,
                requirement,
                pipeline=args.pipeline,
                request_key=request_key,
            )
        elif args.command in {
            "approve",
            "request-changes",
            "reject",
        }:
            comment = _optional_text(
                args.comment_file,
                "Decision comment",
            )
            result = getattr(
                service,
                args.command.replace("-", "_"),
            )(
                project,
                conversation,
                comment=comment,
            )
        elif args.command == "continue":
            result = service.continue_work(
                project,
                conversation,
            )
        elif args.command == "recover":
            result = service.recover(
                project,
                conversation,
            )
        elif args.command == "retry":
            result = service.retry(
                project,
                conversation,
            )
        elif args.command == "export":
            result = service.export(
                project,
                conversation,
                target_engine=args.target_engine,
            )
        elif args.command == "improvement-open":
            proposal = (
                _read_object(
                    args.proposal_file,
                    "Improvement proposal",
                )
                if args.proposal_file is not None
                else None
            )
            result = service.open_improvement(
                project,
                conversation,
                change_type=args.change_type,
                observed_behavior=_read_text(
                    args.observed_file,
                    "Observed behavior",
                ),
                expected_behavior=_read_text(
                    args.expected_file,
                    "Expected behavior",
                ),
                diagnosis=_optional_text(
                    args.diagnosis_file,
                    "Improvement diagnosis",
                ),
                proposal=proposal,
                affected_tool_id=args.tool_id,
                capability=args.capability,
                adoption_scope=args.adoption_scope,
                actor="codex-plugin-user",
            )
        elif args.command == "improvement-status":
            result = service.improvement_status(
                project,
                conversation,
            )
        elif args.command == "improvement-propose":
            result = service.propose_improvement(
                project,
                conversation,
                _read_object(
                    args.proposal_file,
                    "Improvement proposal",
                ),
                actor="codex-plugin-user",
            )
        elif args.command in {
            "improvement-trial-approve",
            "improvement-trial-request-changes",
            "improvement-trial-reject",
        }:
            decisions = {
                "improvement-trial-approve": "approved",
                "improvement-trial-request-changes": (
                    "changes-requested"
                ),
                "improvement-trial-reject": "rejected",
            }
            result = service.decide_improvement_trial(
                project,
                conversation,
                decisions[args.command],
                comment=_optional_text(
                    args.comment_file,
                    "Trial decision comment",
                ),
                actor="codex-plugin-user",
            )
        elif args.command == "improvement-bundle":
            result = service.improvement_development_bundle(
                project,
                conversation,
            )
        elif args.command == "improvement-candidate-link":
            result = service.link_improvement_candidate(
                project,
                conversation,
                _read_object(
                    args.candidate_file,
                    "Candidate metadata",
                ),
                actor="codex-plugin-user",
            )
        elif args.command == "improvement-candidate-run":
            result = service.start_improvement_candidate(
                project,
                conversation,
                actor="codex-plugin-user",
            )
        elif args.command == "improvement-result":
            metadata = (
                _read_object(
                    args.metadata_file,
                    "Improvement result metadata",
                )
                if args.metadata_file is not None
                else None
            )
            result = service.record_improvement_result(
                project,
                conversation,
                group=args.group,
                summary=_read_text(
                    args.summary_file,
                    "Improvement result summary",
                ),
                file_path=args.artifact_file,
                metadata=metadata,
                actor="codex-plugin-user",
            )
        elif args.command in {
            "improvement-adopt",
            "improvement-adoption-request-changes",
            "improvement-adoption-reject",
        }:
            decisions = {
                "improvement-adopt": "approved",
                "improvement-adoption-request-changes": (
                    "changes-requested"
                ),
                "improvement-adoption-reject": "rejected",
            }
            result = service.decide_improvement_adoption(
                project,
                conversation,
                decisions[args.command],
                comment=_optional_text(
                    args.comment_file,
                    "Adoption decision comment",
                ),
                actor="codex-plugin-user",
            )
        elif args.command == "improvement-published":
            result = service.mark_improvement_published(
                project,
                conversation,
                _read_object(
                    args.delivery_file,
                    "Improvement delivery",
                ),
                actor="codex-plugin-user",
            )
        elif args.command == "improvement-refresh-confirm":
            result = service.confirm_improvement_refresh(
                project,
                conversation,
                current_plugin_version=(
                    args.current_version
                    or _plugin_version()
                ),
                actor="codex-plugin-user",
            )
        elif args.command in {
            "improvement-regression-pass",
            "improvement-regression-fail",
        }:
            result = service.record_improvement_regression(
                project,
                conversation,
                passed=(
                    args.command
                    == "improvement-regression-pass"
                ),
                summary=_read_text(
                    args.summary_file,
                    "Regression summary",
                ),
                actor="codex-plugin-user",
            )
        elif args.command == "improvement-resume":
            result = service.resume_after_improvement(
                project,
                conversation,
                actor="codex-plugin-user",
            )
        elif args.command == "host-prepare":
            result = _prepare_host(
                workspace,
                context,
                service,
            )
        elif args.command == "host-complete-image":
            result = _complete_image(
                workspace,
                context,
                service,
                args.session,
                args.image,
                args.model_id,
            )
        elif args.command == "host-complete-visual":
            result = _complete_visual(
                workspace,
                context,
                service,
                args.session,
                args.result_file,
                args.inspector_id,
            )
        elif args.command == "host-abort":
            result = _abort(
                workspace,
                context,
                service,
                args.session,
            )
        else:
            raise ValueError(
                f"Unsupported command: {args.command}"
            )
        print(_dump(result))
        return 0
    except (
        ConversationWorkflowError,
        ImprovementCaseError,
        FileNotFoundError,
        RuntimeError,
        ValueError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        print(
            _dump(
                {
                    "schema_version": SCHEMA_VERSION,
                    "status": "error",
                    "error": str(exc),
                }
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
