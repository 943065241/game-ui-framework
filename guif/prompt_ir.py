from __future__ import annotations

from typing import Any

from guif.resource import validate_resource_data

PROMPT_IR_SCHEMA_VERSION = 1
EDIT_TERMS = (
    "edit",
    "modify",
    "revise",
    "replace",
    "retouch",
    "adjust",
    "修改",
    "修图",
    "替换",
    "调整",
    "重绘",
)


def _dedupe(values: list[str]) -> list[str]:
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


def _operation(requirement: str) -> str:
    lowered = requirement.lower()
    return "edit" if any(term in lowered for term in EDIT_TERMS) else "generate"


def _approval_points(
    direction: dict[str, Any],
    theme_contract: dict[str, Any],
    resource_bundle: dict[str, Any],
) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    if theme_contract.get("approval_required"):
        values.append(
            {
                "id": "theme-contract",
                "question": "Approve the resolved Theme contract before a provider receives generation instructions.",
                "required": True,
                "source": "theme",
            }
        )
    for source, items in (
        ("director", direction.get("approval_points", [])),
        ("resource", resource_bundle.get("approval_points", [])),
    ):
        for item in items:
            if not isinstance(item, dict):
                continue
            values.append({**item, "source": source})

    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in values:
        identity = str(item.get("id") or item.get("question") or "")
        if not identity or identity in seen:
            continue
        seen.add(identity)
        deduped.append(item)
    return deduped


