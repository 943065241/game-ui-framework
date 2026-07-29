from __future__ import annotations

from typing import Any

from guif.resource import validate_resource_data

RESOURCE_BUNDLE_SCHEMA_VERSION = 1


def _context_value(context: Any, name: str, default: Any) -> Any:
    if hasattr(context, name):
        return getattr(context, name)
    if isinstance(context, dict):
        return context.get(name, default)
    return default


def _even(value: float, *, minimum: int = 2) -> int:
    rounded = max(minimum, int(round(value)))
    return rounded if rounded % 2 == 0 else rounded + 1


def _propose_dimensions(
    resource_id: str,
    resource_type: str,
    width: int | None,
    height: int | None,
    canvas_width: int | None,
    canvas_height: int | None,
) -> tuple[int | None, int | None, str]:
    if isinstance(width, int) and width > 0 and isinstance(height, int) and height > 0:
        return width, height, "plan"
    if not canvas_width or not canvas_height:
        return None, None, "unresolved"
    if resource_type == "background":
        return canvas_width, canvas_height, "canvas"
    if resource_type == "button":
        proposed_width = _even(canvas_width * 0.2444, minimum=160)
        proposed_width = min(proposed_width, 512)
        return proposed_width, _even(proposed_width * 0.5076, minimum=64), "layout-proposal"
    if resource_type == "icon":
        side = min(256, _even(min(canvas_width, canvas_height) * 0.1185, minimum=64))
        return side, side, "layout-proposal"
    if resource_type == "panel":
        if "product-card" in resource_id:
            return (
                _even(canvas_width * 0.38, minimum=240),
                _even(canvas_height * 0.24, minimum=280),
                "layout-proposal",
            )
        if "main-panel" in resource_id:
            return (
                _even(canvas_width * 0.82, minimum=480),
                _even(canvas_height * 0.45, minimum=480),
                "layout-proposal",
            )
        return (
            _even(canvas_width * 0.8, minimum=320),
            _even(canvas_height * 0.4, minimum=320),
            "layout-proposal",
        )
    if resource_type == "sprite":
        return (
            _even(canvas_width * 0.45, minimum=256),
            _even(canvas_height * 0.45, minimum=256),
            "layout-proposal",
        )
    return (
        _even(canvas_width * 0.5, minimum=128),
        _even(canvas_height * 0.25, minimum=128),
        "layout-proposal",
    )


def _import_settings(target_engine: str, resource_type: str) -> dict[str, object]:
    texture_like = resource_type in {"sprite", "panel", "button", "icon", "background", "atlas"}
    if not texture_like:
        return {}
    if target_engine == "unity":
        return {"spriteMode": "Single", "mipmapEnabled": False}
    if target_engine == "godot":
        return {"filter": True, "mipmaps": False}
    if target_engine == "unreal":
        return {"textureGroup": "UI", "mipGenSettings": "NoMipmaps"}
    return {}


def _existing_manifest(resource: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": int(resource.get("schema_version", 1)),
        "id": resource.get("id"),
        "type": resource.get("type"),
        "width": resource.get("width"),
        "height": resource.get("height"),
        "format": resource.get("format"),
        "alpha_required": resource.get("alpha_required"),
        "target_engine": resource.get("target_engine"),
        "output_name": resource.get("output_name"),
        "source": resource.get("source"),
        "import_settings": dict(resource.get("import_settings", {})),
    }


