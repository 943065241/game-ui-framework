from __future__ import annotations

from typing import Any

from guif.prompt_ir import validate_prompt_ir
from guif.resource import validate_resource_data

SEMANTIC_QA_SCHEMA_VERSION = 1
ARTIFACT_OUTPUT_TYPES = {
    "generated-artifact",
    "image-artifact",
    "production-artifact",
    "effect-image-artifact",
}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _normalize(values: list[Any]) -> set[str]:
    return {" ".join(str(value).split()).casefold() for value in values if str(value).strip()}


def _check(
    checks: list[dict[str, Any]],
    check_id: str,
    category: str,
    passed: bool,
    message: str,
    *,
    evidence: Any = None,
) -> None:
    checks.append(
        {
            "id": check_id,
            "category": category,
            "status": "passed" if passed else "failed",
            "message": message,
            "evidence": evidence,
        }
    )


def _finding(
    findings: list[dict[str, Any]],
    severity: str,
    code: str,
    message: str,
    *,
    source: str,
    evidence: Any = None,
) -> None:
    findings.append(
        {
            "severity": severity,
            "code": code,
            "message": message,
            "source": source,
            "evidence": evidence,
        }
    )


def _artifact_outputs(task: Any) -> list[dict[str, Any]]:
    return [
        output
        for output in getattr(task, "outputs", [])
        if isinstance(output, dict) and output.get("type") in ARTIFACT_OUTPUT_TYPES
    ]


def _required_output_types(task: Any) -> set[str]:
    return {
        str(output.get("type"))
        for output in getattr(task, "outputs", [])
        if isinstance(output, dict) and output.get("type")
    }


