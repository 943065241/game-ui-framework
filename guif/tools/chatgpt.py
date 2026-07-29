from __future__ import annotations

from guif.tools.base import HostProfile, ToolAdapter, ToolHandoff, ToolManifest, ToolRequest


class ChatGPTImageToolAdapter(ToolAdapter):
    manifest = ToolManifest(
        tool_id="chatgpt-image",
        name="ChatGPT Image Generation and Editing",
        version="1.0",
        capabilities=frozenset(
            {
                "image-generation",
                "image-editing",
                "protected-region-editing",
                "transparent-output",
            }
        ),
        execution_mode="external-callback",
        production_allowed=True,
        requires_host_support=True,
        supported_hosts=("chatgpt",),
        requires_credentials=False,
        external_call=True,
        billable=None,
        description=(
            "Default GUIF production bridge. ChatGPT receives a structured handoff, "
            "uses its configured image generation or editing capability, and submits "
            "the resulting file back to GUIF."
        ),
    )
    requires_bound_references = True

    def prepare(self, request: ToolRequest, host: HostProfile) -> ToolHandoff:
        job = request.job
        operation = str(job.get("operation") or "generate")
        return ToolHandoff.create(
            request,
            instructions={
                "host_action": (
                    "Call the ChatGPT image editing capability with the bound source references."
                    if operation == "edit"
                    else "Call the ChatGPT image generation capability."
                ),
                "operation": operation,
                "job": dict(job),
                "references": [dict(item) for item in request.references],
                "safety": [
                    "Do not discard negative constraints, output contracts, or acceptance criteria.",
                    "Do not report completion until a real result file is submitted to GUIF.",
                    "For edits, preserve the original Artifact and all protected regions.",
                ],
            },
            expected_result={
                "contract": "artifact-submission-v1",
                "required_fields": [
                    "handoff_id",
                    "file",
                    "mime_type",
                    "width",
                    "height",
                    "tool_id",
                ],
                "tool_id": self.tool_id,
                "visual": True,
                "simulation": False,
            },
        )


def build_default_chatgpt_host() -> HostProfile:
    return HostProfile(
        host_id="chatgpt",
        capabilities=frozenset(
            {
                "image-generation",
                "image-editing",
                "protected-region-editing",
                "transparent-output",
                "visual-inspection",
                "github-operation",
            }
        ),
        available_tools=frozenset({"chatgpt-image"}),
        metadata={
            "default": True,
            "execution": "host-managed",
            "description": "Default GUIF conversational and visual production host.",
        },
    )
