from __future__ import annotations

from typing import Any

from guif.upgrade_assurance import BETA_RELEASE, SUPPORTED_ALPHA_SOURCES

SUPPORT_POLICY_VERSION = 1


def support_contract() -> dict[str, Any]:
    """Return GUIF's beta support and deprecation policy.

    This is a product contract, not a service-level agreement. Dates are
    intentionally relative to release/supersession events so the repository
    does not silently promise unattended calendar operations.
    """

    return {
        "schema_version": SUPPORT_POLICY_VERSION,
        "release": BETA_RELEASE,
        "channel": "beta",
        "service_level_agreement": None,
        "supported_upgrade_sources": list(SUPPORTED_ALPHA_SOURCES),
        "support_window": {
            "current_beta": "supported until superseded by a newer beta",
            "previous_beta_security_fixes": "30 days after supersession when a safe patch is practical",
            "frozen_public_api": "preserved through beta.2 under public API version 1",
        },
        "security_reporting": {
            "public_issue_for_secrets": False,
            "guidance": "Do not post credentials, private Theme content, images, or backup archives in public issues.",
        },
        "deprecation": {
            "breaking_change_requires_new_public_api_version": True,
            "migration_path_required": True,
            "silent_private_schema_mutation_allowed": False,
        },
        "out_of_scope": [
            "third-party Host or Tool availability",
            "external encryption tool correctness or key custody",
            "distributed consensus for file-backed leases",
            "internet-edge reverse proxy operation",
            "release signing or third-party supply-chain attestation",
        ],
    }


__all__ = ["SUPPORT_POLICY_VERSION", "support_contract"]
