from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from guif.runtime import Runtime

ImageExecutor = Callable[[dict[str, Any], tuple[dict[str, Any], ...]], dict[str, Any]]
VisualInspector = Callable[[dict[str, Any], tuple[dict[str, Any], ...]], dict[str, Any]]


@dataclass(frozen=True)
class HostAttachmentContent:
    descriptor: dict[str, Any]
    content: bytes

    def to_dict(self) -> dict[str, Any]:
        return {
            "descriptor": dict(self.descriptor),
            "content": self.content,
        }


class ChatGPTHostLoop:
    """Embeddable Host loop; the Host supplies real image and vision callables."""

    def __init__(
        self,
        runtime: Runtime,
        *,
        bearer_token: str,
        claim_ttl_seconds: int = 300,
        lease_ttl_seconds: int = 300,
    ) -> None:
        self.runtime = runtime
        self.bearer_token = bearer_token
        self.claim_ttl_seconds = claim_ttl_seconds
        self.lease_ttl_seconds = lease_ttl_seconds
        self.runtime.authenticate_actor(
            bearer_token,
            required_capabilities=(
                "host-work:read",
                "host-work:claim",
                "host-work:complete",
                "task:lease",
            ),
        )

    def _attachments(
        self,
        project: str,
        work: dict[str, Any],
        claim_token: str,
    ) -> tuple[dict[str, Any], ...]:
        values: list[dict[str, Any]] = []
        for descriptor in work.get("attachments", []):
            if not isinstance(descriptor, dict) or not descriptor.get("attachment_id"):
                continue
            verified, content = self.runtime.get_host_work_attachment(
                project,
                str(work["work_id"]),
                str(descriptor["attachment_id"]),
                bearer_token=self.bearer_token,
                claim_token=claim_token,
            )
            values.append(
                HostAttachmentContent(
                    descriptor=verified,
                    content=content,
                ).to_dict()
            )
        return tuple(values)

    def run_once(
        self,
        project: str,
        *,
        task_id: str | None = None,
        image_executor: ImageExecutor | None = None,
        visual_inspector: VisualInspector | None = None,
        capabilities: Iterable[str] = (),
    ) -> dict[str, Any] | None:
        requested = tuple(str(item) for item in capabilities if str(item))
        requested_task_id = task_id.strip() if isinstance(task_id, str) else None
        candidates = self.runtime.list_host_work(
            project,
            capabilities=requested,
            statuses=("available",),
            limit=100,
        )
        work = next(
            (
                item
                for item in candidates
                if (requested_task_id is None or item.get("task_id") == requested_task_id)
                and (
                    (
                        item.get("kind") in {"image-generation", "image-editing"}
                        and image_executor is not None
                    )
                    or (
                        item.get("kind") == "visual-inspection"
                        and visual_inspector is not None
                    )
                )
            ),
            None,
        )
        if not isinstance(work, dict):
            return None

        selected_task_id = str(work["task_id"])
        etag = self.runtime.get_task_etag(project, selected_task_id)
        lease = self.runtime.acquire_task_lease(
            project,
            selected_task_id,
            bearer_token=self.bearer_token,
            expected_task_etag=etag,
            ttl_seconds=self.lease_ttl_seconds,
            purpose=f"chatgpt-host-work:{work['work_id']}",
        )
        try:
            claimed = self.runtime.claim_host_work(
                project,
                str(work["work_id"]),
                bearer_token=self.bearer_token,
                ttl_seconds=self.claim_ttl_seconds,
            )
        except Exception:
            self.runtime.release_task_lease(
                project,
                selected_task_id,
                bearer_token=self.bearer_token,
                lease_token=lease["lease_token"],
                reason="Host work claim failed",
            )
            raise

        claimed_work = claimed["work"]
        claim_token = claimed["claim_token"]
        attachments = self._attachments(project, claimed_work, claim_token)
        try:
            if claimed_work.get("kind") in {"image-generation", "image-editing"}:
                if image_executor is None:
                    raise RuntimeError("Image Host work requires an image_executor")
                result = image_executor(claimed_work, attachments)
                content = result.get("content")
                if not isinstance(content, bytes) or not content:
                    raise ValueError("image_executor must return non-empty bytes in result['content']")
                return self.runtime.complete_host_image_work(
                    project,
                    str(claimed_work["work_id"]),
                    bearer_token=self.bearer_token,
                    claim_token=claim_token,
                    lease_token=lease["lease_token"],
                    expected_task_etag=etag,
                    content=content,
                    filename=str(result.get("filename") or "generated-image.png"),
                    mime_type=str(result.get("mime_type") or "image/png"),
                    content_sha256=result.get("content_sha256"),
                    width=result.get("width"),
                    height=result.get("height"),
                    model_id=str(result.get("model_id") or "chatgpt-image"),
                    metadata=result.get("metadata") if isinstance(result.get("metadata"), dict) else None,
                    request_id=str(result.get("request_id") or claimed_work["work_id"]),
                )

            if visual_inspector is None:
                raise RuntimeError("Visual Host work requires a visual_inspector")
            result = visual_inspector(claimed_work, attachments)
            findings = result.get("findings", [])
            if not isinstance(findings, list):
                raise ValueError("visual_inspector result findings must be an array")
            return self.runtime.complete_host_visual_work(
                project,
                str(claimed_work["work_id"]),
                bearer_token=self.bearer_token,
                claim_token=claim_token,
                lease_token=lease["lease_token"],
                expected_task_etag=etag,
                status=str(result.get("status") or ""),
                findings=tuple(item for item in findings if isinstance(item, dict)),
                summary=str(result.get("summary") or ""),
                inspector_id=str(result.get("inspector_id") or "chatgpt-vision"),
                metadata=result.get("metadata") if isinstance(result.get("metadata"), dict) else None,
            )
        except Exception:
            current = self.runtime.get_task_lease(project, selected_task_id)
            if current.get("status") == "active":
                self.runtime.release_task_lease(
                    project,
                    selected_task_id,
                    bearer_token=self.bearer_token,
                    lease_token=lease["lease_token"],
                    reason="ChatGPT Host work execution failed",
                )
            raise


__all__ = [
    "ChatGPTHostLoop",
    "HostAttachmentContent",
    "ImageExecutor",
    "VisualInspector",
]
