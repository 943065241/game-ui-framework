from __future__ import annotations

import re
from typing import Any

PLAN_SCHEMA_VERSION = 1

PAGE_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("shop", ("shop", "store", "商城", "商店")),
    ("trade", ("trade", "trading", "交易", "盘口", "k线", "orderbook")),
    ("home", ("home", "lobby", "主页", "首页", "大厅")),
    ("login", ("login", "sign in", "登录")),
    ("ranking", ("ranking", "leaderboard", "排行榜")),
    ("laboratory", ("laboratory", "research", "研究所", "实验室")),
)

RESOURCE_TEMPLATES: dict[str, tuple[tuple[str, str, bool], ...]] = {
    "shop": (
        ("shop-background", "background", False),
        ("shop-main-panel", "panel", True),
        ("currency-icon", "icon", True),
        ("product-card", "panel", True),
        ("purchase-button", "button", True),
    ),
    "trade": (
        ("trade-background", "background", False),
        ("chart-panel", "panel", True),
        ("orderbook-panel", "panel", True),
        ("trade-button-long", "button", True),
        ("trade-button-short", "button", True),
        ("trade-button-cancel", "button", True),
    ),
    "home": (
        ("home-background", "background", False),
        ("navigation-button", "button", True),
        ("status-panel", "panel", True),
    ),
    "login": (
        ("login-background", "background", False),
        ("game-logo", "sprite", True),
        ("login-button", "button", True),
    ),
    "ranking": (
        ("ranking-background", "background", False),
        ("ranking-panel", "panel", True),
        ("rank-row", "panel", True),
    ),
    "laboratory": (
        ("laboratory-background", "background", False),
        ("research-panel", "panel", True),
        ("research-button", "button", True),
    ),
    "generic": (
        ("page-background", "background", False),
        ("primary-panel", "panel", True),
        ("primary-button", "button", True),
    ),
}

PAGE_RESOURCE_HINTS: dict[str, tuple[str, ...]] = {
    "shop": ("shop", "store", "coin", "currency", "product", "card", "purchase", "button"),
    "trade": ("trade", "chart", "orderbook", "long", "short", "cancel", "button"),
    "home": ("home", "lobby", "navigation", "status", "button"),
    "login": ("login", "logo", "button", "background"),
    "ranking": ("ranking", "rank", "leaderboard", "row", "panel"),
    "laboratory": ("laboratory", "research", "lab", "button", "panel"),
    "generic": ("background", "panel", "button"),
}

DIMENSION_PATTERN = re.compile(r"(?<!\d)(\d{2,5})\s*[x×*]\s*(\d{2,5})(?!\d)", re.IGNORECASE)
TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _context_value(context: Any, name: str, default: Any) -> Any:
    if hasattr(context, name):
        return getattr(context, name)
    if isinstance(context, dict):
        return context.get(name, default)
    return default


def _detect_page_type(text: str) -> str:
    lowered = text.lower()
    for page_type, terms in PAGE_PATTERNS:
        if any(term in lowered for term in terms):
            return page_type
    return "generic"


def _detect_dimensions(text: str) -> tuple[int | None, int | None]:
    match = DIMENSION_PATTERN.search(text)
    if not match:
        return None, None
    return int(match.group(1)), int(match.group(2))


def _detect_orientation(text: str, width: int | None, height: int | None) -> str | None:
    lowered = text.lower()
    if any(term in lowered for term in ("landscape", "横屏", "横向")):
        return "landscape"
    if any(term in lowered for term in ("portrait", "竖屏", "竖向")):
        return "portrait"
    if width and height:
        if width > height:
            return "landscape"
        if height > width:
            return "portrait"
        return "square"
    return None


def _detect_target_engine(text: str, resources: tuple[dict[str, Any], ...]) -> str:
    lowered = text.lower()
    for engine in ("unity", "godot", "unreal"):
        if engine in lowered:
            return engine
    configured = {
        str(resource.get("target_engine"))
        for resource in resources
        if resource.get("target_engine") in {"unity", "godot", "unreal"}
    }
    return next(iter(configured)) if len(configured) == 1 else "generic"


def _resource_tokens(resource: dict[str, Any]) -> set[str]:
    resource_id = str(resource.get("id") or "")
    output_name = str(resource.get("output_name") or "")
    return {token.lower() for token in TOKEN_PATTERN.findall(f"{resource_id} {output_name}")}


