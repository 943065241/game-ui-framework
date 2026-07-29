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
    """Return GUIF's private data root, deliberately outside framework Git."""

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

    def plans(self, project: str) -> Path:
        return self.root / "plans" / project

    @property
    def host_credentials(self) -> Path:
        return self.root / "host-credentials"

    @property
    def host_work(self) -> Path:
        return self.root / "host-work"

    @property
    def operation_audit(self) -> Path:
        return self.root / "operation-audit"

    @property
    def operation_ledger(self) -> Path:
        return self.root / "operation-ledger"

    @property
    def gateway_requests(self) -> Path:
        return self.root / "gateway-requests"

    @property
    def migrations(self) -> Path:
        return self.root / "migrations"

    @property
    def privacy_reports(self) -> Path:
        return self.root / "privacy-reports"


__all__ = ["PrivateDataLayout", "default_private_data_root"]
