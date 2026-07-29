from __future__ import annotations

import re
from typing import Any

from guif.theme import validate_theme_data

THEME_CONTRACT_SCHEMA_VERSION = 1

THEME_PRESETS: tuple[dict[str, Any], ...] = (
    {
        "id": "medieval-harbor",
        "terms": ("medieval harbor", "medieval port", "中世纪港口", "中世纪海港", "中世纪"),
        "manifest": {
            "name": "Medieval Harbor",
            "description": "Warm, readable medieval harbor UI direction with maritime trade motifs.",
            "palette": ["warm gold", "deep sea blue", "weathered wood brown", "muted parchment"],
            "materials": ["weathered wood", "aged brass", "parchment", "stone"],
            "lighting": "warm sunset or candlelit ambient lighting with controlled highlights",
            "must_include": ["harbor or maritime trade cues", "clear UI hierarchy", "warm metallic accents"],
            "avoid": ["pirate skulls", "casino styling", "dirty visual noise", "overexposed highlights"],
        },
    },
    {
        "id": "natural-trading",
        "terms": ("natural trading", "自然交易", "田园", "forest", "森林"),
        "manifest": {
            "name": "Natural Trading",
            "description": "Calm natural UI direction that keeps trading information clear and restrained.",
            "palette": ["deep ink green", "soft leaf green", "warm neutral", "muted amber"],
            "materials": ["matte glass", "wood", "paper", "soft metal"],
            "lighting": "soft low-contrast ambient lighting",
            "must_include": ["clear data hierarchy", "restrained natural motifs"],
            "avoid": ["casino styling", "large neon fields", "busy illustration behind data"],
        },
    },
    {
        "id": "soft-neon-party",
        "terms": ("soft neon", "party", "派对", "轻霓虹", "neon party"),
        "manifest": {
            "name": "Soft Neon Party",
            "description": "Friendly social party direction with controlled neon accents and dark readable surfaces.",
            "palette": ["deep violet", "soft cyan", "warm magenta", "dark navy"],
            "materials": ["matte glass", "soft plastic", "brushed metal"],
            "lighting": "low-key party lighting with localized neon accents",
            "must_include": ["friendly social energy", "clear interactive states"],
            "avoid": ["harsh cyberpunk glare", "casino styling", "excessive bloom"],
        },
    },
    {
        "id": "minimal-ui",
        "terms": ("minimal", "minimalist", "极简", "简洁", "clean ui"),
        "manifest": {
            "name": "Minimal UI",
            "description": "Minimal production direction focused on hierarchy, whitespace, and predictable interaction.",
            "palette": ["charcoal", "off white", "single accent color"],
            "materials": ["matte surface", "subtle glass"],
            "lighting": "neutral and low contrast",
            "must_include": ["strong hierarchy", "consistent spacing", "clear interaction states"],
            "avoid": ["decorative clutter", "unnecessary glow", "low-contrast text"],
        },
    },
)

NEGATIVE_MARKERS = (
    "avoid",
    "must not",
    "do not",
    "don't",
    "never",
    "cannot",
    "不要",
    "避免",
    "禁止",
    "不能",
)
POSITIVE_MARKERS = ("must", "keep", "should", "需要", "必须", "保持")


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "inferred-theme"


