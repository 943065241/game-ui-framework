from __future__ import annotations

import re
from typing import Any

DIRECTION_SCHEMA_VERSION = 1
CONSTRAINT_MARKERS = (
    "必须",
    "不要",
    "避免",
    "保持",
    "需要",
    "禁止",
    "不能",
    "must",
    "should",
    "avoid",
    "keep",
    "do not",
    "don't",
    "never",
    "cannot",
)

COMPOSITION_TEMPLATES: dict[str, dict[str, tuple[str, ...]]] = {
    "shop": {
        "portrait": (
            "top status and currency area",
            "primary character or environment focal area",
            "product and offer content area",
            "primary purchase action area",
        ),
        "landscape": (
            "left identity or character focal area",
            "center environment and product presentation area",
            "right product and purchase action column",
        ),
    },
    "trade": {
        "portrait": (
            "market status header",
            "chart area",
            "orderbook and trade tape area",
            "position summary",
            "core trade action bar",
        ),
        "landscape": (
            "left chat column",
            "center chart and market information area",
            "right orderbook and trade tape area",
            "bottom core trade action bar",
        ),
    },
    "home": {
        "portrait": (
            "project identity and status header",
            "primary environment focal area",
            "feature-entry grid",
            "secondary status and social area",
        ),
        "landscape": (
            "left identity and status area",
            "center environment focal area",
            "right feature-entry area",
        ),
    },
    "login": {
        "portrait": ("brand focal area", "account input area", "primary login action", "legal and secondary actions"),
        "landscape": ("visual identity area", "account and login action panel"),
    },
    "ranking": {
        "portrait": ("ranking header", "top-rank focal area", "scrolling rank list", "player rank summary"),
        "landscape": ("ranking identity area", "top-rank focal area", "rank list and player summary"),
    },
    "laboratory": {
        "portrait": ("research status header", "primary research focus", "research options", "activation action"),
        "landscape": ("research identity area", "research tree or option area", "detail and activation panel"),
    },
    "generic": {
        "portrait": ("page header", "primary content area", "secondary content area", "primary action area"),
        "landscape": ("left supporting area", "center primary content area", "right action or detail area"),
    },
}


def _layout_key(orientation: str | None) -> str:
    return "landscape" if orientation == "landscape" else "portrait"


def _extract_memory_constraints(selection: dict[str, Any]) -> list[dict[str, str]]:
    constraints: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in selection.get("memory", []):
        if not isinstance(item, dict):
            continue
        record = item.get("record")
        if not isinstance(record, dict):
            continue
        source = str(record.get("path") or "memory")
        content = str(record.get("content") or "")
        for raw_line in content.splitlines():
            line = raw_line.strip().lstrip("-*").strip()
            lowered = line.lower()
            if not line or line.startswith("#") or line.startswith("Project:") or line.startswith("Recorded:"):
                continue
            if not any(marker in lowered for marker in CONSTRAINT_MARKERS):
                continue
            normalized = re.sub(r"\s+", " ", line)
            if normalized in seen:
                continue
            seen.add(normalized)
            constraints.append({"source": source, "text": normalized})
            if len(constraints) >= 12:
                return constraints
    return constraints


def _reuse_decisions(plan: dict[str, Any]) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for candidate in plan.get("reuse_candidates", []):
        if not isinstance(candidate, dict):
            continue
        score = int(candidate.get("score") or 0)
        if score >= 6:
            decision = "approve"
        elif score >= 3:
            decision = "review"
        else:
            decision = "weak-match"
        decisions.append(
            {
                "resource_id": candidate.get("id"),
                "decision": decision,
                "score": score,
                "reasons": list(candidate.get("reasons", [])),
            }
        )
    return decisions


