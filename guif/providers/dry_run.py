from __future__ import annotations

import hashlib
import json
from typing import Any

from guif.providers.base import ExecutionRequest, ExecutionResult, ProviderAdapter


def _canonical_json(payload: Any) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


class DryRunProviderAdapter(ProviderAdapter):
    provider_id = "dry-run"
    capabilities = frozenset(
        {
            "image-generation",
            "image-editing",
            "protected-region-editing",
            "transparent-output",
            "deterministic-dry-run",
        }
    )
    requires_bound_references = False

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        job = request.job
        canvas = job.get("canvas") if isinstance(job.get("canvas"), dict) else {}
        output_contract = (
            job.get("output_contract") if isinstance(job.get("output_contract"), dict) else {}
        )
        width = output_contract.get("width") or canvas.get("width")
        height = output_contract.get("height") or canvas.get("height")
        payload = {
            "schema_version": 1,
            "mode": "deterministic-dry-run",
            "execution_request": request.to_dict(),
            "simulated_result": {
                "artifact_kind": job.get("artifact_kind"),
                "operation": job.get("operation"),
                "width": width,
                "height": height,
                "output_contract": output_contract,
                "message": "No external Provider was called and no visual pixels were generated.",
            },
        }
        content = _canonical_json(payload)
        digest = hashlib.sha256(content).hexdigest()
        return ExecutionResult(
            provider_id=self.provider_id,
            request_id=f"dryrun-{digest[:16]}",
            content=content,
            filename=f"{request.job_id}.dry-run.json",
            mime_type="application/vnd.guif.dry-run+json",
            width=int(width) if isinstance(width, int) and width > 0 else None,
            height=int(height) if isinstance(height, int) and height > 0 else None,
            model_id=None,
            simulation=True,
            visual=False,
            metadata={
                "deterministic_sha256": digest,
                "billable": False,
                "external_call_performed": False,
            },
        )
