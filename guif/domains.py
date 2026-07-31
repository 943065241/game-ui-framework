from __future__ import annotations

"""Compatibility surface for the original GUIF domain API.

The authoritative Domain Pack model and registry now live under ``aipg.domains``.
"""

from aipg.domains import (
    BUILTIN_DOMAIN_REGISTRY,
    DomainPackDefinition,
    domain_for_workflow,
    get_domain_pack,
    list_domain_packs,
)

DomainPack = DomainPackDefinition
BUILTIN_DOMAIN_PACKS = BUILTIN_DOMAIN_REGISTRY.domains

__all__ = [
    "BUILTIN_DOMAIN_PACKS",
    "DomainPack",
    "domain_for_workflow",
    "get_domain_pack",
    "list_domain_packs",
]
