from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4

from guif.private_data import PrivateDataLayout
from guif.tools.config import bind_workspace_tool

IMPROVEMENT_CASE_SCHEMA_VERSION = 1
IMPROVEMENT_RESULT_SCHEMA_VERSION = 1

CHANGE_TYPES = {
    "skill-change",
    "framework-change",
    "tool-change",
    "tool-integration-change",
    "theme-policy-change",
    "workflow-change",
    "provider-routing-change",
    "multi-layer-change",
}

CASE_STATUSES = {
    "proposal-required",
    "trial-approval-required",
    "candidate-building",
    "candidate-ready",
    "candidate-running",
    "result-review-required",
    "publishing-required",
    "plugin-refresh-required",
    "regression-validation-required",
    "resolved",
    "closed-stable-retained",
}

TRIAL_DECISIONS = {"approved", "changes-requested", "rejected"}
ADOPTION_DECISIONS = {"approved", "changes-requested", "rejected"}
RESULT_GROUPS = {"stable", "candidate"}
TOOL_ADOPTION_SCOPES = {"task", "project", "workspace"}


class ImprovementCaseError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def _safe_identity(value: str, label: str) -> str:
    normalized = value.strip()
    if not normalized or Path(normalized).name != normalized:
        raise ValueError(f"Invalid {label}: {value}")
    return normalized


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    try:
        os.chmod(temporary, 0o600)
    except OSError:
        pass
    temporary.replace(path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ImprovementCaseError(f"Expected Improvement Case object: {path}")
    return value


def _normalize_strings(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = " ".join(str(value).split())
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _version_parts(value: str) -> tuple[int, ...]:
    normalized = value.strip().lower().replace("-", ".")
    values: list[int] = []
    for token in normalized.split("."):
        digits = "".join(character for character in token if character.isdigit())
        if digits:
            values.append(int(digits))
    return tuple(values)


def version_satisfies(current: str, minimum: str) -> bool:
    current_parts = _version_parts(current)
    minimum_parts = _version_parts(minimum)
    length = max(len(current_parts), len(minimum_parts))
    return current_parts + (0,) * (length - len(current_parts)) >= minimum_parts + (0,) * (
        length - len(minimum_parts)
    )


class ImprovementCaseStore:
    """Private candidate-change records and evidence outside Project Git."""

    def __init__(self, workspace: Path, *, data_root: Path | None = None) -> None:
        self.workspace = workspace.resolve()
        self.layout = PrivateDataLayout(self.workspace, data_root)

    def _project_dir(self, project: str) -> Path:
        return self.layout.improvement_cases / _safe_identity(project, "project")

    def _path(self, project: str, case_id: str) -> Path:
        normalized = _safe_identity(case_id, "case_id")
        return self._project_dir(project) / f"{normalized}.json"

    def _evidence_dir(self, project: str, case_id: str) -> Path:
        normalized = _safe_identity(case_id, "case_id")
        return self._project_dir(project) / normalized / "evidence"

    def get(self, project: str, case_id: str) -> dict[str, Any]:
        path = self._path(project, case_id)
        if not path.is_file():
            raise ValueError(f"Unknown Improvement Case: {case_id}")
        record = _read_json(path)
        self.validate(record)
        return record

    def list(self, project: str) -> tuple[dict[str, Any], ...]:
        root = self._project_dir(project)
        if not root.is_dir():
            return ()
        records: list[dict[str, Any]] = []
        for path in root.glob("improvement-*.json"):
            try:
                record = _read_json(path)
                self.validate(record)
            except (OSError, ValueError, json.JSONDecodeError, ImprovementCaseError):
                continue
            records.append(record)
        records.sort(key=lambda item: str(item.get("updated_at") or ""), reverse=True)
        return tuple(records)

    def save(self, record: dict[str, Any]) -> dict[str, Any]:
        self.validate(record)
        record["updated_at"] = _now()
        _write_json(
            self._path(str(record["project"]), str(record["case_id"])),
            record,
        )
        return record

    def create(
        self,
        *,
        project: str,
        conversation_id: str,
        change_type: str,
        observed_behavior: str,
        expected_behavior: str,
        diagnosis: str | None,
        proposal: dict[str, Any] | None,
        source_task: dict[str, Any] | None,
        tool_trial: dict[str, Any] | None,
        actor: str,
    ) -> dict[str, Any]:
        normalized_project = _safe_identity(project, "project")
        normalized_conversation = _safe_identity(conversation_id, "conversation_id")
        normalized_change_type = change_type.strip()
        if normalized_change_type not in CHANGE_TYPES:
            raise ValueError(
                "change_type must be one of: " + ", ".join(sorted(CHANGE_TYPES))
            )
        observed = observed_behavior.strip()
        expected = expected_behavior.strip()
        normalized_actor = actor.strip()
        if not observed or not expected or not normalized_actor:
            raise ValueError(
                "observed_behavior, expected_behavior, and actor must not be empty"
            )
        timestamp = _now()
        case_id = "improvement-" + uuid4().hex[:16]
        normalized_proposal = self._normalize_proposal(proposal)
        status = (
            "trial-approval-required"
            if normalized_proposal is not None
            else "proposal-required"
        )
        record: dict[str, Any] = {
            "schema_version": IMPROVEMENT_CASE_SCHEMA_VERSION,
            "case_id": case_id,
            "project": normalized_project,
            "conversation_id": normalized_conversation,
            "change_type": normalized_change_type,
            "status": status,
            "issue": {
                "observed_behavior": observed,
                "expected_behavior": expected,
                "diagnosis": diagnosis.strip()
                if isinstance(diagnosis, str) and diagnosis.strip()
                else None,
            },
            "source_task": dict(source_task) if isinstance(source_task, dict) else None,
            "proposal": normalized_proposal,
            "trial_approval": None,
            "candidate": {
                "kind": None,
                "branch": None,
                "commit": None,
                "version": None,
                "notes": None,
                "task_id": None,
                "development_bundle": None,
                "tool_trial": dict(tool_trial)
                if isinstance(tool_trial, dict)
                else None,
            },
            "results": [],
            "adoption": None,
            "delivery": {
                "repository": None,
                "branch": None,
                "pull_request": None,
                "merge_commit": None,
                "minimum_plugin_version": None,
                "published_at": None,
            },
            "refresh": {
                "required": False,
                "confirmed": False,
                "current_plugin_version": None,
                "confirmed_at": None,
            },
            "regression": {
                "status": "pending",
                "summary": None,
                "recorded_at": None,
            },
            "resume": {
                "policy": "restore-production-task",
                "source_task_id": (
                    source_task.get("task_id")
                    if isinstance(source_task, dict)
                    else None
                ),
                "status": "paused" if source_task else "not-applicable",
            },
            "privacy": {
                "storage": "private-outside-project-git",
                "public_fixture_required": True,
                "real_user_assets_in_public_repo": False,
            },
            "history": [
                {
                    "event": "improvement-opened",
                    "actor": normalized_actor,
                    "recorded_at": timestamp,
                }
            ],
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        return self.save(record)

    @staticmethod
    def _normalize_proposal(
        proposal: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if proposal is None:
            return None
        if not isinstance(proposal, dict):
            raise ValueError("proposal must be an object")
        summary = str(proposal.get("summary") or "").strip()
        changes = _normalize_strings(proposal.get("changes", []))
        affected_layers = _normalize_strings(proposal.get("affected_layers", []))
        validation_plan = _normalize_strings(proposal.get("validation_plan", []))
        safety_constraints = _normalize_strings(
            proposal.get("safety_constraints", [])
        )
        public_fixture = str(
            proposal.get("public_fixture")
            or "Use a wholly fictional fixture that reproduces the same state transition."
        ).strip()
        if not summary or not changes or not validation_plan:
            raise ValueError(
                "proposal requires summary, changes, and validation_plan"
            )
        return {
            "summary": summary,
            "changes": changes,
            "affected_layers": affected_layers,
            "validation_plan": validation_plan,
            "safety_constraints": safety_constraints,
            "public_fixture": public_fixture,
        }

    def stage_result(
        self,
        project: str,
        case_id: str,
        *,
        group: str,
        summary: str,
        file_path: Path | None = None,
        metadata: dict[str, Any] | None = None,
        actor: str,
    ) -> dict[str, Any]:
        normalized_group = group.strip()
        if normalized_group not in RESULT_GROUPS:
            raise ValueError("result group must be stable or candidate")
        normalized_summary = summary.strip()
        normalized_actor = actor.strip()
        if not normalized_summary or not normalized_actor:
            raise ValueError("result summary and actor must not be empty")
        evidence_id = "evidence-" + uuid4().hex[:16]
        file_data: dict[str, Any] | None = None
        if file_path is not None:
            source = file_path.expanduser().resolve(strict=True)
            if not source.is_file():
                raise ValueError("Improvement result file must be a regular file")
            content = source.read_bytes()
            if not content:
                raise ValueError("Improvement result file must not be empty")
            name = Path(source.name).name
            target_dir = self._evidence_dir(project, case_id)
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / f"{evidence_id}-{name}"
            target.write_bytes(content)
            try:
                os.chmod(target, 0o600)
            except OSError:
                pass
            file_data = {
                "path": str(target),
                "filename": name,
                "mime_type": mimetypes.guess_type(name)[0]
                or "application/octet-stream",
                "size_bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
                "storage_scope": "private-improvement-evidence",
            }
        return {
            "schema_version": IMPROVEMENT_RESULT_SCHEMA_VERSION,
            "evidence_id": evidence_id,
            "group": normalized_group,
            "summary": normalized_summary,
            "file": file_data,
            "metadata": dict(metadata or {}),
            "actor": normalized_actor,
            "recorded_at": _now(),
        }

    @staticmethod
    def validate(record: object) -> None:
        if not isinstance(record, dict):
            raise ValueError("Improvement Case must be an object")
        required = {
            "schema_version",
            "case_id",
            "project",
            "conversation_id",
            "change_type",
            "status",
            "issue",
            "candidate",
            "results",
            "delivery",
            "refresh",
            "regression",
            "resume",
            "privacy",
            "history",
            "created_at",
            "updated_at",
        }
        missing = sorted(required - set(record))
        if missing:
            raise ValueError(
                "Improvement Case missing fields: " + ", ".join(missing)
            )
        if record.get("schema_version") != IMPROVEMENT_CASE_SCHEMA_VERSION:
            raise ValueError(
                f"Improvement Case schema_version must be {IMPROVEMENT_CASE_SCHEMA_VERSION}"
            )
        if record.get("change_type") not in CHANGE_TYPES:
            raise ValueError("Unsupported Improvement Case change_type")
        if record.get("status") not in CASE_STATUSES:
            raise ValueError("Unsupported Improvement Case status")
        for field in (
            "issue",
            "candidate",
            "delivery",
            "refresh",
            "regression",
            "resume",
            "privacy",
        ):
            if not isinstance(record.get(field), dict):
                raise ValueError(f"Improvement Case {field} must be an object")
        for field in ("results", "history"):
            if not isinstance(record.get(field), list):
                raise ValueError(f"Improvement Case {field} must be an array")


class ImprovementCaseService:
    """Candidate-change lifecycle with separate trial and adoption approvals."""

    def __init__(
        self,
        workspace: Path,
        *,
        runtime: Any,
        data_root: Path | None = None,
    ) -> None:
        self.workspace = workspace.resolve()
        self.runtime = runtime
        self.store = ImprovementCaseStore(
            self.workspace,
            data_root=data_root,
        )

    @staticmethod
    def _record(
        case: dict[str, Any],
        event: str,
        *,
        actor: str,
        **details: Any,
    ) -> None:
        history = case.setdefault("history", [])
        if not isinstance(history, list):
            raise ImprovementCaseError("Invalid Improvement Case history")
        history.append(
            {
                "event": event,
                "actor": actor,
                "recorded_at": _now(),
                **details,
            }
        )
        if len(history) > 500:
            del history[:-500]

    @staticmethod
    def _source_task_snapshot(task: Any | None, checkpoint: Any) -> dict[str, Any] | None:
        if task is None:
            return None
        checkpoint_data = checkpoint if isinstance(checkpoint, dict) else {}
        return {
            "task_id": task.task_id,
            "stage": checkpoint_data.get("stage"),
            "status": task.status,
            "pipeline": task.pipeline,
            "requirement_hash": _canonical_hash(task.requirement),
            "created_at": task.created_at,
        }

    def open(
        self,
        *,
        project: str,
        conversation_id: str,
        task: Any | None,
        checkpoint: dict[str, Any] | None,
        change_type: str,
        observed_behavior: str,
        expected_behavior: str,
        diagnosis: str | None = None,
        proposal: dict[str, Any] | None = None,
        affected_tool_id: str | None = None,
        capability: str | None = None,
        adoption_scope: str = "project",
        actor: str = "conversation-user",
    ) -> dict[str, Any]:
        tool_trial = None
        if change_type == "tool-change":
            normalized_tool_id = (
                affected_tool_id.strip()
                if isinstance(affected_tool_id, str)
                else ""
            )
            normalized_capability = (
                capability.strip() if isinstance(capability, str) else ""
            )
            if not normalized_tool_id or not normalized_capability:
                raise ValueError(
                    "tool-change requires affected_tool_id and capability"
                )
            normalized_scope = adoption_scope.strip()
            if normalized_scope not in TOOL_ADOPTION_SCOPES:
                raise ValueError(
                    "adoption_scope must be task, project, or workspace"
                )
            tool_trial = {
                "tool_id": normalized_tool_id,
                "capability": normalized_capability,
                "adoption_scope": normalized_scope,
                "assessment": None,
                "stable_configuration_changed": False,
            }
        return self.store.create(
            project=project,
            conversation_id=conversation_id,
            change_type=change_type,
            observed_behavior=observed_behavior,
            expected_behavior=expected_behavior,
            diagnosis=diagnosis,
            proposal=proposal,
            source_task=self._source_task_snapshot(task, checkpoint),
            tool_trial=tool_trial,
            actor=actor,
        )

    def propose(
        self,
        project: str,
        case_id: str,
        proposal: dict[str, Any],
        *,
        actor: str,
    ) -> dict[str, Any]:
        case = self.store.get(project, case_id)
        if case["status"] not in {
            "proposal-required",
            "trial-approval-required",
        }:
            raise ImprovementCaseError(
                "Proposal can only be changed before trial approval"
            )
        case["proposal"] = self.store._normalize_proposal(proposal)
        case["status"] = "trial-approval-required"
        self._record(case, "proposal-updated", actor=actor)
        return self.store.save(case)

    def _assess_tool(self, project: str, tool_id: str) -> dict[str, Any]:
        descriptor = next(
            (
                item
                for item in self.runtime.discover_tools(project=project)
                if isinstance(item, dict) and item.get("tool_id") == tool_id
            ),
            None,
        )
        if not isinstance(descriptor, dict):
            return {
                "status": "unsupported",
                "registered": False,
                "available": False,
                "ready": False,
                "installable": False,
                "integration_required": True,
                "disclosure": None,
            }
        ready = bool(
            descriptor.get("ready")
            and descriptor.get("registered")
            and descriptor.get("available")
        )
        return {
            "status": descriptor.get("status"),
            "registered": bool(descriptor.get("registered")),
            "available": bool(descriptor.get("available")),
            "ready": ready,
            "installable": bool(descriptor.get("installable")),
            "integration_required": not ready,
            "disclosure": descriptor.get("disclosure")
            if isinstance(descriptor.get("disclosure"), dict)
            else None,
        }

    def approve_trial(
        self,
        project: str,
        case_id: str,
        *,
        actor: str,
        comment: str | None = None,
    ) -> dict[str, Any]:
        case = self.store.get(project, case_id)
        if case["status"] != "trial-approval-required":
            raise ImprovementCaseError(
                "Trial approval requires trial-approval-required status"
            )
        if not isinstance(case.get("proposal"), dict):
            raise ImprovementCaseError(
                "Trial approval requires a complete proposal"
            )
        timestamp = _now()
        case["trial_approval"] = {
            "decision": "approved",
            "actor": actor,
            "comment": comment.strip()
            if isinstance(comment, str) and comment.strip()
            else None,
            "decided_at": timestamp,
        }
        candidate = case["candidate"]
        tool_trial = candidate.get("tool_trial")
        if case["change_type"] == "tool-change" and isinstance(tool_trial, dict):
            assessment = self._assess_tool(project, str(tool_trial["tool_id"]))
            tool_trial["assessment"] = assessment
            if assessment["integration_required"]:
                case["change_type"] = "tool-integration-change"
                candidate["kind"] = "tool-integration"
                case["status"] = "candidate-building"
            else:
                candidate["kind"] = "tool-trial"
                case["status"] = "candidate-ready"
        else:
            candidate["kind"] = "code-candidate"
            case["status"] = "candidate-building"
        self._record(
            case,
            "trial-approved",
            actor=actor,
            next_status=case["status"],
        )
        self._ensure_development_bundle(case)
        return self.store.save(case)

    def decide_trial(
        self,
        project: str,
        case_id: str,
        decision: str,
        *,
        actor: str,
        comment: str | None = None,
    ) -> dict[str, Any]:
        normalized = decision.strip().lower()
        if normalized not in TRIAL_DECISIONS:
            raise ValueError(
                "trial decision must be approved, changes-requested, or rejected"
            )
        if normalized == "approved":
            return self.approve_trial(
                project,
                case_id,
                actor=actor,
                comment=comment,
            )
        case = self.store.get(project, case_id)
        if case["status"] not in {
            "trial-approval-required",
            "proposal-required",
        }:
            raise ImprovementCaseError(
                "Trial decision is no longer available"
            )
        case["trial_approval"] = {
            "decision": normalized,
            "actor": actor,
            "comment": comment.strip()
            if isinstance(comment, str) and comment.strip()
            else None,
            "decided_at": _now(),
        }
        if normalized == "changes-requested":
            case["status"] = "proposal-required"
            event = "trial-changes-requested"
        else:
            case["status"] = "closed-stable-retained"
            case["resume"]["status"] = "ready"
            event = "trial-rejected"
        self._record(case, event, actor=actor)
        return self.store.save(case)

    def _ensure_development_bundle(
        self,
        case: dict[str, Any],
    ) -> Path | None:
        if case["status"] != "candidate-building":
            return None
        candidate = case["candidate"]
        existing = candidate.get("development_bundle")
        if isinstance(existing, str) and Path(existing).is_file():
            return Path(existing)
        root = (
            self.store.layout.improvement_cases
            / str(case["project"])
            / str(case["case_id"])
        )
        root.mkdir(parents=True, exist_ok=True)
        path = root / "development-bundle.json"
        source_task = case.get("source_task")
        payload = {
            "schema_version": 1,
            "case_id": case["case_id"],
            "change_type": case["change_type"],
            "issue": dict(case["issue"]),
            "proposal": dict(case["proposal"] or {}),
            "source_checkpoint": {
                "stage": source_task.get("stage")
                if isinstance(source_task, dict)
                else None,
                "pipeline": source_task.get("pipeline")
                if isinstance(source_task, dict)
                else None,
            },
            "candidate_rules": {
                "stable_plugin_must_remain_unchanged": True,
                "merge_before_adoption_approval": False,
                "real_result_evidence_required": True,
                "public_fixture_required": True,
                "real_user_assets_in_public_repo": False,
                "production_dry_run_fallback": False,
                "fake_semantic_pass": False,
            },
            "resume_policy": dict(case["resume"]),
        }
        _write_json(path, payload)
        candidate["development_bundle"] = str(path)
        return path

    def development_bundle(
        self,
        project: str,
        case_id: str,
    ) -> dict[str, Any]:
        case = self.store.get(project, case_id)
        path = self._ensure_development_bundle(case)
        if path is None:
            raise ImprovementCaseError(
                "A development bundle is only available while a code candidate is being built"
            )
        self.store.save(case)
        return {
            "status": "ready",
            "case_id": case_id,
            "private_bundle_path": str(path),
            "privacy": "private-outside-project-git",
        }

    def link_candidate(
        self,
        project: str,
        case_id: str,
        candidate_data: dict[str, Any],
        *,
        actor: str,
    ) -> dict[str, Any]:
        case = self.store.get(project, case_id)
        if case["status"] not in {
            "candidate-building",
            "candidate-ready",
        }:
            raise ImprovementCaseError(
                "Candidate metadata can only be linked before a trial run"
            )
        if not isinstance(candidate_data, dict):
            raise ValueError("candidate_data must be an object")
        candidate = case["candidate"]
        for field in ("branch", "commit", "version", "notes"):
            value = candidate_data.get(field)
            candidate[field] = (
                str(value).strip()
                if value is not None and str(value).strip()
                else None
            )
        if not any(candidate.get(field) for field in ("branch", "commit", "version")):
            raise ValueError(
                "Candidate metadata requires branch, commit, or version"
            )
        candidate["kind"] = candidate.get("kind") or "code-candidate"
        case["status"] = "candidate-ready"
        self._record(case, "candidate-linked", actor=actor)
        return self.store.save(case)

    def start_tool_trial(
        self,
        project: str,
        case_id: str,
        *,
        actor: str,
    ) -> tuple[dict[str, Any], Any]:
        case = self.store.get(project, case_id)
        if case["status"] != "candidate-ready":
            raise ImprovementCaseError(
                "Tool trial requires candidate-ready status"
            )
        candidate = case["candidate"]
        tool_trial = candidate.get("tool_trial")
        if candidate.get("kind") != "tool-trial" or not isinstance(
            tool_trial, dict
        ):
            raise ImprovementCaseError(
                "This Candidate Change does not contain an executable Tool trial"
            )
        assessment = tool_trial.get("assessment")
        if not isinstance(assessment, dict) or assessment.get("ready") is not True:
            raise ImprovementCaseError(
                "Candidate Tool is not registered and available"
            )
        source_task = case.get("source_task")
        source_task_id = (
            str(source_task.get("task_id"))
            if isinstance(source_task, dict) and source_task.get("task_id")
            else ""
        )
        if not source_task_id:
            raise ImprovementCaseError(
                "Tool trial requires a paused production Task"
            )
        original = self.runtime.load_task(project, source_task_id)
        conversation_theme = original.state.get("conversation_theme")
        theme_ref = (
            conversation_theme.get("theme_ref")
            if isinstance(conversation_theme, dict)
            else None
        )
        trial = self.runtime.run(
            project,
            original.requirement,
            pipeline=original.pipeline,
            conversation_id=str(case["conversation_id"]),
            continue_unbound=not isinstance(theme_ref, dict),
        )
        trial.state["execution_overrides"] = {
            "tools": {
                str(tool_trial["capability"]): {
                    "primary": str(tool_trial["tool_id"]),
                    "fallback": [],
                }
            }
        }
        trial.state["candidate_change"] = {
            "case_id": case_id,
            "kind": "tool-trial",
            "stable_configuration_changed": False,
        }
        self.runtime.store.save(trial)
        candidate["task_id"] = trial.task_id
        case["status"] = "candidate-running"
        self._record(
            case,
            "tool-trial-started",
            actor=actor,
            tool_id=tool_trial["tool_id"],
            capability=tool_trial["capability"],
        )
        self.store.save(case)
        return case, trial

    def sync_candidate_task(
        self,
        project: str,
        case_id: str,
    ) -> dict[str, Any]:
        case = self.store.get(project, case_id)
        if case["status"] != "candidate-running":
            return case
        candidate = case["candidate"]
        task_id = candidate.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            return case
        try:
            task = self.runtime.load_task(project, task_id)
        except (FileNotFoundError, ValueError):
            return case
        if task.status == "failed":
            case["status"] = "candidate-building"
            self._record(
                case,
                "candidate-run-failed",
                actor="runtime",
                error_type=(
                    task.error.get("type")
                    if isinstance(task.error, dict)
                    else None
                ),
            )
            return self.store.save(case)
        report = task.state.get("qa_report")
        export_gate = (
            report.get("export_gate")
            if isinstance(report, dict)
            else None
        )
        if not isinstance(export_gate, dict) or export_gate.get("allowed") is not True:
            return case
        registry = task.state.get("artifact_registry")
        records = (
            registry.get("records", [])
            if isinstance(registry, dict)
            else []
        )
        artifacts = [
            {
                "kind": item.get("artifact_kind"),
                "operation": item.get("operation"),
                "review_status": (
                    item.get("qa", {}).get("status")
                    if isinstance(item.get("qa"), dict)
                    else None
                ),
                "tool_id": (
                    item.get("provider", {}).get("provider_id")
                    if isinstance(item.get("provider"), dict)
                    else None
                ),
                "width": (
                    item.get("file", {}).get("width")
                    if isinstance(item.get("file"), dict)
                    else None
                ),
                "height": (
                    item.get("file", {}).get("height")
                    if isinstance(item.get("file"), dict)
                    else None
                ),
            }
            for item in records
            if isinstance(item, dict)
        ]
        if not any(
            isinstance(item, dict)
            and isinstance(item.get("metadata"), dict)
            and item["metadata"].get("candidate_task_id") == task_id
            for item in case.get("results", [])
        ):
            case["results"].append(
                {
                    "schema_version": IMPROVEMENT_RESULT_SCHEMA_VERSION,
                    "evidence_id": "runtime-" + task_id,
                    "group": "candidate",
                    "summary": "Candidate Task produced a reviewed GUIF Artifact.",
                    "file": None,
                    "metadata": {
                        "source": "runtime-artifact",
                        "candidate_task_id": task_id,
                        "artifact_count": len(artifacts),
                        "artifacts": artifacts,
                    },
                    "actor": "runtime",
                    "recorded_at": _now(),
                }
            )
        case["status"] = "result-review-required"
        self._record(
            case,
            "candidate-result-ready",
            actor="runtime",
            artifact_count=len(artifacts),
        )
        return self.store.save(case)

    def record_result(
        self,
        project: str,
        case_id: str,
        *,
        group: str,
        summary: str,
        file_path: Path | None = None,
        metadata: dict[str, Any] | None = None,
        actor: str,
    ) -> dict[str, Any]:
        case = self.store.get(project, case_id)
        if case["status"] not in {
            "candidate-ready",
            "candidate-running",
            "result-review-required",
        }:
            raise ImprovementCaseError(
                "Candidate evidence cannot be added in the current status"
            )
        evidence = self.store.stage_result(
            project,
            case_id,
            group=group,
            summary=summary,
            file_path=file_path,
            metadata=metadata,
            actor=actor,
        )
        case["results"].append(evidence)
        if group == "candidate":
            case["status"] = "result-review-required"
        self._record(
            case,
            "candidate-evidence-recorded",
            actor=actor,
            group=group,
        )
        return self.store.save(case)

    def _apply_tool_adoption(
        self,
        case: dict[str, Any],
    ) -> dict[str, Any]:
        candidate = case["candidate"]
        tool_trial = candidate.get("tool_trial")
        if not isinstance(tool_trial, dict):
            raise ImprovementCaseError(
                "Tool adoption requires Tool trial metadata"
            )
        assessment = tool_trial.get("assessment")
        if not isinstance(assessment, dict) or assessment.get("ready") is not True:
            raise ImprovementCaseError(
                "Unavailable Tool cannot be adopted without an integration release"
            )
        capability = str(tool_trial["capability"])
        tool_id = str(tool_trial["tool_id"])
        scope = str(tool_trial["adoption_scope"])
        if scope == "project":
            path = self.runtime.bind_project_tool(
                str(case["project"]),
                capability,
                tool_id,
            )
            applied = {
                "scope": scope,
                "target": "project execution configuration",
                "path": str(path),
            }
        elif scope == "workspace":
            path = bind_workspace_tool(
                self.workspace,
                capability,
                tool_id,
            )
            applied = {
                "scope": scope,
                "target": "workspace execution configuration",
                "path": str(path),
            }
        elif scope == "task":
            source = case.get("source_task")
            task_id = (
                str(source.get("task_id"))
                if isinstance(source, dict) and source.get("task_id")
                else ""
            )
            if not task_id:
                raise ImprovementCaseError(
                    "Task-scoped Tool adoption requires a source Task"
                )
            task = self.runtime.load_task(str(case["project"]), task_id)
            overrides = task.state.setdefault("execution_overrides", {})
            if not isinstance(overrides, dict):
                raise ImprovementCaseError("Invalid Task execution_overrides")
            tools = overrides.setdefault("tools", {})
            if not isinstance(tools, dict):
                raise ImprovementCaseError(
                    "Invalid Task execution_overrides.tools"
                )
            tools[capability] = {"primary": tool_id, "fallback": []}
            self.runtime.store.save(task)
            applied = {
                "scope": scope,
                "target": "paused production Task",
                "path": None,
            }
        else:
            raise ImprovementCaseError(
                "Unsupported Tool adoption scope"
            )
        tool_trial["stable_configuration_changed"] = True
        return applied

    def decide_adoption(
        self,
        project: str,
        case_id: str,
        decision: str,
        *,
        actor: str,
        comment: str | None = None,
    ) -> dict[str, Any]:
        normalized = decision.strip().lower()
        if normalized not in ADOPTION_DECISIONS:
            raise ValueError(
                "adoption decision must be approved, changes-requested, or rejected"
            )
        case = self.store.get(project, case_id)
        if case["status"] != "result-review-required":
            raise ImprovementCaseError(
                "Adoption decision requires reviewed candidate results"
            )
        has_candidate = any(
            isinstance(item, dict) and item.get("group") == "candidate"
            for item in case.get("results", [])
        )
        if not has_candidate:
            raise ImprovementCaseError(
                "Adoption cannot be approved without real candidate evidence"
            )
        case["adoption"] = {
            "decision": normalized,
            "actor": actor,
            "comment": comment.strip()
            if isinstance(comment, str) and comment.strip()
            else None,
            "decided_at": _now(),
            "applied": None,
        }
        if normalized == "changes-requested":
            case["status"] = "candidate-building"
            event = "adoption-changes-requested"
        elif normalized == "rejected":
            case["status"] = "closed-stable-retained"
            case["resume"]["status"] = "ready"
            event = "candidate-rejected"
        else:
            candidate = case["candidate"]
            tool_trial = candidate.get("tool_trial")
            assessment = (
                tool_trial.get("assessment")
                if isinstance(tool_trial, dict)
                else None
            )
            if (
                candidate.get("kind") == "tool-trial"
                and isinstance(assessment, dict)
                and assessment.get("integration_required") is False
            ):
                case["adoption"]["applied"] = self._apply_tool_adoption(case)
                case["regression"] = {
                    "status": "passed-by-reviewed-trial",
                    "summary": "The adopted Tool routing was validated by the reviewed candidate result.",
                    "recorded_at": _now(),
                }
                case["status"] = "resolved"
                case["resume"]["status"] = "ready"
                event = "tool-change-adopted"
            else:
                case["status"] = "publishing-required"
                event = "candidate-adopted"
        self._record(case, event, actor=actor)
        return self.store.save(case)

    def mark_published(
        self,
        project: str,
        case_id: str,
        delivery: dict[str, Any],
        *,
        actor: str,
    ) -> dict[str, Any]:
        case = self.store.get(project, case_id)
        if case["status"] != "publishing-required":
            raise ImprovementCaseError(
                "Publishing requires an adopted code candidate"
            )
        if not isinstance(delivery, dict):
            raise ValueError("delivery must be an object")
        required = (
            "repository",
            "branch",
            "pull_request",
            "merge_commit",
            "minimum_plugin_version",
        )
        values: dict[str, Any] = {}
        for field in required:
            value = delivery.get(field)
            if value is None or not str(value).strip():
                raise ValueError(f"delivery requires {field}")
            values[field] = (
                int(value)
                if field == "pull_request" and str(value).isdigit()
                else str(value).strip()
            )
        case["delivery"].update(
            {
                **values,
                "published_at": _now(),
            }
        )
        case["refresh"].update(
            {
                "required": True,
                "confirmed": False,
                "current_plugin_version": None,
                "confirmed_at": None,
            }
        )
        case["status"] = "plugin-refresh-required"
        self._record(case, "candidate-published", actor=actor)
        return self.store.save(case)

    def confirm_refresh(
        self,
        project: str,
        case_id: str,
        *,
        current_plugin_version: str,
        actor: str,
    ) -> dict[str, Any]:
        case = self.store.get(project, case_id)
        if case["status"] != "plugin-refresh-required":
            raise ImprovementCaseError(
                "Plugin refresh confirmation is not currently required"
            )
        current = current_plugin_version.strip()
        minimum = str(
            case.get("delivery", {}).get("minimum_plugin_version") or ""
        ).strip()
        if not current or not minimum:
            raise ImprovementCaseError(
                "Plugin refresh confirmation requires current and minimum versions"
            )
        if not version_satisfies(current, minimum):
            raise ImprovementCaseError(
                f"Installed plugin {current} does not satisfy required version {minimum}"
            )
        case["refresh"].update(
            {
                "confirmed": True,
                "current_plugin_version": current,
                "confirmed_at": _now(),
            }
        )
        case["status"] = "regression-validation-required"
        self._record(case, "plugin-refresh-confirmed", actor=actor)
        return self.store.save(case)

    def record_regression(
        self,
        project: str,
        case_id: str,
        *,
        passed: bool,
        summary: str,
        actor: str,
    ) -> dict[str, Any]:
        case = self.store.get(project, case_id)
        if case["status"] != "regression-validation-required":
            raise ImprovementCaseError(
                "Regression result is not currently expected"
            )
        normalized_summary = summary.strip()
        if not normalized_summary:
            raise ValueError("Regression summary must not be empty")
        case["regression"] = {
            "status": "passed" if passed else "failed",
            "summary": normalized_summary,
            "recorded_at": _now(),
        }
        if passed:
            case["status"] = "resolved"
            case["resume"]["status"] = "ready"
            event = "regression-passed"
        else:
            case["status"] = "candidate-building"
            case["resume"]["status"] = "paused"
            event = "regression-failed-reopened"
            self._ensure_development_bundle(case)
        self._record(case, event, actor=actor)
        return self.store.save(case)

    def mark_resumed(
        self,
        project: str,
        case_id: str,
        *,
        actor: str,
    ) -> dict[str, Any]:
        case = self.store.get(project, case_id)
        if case["status"] not in {
            "resolved",
            "closed-stable-retained",
        }:
            raise ImprovementCaseError(
                "Production can resume only after resolution or candidate rejection"
            )
        case["resume"]["status"] = "resumed"
        self._record(case, "production-resumed", actor=actor)
        return self.store.save(case)

    @staticmethod
    def public_case(case: dict[str, Any]) -> dict[str, Any]:
        candidate = case.get("candidate")
        tool_trial = (
            candidate.get("tool_trial")
            if isinstance(candidate, dict)
            else None
        )
        source = case.get("source_task")
        results: list[dict[str, Any]] = []
        for item in case.get("results", []):
            if not isinstance(item, dict):
                continue
            file_data = (
                item.get("file")
                if isinstance(item.get("file"), dict)
                else None
            )
            metadata = (
                item.get("metadata")
                if isinstance(item.get("metadata"), dict)
                else {}
            )
            results.append(
                {
                    "group": item.get("group"),
                    "summary": item.get("summary"),
                    "file_present": file_data is not None,
                    "mime_type": (
                        file_data.get("mime_type")
                        if isinstance(file_data, dict)
                        else None
                    ),
                    "artifact_count": metadata.get("artifact_count"),
                    "recorded_at": item.get("recorded_at"),
                }
            )
        proposal = case.get("proposal")
        assessment = (
            tool_trial.get("assessment")
            if isinstance(tool_trial, dict)
            else None
        )
        adoption = (
            dict(case["adoption"])
            if isinstance(case.get("adoption"), dict)
            else None
        )
        if isinstance(adoption, dict) and isinstance(adoption.get("applied"), dict):
            adoption["applied"] = {
                "scope": adoption["applied"].get("scope"),
                "target": adoption["applied"].get("target"),
            }
        return {
            "schema_version": IMPROVEMENT_CASE_SCHEMA_VERSION,
            "case_id": case.get("case_id"),
            "change_type": case.get("change_type"),
            "status": case.get("status"),
            "issue": dict(case.get("issue") or {}),
            "proposal": dict(proposal)
            if isinstance(proposal, dict)
            else None,
            "source_checkpoint": {
                "stage": source.get("stage")
                if isinstance(source, dict)
                else None,
                "status": source.get("status")
                if isinstance(source, dict)
                else None,
                "pipeline": source.get("pipeline")
                if isinstance(source, dict)
                else None,
            },
            "trial_approval": dict(case["trial_approval"])
            if isinstance(case.get("trial_approval"), dict)
            else None,
            "candidate": {
                "kind": candidate.get("kind")
                if isinstance(candidate, dict)
                else None,
                "branch": candidate.get("branch")
                if isinstance(candidate, dict)
                else None,
                "commit": candidate.get("commit")
                if isinstance(candidate, dict)
                else None,
                "version": candidate.get("version")
                if isinstance(candidate, dict)
                else None,
                "development_bundle_ready": bool(
                    isinstance(candidate, dict)
                    and candidate.get("development_bundle")
                ),
                "tool_trial": {
                    "tool_id": tool_trial.get("tool_id"),
                    "capability": tool_trial.get("capability"),
                    "adoption_scope": tool_trial.get("adoption_scope"),
                    "assessment": {
                        "status": assessment.get("status"),
                        "registered": assessment.get("registered"),
                        "available": assessment.get("available"),
                        "ready": assessment.get("ready"),
                        "installable": assessment.get("installable"),
                        "integration_required": assessment.get(
                            "integration_required"
                        ),
                        "disclosure": assessment.get("disclosure"),
                    }
                    if isinstance(assessment, dict)
                    else None,
                    "stable_configuration_changed": tool_trial.get(
                        "stable_configuration_changed"
                    ),
                }
                if isinstance(tool_trial, dict)
                else None,
            },
            "results": results,
            "adoption": adoption,
            "delivery": dict(case.get("delivery") or {}),
            "refresh": dict(case.get("refresh") or {}),
            "regression": dict(case.get("regression") or {}),
            "resume": {
                "policy": case.get("resume", {}).get("policy"),
                "status": case.get("resume", {}).get("status"),
            },
            "privacy": dict(case.get("privacy") or {}),
            "updated_at": case.get("updated_at"),
        }


__all__ = [
    "ADOPTION_DECISIONS",
    "CASE_STATUSES",
    "CHANGE_TYPES",
    "IMPROVEMENT_CASE_SCHEMA_VERSION",
    "ImprovementCaseError",
    "ImprovementCaseService",
    "ImprovementCaseStore",
    "TOOL_ADOPTION_SCOPES",
    "TRIAL_DECISIONS",
    "version_satisfies",
]
