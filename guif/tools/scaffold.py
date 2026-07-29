from __future__ import annotations

import json
import re
from pathlib import Path

TOOL_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]{1,63}$")


def create_tool_scaffold(
    workspace: Path,
    tool_id: str,
    capabilities: tuple[str, ...],
    *,
    execution_mode: str = "external-callback",
) -> Path:
    normalized = tool_id.strip()
    if not TOOL_ID_PATTERN.fullmatch(normalized):
        raise ValueError("Tool ID must match ^[a-z][a-z0-9-]{1,63}$")
    cleaned = tuple(sorted({value.strip() for value in capabilities if value.strip()}))
    if not cleaned:
        raise ValueError("At least one Tool capability is required")
    if execution_mode not in {"direct", "external-callback"}:
        raise ValueError("execution_mode must be direct or external-callback")

    root = workspace / "tools" / normalized
    if root.exists():
        raise FileExistsError(f"Tool scaffold already exists: {root}")
    (root / "tests").mkdir(parents=True)
    manifest = {
        "schema_version": 1,
        "id": normalized,
        "name": normalized.replace("-", " ").title(),
        "version": "0.1.0",
        "status": "adapter-required",
        "capabilities": list(cleaned),
        "execution_mode": execution_mode,
        "input_contract": "prompt-ir-job-v1",
        "output_contract": "artifact-submission-v1",
        "configuration": {
            "requires_credentials": False,
            "requires_host_support": execution_mode == "external-callback",
        },
        "implementation_ready": False,
    }
    (root / "tool.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    class_name = "".join(part.title() for part in normalized.split("-")) + "ToolAdapter"
    (root / "adapter.py").write_text(
        "from guif.tools import ToolAdapter, ToolManifest\n\n\n"
        f"class {class_name}(ToolAdapter):\n"
        "    manifest = ToolManifest(\n"
        f"        tool_id={normalized!r},\n"
        f"        name={manifest['name']!r},\n"
        "        version='0.1.0',\n"
        f"        capabilities=frozenset({cleaned!r}),\n"
        f"        execution_mode={execution_mode!r},\n"
        "    )\n\n"
        "    # Implement prepare() for external-callback or execute() for direct mode.\n",
        encoding="utf-8",
    )
    (root / "config.schema.json").write_text(
        json.dumps(
            {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object",
                "additionalProperties": True,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_contract.py").write_text(
        "def test_adapter_contract_is_not_implemented_yet():\n"
        "    # Replace with manifest, capability, health, input, output, error, timeout,\n"
        "    # cancellation, credential-isolation, and idempotency contract tests.\n"
        "    assert True\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text(
        f"# {manifest['name']}\n\n"
        "This scaffold is not registered or production-ready. Implement the adapter,\n"
        "add contract tests, run a health check, and explicitly register it before use.\n",
        encoding="utf-8",
    )
    return root
