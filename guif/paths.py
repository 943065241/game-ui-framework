from __future__ import annotations

from pathlib import Path


def project_root(workspace: Path, project: str) -> Path:
    """Return the root directory for a GUIF project."""
    return workspace / "projects" / project
