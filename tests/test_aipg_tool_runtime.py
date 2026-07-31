from __future__ import annotations

import time

import pytest

from aipg import (
    CapabilityRequirement,
    ToolAdapter,
    ToolExecutionPolicy,
    ToolHealth,
    ToolRegistry,
    ToolRetryableError,
    ToolUnavailableError,
)


def test_health_reports_misconfigured_and_available_adapters() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolAdapter(
            adapter_id="missing-key",
            provider="example",
            capabilities=("image-generation",),
            configuration_schema={"required": ("api_key",)},
            execute_handler=lambda arguments: {},
        )
    )
    registry.register(
        ToolAdapter(
            adapter_id="ready",
            provider="local",
            capabilities=("image-generation",),
            execute_handler=lambda arguments: {"ok": True},
        )
    )

    assert registry.health() == {
        "missing-key": ToolHealth.MISCONFIGURED,
        "ready": ToolHealth.AVAILABLE,
    }


def test_registry_retries_retryable_error() -> None:
    attempts = 0

    def execute(arguments):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise ToolRetryableError("temporary provider failure")
        return {"artifact_id": "artifact-1"}

    registry = ToolRegistry()
    registry.register(
        ToolAdapter(
            adapter_id="retrying",
            provider="provider-a",
            capabilities=("image-generation",),
            execute_handler=execute,
        )
    )

    result = registry.execute(
        CapabilityRequirement("image-generation"),
        policy=ToolExecutionPolicy(max_attempts=2),
    )

    assert result.output == {"artifact_id": "artifact-1"}
    assert result.attempts == 2


def test_registry_falls_back_to_next_adapter() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolAdapter(
            adapter_id="primary",
            provider="provider-a",
            capabilities=("image-editing",),
            priority=10,
            execute_handler=lambda arguments: (_ for _ in ()).throw(RuntimeError("down")),
        )
    )
    registry.register(
        ToolAdapter(
            adapter_id="fallback",
            provider="provider-b",
            capabilities=("image-editing",),
            priority=20,
            execute_handler=lambda arguments: {"artifact_id": "edited-1"},
        )
    )

    result = registry.execute(CapabilityRequirement("image-editing"))

    assert result.adapter_id == "fallback"
    assert result.provider == "provider-b"


def test_timeout_is_reported_after_all_candidates_fail() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolAdapter(
            adapter_id="slow",
            provider="provider-a",
            capabilities=("vision",),
            execute_handler=lambda arguments: time.sleep(0.05),
        )
    )

    with pytest.raises(ToolUnavailableError, match="timed out"):
        registry.execute(
            CapabilityRequirement("vision"),
            policy=ToolExecutionPolicy(timeout_seconds=0.001),
        )


def test_fallback_can_be_disabled() -> None:
    registry = ToolRegistry()
    registry.register(
        ToolAdapter(
            adapter_id="primary",
            provider="provider-a",
            capabilities=("export",),
            priority=1,
            execute_handler=lambda arguments: (_ for _ in ()).throw(RuntimeError("down")),
        )
    )
    registry.register(
        ToolAdapter(
            adapter_id="secondary",
            provider="provider-b",
            capabilities=("export",),
            priority=2,
            execute_handler=lambda arguments: {"ok": True},
        )
    )

    with pytest.raises(ToolUnavailableError):
        registry.execute(
            CapabilityRequirement("export"),
            policy=ToolExecutionPolicy(allow_fallback=False),
        )