def build_semantic_qa_report(task: Any) -> dict[str, Any]:
    plan = task.state.get("plan")
    direction = task.state.get("direction")
    theme_contract = task.state.get("theme_contract")
    resource_bundle = task.state.get("resource_contracts")
    prompt_ir = task.state.get("prompt_ir")
    for name, value in (
        ("plan", plan),
        ("direction", direction),
        ("theme_contract", theme_contract),
        ("resource_contracts", resource_bundle),
        ("prompt_ir", prompt_ir),
    ):
        if not isinstance(value, dict):
            raise ValueError(f"Semantic QA requires task.state['{name}']")

    checks: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []

    prompt_errors = validate_prompt_ir(prompt_ir)
    _check(
        checks,
        "prompt-ir-schema",
        "contract",
        not prompt_errors,
        "Prompt IR conforms to schema v1." if not prompt_errors else "Prompt IR schema validation failed.",
        evidence=prompt_errors,
    )
    for error in prompt_errors:
        _finding(findings, "blocking", "invalid-prompt-ir", error, source="prompt")

    output_types = _required_output_types(task)
    required_outputs = {
        "ui-production-plan",
        "art-direction-review",
        "resolved-theme-contract",
        "resource-contract-bundle",
        "model-neutral-prompt-ir",
    }
    missing_outputs = sorted(required_outputs - output_types)
    _check(
        checks,
        "provenance-chain",
        "provenance",
        not missing_outputs,
        "All upstream contract outputs are registered." if not missing_outputs else "Upstream output registration is incomplete.",
        evidence={"missing_output_types": missing_outputs},
    )
    if missing_outputs:
        _finding(
            findings,
            "blocking",
            "missing-provenance-output",
            "Required upstream outputs are missing from the Task output index.",
            source="qa",
            evidence=missing_outputs,
        )

    plan_page = _as_dict(plan.get("page"))
    prompt_page = _as_dict(_as_dict(prompt_ir.get("global_contract")).get("page"))
    page_fields = ("type", "orientation", "width", "height")
    page_mismatches = {
        field: {"plan": plan_page.get(field), "prompt": prompt_page.get(field)}
        for field in page_fields
        if plan_page.get(field) != prompt_page.get(field)
    }
    _check(
        checks,
        "page-contract-consistency",
        "composition",
        not page_mismatches,
        "Prompt IR preserves the planned page contract." if not page_mismatches else "Prompt IR page values differ from the Plan.",
        evidence=page_mismatches,
    )
    if page_mismatches:
        _finding(
            findings,
            "blocking",
            "page-contract-mismatch",
            "Canvas, orientation, or page type changed between Plan and Prompt IR.",
            source="qa",
            evidence=page_mismatches,
        )

    manifest = _as_dict(theme_contract.get("manifest"))
    global_contract = _as_dict(prompt_ir.get("global_contract"))
    negative_constraints = _normalize(_as_list(global_contract.get("negative_constraints")))
    visual_instructions = _normalize(_as_list(global_contract.get("visual_instructions")))
    missing_negative = [
        value
        for value in _as_list(manifest.get("avoid"))
        if " ".join(str(value).split()).casefold() not in negative_constraints
    ]
    missing_positive = [
        value
        for value in _as_list(manifest.get("must_include"))
        if f"must include: {' '.join(str(value).split())}".casefold() not in visual_instructions
    ]
    theme_ok = not missing_negative and not missing_positive
    _check(
        checks,
        "theme-constraint-preservation",
        "theme",
        theme_ok,
        "Prompt IR preserves Theme must-include and avoid constraints." if theme_ok else "Theme constraints were lost while building Prompt IR.",
        evidence={"missing_must_include": missing_positive, "missing_avoid": missing_negative},
    )
    if not theme_ok:
        _finding(
            findings,
            "blocking",
            "theme-constraint-loss",
            "Prompt IR does not preserve every resolved Theme constraint.",
            source="qa",
            evidence={"missing_must_include": missing_positive, "missing_avoid": missing_negative},
        )

    jobs = [job for job in _as_list(prompt_ir.get("jobs")) if isinstance(job, dict)]
    production_jobs = {
        str(job.get("id")): job
        for job in jobs
        if job.get("artifact_kind") == "production-asset" and job.get("id")
    }
    candidates = {
        str(item.get("resource_id")): item
        for item in _as_list(resource_bundle.get("manifest_candidates"))
        if isinstance(item, dict) and item.get("resource_id")
    }
    missing_jobs = sorted(set(candidates) - set(production_jobs))
    extra_jobs = sorted(set(production_jobs) - set(candidates))
    output_contract_errors: dict[str, list[str]] = {}
    output_contract_mismatches: dict[str, Any] = {}
    for resource_id, candidate in candidates.items():
        job = production_jobs.get(resource_id)
        if not job:
            continue
        expected = _as_dict(candidate.get("manifest"))
        actual = _as_dict(job.get("output_contract"))
        errors = validate_resource_data(actual)
        if errors:
            output_contract_errors[resource_id] = errors
        if actual != expected:
            output_contract_mismatches[resource_id] = {"resource": expected, "prompt": actual}
    resources_ok = not missing_jobs and not extra_jobs and not output_contract_errors and not output_contract_mismatches
    _check(
        checks,
        "resource-job-coverage",
        "resource",
        resources_ok,
        "Every proposed Resource has one matching validated production job." if resources_ok else "Resource candidates and Prompt jobs are inconsistent.",
        evidence={
            "missing_jobs": missing_jobs,
            "extra_jobs": extra_jobs,
            "validation_errors": output_contract_errors,
            "contract_mismatches": output_contract_mismatches,
        },
    )
    if not resources_ok:
        _finding(
            findings,
            "blocking",
            "resource-job-mismatch",
            "Prompt IR production jobs do not exactly represent the Resource Contract Bundle.",
            source="qa",
            evidence={
                "missing_jobs": missing_jobs,
                "extra_jobs": extra_jobs,
                "validation_errors": output_contract_errors,
                "contract_mismatches": output_contract_mismatches,
            },
        )

    approved_ids = {
        str(item.get("resource_id"))
        for item in _as_list(resource_bundle.get("approved_existing"))
        if isinstance(item, dict) and item.get("resource_id")
    }
    referenced_ids = {
        str(reference.get("resource_id"))
        for job in jobs
        for reference in _as_list(job.get("references"))
        if isinstance(reference, dict) and reference.get("resource_id")
    }
    unapproved_references = sorted(referenced_ids - approved_ids)
    _check(
        checks,
        "reference-approval",
        "reference",
        not unapproved_references,
        "All Prompt references originate from approved reusable Resources." if not unapproved_references else "Prompt IR contains unapproved Resource references.",
        evidence={"unapproved_resource_ids": unapproved_references},
    )
    if unapproved_references:
        _finding(
            findings,
            "blocking",
            "unapproved-reference",
            "A Provider must not receive references that were not approved for reuse.",
            source="qa",
            evidence=unapproved_references,
        )

    prompt_status = str(prompt_ir.get("status") or "blocked")
    executable_jobs = [str(job.get("id")) for job in jobs if job.get("executable") is True]
    expected_executable = prompt_status == "ready"
    unsafe_executable = executable_jobs if not expected_executable else []
    unexpectedly_disabled = [
        str(job.get("id"))
        for job in jobs
        if expected_executable and job.get("executable") is not True
    ]
    execution_ok = not unsafe_executable and not unexpectedly_disabled
    _check(
        checks,
        "execution-gate",
        "safety",
        execution_ok,
        "Job executable flags match Prompt IR approval state." if execution_ok else "Prompt jobs violate the review-before-execute gate.",
        evidence={
            "prompt_status": prompt_status,
            "unsafe_executable_jobs": unsafe_executable,
            "unexpectedly_disabled_jobs": unexpectedly_disabled,
        },
    )
    if unsafe_executable:
        _finding(
            findings,
            "blocking",
            "unsafe-executable-job",
            "A blocked or review-required Prompt job is marked executable.",
            source="qa",
            evidence=unsafe_executable,
        )
    if unexpectedly_disabled:
        _finding(
            findings,
            "blocking",
            "ready-job-disabled",
            "A ready Prompt IR contains jobs that are not executable.",
            source="qa",
            evidence=unexpectedly_disabled,
        )

    capabilities = set(str(value) for value in _as_list(prompt_ir.get("capability_requirements")))
    edit_jobs = [job for job in jobs if job.get("operation") == "edit"]
    transparent_jobs = [
        job
        for job in jobs
        if _as_dict(job.get("output_contract")).get("alpha_required") is True
    ]
    missing_capabilities: list[str] = []
    if edit_jobs:
        for required in ("image-editing", "protected-region-editing"):
            if required not in capabilities:
                missing_capabilities.append(required)
    if transparent_jobs and "transparent-output" not in capabilities:
        missing_capabilities.append("transparent-output")
    _check(
        checks,
        "capability-contract",
        "capability",
        not missing_capabilities,
        "Prompt IR declares all capabilities required by its jobs." if not missing_capabilities else "Prompt IR omits required Provider capabilities.",
        evidence={"missing_capabilities": missing_capabilities},
    )
    if missing_capabilities:
        _finding(
            findings,
            "blocking",
            "missing-capability-requirement",
            "Provider capability requirements are incomplete.",
            source="qa",
            evidence=missing_capabilities,
        )

    upstream_blockers = [
        item for item in _as_list(prompt_ir.get("blockers")) if isinstance(item, dict)
    ]
    for blocker in upstream_blockers:
        _finding(
            findings,
            "blocking",
            str(blocker.get("code") or "upstream-blocker"),
            str(blocker.get("message") or "Upstream production contract is blocked."),
            source=str(blocker.get("source") or "prompt"),
            evidence=blocker.get("evidence") or {
                "approval_id": blocker.get("approval_id"),
                "actor": blocker.get("actor"),
                "comment": blocker.get("comment"),
            },
        )

    approvals = [
        item
        for item in _as_list(prompt_ir.get("approval_points"))
        if isinstance(item, dict) and item.get("required") is not False and item.get("id")
    ]
    approval_state = _as_dict(task.state.get("approval_state"))
    required_approval_ids = {str(item.get("id")) for item in approvals}
    pending_approval_ids = set(
        str(value)
        for value in _as_list(approval_state.get("pending_ids"))
    )
    if not approval_state:
        pending_approval_ids = set(required_approval_ids)
    approved_approval_ids = set(
        str(value)
        for value in _as_list(approval_state.get("approved_ids"))
    )
    rejected_approval_ids = set(
        str(value)
        for value in _as_list(approval_state.get("rejected_ids"))
    )
    changes_requested_ids = set(
        str(value)
        for value in _as_list(approval_state.get("changes_requested_ids"))
    )

    if upstream_blockers or rejected_approval_ids or changes_requested_ids:
        expected_prompt_status = "blocked"
    elif pending_approval_ids:
        expected_prompt_status = "review-required"
    else:
        expected_prompt_status = "ready"
    approval_gate_ok = prompt_status == expected_prompt_status
    _check(
        checks,
        "approval-state-gate",
        "approval",
        approval_gate_ok,
        "Prompt status matches persisted approval decisions." if approval_gate_ok else "Prompt status does not match persisted approval decisions.",
        evidence={
            "prompt_status": prompt_status,
            "expected_prompt_status": expected_prompt_status,
            "required_ids": sorted(required_approval_ids),
            "approved_ids": sorted(approved_approval_ids),
            "pending_ids": sorted(pending_approval_ids),
            "rejected_ids": sorted(rejected_approval_ids),
            "changes_requested_ids": sorted(changes_requested_ids),
        },
    )
    if not approval_gate_ok:
        _finding(
            findings,
            "blocking",
            "approval-state-mismatch",
            "Persisted approval decisions and Prompt execution state are inconsistent.",
            source="qa",
            evidence={
                "prompt_status": prompt_status,
                "expected_prompt_status": expected_prompt_status,
            },
        )

    approvals_by_id = {str(item.get("id")): item for item in approvals}
    for approval_id in sorted(pending_approval_ids):
        approval = approvals_by_id.get(approval_id, {})
        _finding(
            findings,
            "review",
            "approval-required",
            str(approval.get("question") or f"Approval {approval_id} is required."),
            source=str(approval.get("source") or "prompt"),
            evidence={"approval_id": approval_id},
        )

    artifacts = _artifact_outputs(task)
    artifact_review = {
        "status": "not-run",
        "artifact_count": len(artifacts),
        "reason": (
            "No generated visual Artifact is registered in this Task. Contract QA does not claim visual quality results."
            if not artifacts
            else "Artifact metadata is registered, but no semantic image inspection Adapter is available in alpha.16."
        ),
        "checks": [
            "theme consistency",
            "composition and hierarchy",
            "content correctness",
            "readability and usability",
            "resource output compliance",
            "cross-page consistency",
        ],
    }
    _finding(
        findings,
        "info",
        "artifact-review-not-run",
        artifact_review["reason"],
        source="qa",
        evidence={"artifact_count": len(artifacts)},
    )

    contract_failed = any(check["status"] == "failed" for check in checks)
    if contract_failed or upstream_blockers or prompt_status == "blocked":
        status = "blocked"
    elif prompt_status == "review-required" or pending_approval_ids:
        status = "review-required"
    else:
        status = "passed"

    export_reasons: list[str] = []
    if status != "passed":
        export_reasons.append(f"Semantic QA status is {status}.")
    if artifact_review["status"] != "passed":
        export_reasons.append("Visual Artifact review has not passed.")
    export_allowed = not export_reasons

    return {
        "schema_version": SEMANTIC_QA_SCHEMA_VERSION,
        "task_id": task.task_id,
        "project": task.project,
        "status": status,
        "scope": "contract-only" if not artifacts else "contract-and-artifact-metadata",
        "summary": {
            "check_count": len(checks),
            "passed_check_count": sum(check["status"] == "passed" for check in checks),
            "failed_check_count": sum(check["status"] == "failed" for check in checks),
            "finding_count": len(findings),
            "blocking_finding_count": sum(item["severity"] == "blocking" for item in findings),
            "review_finding_count": sum(item["severity"] == "review" for item in findings),
        },
        "checks": checks,
        "findings": findings,
        "artifact_review": artifact_review,
        "export_gate": {
            "allowed": export_allowed,
            "reasons": export_reasons,
        },
        "revision_request": {
            "required": status == "blocked",
            "finding_codes": sorted(
                {item["code"] for item in findings if item["severity"] == "blocking"}
            ),
            "next_step": (
                "Resolve blocking contract or approval findings before Provider execution."
                if status == "blocked"
                else "Complete required approvals before Provider execution."
                if status == "review-required"
                else "Generate and register Artifacts, then run visual Semantic QA."
            ),
        },
        "approval_summary": {
            "status": approval_state.get("status", "pending" if pending_approval_ids else "not-required"),
            "required_ids": sorted(required_approval_ids),
            "approved_ids": sorted(approved_approval_ids),
            "pending_ids": sorted(pending_approval_ids),
            "rejected_ids": sorted(rejected_approval_ids),
            "changes_requested_ids": sorted(changes_requested_ids),
        },
        "provenance": {
            "plan_output": "ui-production-plan",
            "director_output": "art-direction-review",
            "theme_output": "resolved-theme-contract",
            "resource_output": "resource-contract-bundle",
            "prompt_output": "model-neutral-prompt-ir",
        },
        "handoff": {
            "approval": "Persist approval decisions before enabling Prompt jobs.",
            "generation": "Execute only Prompt jobs whose executable flag remains true after approval.",
            "artifact_qa": "Register generated Artifacts and re-run QA with a visual inspection Adapter.",
            "export": "Export only when export_gate.allowed is true.",
        },
    }


