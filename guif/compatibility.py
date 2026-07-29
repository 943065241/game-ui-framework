from __future__ import annotations

from typing import Any

MVP_API_VERSION = 1
MVP_RELEASE = "1.0.0-beta.2"
MVP_ORIGIN_RELEASE = "1.0.0-alpha.28"
MINIMUM_PYTHON = "3.10"
SUPPORTED_PRIVATE_SCHEMAS = {
    "theme-record": (1,),
    "theme-binding": (1,),
    "conversation-workflow": (1,),
    "host-work": (1,),
    "task": (2, 3),
}
FROZEN_USER_STAGES = (
    "theme-confirmation",
    "ready-for-request",
    "approval-required",
    "changes-required",
    "ready-to-produce",
    "image-production",
    "visual-review",
    "revision-approval-required",
    "revision-changes-required",
    "revision-ready",
    "tool-configuration-required",
    "ready-to-export",
    "completed",
    "recoverable-error",
    "cancelled",
    "attention-required",
)
FROZEN_CONVERSATION_ACTIONS = (
    "select-theme",
    "create-theme",
    "continue-unbound",
    "submit-request",
    "approve",
    "request-changes",
    "reject",
    "continue",
    "run-host",
    "export",
    "recover",
    "retry",
)


def compatibility_contract() -> dict[str, Any]:
    """Return the public beta compatibility promise.

    The existing ``release`` field remains the alpha.28 freeze origin for
    backward compatibility. ``current_release`` identifies the implementation
    currently honoring that contract.
    """

    return {
        "schema_version": 1,
        "release": MVP_ORIGIN_RELEASE,
        "current_release": MVP_RELEASE,
        "origin_release": MVP_ORIGIN_RELEASE,
        "channel": "beta",
        "public_api_version": MVP_API_VERSION,
        "minimum_python": MINIMUM_PYTHON,
        "supported_private_schemas": {
            key: list(value) for key, value in SUPPORTED_PRIVATE_SCHEMAS.items()
        },
        "conversation": {
            "stages": list(FROZEN_USER_STAGES),
            "actions": list(FROZEN_CONVERSATION_ACTIONS),
            "default_view_hides_runtime_identifiers": True,
        },
        "compatibility_policy": {
            "alpha_27_and_28_to_current_beta": "supported through explicit upgrade assurance",
            "beta_2_public_facade": "backward-compatible with the alpha.28 frozen conversation facade",
            "breaking_changes": "require a new public API version and an explicit migration path",
            "private_schema_changes": "must be detected before mutation and applied through a recorded migration",
            "legacy_provider_adapter": "preserved as explicit compatibility mode",
        },
        "privacy": {
            "theme_content_in_framework_git": False,
            "conversation_records_in_framework_git": False,
            "portable_backups_include_host_credentials": False,
            "portable_backups_include_ledger_signing_keys": False,
            "backup_protection_secrets_persisted": False,
        },
    }


__all__ = [
    "FROZEN_CONVERSATION_ACTIONS",
    "FROZEN_USER_STAGES",
    "MINIMUM_PYTHON",
    "MVP_API_VERSION",
    "MVP_ORIGIN_RELEASE",
    "MVP_RELEASE",
    "SUPPORTED_PRIVATE_SCHEMAS",
    "compatibility_contract",
]
