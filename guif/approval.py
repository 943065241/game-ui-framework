from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from guif.prompt_ir import validate_prompt_ir

APPROVAL_SCHEMA_VERSION = 1
APPROVAL_DECISIONS = {"approved", "rejected", "changes-requested"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _required_points(prompt_ir: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in prompt_ir.get("approval_points", [])
        if isinstance(item, dict) and item.get("required") is not False and item.get("id")
    ]


def _approval_state(task: Any) -> dict[str, Any]:
    state = task.state.get("approval_state")
    if not isinstance(state, dict):
        state = {
            "schema_version": APPROVAL_SCHEMA_VERSION,
            "task_id": task.task_id,
            "project": task.project,
            "records": {},
            "history": [],
            "status": "not-required",
            "required_ids": [],
            "approved_ids": [],
            "pending_ids": [],
            "rejected_ids": [],
            "changes_requested_ids": [],
            "project_mutated": False,
            "provider_executed": False,
            "provider_execution_ids": [],
            "updated_at": _now(),
        }
        task.state["approval_state"] = state
    return state


def _replace_output(task: Any, output_type: str, value: Any, *, agent: str) -> None:
    for output in reversed(task.outputs):
        if isinstance(output, dict) and output.get("type") == output_type:
            output["value"] = value
            output["agent"] = agent
            return
    task.add_output(output_type, value, agent=agent)


def refresh_approval_gate(task: Any) -> dict[str, Any]:
    prompt_ir = task.state.get("prompt_ir")
    if not isinstance(prompt_ir, dict):
        raise ValueError("Approval requires task.state['prompt_ir']")

    state = _approval_state(task)
    points = _required_points(prompt_ir)
    required_ids = [str(item["id"]) for item in points]
    records = state.get("records")
    if not isinstance(records, dict):
        records = {}
        state["records"] = records

    approved_ids = sorted(
        approval_id
        for approval_id in required_ids
        if isinstance(records.get(approval_id), dict)
        and records[approval_id].get("decision") == "approved"
    )
    rejected_ids = sorted(
        approval_id
        for approval_id in required_ids
        if isinstance(records.get(approval_id), dict)
        and records[approval_id].get("decision") == "rejected"
    )
    changes_requested_ids = sorted(
        approval_id
        for approval_id in required_ids
        if isinstance(records.get(approval_id), dict)
        and records[approval_id].get("decision") == "changes-requested"
    )
    pending_ids = sorted(set(required_ids) - set(approved_ids) - set(rejected_ids) - set(changes_requested_ids))

    original_blockers = [
        dict(item)
        for item in prompt_ir.get("blockers", [])
        if isinstance(item, dict) and item.get("source") != "approval"
    ]
    approval_blockers: list[dict[str, Any]] = []
    for approval_id in rejected_ids:
        record = records[approval_id]
        approval_blockers.append(
            {
                "severity": "blocking",
                "code": "approval-rejected",
                "message": f"Approval point {approval_id} was rejected.",
                "source": "approval",
                "approval_id": approval_id,
                "actor": record.get("actor"),
                "comment": record.get("comment"),
            }
        )
    for approval_id in changes_requested_ids:
        record = records[approval_id]
        approval_blockers.append(
            {
                "severity": "blocking",
                "code": "approval-changes-requested",
                "message": f"Approval point {approval_id} requires changes.",
                "source": "approval",
                "approval_id": approval_id,
                "actor": record.get("actor"),
                "comment": record.get("comment"),
            }
        )

    prompt_ir["blockers"] = original_blockers + approval_blockers
    if original_blockers or approval_blockers:
        prompt_status = "blocked"
    elif pending_ids:
        prompt_status = "review-required"
    else:
        prompt_status = "ready"

    prompt_ir["status"] = prompt_status
    executable = prompt_status == "ready"
    for job in prompt_ir.get("jobs", []):
        if isinstance(job, dict):
            job["executable"] = executable

    if rejected_ids:
        approval_status = "rejected"
    elif changes_requested_ids:
        approval_status = "changes-requested"
    elif pending_ids:
        approval_status = "pending"
    elif required_ids:
        approval_status = "approved"
    else:
        approval_status = "not-required"

    project_mutated = bool(state.get("project_mutated", False))
    provider_executed = bool(state.get("provider_executed", False))
    provider_execution_ids = list(state.get("provider_execution_ids", []))
    state.update(
        {
            "schema_version": APPROVAL_SCHEMA_VERSION,
            "task_id": task.task_id,
            "project": task.project,
            "status": approval_status,
            "required_ids": required_ids,
            "approved_ids": approved_ids,
            "pending_ids": pending_ids,
            "rejected_ids": rejected_ids,
            "changes_requested_ids": changes_requested_ids,
            "prompt_status": prompt_status,
            "project_mutated": project_mutated,
            "provider_executed": provider_executed,
            "provider_execution_ids": provider_execution_ids,
            "updated_at": _now(),
        }
    )
    prompt_ir["approval_control"] = {
        "schema_version": APPROVAL_SCHEMA_VERSION,
        "status": approval_status,
        "required_ids": required_ids,
        "approved_ids": approved_ids,
        "pending_ids": pending_ids,
        "rejected_ids": rejected_ids,
        "changes_requested_ids": changes_requested_ids,
        "project_mutated": project_mutated,
        "provider_executed": provider_executed,
        "provider_execution_ids": provider_execution_ids,
    }

    errors = validate_prompt_ir(prompt_ir)
    if errors:
        raise ValueError("Approval produced invalid Prompt IR: " + "; ".join(errors))
    _replace_output(task, "model-neutral-prompt-ir", prompt_ir, agent="approval")
    return state


def initialize_approvals(task: Any) -> dict[str, Any]:
    state = refresh_approval_gate(task)
    task.record(
        "approval",
        "initialized",
        f"Approval gate initialized with {len(state['required_ids'])} required point(s).",
    )
    return state


def decide_approval(
    task: Any,
    approval_id: str,
    decision: str,
    *,
    actor: str,
    comment: str | None = None,
) -> dict[str, Any]:
    normalized_id = approval_id.strip()
    normalized_actor = actor.strip()
    normalized_decision = decision.strip().lower()
    if not normalized_id:
        raise ValueError("approval_id must not be empty")
    if not normalized_actor:
        raise ValueError("actor must not be empty")
    if normalized_decision not in APPROVAL_DECISIONS:
        raise ValueError("decision must be approved, rejected, or changes-requested")

    prompt_ir = task.state.get("prompt_ir")
    if not isinstance(prompt_ir, dict):
        raise ValueError("Approval requires task.state['prompt_ir']")
    known_points = {
        str(item.get("id")): item
        for item in prompt_ir.get("approval_points", [])
        if isinstance(item, dict) and item.get("id")
    }
    if normalized_id not in known_points:
        raise ValueError(f"Unknown approval point: {normalized_id}")
    if known_points[normalized_id].get("required") is False:
        raise ValueError(f"Approval point is not required: {normalized_id}")

    state = _approval_state(task)
    timestamp = _now()
    record = {
        "approval_id": normalized_id,
        "decision": normalized_decision,
        "actor": normalized_actor,
        "comment": comment.strip() if isinstance(comment, str) and comment.strip() else None,
        "decided_at": timestamp,
        "question": known_points[normalized_id].get("question"),
        "source": known_points[normalized_id].get("source"),
    }
    records = state.setdefault("records", {})
    history = state.setdefault("history", [])
    if not isinstance(records, dict) or not isinstance(history, list):
        raise ValueError("Invalid persisted approval state")
    records[normalized_id] = record
    history.append(dict(record))

    refreshed = refresh_approval_gate(task)
    task.record(
        "approval",
        normalized_decision,
        f"{normalized_actor} set {normalized_id} to {normalized_decision}.",
    )
    return refreshed


def mark_provider_executed(task: Any, execution_id: str, provider_id: str) -> dict[str, Any]:
    state = _approval_state(task)
    execution_ids = state.setdefault("provider_execution_ids", [])
    if not isinstance(execution_ids, list):
        raise ValueError("Invalid persisted provider execution ids")
    if execution_id not in execution_ids:
        execution_ids.append(execution_id)
    state["provider_executed"] = True
    state["updated_at"] = _now()
    prompt_ir = task.state.get("prompt_ir")
    if isinstance(prompt_ir, dict):
        control = prompt_ir.setdefault("approval_control", {})
        if isinstance(control, dict):
            control["provider_executed"] = True
            control["provider_execution_ids"] = list(execution_ids)
        _replace_output(task, "model-neutral-prompt-ir", prompt_ir, agent="approval")
    task.record(
        "approval",
        "provider-executed",
        f"Provider {provider_id} executed approved work under execution {execution_id}.",
    )
    return state


def approval_summary(task: Any) -> dict[str, Any]:
    if not isinstance(task.state.get("prompt_ir"), dict):
        raise ValueError("Task does not contain a Prompt IR approval contract")
    return refresh_approval_gate(task)
