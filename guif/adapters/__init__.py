from __future__ import annotations

from guif.adapters.base import EngineAdapter
from guif.adapters.generic import GenericAdapter
from guif.adapters.godot import GodotAdapter
from guif.adapters.unity import UnityAdapter
from guif.adapters.unreal import UnrealAdapter

_ADAPTERS: dict[str, type[EngineAdapter]] = {
    "generic": GenericAdapter,
    "unity": UnityAdapter,
    "godot": GodotAdapter,
    "unreal": UnrealAdapter,
}


def get_adapter(engine: str) -> EngineAdapter:
    try:
        adapter_type = _ADAPTERS[engine]
    except KeyError as exc:
        raise ValueError(f"Unsupported target engine: {engine}") from exc
    return adapter_type()


def supported_engines() -> tuple[str, ...]:
    return tuple(sorted(_ADAPTERS))
