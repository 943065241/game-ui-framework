from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from guif.private_data import PrivateDataLayout

TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".yml", ".py", ".toml"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def audit_workspace_privacy(
    workspace: Path,
    *,
    sensitive_terms: Iterable[str] = (),
    persist: bool = True,
) -> dict[str, Any]:
    """Audit the current working tree for known private-data leak paths.

    This audit intentionally examines the current tree only. Git history, forks,
    caches, release archives, PR descriptions, and external clones require a
    separate repository-history incident response.
    """

    root = workspace.resolve()
    findings: list[dict[str, Any]] = []
    forbidden_globs = (
        "projects/*/themes/*.json",
        "projects/*/runs/*/task.json",
        "projects/*/runs/*/context.json",
        "projects/*/runs/*/outputs.json",
        "projects/*/plans/*.json",
        "**/*.private-theme.json",
    )
    for pattern in forbidden_globs:
        for path in root.glob(pattern):
            if path.is_file():
                findings.append(
                    {
                        "severity": "blocking",
                        "code": "private-data-in-project-tree",
                        "path": str(path.relative_to(root)),
                        "message": "Private Theme or Runtime data is present inside the framework/project working tree.",
                    }
                )

    projects = root / "projects"
    if projects.exists():
        for config_path in projects.glob("*/project.json"):
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(config, dict) and (
                config.get("current_theme") is not None
                or config.get("theme_binding") is not None
            ):
                findings.append(
                    {
                        "severity": "blocking",
                        "code": "theme-binding-in-project-config",
                        "path": str(config_path.relative_to(root)),
                        "message": "Theme binding must be stored in PrivateThemeStore, not project.json.",
                    }
                )

    normalized_terms = tuple(term.strip() for term in sensitive_terms if term.strip())
    if normalized_terms:
        ignored_roots = {".git", ".venv", "venv", "build", "dist", ".pytest_cache"}
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if any(part in ignored_roots for part in path.relative_to(root).parts):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            matches = [term for term in normalized_terms if term.casefold() in text.casefold()]
            if matches:
                findings.append(
                    {
                        "severity": "blocking",
                        "code": "sensitive-term-in-working-tree",
                        "path": str(path.relative_to(root)),
                        "matched_terms": matches,
                        "message": "A caller-supplied sensitive term appears in the current working tree.",
                    }
                )

    report = {
        "schema_version": 1,
        "workspace": str(root),
        "scope": "current-working-tree-only",
        "status": "passed" if not findings else "blocked",
        "findings": findings,
        "history_rewrite_required": bool(findings),
        "history_note": (
            "Removing current files does not remove prior Git commits, PR diffs, forks, caches, or clones. "
            "Review repository history separately before deciding on a destructive rewrite."
        ),
        "created_at": _now(),
    }
    if persist:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = PrivateDataLayout(workspace).privacy_reports / f"privacy-audit-{stamp}.json"
        _write_json(path, report)
        report["report_path"] = str(path)
    return report


__all__ = ["audit_workspace_privacy"]
