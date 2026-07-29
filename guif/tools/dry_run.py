from __future__ import annotations

import hashlib
import json
from typing import Any

from guif.tools.base import ToolAdapter, ToolManifest, ToolRequest, ToolResult


def _canonical_json(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


class DryRunToolAdapter(ToolAdapter):
    manifest = ToolManifest(
        tool_id="dry-run",
        name="Deterministic Dry-run",
        version="1.0",
        capabilities=frozenset(
            {
                "image-generation",
                "image-editing",
                "protected-region-editing",
                "transparent-output",
                "deterministic-dry-run",
            }
        ),
        execution_mode="direct",
        environments=("development", "ci", "production"),
        production_allowed=False,
        requires_host_support=False,
        requires_credentials=False,
        external_call=False,
        billable=False,
        description="Contract-testing Tool that creates a non-visual JSON receipt.",
    )
    requires_bound_references = False

    def execute(self, request: ToolRequest) -> ToolResult:
        job = request.job
        canvas = job.get("canvas") if isinstance(job.get("canvas"), dict) else {}
        output_contract = job.get("output_contract") if isinstance(job.get("output_contract"), dict) else {}
        width = output_contract.get("width") or canvas.get("width")
        height = output_contract.get("height") or canvas.get("height")
        payload = {
            "schema_version": 1,
            "mode": "deterministic-dry-run",
            "tool_request": request.to_dict(),
            "simulated_result": {
                "artifact_kind": job.get("artifact_kind"),
                "operation": job.get("operation"),
                "width": width,
                "height": height,
                "output_contract": output_contract,
                "message": "No external Tool was called and no visual pixels were generated.",
            },
        }
        content = _canonical_json(payload)
        digest = hashlib.sha256(content).hexdigest()
        return ToolResult(
            tool_id=self.tool_id,
            request_id=f"dryrun-{digest[:16]}",
            content=content,
            filename=f"{request.job_id}.dry-run.json",
            mime_type="application/vnd.guif.dry-run+json",
            width=int(width) if isinstance(width, int) and width > 0 else None,
            height=int(height) if isinstance(height, int) and height > 0 else None,
            simulation=True,
            visual=False,
            metadata={
                "deterministic_sha256": digest,
                "billable": False,
                "external_call_performed": False,
                "explicit_selection_required_in_production": True,
            },
        )