def validate_semantic_qa_report(report: object) -> list[str]:
    if not isinstance(report, dict):
        return ["Semantic QA report must be an object"]
    errors: list[str] = []
    required = (
        "schema_version",
        "task_id",
        "project",
        "status",
        "scope",
        "summary",
        "checks",
        "findings",
        "artifact_review",
        "export_gate",
        "revision_request",
        "provenance",
        "handoff",
    )
    for field in required:
        if field not in report:
            errors.append(f"Missing Semantic QA field: {field}")
    if report.get("schema_version") != SEMANTIC_QA_SCHEMA_VERSION:
        errors.append(f"schema_version must be {SEMANTIC_QA_SCHEMA_VERSION}")
    if report.get("status") not in {"passed", "review-required", "blocked"}:
        errors.append("status must be passed, review-required, or blocked")
    for field in (
        "summary",
        "artifact_review",
        "export_gate",
        "revision_request",
        "provenance",
        "handoff",
    ):
        if field in report and not isinstance(report[field], dict):
            errors.append(f"{field} must be an object")
    if "approval_summary" in report and not isinstance(report["approval_summary"], dict):
        errors.append("approval_summary must be an object")
    for field in ("checks", "findings"):
        if field in report and not isinstance(report[field], list):
            errors.append(f"{field} must be a list")
    if isinstance(report.get("export_gate"), dict) and not isinstance(
        report["export_gate"].get("allowed"), bool
    ):
        errors.append("export_gate.allowed must be a boolean")
    for index, check in enumerate(report.get("checks", [])):
        if not isinstance(check, dict):
            errors.append(f"checks[{index}] must be an object")
            continue
        if check.get("status") not in {"passed", "failed"}:
            errors.append(f"checks[{index}].status must be passed or failed")
    for index, finding in enumerate(report.get("findings", [])):
        if not isinstance(finding, dict):
            errors.append(f"findings[{index}] must be an object")
            continue
        if finding.get("severity") not in {"blocking", "review", "warning", "info"}:
            errors.append(f"findings[{index}].severity is invalid")
        if not str(finding.get("code") or "").strip():
            errors.append(f"findings[{index}].code must be a non-empty string")
    return errors
