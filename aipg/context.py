from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class ContextMode(str, Enum):
    """Lifecycle mode for one production request."""

    PROJECT = "project"
    STANDALONE = "standalone"


@dataclass(frozen=True)
class ProductionRequest:
    domain_id: str
    workflow_id: str
    context_mode: ContextMode
    inputs: Mapping[str, Any]
    project_context_id: str | None = None

    def validate(self) -> None:
        if self.context_mode is ContextMode.PROJECT and not self.project_context_id:
            raise ValueError("Project context mode requires project_context_id")
        if self.context_mode is ContextMode.STANDALONE and self.project_context_id:
            raise ValueError("Standalone mode cannot bind a project_context_id")