def build_resource_contract_bundle(task: Any) -> dict[str, Any]:
    plan = task.state.get("plan")
    direction = task.state.get("direction")
    theme_contract = task.state.get("theme_contract")
    if not isinstance(plan, dict):
        raise ValueError("Resource Agent requires task.state['plan'] from Planner")
    if not isinstance(direction, dict):
        raise ValueError("Resource Agent requires task.state['direction'] from Director")
    if not isinstance(theme_contract, dict):
        raise ValueError("Resource Agent requires task.state['theme_contract'] from Theme Agent")

    page = plan.get("page", {}) if isinstance(plan.get("page"), dict) else {}
    canvas_width = page.get("width") if isinstance(page.get("width"), int) else None
    canvas_height = page.get("height") if isinstance(page.get("height"), int) else None
    target_engine = str(plan.get("target_engine") or "generic")
    context_resources = tuple(_context_value(task.context, "resources", ()))
    by_id = {str(resource.get("id") or ""): resource for resource in context_resources}

    direction_review = direction.get("resource_review", {})
    approved_decisions = (
        direction_review.get("approved_reuse", [])
        if isinstance(direction_review, dict)
        else []
    )
    review_decisions = (
        direction_review.get("requires_review", [])
        if isinstance(direction_review, dict)
        else []
    )

    approved_existing: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for decision in approved_decisions:
        if not isinstance(decision, dict):
            continue
        resource_id = str(decision.get("resource_id") or "")
        resource = by_id.get(resource_id)
        if resource is None:
            unresolved.append(
                {
                    "resource_id": resource_id,
                    "code": "approved-resource-missing",
                    "message": "Director approved reuse, but the Resource manifest is absent from Project Context.",
                }
            )
            continue
        approved_existing.append(
            {
                "resource_id": resource_id,
                "decision": "approved-reuse",
                "manifest": _existing_manifest(resource),
                "reasons": list(decision.get("reasons", [])),
            }
        )

    manifest_candidates: list[dict[str, Any]] = []
    for suggestion in plan.get("new_resources", []):
        if not isinstance(suggestion, dict):
            continue
        resource_id = str(suggestion.get("suggested_id") or "")
        if not resource_id or resource_id in by_id:
            continue
        resource_type = str(suggestion.get("type") or "other")
        width, height, dimension_source = _propose_dimensions(
            resource_id,
            resource_type,
            suggestion.get("width") if isinstance(suggestion.get("width"), int) else None,
            suggestion.get("height") if isinstance(suggestion.get("height"), int) else None,
            canvas_width,
            canvas_height,
        )
        if width is None or height is None:
            unresolved.append(
                {
                    "resource_id": resource_id,
                    "type": resource_type,
                    "code": "dimension-unresolved",
                    "message": "Canvas or component dimensions must be confirmed before a valid Resource manifest can be produced.",
                }
            )
            continue
        file_format = str(suggestion.get("format") or "png").lower()
        manifest = {
            "schema_version": 1,
            "id": resource_id,
            "type": resource_type,
            "width": width,
            "height": height,
            "format": file_format,
            "alpha_required": bool(suggestion.get("alpha_required", True)),
            "target_engine": target_engine,
            "output_name": f"{resource_id}.{file_format}",
            "source": None,
            "import_settings": _import_settings(target_engine, resource_type),
        }
        errors = validate_resource_data(manifest)
        if errors:
            raise ValueError(
                f"Invalid generated Resource manifest for {resource_id}: " + "; ".join(errors)
            )
        manifest_candidates.append(
            {
                "resource_id": resource_id,
                "status": "review-required",
                "dimension_source": dimension_source,
                "manifest": manifest,
            }
        )

    blocking_conflicts = []
    for conflict in direction.get("conflicts", []):
        if not isinstance(conflict, dict) or conflict.get("severity") != "blocking":
            continue
        code = str(conflict.get("code") or "")
        if code == "missing-theme" and theme_contract.get("status") != "blocked":
            continue
        if code == "missing-canvas" and canvas_width and canvas_height:
            continue
        blocking_conflicts.append(dict(conflict))

    if theme_contract.get("status") == "blocked":
        blocking_conflicts.append(
            {
                "severity": "blocking",
                "code": "theme-contract-blocked",
                "message": "Resource production cannot be approved while the Theme contract is blocked.",
            }
        )

    if blocking_conflicts or unresolved:
        status = "blocked"
    elif manifest_candidates or review_decisions or theme_contract.get("approval_required"):
        status = "review-required"
    else:
        status = "ready"

    approval_points = []
    if theme_contract.get("approval_required"):
        approval_points.append(
            {
                "id": "theme-contract",
                "question": "Approve the inferred or modified Theme contract before materializing Resources.",
                "required": True,
            }
        )
    if manifest_candidates:
        approval_points.append(
            {
                "id": "resource-manifests",
                "question": "Approve proposed dimensions and import settings before writing Resource manifests to the Project.",
                "required": True,
            }
        )
    if review_decisions:
        approval_points.append(
            {
                "id": "resource-reuse-review",
                "question": "Resolve Resource reuse candidates that the Director did not approve automatically.",
                "required": True,
            }
        )

    return {
        "schema_version": RESOURCE_BUNDLE_SCHEMA_VERSION,
        "task_id": task.task_id,
        "project": task.project,
        "status": status,
        "target_engine": target_engine,
        "theme_contract_status": theme_contract.get("status"),
        "approved_existing": approved_existing,
        "requires_reuse_review": list(review_decisions),
        "manifest_candidates": manifest_candidates,
        "unresolved": unresolved,
        "blocking_conflicts": blocking_conflicts,
        "approval_points": approval_points,
        "materialization_policy": {
            "mode": "review-before-write",
            "project_mutated": False,
            "message": "Runtime produces validated manifest candidates but does not write or overwrite Project Resource files without explicit approval.",
        },
        "handoff": {
            "prompt": "Use approved Resource dimensions, transparency requirements, and target Engine settings in Prompt IR.",
            "qa": "Validate every produced asset against its approved Resource manifest.",
            "export": "Export only Resources with approved manifests and passing QA results.",
        },
    }


def validate_resource_contract_bundle(bundle: object) -> list[str]:
    if not isinstance(bundle, dict):
        return ["Resource contract bundle must be an object"]
    errors: list[str] = []
    required = (
        "schema_version",
        "task_id",
        "project",
        "status",
        "target_engine",
        "theme_contract_status",
        "approved_existing",
        "requires_reuse_review",
        "manifest_candidates",
        "unresolved",
        "blocking_conflicts",
        "approval_points",
        "materialization_policy",
        "handoff",
    )
    for field in required:
        if field not in bundle:
            errors.append(f"Missing Resource bundle field: {field}")
    if bundle.get("schema_version") != RESOURCE_BUNDLE_SCHEMA_VERSION:
        errors.append(f"schema_version must be {RESOURCE_BUNDLE_SCHEMA_VERSION}")
    if bundle.get("status") not in {"ready", "review-required", "blocked"}:
        errors.append("status must be ready, review-required, or blocked")
    for field in (
        "approved_existing",
        "requires_reuse_review",
        "manifest_candidates",
        "unresolved",
        "blocking_conflicts",
        "approval_points",
    ):
        if field in bundle and not isinstance(bundle[field], list):
            errors.append(f"{field} must be a list")
    for field in ("materialization_policy", "handoff"):
        if field in bundle and not isinstance(bundle[field], dict):
            errors.append(f"{field} must be an object")
    candidates = bundle.get("manifest_candidates", [])
    if isinstance(candidates, list):
        for item in candidates:
            if not isinstance(item, dict) or not isinstance(item.get("manifest"), dict):
                errors.append("every manifest candidate must contain a manifest object")
                continue
            errors.extend(
                f"{item.get('resource_id', 'resource')}: {error}"
                for error in validate_resource_data(item["manifest"])
            )
    return errors
