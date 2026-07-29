from __future__ import annotations

import hashlib
from typing import Any, Iterable

from guif.host_work import HostWorkError, HostWorkService
from guif.runtime.gateway import Runtime as GatewayRuntime


class Runtime(GatewayRuntime):
    """GUIF Runtime with claimable ChatGPT-first image and visual work."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.host_work = HostWorkService(
            self.workspace,
            store=self.store,
            runtime=self,
        )

    def list_host_work(
        self,
        project: str,
        *,
        capabilities: Iterable[str] = (),
        statuses: Iterable[str] = ("available", "claimed"),
        limit: int = 100,
    ) -> tuple[dict[str, Any], ...]:
        return self.host_work.list(
            project,
            capabilities=capabilities,
            statuses=statuses,
            limit=limit,
        )

    def get_host_work(self, project: str, work_id: str) -> dict[str, Any]:
        return self.host_work.get(project, work_id)

    def prepare_visual_inspection_work(
        self,
        project: str,
        task_id: str,
        artifact_id: str,
    ) -> dict[str, Any] | None:
        return self.host_work.prepare_visual_inspection(project, task_id, artifact_id)

    def claim_host_work(
        self,
        project: str,
        work_id: str,
        *,
        bearer_token: str,
        ttl_seconds: int = 300,
    ) -> dict[str, Any]:
        actor = self.authenticate_actor(
            bearer_token,
            required_capabilities=("host-work:claim",),
        )
        return self._ledgered(
            "host.work.claim",
            actor=actor.to_dict(),
            scope={"project": project, "work_id": work_id},
            request={"ttl_seconds": ttl_seconds},
            action=lambda: self.host_work.claim(
                project,
                work_id,
                actor,
                ttl_seconds=ttl_seconds,
            ),
            summarize=lambda value: {
                "work": value.get("work"),
                "secret_visible_once": value.get("secret_visible_once"),
            },
        )

    def get_host_work_attachment(
        self,
        project: str,
        work_id: str,
        attachment_id: str,
        *,
        bearer_token: str,
        claim_token: str,
    ) -> tuple[dict[str, Any], bytes]:
        actor = self.authenticate_actor(
            bearer_token,
            required_capabilities=("host-work:read",),
        )
        return self.host_work.attachment(
            project,
            work_id,
            actor,
            claim_token,
            attachment_id,
        )

    def complete_host_image_work(
        self,
        project: str,
        work_id: str,
        *,
        bearer_token: str,
        claim_token: str,
        lease_token: str,
        expected_task_etag: str,
        content: bytes,
        filename: str,
        mime_type: str,
        content_sha256: str | None = None,
        width: int | None = None,
        height: int | None = None,
        model_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        actor = self.authenticate_actor(
            bearer_token,
            required_capabilities=(
                "host-work:complete",
                "tool-result:submit",
            ),
        )
        work = self.host_work.validate_claim(
            project,
            work_id,
            actor,
            claim_token,
        )
        if work.get("kind") not in {"image-generation", "image-editing"}:
            raise HostWorkError("Host work item does not accept an image result")
        task_id = str(work.get("task_id") or "")
        handoff_id = str(work.get("handoff_id") or "")
        if not task_id or not handoff_id:
            raise HostWorkError("Image Host work is missing Task or Handoff identity")

        def execute() -> dict[str, Any]:
            task = super(Runtime, self).submit_authenticated_tool_result(
                project,
                task_id,
                handoff_id,
                bearer_token=bearer_token,
                lease_token=lease_token,
                expected_task_etag=expected_task_etag,
                content=content,
                filename=filename,
                mime_type=mime_type,
                content_sha256=content_sha256,
                width=width,
                height=height,
                model_id=model_id,
                tool_id=str(work.get("tool_id") or "") or None,
                metadata={
                    **dict(metadata or {}),
                    "host_work_id": work_id,
                    "submitted_via": "chatgpt-host-work-loop",
                },
                request_id=request_id or work_id,
            )
            callbacks = self.list_host_callbacks(project, task_id)
            callback = callbacks[-1] if callbacks else {}
            artifact_id = callback.get("artifact_id")
            receipt = {
                "schema_version": 1,
                "status": "completed",
                "work_id": work_id,
                "kind": work.get("kind"),
                "project": project,
                "task_id": task_id,
                "handoff_id": handoff_id,
                "callback_id": callback.get("callback_id"),
                "artifact_id": artifact_id,
                "content_sha256": hashlib.sha256(content).hexdigest(),
                "task_etag": self.get_task_etag(project, task_id),
            }
            self.host_work.mark_completed(project, work_id, result=receipt)
            visual_work = self.host_work.prepare_latest_visual_inspection(project, task_id)
            receipt["visual_work_id"] = (
                visual_work.get("work_id") if isinstance(visual_work, dict) else None
            )
            return receipt

        return self._ledgered(
            "host.work.image.complete",
            actor=actor.to_dict(),
            scope={
                "project": project,
                "task_id": task_id,
                "work_id": work_id,
                "handoff_id": handoff_id,
            },
            request={
                "expected_task_etag": expected_task_etag,
                "filename": filename,
                "mime_type": mime_type,
                "content_sha256": content_sha256,
                "content_length": len(content),
                "width": width,
                "height": height,
                "model_id": model_id,
                "request_id": request_id,
            },
            action=execute,
            summarize=lambda value: dict(value),
        )

    def complete_host_visual_work(
        self,
        project: str,
        work_id: str,
        *,
        bearer_token: str,
        claim_token: str,
        lease_token: str,
        expected_task_etag: str,
        status: str,
        findings: Iterable[dict[str, Any]] = (),
        summary: str = "",
        inspector_id: str = "chatgpt-vision",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        actor = self.authenticate_actor(
            bearer_token,
            required_capabilities=(
                "host-work:complete",
                "visual-inspection:submit",
            ),
        )
        work = self.host_work.validate_claim(
            project,
            work_id,
            actor,
            claim_token,
        )
        if work.get("kind") != "visual-inspection":
            raise HostWorkError("Host work item does not accept a Visual Inspection result")
        task_id = str(work.get("task_id") or "")
        lease = self.task_leases.validate(
            project,
            task_id,
            lease_token,
            actor,
            expected_task_etag=expected_task_etag,
        )
        finding_values = tuple(dict(item) for item in findings if isinstance(item, dict))

        def execute() -> dict[str, Any]:
            task, receipt = self.host_work.complete_visual(
                project,
                work_id,
                inspector_id=inspector_id,
                status=status,
                findings=finding_values,
                summary=summary,
                metadata={
                    **dict(metadata or {}),
                    "authenticated_actor": actor.to_dict(),
                    "host_work_id": work_id,
                },
            )
            self.task_leases.consume(
                project,
                task_id,
                lease_token,
                actor,
                operation_id=f"host-visual:{work_id}",
            )
            return {
                "schema_version": 1,
                "status": "completed",
                "work_id": work_id,
                "project": project,
                "task_id": task_id,
                "lease_id": lease.get("lease_id"),
                "task_status": task.status,
                "task_etag": self.get_task_etag(project, task_id),
                **receipt,
            }

        return self._ledgered(
            "host.work.visual.complete",
            actor=actor.to_dict(),
            scope={
                "project": project,
                "task_id": task_id,
                "work_id": work_id,
                "artifact_id": work.get("artifact_id"),
            },
            request={
                "expected_task_etag": expected_task_etag,
                "inspector_id": inspector_id,
                "status": status,
                "finding_count": len(finding_values),
            },
            action=execute,
            summarize=lambda value: dict(value),
        )

    def operation_summary(self, project: str, task_id: str) -> dict[str, Any]:
        payload = super().operation_summary(project, task_id)
        work = [
            item
            for item in self.list_host_work(
                project,
                statuses=("available", "claimed", "completed"),
                limit=1000,
            )
            if item.get("task_id") == task_id
        ]
        payload["host_work_count"] = len(work)
        payload["available_host_work_count"] = sum(
            1 for item in work if item.get("status") == "available"
        )
        payload["claimed_host_work_count"] = sum(
            1 for item in work if item.get("status") == "claimed"
        )
        payload["completed_host_work_count"] = sum(
            1 for item in work if item.get("status") == "completed"
        )
        payload["host_work"] = work
        return payload


__all__ = ["Runtime"]
