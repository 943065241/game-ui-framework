from __future__ import annotations

from collections.abc import Iterable

from guif.providers.base import ProviderAdapter
from guif.providers.dry_run import DryRunProviderAdapter


class ProviderRegistry:
    def __init__(self, providers: Iterable[ProviderAdapter] = ()) -> None:
        self._providers: dict[str, ProviderAdapter] = {}
        for provider in providers:
            self.register(provider)

    def register(self, provider: ProviderAdapter) -> None:
        provider_id = str(provider.provider_id).strip()
        if not provider_id:
            raise ValueError("Provider adapter must define a non-empty provider_id")
        if provider_id in self._providers:
            raise ValueError(f"Provider already registered: {provider_id}")
        self._providers[provider_id] = provider

    def get(self, provider_id: str) -> ProviderAdapter:
        try:
            return self._providers[provider_id]
        except KeyError as exc:
            raise ValueError(f"Unknown Provider adapter: {provider_id}") from exc

    def describe(self) -> tuple[dict[str, object], ...]:
        return tuple(self._providers[key].describe() for key in sorted(self._providers))


def build_default_provider_registry() -> ProviderRegistry:
    return ProviderRegistry((DryRunProviderAdapter(),))
