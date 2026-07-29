from __future__ import annotations

from pathlib import Path
from typing import Any

from guif.runtime.host_loop import Runtime as HostLoopRuntime


class Runtime(HostLoopRuntime):
    """GUIF Runtime with a conversation-first facade entry point."""

    def list_tasks(self, project: str) -> tuple[dict[str, Any], ...]:
        """Compatibility-friendly task listing used by conversation recovery."""

        return tuple(dict(item) for item in self.list_runs(project))

    def conversation_workflow(
        self,
        *,
        bearer_token: str | None = None,
        data_root: Path | None = None,
    ) -> Any:
        from guif.conversation_workflow import ConversationWorkflowService

        return ConversationWorkflowService(
            self.workspace,
            runtime=self,
            bearer_token=bearer_token,
            data_root=data_root,
        )


__all__ = ["Runtime"]