def build_art_direction_review(task: Any) -> dict[str, Any]:
    plan = task.state.get("plan")
    if not isinstance(plan, dict):
        raise ValueError("Director requires task.state['plan'] from Planner")

    page = plan.get("page", {})
    page_type = str(page.get("type") or "generic")
    orientation = page.get("orientation")
    layout = _layout_key(orientation)
    composition = COMPOSITION_TEMPLATES.get(page_type, COMPOSITION_TEMPLATES["generic"])[layout]
    theme = plan.get("theme", {}) if isinstance(plan.get("theme"), dict) else {}
    selection = task.state.get("context_selection", {})
    if not isinstance(selection, dict):
        selection = {}

    memory_constraints = _extract_memory_constraints(selection)
    reuse_decisions = _reuse_decisions(plan)
    approved_reuse = [item for item in reuse_decisions if item["decision"] == "approve"]
    review_reuse = [item for item in reuse_decisions if item["decision"] != "approve"]

    conflicts: list[dict[str, str]] = []
    if theme.get("status") != "loaded":
        conflicts.append(
            {
                "severity": "blocking",
                "code": "missing-theme",
                "message": "An active Theme is required before final visual direction can be approved.",
            }
        )
    if not page.get("width") or not page.get("height"):
        conflicts.append(
            {
                "severity": "blocking",
                "code": "missing-canvas",
                "message": "Canvas width and height must be confirmed before production resource contracts are finalized.",
            }
        )
    if review_reuse:
        conflicts.append(
            {
                "severity": "review",
                "code": "unconfirmed-reuse",
                "message": f"{len(review_reuse)} Resource candidate(s) require visual or technical review before reuse.",
            }
        )

    approval_points = [
        {
            "id": "composition",
            "question": "Approve the proposed page zones and focal hierarchy.",
            "required": True,
        },
        {
            "id": "resource-reuse",
            "question": "Approve reuse decisions before creating replacement Resources.",
            "required": bool(reuse_decisions),
        },
    ]
    if plan.get("open_questions"):
        approval_points.append(
            {
                "id": "planner-open-questions",
                "question": "Resolve Planner open questions before Generation or Export.",
                "required": True,
            }
        )

    blocking = any(item["severity"] == "blocking" for item in conflicts)
    status = "blocked" if blocking else ("needs-review" if conflicts or plan.get("open_questions") else "ready")

    return {
        "schema_version": DIRECTION_SCHEMA_VERSION,
        "task_id": task.task_id,
        "project": task.project,
        "status": status,
        "page": {
            "type": page_type,
            "orientation": orientation,
            "width": page.get("width"),
            "height": page.get("height"),
            "layout_profile": f"{page_type}-{layout}",
        },
        "composition": {
            "zones": list(composition),
            "focal_order": list(composition[:3]),
            "interaction_rule": "Keep the primary action visually dominant while preserving clear separation between decorative and interactive regions.",
        },
        "visual_contract": {
            "theme_status": theme.get("status"),
            "theme_name": theme.get("name"),
            "palette": list(theme.get("palette", [])),
            "materials": list(theme.get("materials", [])),
            "lighting": theme.get("lighting", ""),
            "must_include": list(theme.get("must_include", [])),
            "avoid": list(theme.get("avoid", [])),
            "memory_constraints": memory_constraints,
        },
        "resource_review": {
            "approved_reuse": approved_reuse,
            "requires_review": review_reuse,
            "new_resources": list(plan.get("new_resources", [])),
        },
        "conflicts": conflicts,
        "approval_points": approval_points,
        "handoff": {
            "theme": "Apply the approved visual contract without introducing excluded motifs.",
            "resource": "Create contracts only for missing or rejected Resources and preserve approved reusable assets.",
            "prompt": "Preserve composition zones, hierarchy, Theme constraints, and memory-derived constraints in the Prompt IR.",
            "qa": [
                "Verify the approved composition zones and focal order.",
                "Verify Theme must-include and avoid constraints.",
                "Verify reused Resources remain visually coherent and technically compliant.",
                "Verify canvas dimensions and orientation against the Plan.",
            ],
        },
    }


def validate_art_direction_review(review: object) -> list[str]:
    if not isinstance(review, dict):
        return ["Art direction review must be an object"]
    errors: list[str] = []
    required = (
        "schema_version",
        "task_id",
        "project",
        "status",
        "page",
        "composition",
        "visual_contract",
        "resource_review",
        "conflicts",
        "approval_points",
        "handoff",
    )
    for field in required:
        if field not in review:
            errors.append(f"Missing art direction field: {field}")
    if review.get("schema_version") != DIRECTION_SCHEMA_VERSION:
        errors.append(f"schema_version must be {DIRECTION_SCHEMA_VERSION}")
    if review.get("status") not in {"ready", "needs-review", "blocked"}:
        errors.append("status must be ready, needs-review, or blocked")
    for field in ("page", "composition", "visual_contract", "resource_review", "handoff"):
        if field in review and not isinstance(review[field], dict):
            errors.append(f"{field} must be an object")
    for field in ("conflicts", "approval_points"):
        if field in review and not isinstance(review[field], list):
            errors.append(f"{field} must be a list")
    return errors