def _dedupe(values: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = re.sub(r"\s+", " ", str(value).strip())
        key = normalized.casefold()
        if not normalized or key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _infer_preset(requirement: str) -> dict[str, Any] | None:
    lowered = requirement.lower()
    for preset in THEME_PRESETS:
        if any(term.lower() in lowered for term in preset["terms"]):
            return preset
    return None


def _memory_constraints(direction: dict[str, Any]) -> tuple[list[str], list[str], list[str]]:
    visual = direction.get("visual_contract", {})
    values = visual.get("memory_constraints", []) if isinstance(visual, dict) else []
    positive: list[str] = []
    negative: list[str] = []
    sources: list[str] = []
    for item in values:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        source = str(item.get("source") or "memory")
        lowered = text.lower()
        if not text:
            continue
        if any(marker in lowered for marker in NEGATIVE_MARKERS):
            negative.append(text)
        elif any(marker in lowered for marker in POSITIVE_MARKERS):
            positive.append(text)
        else:
            positive.append(text)
        sources.append(source)
    return _dedupe(positive), _dedupe(negative), _dedupe(sources)


def build_theme_contract(task: Any) -> dict[str, Any]:
    plan = task.state.get("plan")
    direction = task.state.get("direction")
    if not isinstance(plan, dict):
        raise ValueError("Theme Agent requires task.state['plan'] from Planner")
    if not isinstance(direction, dict):
        raise ValueError("Theme Agent requires task.state['direction'] from Director")

    plan_theme = plan.get("theme", {}) if isinstance(plan.get("theme"), dict) else {}
    positive_memory, negative_memory, memory_sources = _memory_constraints(direction)
    source = "project-theme"
    approval_required = False
    confidence = 1.0

    if plan_theme.get("status") == "loaded":
        manifest = {
            "schema_version": 1,
            "name": str(plan_theme.get("name") or "Project Theme"),
            "description": str(plan_theme.get("description") or ""),
            "palette": list(plan_theme.get("palette", [])),
            "materials": list(plan_theme.get("materials", [])),
            "lighting": str(plan_theme.get("lighting") or ""),
            "must_include": list(plan_theme.get("must_include", [])),
            "avoid": list(plan_theme.get("avoid", [])),
        }
        manifest_id = _slug(manifest["name"])
        status = "ready"
    else:
        preset = _infer_preset(str(task.requirement))
        if preset is None:
            manifest = {
                "schema_version": 1,
                "name": "Unresolved Theme",
                "description": "Theme details must be supplied before visual production.",
                "palette": [],
                "materials": [],
                "lighting": "",
                "must_include": [],
                "avoid": [],
            }
            manifest_id = "unresolved-theme"
            source = "unresolved"
            approval_required = True
            confidence = 0.0
            status = "blocked"
        else:
            manifest = {"schema_version": 1, **dict(preset["manifest"])}
            manifest_id = str(preset["id"])
            source = "inferred-preset"
            approval_required = True
            confidence = 0.7
            status = "review-required"

    visual = direction.get("visual_contract", {})
    if isinstance(visual, dict):
        manifest["must_include"] = _dedupe(
            list(manifest.get("must_include", []))
            + list(visual.get("must_include", []))
            + positive_memory
        )
        manifest["avoid"] = _dedupe(
            list(manifest.get("avoid", []))
            + list(visual.get("avoid", []))
            + negative_memory
        )

    positive_keys = {value.casefold() for value in manifest["must_include"]}
    negative_keys = {value.casefold() for value in manifest["avoid"]}
    overlaps = sorted(positive_keys & negative_keys)
    conflicts = [
        {
            "severity": "blocking",
            "code": "theme-constraint-conflict",
            "message": f"The same constraint appears in must_include and avoid: {value}",
        }
        for value in overlaps
    ]
    if conflicts:
        status = "blocked"
        approval_required = True

    return {
        "schema_version": THEME_CONTRACT_SCHEMA_VERSION,
        "task_id": task.task_id,
        "project": task.project,
        "status": status,
        "source": source,
        "approval_required": approval_required,
        "confidence": confidence,
        "manifest_id": manifest_id,
        "manifest": manifest,
        "conflicts": conflicts,
        "provenance": {
            "plan_output": "ui-production-plan",
            "director_output": "art-direction-review",
            "memory_sources": memory_sources,
        },
        "handoff": {
            "resource": "Use this Theme contract when proposing production Resource manifests.",
            "prompt": "Preserve palette, materials, lighting, must_include, and avoid as explicit Prompt IR fields.",
            "qa": "Validate generated artifacts against every must_include and avoid constraint.",
        },
    }


def validate_theme_contract(contract: object) -> list[str]:
    if not isinstance(contract, dict):
        return ["Theme contract must be an object"]
    errors: list[str] = []
    required = (
        "schema_version",
        "task_id",
        "project",
        "status",
        "source",
        "approval_required",
        "confidence",
        "manifest_id",
        "manifest",
        "conflicts",
        "provenance",
        "handoff",
    )
    for field in required:
        if field not in contract:
            errors.append(f"Missing Theme contract field: {field}")
    if contract.get("schema_version") != THEME_CONTRACT_SCHEMA_VERSION:
        errors.append(f"schema_version must be {THEME_CONTRACT_SCHEMA_VERSION}")
    if contract.get("status") not in {"ready", "review-required", "blocked"}:
        errors.append("status must be ready, review-required, or blocked")
    if not isinstance(contract.get("approval_required"), bool):
        errors.append("approval_required must be a boolean")
    confidence = contract.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
        errors.append("confidence must be a number between 0 and 1")
    manifest = contract.get("manifest")
    if isinstance(manifest, dict):
        errors.extend(validate_theme_data(manifest))
    else:
        errors.append("manifest must be an object")
    for field in ("provenance", "handoff"):
        if field in contract and not isinstance(contract[field], dict):
            errors.append(f"{field} must be an object")
    if "conflicts" in contract and not isinstance(contract["conflicts"], list):
        errors.append("conflicts must be a list")
    return errors
