from __future__ import annotations

import json
import re
from typing import Any

ASCII_TOKEN_PATTERN = re.compile(r"[a-z0-9]+", re.IGNORECASE)
CJK_PATTERN = re.compile(r"[\u3400-\u9fff]+")
MEMORY_TYPE_WEIGHT = {
    "decisions": 4,
    "best-practices": 3,
    "lessons": 2,
    "mistakes": 2,
}


def _context_value(context: Any, name: str, default: Any) -> Any:
    if hasattr(context, name):
        return getattr(context, name)
    if isinstance(context, dict):
        return context.get(name, default)
    return default


def tokenize(text: str) -> set[str]:
    lowered = text.lower()
    tokens = {match.group(0) for match in ASCII_TOKEN_PATTERN.finditer(lowered)}
    for match in CJK_PATTERN.finditer(lowered):
        segment = match.group(0)
        tokens.add(segment)
        for size in (2, 3, 4):
            if len(segment) < size:
                continue
            tokens.update(segment[index : index + size] for index in range(len(segment) - size + 1))
    return {token for token in tokens if token}


def _serialize(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _score_record(query_tokens: set[str], text: str, *, base_score: int = 0) -> tuple[int, list[str]]:
    record_tokens = tokenize(text)
    matched = sorted(query_tokens & record_tokens)
    if not matched:
        return 0, []
    score = base_score + len(matched) * 3
    lowered = text.lower()
    for token in matched:
        if token in lowered:
            score += 1
    return score, matched


def _rank(
    values: tuple[dict[str, Any], ...],
    query_tokens: set[str],
    *,
    text_builder,
    base_builder,
    limit: int,
) -> tuple[list[dict[str, Any]], int]:
    ranked: list[tuple[int, str, dict[str, Any]]] = []
    for value in values:
        score, matched = _score_record(
            query_tokens,
            text_builder(value),
            base_score=base_builder(value),
        )
        if score <= 0:
            continue
        identity = str(value.get("id") or value.get("path") or value.get("name") or "")
        ranked.append(
            (
                score,
                identity,
                {
                    "score": score,
                    "matched_terms": matched,
                    "record": value,
                },
            )
        )
    ranked.sort(key=lambda item: (-item[0], item[1]))
    selected = [item[2] for item in ranked[:limit]]
    return selected, max(0, len(ranked) - len(selected))


def select_relevant_context(
    context: Any,
    requirement: str,
    *,
    memory_limit: int = 8,
    resource_limit: int = 20,
    workflow_limit: int = 8,
) -> dict[str, Any]:
    query_tokens = tokenize(requirement)
    active_theme = _context_value(context, "active_theme", None)
    if isinstance(active_theme, dict):
        query_tokens.update(tokenize(_serialize(active_theme)))

    memory_values = tuple(_context_value(context, "memory", ()))
    resource_values = tuple(_context_value(context, "resources", ()))
    workflow_values = tuple(_context_value(context, "workflows", ()))

    selected_memory, omitted_memory = _rank(
        memory_values,
        query_tokens,
        text_builder=lambda value: f"{value.get('path', '')} {value.get('content', '')}",
        base_builder=lambda value: MEMORY_TYPE_WEIGHT.get(str(value.get("type") or ""), 1),
        limit=memory_limit,
    )
    selected_resources, omitted_resources = _rank(
        resource_values,
        query_tokens,
        text_builder=lambda value: _serialize(value),
        base_builder=lambda value: 1 if value.get("type") in {"background", "panel", "button", "icon", "sprite"} else 0,
        limit=resource_limit,
    )
    selected_workflows, omitted_workflows = _rank(
        workflow_values,
        query_tokens,
        text_builder=lambda value: _serialize(value),
        base_builder=lambda value: 1,
        limit=workflow_limit,
    )

    return {
        "schema_version": 1,
        "query": requirement,
        "query_terms": sorted(query_tokens),
        "budgets": {
            "memory": memory_limit,
            "resources": resource_limit,
            "workflows": workflow_limit,
        },
        "memory": selected_memory,
        "resources": selected_resources,
        "workflows": selected_workflows,
        "omitted": {
            "memory": omitted_memory,
            "resources": omitted_resources,
            "workflows": omitted_workflows,
        },
        "totals": {
            "memory": len(memory_values),
            "resources": len(resource_values),
            "workflows": len(workflow_values),
        },
    }


def selected_records(selection: dict[str, Any], key: str) -> tuple[dict[str, Any], ...]:
    values = selection.get(key, [])
    if not isinstance(values, list):
        return ()
    records: list[dict[str, Any]] = []
    for item in values:
        if isinstance(item, dict) and isinstance(item.get("record"), dict):
            records.append(dict(item["record"]))
    return tuple(records)