def _reuse_candidates(
    requirement: str,
    page_type: str,
    resources: tuple[dict[str, Any], ...],
) -> list[dict[str, Any]]:
    requirement_tokens = {token.lower() for token in TOKEN_PATTERN.findall(requirement)}
    hints = set(PAGE_RESOURCE_HINTS[page_type])
    candidates: list[tuple[int, dict[str, Any]]] = []
    for resource in resources:
        tokens = _resource_tokens(resource)
        score = 0
        reasons: list[str] = []
        direct = tokens & requirement_tokens
        related = tokens & hints
        if direct:
            score += 3
            reasons.append("resource name matches requirement terms")
        if related:
            score += 2
            reasons.append("resource name is related to the detected page type")
        if resource.get("type") in {"background", "panel", "button", "icon", "sprite"}:
            score += 1
            reasons.append("resource type is reusable in UI composition")
        if score:
            candidates.append(
                (
                    score,
                    {
                        "id": resource.get("id"),
                        "type": resource.get("type"),
                        "width": resource.get("width"),
                        "height": resource.get("height"),
                        "format": resource.get("format"),
                        "target_engine": resource.get("target_engine"),
                        "score": score,
                        "reasons": reasons,
                    },
                )
            )
    candidates.sort(key=lambda item: (-item[0], str(item[1].get("id") or "")))
    return [candidate for _, candidate in candidates]


def _new_resources(
    page_type: str,
    width: int | None,
    height: int | None,
    resources: tuple[dict[str, Any], ...],
) -> list[dict[str, Any]]:
    existing_ids = {str(resource.get("id") or "") for resource in resources}
    items: list[dict[str, Any]] = []
    for resource_id, resource_type, alpha_required in RESOURCE_TEMPLATES[page_type]:
        if resource_id in existing_ids:
            continue
        is_background = resource_type == "background"
        items.append(
            {
                "suggested_id": resource_id,
                "type": resource_type,
                "width": width if is_background else None,
                "height": height if is_background else None,
                "format": "png",
                "alpha_required": alpha_required,
                "status": "dimension-required" if not is_background or not width or not height else "ready-for-contract",
            }
        )
    return items


def _theme_contract(active_theme: dict[str, Any] | None) -> dict[str, Any]:
    if not active_theme:
        return {
            "status": "missing",
            "name": None,
            "description": "",
            "palette": [],
            "materials": [],
            "lighting": "",
            "must_include": [],
            "avoid": [],
        }
    return {
        "status": "loaded",
        "name": active_theme.get("name"),
        "description": active_theme.get("description", ""),
        "palette": list(active_theme.get("palette", [])),
        "materials": list(active_theme.get("materials", [])),
        "lighting": active_theme.get("lighting", ""),
        "must_include": list(active_theme.get("must_include", [])),
        "avoid": list(active_theme.get("avoid", [])),
    }