def _blockers(
    operation: str,
    direction: dict[str, Any],
    theme_contract: dict[str, Any],
    resource_bundle: dict[str, Any],
    references: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for item in theme_contract.get("conflicts", []):
        if isinstance(item, dict):
            values.append({**item, "source": "theme"})
    for key in ("blocking_conflicts", "unresolved"):
        for item in resource_bundle.get(key, []):
            if isinstance(item, dict):
                values.append({**item, "source": "resource"})
    for item in direction.get("conflicts", []):
        if isinstance(item, dict) and item.get("severity") == "blocking":
            values.append({**item, "source": "director"})
    if operation == "edit" and not references:
        values.append(
            {
                "severity": "blocking",
                "code": "missing-edit-reference",
                "message": "An edit operation requires at least one approved input reference.",
                "source": "prompt",
            }
        )

    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in values:
        key = (str(item.get("code") or ""), str(item.get("message") or ""))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def task_objective(plan: dict[str, Any]) -> str:
    page = plan.get("page", {}) if isinstance(plan.get("page"), dict) else {}
    return f"Produce a {page.get('type') or 'game UI'} deliverable that follows the approved production contracts."


def _global_contract(
    plan: dict[str, Any],
    direction: dict[str, Any],
    theme_contract: dict[str, Any],
) -> dict[str, Any]:
    page = plan.get("page", {}) if isinstance(plan.get("page"), dict) else {}
    composition = direction.get("composition", {}) if isinstance(direction.get("composition"), dict) else {}
    manifest = theme_contract.get("manifest", {}) if isinstance(theme_contract.get("manifest"), dict) else {}

    visual_instructions = _dedupe(
        [
            str(manifest.get("description") or ""),
            f"Palette: {', '.join(str(value) for value in manifest.get('palette', []))}",
            f"Materials: {', '.join(str(value) for value in manifest.get('materials', []))}",
            f"Lighting: {manifest.get('lighting', '')}",
        ]
        + [f"Must include: {value}" for value in manifest.get("must_include", [])]
    )
    negative_constraints = _dedupe(
        [str(value) for value in manifest.get("avoid", [])]
        + [
            "Do not merge effect-image composition files with production asset files.",
            "Do not change approved reusable Resources unless the Task explicitly requests an edit.",
        ]
    )
    return {
        "objective": str(plan.get("objective") or task_objective(plan)),
        "page": {
            "type": page.get("type"),
            "orientation": page.get("orientation"),
            "width": page.get("width"),
            "height": page.get("height"),
        },
        "composition": {
            "zones": list(composition.get("zones", [])),
            "focal_order": list(composition.get("focal_order", [])),
            "interaction_rule": str(composition.get("interaction_rule") or ""),
        },
        "visual_instructions": visual_instructions,
        "negative_constraints": negative_constraints,
        "theme_manifest_id": theme_contract.get("manifest_id"),
    }


def _approved_references(resource_bundle: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for item in resource_bundle.get("approved_existing", []):
        if not isinstance(item, dict):
            continue
        manifest = item.get("manifest")
        if not isinstance(manifest, dict):
            continue
        values.append(
            {
                "resource_id": item.get("resource_id"),
                "role": "approved-reuse",
                "manifest": manifest,
                "reasons": list(item.get("reasons", [])),
            }
        )
    return values


def _effect_image_job(
    operation: str,
    plan: dict[str, Any],
    direction: dict[str, Any],
    global_contract: dict[str, Any],
    references: list[dict[str, Any]],
) -> dict[str, Any]:
    page = global_contract["page"]
    composition = global_contract["composition"]
    page_type = str(page.get("type") or "page")
    technical = [
        "Keep effect images separate from production assets.",
        "Preserve clear separation between decorative and interactive regions.",
    ]
    if operation == "edit":
        technical.append("Preserve all non-target pixels and geometry outside the approved edit region.")
    return {
        "id": f"{page_type}-effect-image",
        "artifact_kind": "effect-image",
        "operation": operation,
        "executable": False,
        "canvas": {
            "width": page.get("width"),
            "height": page.get("height"),
            "orientation": page.get("orientation"),
        },
        "instructions": {
            "objective": global_contract["objective"],
            "composition": [
                f"Use these page zones in order: {', '.join(str(value) for value in composition.get('zones', []))}.",
                f"Use this focal order: {', '.join(str(value) for value in composition.get('focal_order', []))}.",
                str(composition.get("interaction_rule") or ""),
            ],
            "visual": list(global_contract["visual_instructions"]),
            "content": [str(plan.get("requirement") or "")],
            "technical": technical,
        },
        "negative_constraints": list(global_contract["negative_constraints"]),
        "references": references,
        "output_contract": {
            "format": "png",
            "alpha_required": False,
            "separate_from_production_assets": True,
        },
        "acceptance_criteria": _dedupe(
            [str(value) for value in plan.get("qa_criteria", [])]
            + [str(value) for value in direction.get("handoff", {}).get("qa", [])]
        ),
    }


def _resource_jobs(
    resource_bundle: dict[str, Any],
    global_contract: dict[str, Any],
    references: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for item in resource_bundle.get("manifest_candidates", []):
        if not isinstance(item, dict) or not isinstance(item.get("manifest"), dict):
            continue
        manifest = dict(item["manifest"])
        resource_id = str(manifest.get("id") or item.get("resource_id") or "resource")
        technical = [
            f"Output exactly {manifest.get('width')}x{manifest.get('height')} pixels.",
            f"Use {manifest.get('format')} format and output name {manifest.get('output_name')}.",
            f"Target Engine contract: {manifest.get('target_engine')}.",
        ]
        if manifest.get("alpha_required"):
            technical.append("Use a transparent background and preserve clean alpha edges.")
        else:
            technical.append("A fully opaque background is permitted by the Resource contract.")
        jobs.append(
            {
                "id": resource_id,
                "artifact_kind": "production-asset",
                "operation": "generate",
                "executable": False,
                "canvas": {
                    "width": manifest.get("width"),
                    "height": manifest.get("height"),
                    "orientation": None,
                },
                "instructions": {
                    "objective": f"Create the production-ready {manifest.get('type')} Resource {resource_id}.",
                    "composition": [],
                    "visual": list(global_contract["visual_instructions"]),
                    "content": [
                        f"Match the approved {global_contract.get('theme_manifest_id') or 'Project'} Theme contract.",
                        "Remain visually coherent with approved reusable Resources.",
                    ],
                    "technical": technical,
                },
                "negative_constraints": _dedupe(
                    list(global_contract["negative_constraints"])
                    + [
                        "Do not include page-level mockup framing in a standalone production asset.",
                        "Do not change dimensions, file format, alpha requirements, or output naming.",
                    ]
                ),
                "references": references,
                "output_contract": manifest,
                "acceptance_criteria": [
                    "Pass Resource Manifest validation.",
                    "Pass dimension, format, alpha, and naming checks.",
                    "Match the resolved Theme contract and approved reuse set.",
                ],
                "provenance": {
                    "dimension_source": item.get("dimension_source"),
                    "resource_bundle": "resource-contract-bundle",
                },
            }
        )
    return jobs


def build_prompt_ir(task: Any) -> dict[str, Any]:
    plan = task.state.get("plan")
    direction = task.state.get("direction")
    theme_contract = task.state.get("theme_contract")
    resource_bundle = task.state.get("resource_contracts")
    if not isinstance(plan, dict):
        raise ValueError("Prompt Agent requires task.state['plan'] from Planner")
    if not isinstance(direction, dict):
        raise ValueError("Prompt Agent requires task.state['direction'] from Director")
    if not isinstance(theme_contract, dict):
        raise ValueError("Prompt Agent requires task.state['theme_contract'] from Theme Agent")
    if not isinstance(resource_bundle, dict):
        raise ValueError("Prompt Agent requires task.state['resource_contracts'] from Resource Agent")

    operation = _operation(str(task.requirement))
    references = _approved_references(resource_bundle)
    global_contract = _global_contract(plan, direction, theme_contract)
    blockers = _blockers(operation, direction, theme_contract, resource_bundle, references)
    approval_points = _approval_points(direction, theme_contract, resource_bundle)
    jobs = [
        _effect_image_job(operation, plan, direction, global_contract, references),
        *_resource_jobs(resource_bundle, global_contract, references),
    ]

    if blockers:
        status = "blocked"
    elif approval_points or theme_contract.get("status") == "review-required" or resource_bundle.get("status") == "review-required":
        status = "review-required"
    else:
        status = "ready"
    executable = status == "ready"
    for job in jobs:
        job["executable"] = executable

    return {
        "schema_version": PROMPT_IR_SCHEMA_VERSION,
        "task_id": task.task_id,
        "project": task.project,
        "status": status,
        "provider": {
            "mode": "model-neutral",
            "provider_id": None,
            "model_id": None,
            "selection": "agent-host-or-adapter",
            "must_preserve_fields": [
                "instructions",
                "negative_constraints",
                "references",
                "output_contract",
                "acceptance_criteria",
            ],
        },
        "global_contract": global_contract,
        "jobs": jobs,
        "approval_points": approval_points,
        "blockers": blockers,
        "capability_requirements": _dedupe(
            ["image-generation"]
            + (["image-editing", "protected-region-editing"] if operation == "edit" else [])
            + (["transparent-output"] if any(job.get("output_contract", {}).get("alpha_required") for job in jobs) else [])
        ),
        "provenance": {
            "plan_output": "ui-production-plan",
            "director_output": "art-direction-review",
            "theme_output": "resolved-theme-contract",
            "resource_output": "resource-contract-bundle",
            "context_selection_schema_version": task.state.get("context_selection", {}).get("schema_version"),
        },
        "handoff": {
            "generation": "A Provider Adapter may translate each executable job without discarding structured constraints or provenance.",
            "qa": "Validate each Artifact against its job acceptance criteria and output contract.",
            "export": "Export only production assets whose Resource contracts are approved and whose QA status passes.",
        },
    }


def validate_prompt_ir(prompt_ir: object) -> list[str]:
    if not isinstance(prompt_ir, dict):
        return ["Prompt IR must be an object"]
    errors: list[str] = []
    required = (
        "schema_version",
        "task_id",
        "project",
        "status",
        "provider",
        "global_contract",
        "jobs",
        "approval_points",
        "blockers",
        "capability_requirements",
        "provenance",
        "handoff",
    )
    for field in required:
        if field not in prompt_ir:
            errors.append(f"Missing Prompt IR field: {field}")
    if prompt_ir.get("schema_version") != PROMPT_IR_SCHEMA_VERSION:
        errors.append(f"schema_version must be {PROMPT_IR_SCHEMA_VERSION}")
    if prompt_ir.get("status") not in {"ready", "review-required", "blocked"}:
        errors.append("status must be ready, review-required, or blocked")
    for field in ("provider", "global_contract", "provenance", "handoff"):
        if field in prompt_ir and not isinstance(prompt_ir[field], dict):
            errors.append(f"{field} must be an object")
    for field in ("jobs", "approval_points", "blockers", "capability_requirements"):
        if field in prompt_ir and not isinstance(prompt_ir[field], list):
            errors.append(f"{field} must be a list")

    jobs = prompt_ir.get("jobs", [])
    seen: set[str] = set()
    if isinstance(jobs, list):
        for index, job in enumerate(jobs):
            if not isinstance(job, dict):
                errors.append(f"jobs[{index}] must be an object")
                continue
            for field in (
                "id",
                "artifact_kind",
                "operation",
                "executable",
                "canvas",
                "instructions",
                "negative_constraints",
                "references",
                "output_contract",
                "acceptance_criteria",
            ):
                if field not in job:
                    errors.append(f"jobs[{index}] missing field: {field}")
            job_id = str(job.get("id") or "")
            if not job_id:
                errors.append(f"jobs[{index}].id must be a non-empty string")
            elif job_id in seen:
                errors.append(f"duplicate job id: {job_id}")
            seen.add(job_id)
            if job.get("artifact_kind") not in {"effect-image", "production-asset"}:
                errors.append(f"jobs[{index}].artifact_kind is unsupported")
            if job.get("operation") not in {"generate", "edit"}:
                errors.append(f"jobs[{index}].operation must be generate or edit")
            if not isinstance(job.get("executable"), bool):
                errors.append(f"jobs[{index}].executable must be a boolean")
            for field in ("canvas", "instructions", "output_contract"):
                if field in job and not isinstance(job[field], dict):
                    errors.append(f"jobs[{index}].{field} must be an object")
            for field in ("negative_constraints", "references", "acceptance_criteria"):
                if field in job and not isinstance(job[field], list):
                    errors.append(f"jobs[{index}].{field} must be a list")
            if job.get("artifact_kind") == "production-asset" and isinstance(job.get("output_contract"), dict):
                errors.extend(
                    f"jobs[{index}].output_contract: {error}"
                    for error in validate_resource_data(job["output_contract"])
                )
    return errors
