from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path


def _workspace_key(workspace: Path) -> str:
    resolved = str(workspace.resolve())
    digest = hashlib.sha256(resolved.encode("utf-8")).hexdigest()[:12]
    name = workspace.resolve().name or "workspace"
    safe = "-".join(part for part in name.lower().replace("_", "-").split("-") if part)
    return f"{safe or 'workspace'}-{digest}"


def default_private_data_root(workspace: Path) -> Path:
    """Return GUIF's private data root, deliberately outside the framework repository.

    GUIF_DATA_HOME is authoritative when set. Otherwise data is placed in a hidden
    sibling directory of the workspace, not below the workspace itself. This keeps
    personal Theme data and Runtime evidence out of a public framework Git tree while
    remaining deterministic and isolated for temporary test workspaces.
    """

    configured = os.environ.get("GUIF_DATA_HOME")
    if configured and configured.strip():
        return Path(configured).expanduser().resolve() / _workspace_key(workspace)
    resolved = workspace.resolve()
    return resolved.parent / ".guif-data" / _workspace_key(resolved)


@dataclass(frozen=True)
class PrivateDataLayout:
    workspace: Path
    root_override: Path | None = None

    @property
    def root(self) -> Path:
        if self.root_override is not None:
            return self.root_override.expanduser().resolve()
        return default_private_data_root(self.workspace)

    @property
    def themes(self) -> Path:
        return self.root / "themes"

    @property
    def conversations(self) -> Path:
        return self.root / "conversation-theme-bindings"

    @property
    def project_bindings(self) -> Path:
        return self.root / "project-theme-bindings"

    def runs(self, project: str) -> Path:
        return self.root / "runs" / project

    @property
    def migrations(self) -> Path:
        return self.root / "migrations"


__all__ = ["PrivateDataLayout", "default_private_data_root"]