def build_ui_production_plan(task: Any) -> dict[str, Any]:
    requirement = str(task.requirement).strip()
    context = task.context
    resources = tuple(_context_value(context, "resources", ()))
    memory = tuple(_context_value(context, "memory", ()))
    workflows = tuple(_context_value(context, "workflows", ()))
    active_theme = _context_value(context, "active_theme", None)

    page_type = _detect_page_type(requirement)
    width, height = _detect_dimensions(requirement)
    orientation = _detect_orientation(requirement, width, height)
    target_engine = _detect_target_engine(requirement, resources)
    theme = _theme_contract(active_theme)
    reuse = _reuse_candidates(requirement, page_type, resources)
    new_resources = _new_resources(page_type, width, height, resources)

    open_questions: list[str] = []
    if width is None or height is None:
        open_questions.append("Confirm the target canvas width and height.")
    if orientation is None:
        open_questions.append("Confirm portrait or landscape orientation.")
    if theme["status"] == "missing":
        open_questions.append("Select or create an active project theme.")
    if target_engine == "generic":
        open_questions.append("Confirm the target engine when engine-specific export is required.")

    risks: list[dict[str, str]] = []
    if not resources:
        risks.append({"level": "medium", "code": "no-resource-contracts", "message": "No production resource manifests are available for reuse analysis."})
    if theme["status"] == "missing":
        risks.append({"level": "high", "code": "missing-theme", "message": "Visual consistency cannot be evaluated against an active theme."})
    if new_resources:
        risks.append({"level": "medium", "code": "new-resources-required", "message": f"{len(new_resources)} production resource contracts still need to be created or confirmed."})

    deliverables = [
        {"type": "structured-plan", "required": True},
        {"type": "effect-image", "required": True},
        {"type": "production-assets", "required": True},
        {"type": "qa-report", "required": True},
        {"type": "engine-export", "required": target_engine != "generic", "target_engine": target_engine},
    ]

    execution_steps = [
        {"id": "plan", "agent": "planner", "depends_on": [], "action": "Confirm scope, resources, constraints, deliverables, risks, and open questions."},
        {"id": "direction", "agent": "director", "depends_on": ["plan"], "action": "Resolve composition, hierarchy, reuse decisions, and art-direction conflicts."},
        {"id": "theme", "agent": "theme", "depends_on": ["direction"], "action": "Apply the active theme contract and expose unresolved visual constraints."},
        {"id": "resources", "agent": "resource", "depends_on": ["theme"], "action": "Create or update resource manifests for reusable and missing assets."},
        {"id": "prompt", "agent": "prompt", "depends_on": ["resources"], "action": "Build model-neutral generation or editing instructions."},
        {"id": "qa", "agent": "qa", "depends_on": ["prompt"], "action": "Validate semantics, theme consistency, dimensions, naming, alpha, and protected regions."},
        {"id": "export", "agent": "export", "depends_on": ["qa"], "action": f"Export passing assets for {target_engine}."},
    ]

    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "task_id": task.task_id,
        "project": task.project,
        "requirement": requirement,
        "objective": f"Produce a {page_type} UI deliverable that conforms to project context and production contracts.",
        "page": {
            "type": page_type,
            "orientation": orientation,
            "width": width,
            "height": height,
        },
        "workflow": {
            "id": task.pipeline,
            "source": task.state.get("pipeline", {}).get("source"),
            "agents": list(task.state.get("pipeline", {}).get("agents", [])),
        },
        "target_engine": target_engine,
        "theme": theme,
        "reuse_candidates": reuse,
        "new_resources": new_resources,
        "constraints": {
            "positive": list(theme["must_include"]),
            "negative": list(theme["avoid"]),
            "technical": [
                "Use resource manifests as the source of truth for dimensions, format, alpha, naming, and target engine.",
                "Keep effect images separate from production assets.",
                "Preserve protected pixels during local edits.",
            ],
        },
        "deliverables": deliverables,
        "qa_criteria": [
            "Page composition and information hierarchy match the requirement.",
            "Visual output follows the active theme and avoids excluded motifs.",
            "Production assets pass dimension, format, alpha, and naming validation.",
            "Cross-page reusable assets remain visually and technically consistent.",
            "Export results are deterministic and traceable to source manifests.",
        ],
        "execution_steps": execution_steps,
        "risks": risks,
        "open_questions": open_questions,
        "context_summary": {
            "active_theme_loaded": active_theme is not None,
            "project_workflow_count": len(workflows),
            "resource_count": len(resources),
            "memory_count": len(memory),
        },
    }


def validate_ui_production_plan(plan: object) -> list[str]:
    if not isinstance(plan, dict):
        return ["Plan must be an object"]
    errors: list[str] = []
    required = (
        "schema_version",
        "task_id",
        "project",
        "requirement",
        "objective",
        "page",
        "workflow",
        "target_engine",
        "theme",
        "reuse_candidates",
        "new_resources",
        "constraints",
        "deliverables",
        "qa_criteria",
        "execution_steps",
        "risks",
        "open_questions",
        "context_summary",
    )
    for field in required:
        if field not in plan:
            errors.append(f"Missing plan field: {field}")
    if plan.get("schema_version") != PLAN_SCHEMA_VERSION:
        errors.append(f"schema_version must be {PLAN_SCHEMA_VERSION}")
    for field in ("task_id", "project", "requirement", "objective", "target_engine"):
        if field in plan and (not isinstance(plan[field], str) or not plan[field].strip()):
            errors.append(f"{field} must be a non-empty string")
    for field in ("reuse_candidates", "new_resources", "deliverables", "qa_criteria", "execution_steps", "risks", "open_questions"):
        if field in plan and not isinstance(plan[field], list):
            errors.append(f"{field} must be a list")
    for field in ("page", "workflow", "theme", "constraints", "context_summary"):
        if field in plan and not isinstance(plan[field], dict):
            errors.append(f"{field} must be an object")
    return errors
