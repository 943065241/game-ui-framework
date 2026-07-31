from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from enum import Enum
from time import monotonic, sleep
from typing import Any, Callable, Mapping


ToolExecutionHandler = Callable[[Mapping[str, Any]], Mapping[str, Any] | None]
ToolHealthHandler = Callable[[Mapping[str, Any]], bool]


class ToolHealth(str, Enum):
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    MISCONFIGURED = "misconfigured"
    RATE_LIMITED = "rate_limited"


class ToolError(RuntimeError):
    retryable = False


class ToolConfigurationError(ToolError):
    pass


class ToolUnavailableError(ToolError):
    pass


class ToolTimeoutError(ToolError):
    retryable = True


class ToolRetryableError(ToolError):
    retryable = True


class ToolAuthenticationError(ToolError):
    pass


@dataclass(frozen=True)
class CapabilityRequirement:
    """Provider-neutral capability requested by a workflow."""

    capability_id: str
    required_features: tuple[str, ...] = ()
    optional_features: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolExecutionPolicy:
    timeout_seconds: float = 60.0
    max_attempts: int = 1
    retry_delay_seconds: float = 0.0
    allow_fallback: bool = True

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds cannot be negative")


@dataclass(frozen=True)
class ToolExecutionResult:
    adapter_id: str
    provider: str
    output: Mapping[str, Any]
    attempts: int
    duration_seconds: float


@dataclass(frozen=True)
class ToolAdapter:
    """Provider implementation registered behind one or more capabilities."""

    adapter_id: str
    provider: str
    capabilities: tuple[str, ...]
    features: tuple[str, ...] = ()
    configuration_schema: Mapping[str, Any] = field(default_factory=dict)
    configuration: Mapping[str, Any] = field(default_factory=dict, repr=False)
    priority: int = 100
    execute_handler: ToolExecutionHandler | None = field(default=None, repr=False, compare=False)
    health_handler: ToolHealthHandler | None = field(default=None, repr=False, compare=False)

    def supports(self, requirement: CapabilityRequirement) -> bool:
        return requirement.capability_id in self.capabilities and set(
            requirement.required_features
        ).issubset(self.features)

    def validate_configuration(self) -> None:
        required = tuple(self.configuration_schema.get("required", ()))
        missing = [name for name in required if not self.configuration.get(name)]
        if missing:
            raise ToolConfigurationError(
                f"Tool adapter {self.adapter_id} is missing configuration: {', '.join(missing)}"
            )

    def health(self) -> ToolHealth:
        try:
            self.validate_configuration()
        except ToolConfigurationError:
            return ToolHealth.MISCONFIGURED
        if self.execute_handler is None:
            return ToolHealth.UNAVAILABLE
        if self.health_handler is None:
            return ToolHealth.AVAILABLE
        try:
            return (
                ToolHealth.AVAILABLE
                if self.health_handler(dict(self.configuration))
                else ToolHealth.UNAVAILABLE
            )
        except Exception:
            return ToolHealth.UNAVAILABLE

    def execute(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        self.validate_configuration()
        if self.execute_handler is None:
            raise ToolUnavailableError(
                f"Tool adapter has no execution handler: {self.adapter_id}"
            )
        return dict(self.execute_handler(dict(arguments)) or {})


@dataclass
class ToolRegistry:
    """Shared, provider-neutral tool registry with retries and fallback."""

    adapters: dict[str, ToolAdapter] = field(default_factory=dict)

    def register(self, adapter: ToolAdapter) -> None:
        if adapter.adapter_id in self.adapters:
            raise ValueError(f"Tool adapter already registered: {adapter.adapter_id}")
        self.adapters[adapter.adapter_id] = adapter

    def unregister(self, adapter_id: str) -> ToolAdapter:
        try:
            return self.adapters.pop(adapter_id)
        except KeyError as exc:
            raise LookupError(f"Unknown tool adapter: {adapter_id}") from exc

    def health(self) -> dict[str, ToolHealth]:
        return {
            adapter_id: adapter.health()
            for adapter_id, adapter in self.adapters.items()
        }

    def resolve(
        self,
        requirement: CapabilityRequirement,
        *,
        available_only: bool = False,
    ) -> list[ToolAdapter]:
        """Return capability matches without changing legacy discovery semantics.

        Health and configuration are execution concerns. Callers that explicitly
        need only currently executable adapters may opt into ``available_only``.
        """
        matches = [
            adapter
            for adapter in self.adapters.values()
            if adapter.supports(requirement)
        ]
        if available_only:
            matches = [
                adapter
                for adapter in matches
                if adapter.health() is ToolHealth.AVAILABLE
            ]
        return sorted(matches, key=lambda adapter: (adapter.priority, adapter.adapter_id))

    def select(
        self,
        requirement: CapabilityRequirement,
        *,
        available_only: bool = False,
    ) -> ToolAdapter:
        matches = self.resolve(requirement, available_only=available_only)
        if not matches:
            qualifier = "available " if available_only else ""
            raise ToolUnavailableError(
                f"No {qualifier}tool adapter satisfies capability: "
                f"{requirement.capability_id}"
            )
        return matches[0]

    def execute(
        self,
        requirement: CapabilityRequirement,
        arguments: Mapping[str, Any] | None = None,
        policy: ToolExecutionPolicy | None = None,
    ) -> ToolExecutionResult:
        execution_policy = policy or ToolExecutionPolicy()
        candidates = self.resolve(requirement)
        if not candidates:
            raise ToolUnavailableError(
                f"No tool adapter satisfies capability: {requirement.capability_id}"
            )
        if not execution_policy.allow_fallback:
            candidates = candidates[:1]

        errors: list[str] = []
        for adapter in candidates:
            health = adapter.health()
            if health is not ToolHealth.AVAILABLE:
                errors.append(f"{adapter.adapter_id}: health={health.value}")
                continue

            started = monotonic()
            for attempt in range(1, execution_policy.max_attempts + 1):
                try:
                    output = self._execute_with_timeout(
                        adapter,
                        dict(arguments or {}),
                        execution_policy.timeout_seconds,
                    )
                    return ToolExecutionResult(
                        adapter_id=adapter.adapter_id,
                        provider=adapter.provider,
                        output=output,
                        attempts=attempt,
                        duration_seconds=monotonic() - started,
                    )
                except Exception as exc:
                    normalized = self._normalize_error(adapter, exc)
                    errors.append(f"{adapter.adapter_id}: {normalized}")
                    if (
                        not normalized.retryable
                        or attempt >= execution_policy.max_attempts
                    ):
                        break
                    if execution_policy.retry_delay_seconds:
                        sleep(execution_policy.retry_delay_seconds)

        raise ToolUnavailableError(
            "All tool adapters failed for capability "
            f"{requirement.capability_id}: {'; '.join(errors)}"
        )

    @staticmethod
    def _execute_with_timeout(
        adapter: ToolAdapter,
        arguments: Mapping[str, Any],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(adapter.execute, arguments)
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeoutError as exc:
            future.cancel()
            raise ToolTimeoutError(
                f"Tool adapter timed out after {timeout_seconds}s: {adapter.adapter_id}"
            ) from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    @staticmethod
    def _normalize_error(adapter: ToolAdapter, error: Exception) -> ToolError:
        if isinstance(error, ToolError):
            return error
        return ToolError(f"Tool adapter {adapter.adapter_id} failed: {error}")
