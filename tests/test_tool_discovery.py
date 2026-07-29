from __future__ import annotations

import json
from pathlib import Path

from guif.core import init_project
from guif.runtime import Runtime
from guif.tools import (
    HostProfile,
    ToolAdapter,
    ToolManifest,
    ToolRegistry,
    ToolRequest,
    ToolResult,
)


class CredentialTool(ToolAdapter):
    manifest = ToolManifest(
        tool_id="credential-image",
        name="Credential Image Tool",
        version="1.0",
        capabilities=frozenset({"image-generation"}),
        execution_mode="direct",
        requires_credentials=True,
        credential_kind="api-key-reference",
        permissions=("invoke-remote-image-service",),
        data_scopes=("structured-prompt-job",),
        external_call=True,
        billable=True,
    )
    requires_bound_references = False

    def execute(self, request: ToolRequest) -> ToolResult:
        return ToolResult(
            tool_id=self.tool_id,
            request_id=request.execution_id,
            content=b"result",
            filename="result.bin",
            mime_type="application/octet-stream",
            simulation=False,
            visual=False,
        )


def test_default_host_and_tool_discovery_are_explicit(tmp_path: Path) -> None:
    init_project(tmp_path, "Demo")
    runtime = Runtime(tmp_path)

    host = runtime.discover_host()
    tools = {item["tool_id"]: item for item in runtime.discover_tools(project="Demo")}

    assert host["protocol"] == "guif-host-capability-discovery-v1"
    assert host["host"]["host_id"] == "chatgpt"
    assert "chatgpt-image" in host["available_tool_ids"]
    assert tools["chatgpt-image"]["status"] == "available"
    assert tools["chatgpt-image"]["states"] == ["registered", "available"]
    disclosure = tools["chatgpt-image"]["disclosure"]
    assert disclosure["external_call"] is True
    assert disclosure["cost"] == "unknown"
    assert "approved-project-reference-images" in disclosure["data_scopes"]


def test_workspace_catalog_exposes_installable_tool_without_installing_it(tmp_path: Path) -> None:
    root = init_project(tmp_path, "Demo")
    catalog_path = tmp_path / ".guif" / "tool-catalog.json"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text(
        json.dumps(
            {
                "tools": [
                    {
                        "tool_id": "catalog-image",
                        "name": "Catalog Image",
                        "version": "1.0",
                        "capabilities": ["image-generation"],
                        "install_method": "plugin-manager",
                        "source": "example-catalog",
                        "permissions": ["network-access"],
                        "data_scopes": ["prompt-job"],
                        "external_call": True,
                        "billable": True,
                        "requires_credentials": True,
                        "credential_kind": "api-key-reference"
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    runtime = Runtime(tmp_path)

    discovered = {item["tool_id"]: item for item in runtime.discover_tools(project="Demo")}
    request = runtime.request_tool_connection(
        "Demo",
        "image-generation",
        "catalog-image",
        requested_by="Reviewer",
    )
    decided = runtime.approve_tool_connection(
        "Demo",
        request["request_id"],
        actor="Reviewer",
        credential_ref="secret://catalog-image",
    )
    project = json.loads((root / "project.json").read_text(encoding="utf-8"))

    assert discovered["catalog-image"]["status"] == "installable"
    assert discovered["catalog-image"]["registered"] is False
    assert decided["status"] == "installation-required"
    assert project["execution"]["tools"]["image-generation"]["primary"] == "chatgpt-image"


def test_approved_available_tool_connection_binds_project_and_persists(tmp_path: Path) -> None:
    root = init_project(tmp_path, "Demo")
    runtime = Runtime(tmp_path)
    request = runtime.request_tool_connection(
        "Demo",
        "image-generation",
        "chatgpt-image",
        requested_by="ChatGPT Host",
        reason="Connect the default production image Tool.",
    )

    decided = runtime.approve_tool_connection(
        "Demo",
        request["request_id"],
        actor="Owner",
        comment="Permissions and data scope reviewed.",
    )
    project = json.loads((root / "project.json").read_text(encoding="utf-8"))
    persisted = json.loads((root / "tool-connections.json").read_text(encoding="utf-8"))

    assert decided["status"] == "connected"
    assert decided["credential"]["secret_stored_by_guif"] is False
    assert project["execution"]["tools"]["image-generation"]["primary"] == "chatgpt-image"
    assert persisted["requests"][0]["approval"]["actor"] == "Owner"


def test_credentials_are_references_and_never_stored_as_secrets(tmp_path: Path) -> None:
    root = init_project(tmp_path, "Demo")
    tool = CredentialTool()
    runtime = Runtime(
        tmp_path,
        tools=ToolRegistry((tool,)),
        host=HostProfile(host_id="cli", capabilities=frozenset()),
    )
    request = runtime.request_tool_connection(
        "Demo",
        "image-generation",
        tool.tool_id,
        requested_by="Owner",
    )

    waiting = runtime.approve_tool_connection(
        "Demo",
        request["request_id"],
        actor="Owner",
    )
    connected = runtime.approve_tool_connection(
        "Demo",
        request["request_id"],
        actor="Owner",
        credential_ref="env://CREDENTIAL_IMAGE_API_KEY",
    )
    state = json.loads((root / "tool-connections.json").read_text(encoding="utf-8"))

    assert waiting["status"] == "waiting-for-credentials"
    assert connected["status"] == "connected"
    assert connected["credential"]["reference"] == "env://CREDENTIAL_IMAGE_API_KEY"
    assert connected["credential"]["secret_stored_by_guif"] is False
    assert "CREDENTIAL_IMAGE_API_KEY" in json.dumps(state)
    assert "actual-secret-value" not in json.dumps(state)


def test_health_retry_is_persisted_and_contract_tests_have_no_side_effects(tmp_path: Path) -> None:
    init_project(tmp_path, "Demo")
    runtime = Runtime(tmp_path)

    retry = runtime.retry_tool_health("Demo", "chatgpt-image")
    report = runtime.run_tool_contract_tests("chatgpt-image")
    state = json.loads(
        (tmp_path / "projects" / "Demo" / "tool-connections.json").read_text(encoding="utf-8")
    )

    assert retry["attempt"] == 1
    assert retry["health"]["healthy"] is True
    assert state["health_checks"][0]["tool_id"] == "chatgpt-image"
    assert report["status"] == "passed"
    assert report["summary"]["external_call_performed"] is False
    assert report["summary"]["failed_count"] == 0
