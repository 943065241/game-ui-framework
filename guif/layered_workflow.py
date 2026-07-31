from __future__ import annotations

from copy import deepcopy
from typing import Any

LAYERED_COMPOSITION_SCHEMA_VERSION = 1
CREATIVE_FREEDOM_LEVELS = {"low", "medium", "high"}
LAYER_ROLES = {
    "background",
    "container",
    "frame",
    "content",
    "control",
    "icon",
    "text",
    "decoration",
    "effect",
    "foreground",
}


def _string_list(value: object, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{field} must contain non-empty strings")
    return [item.strip() for item in value]


def validate_layer_spec(layer: object) -> list[str]:
    if not isinstance(layer, dict):
        return ["Layer must be an object"]
    errors: list[str] = []
    for field in ("id", "name", "role", "z_index", "creative_freedom"):
        if field not in layer:
            errors.append(f"Missing layer field: {field}")
    for field in ("id", "name"):
        if field in layer and (
            not isinstance(layer[field], str) or not str(layer[field]).strip()
        ):
            errors.append(f"{field} must be a non-empty string")
    if layer.get("role") not in LAYER_ROLES:
        errors.append(f"role must be one of: {', '.join(sorted(LAYER_ROLES))}")
    if not isinstance(layer.get("z_index"), int):
        errors.append("z_index must be an integer")
    if layer.get("creative_freedom") not in CREATIVE_FREEDOM_LEVELS:
        errors.append("creative_freedom must be low, medium, or high")
    for field in ("hard_constraints", "soft_guidance"):
        value = layer.get(field, [])
        if not isinstance(value, list) or any(
            not isinstance(item, str) or not item.strip() for item in value
        ):
            errors.append(f"{field} must be a list of non-empty strings")
    return errors


def validate_layered_composition(record: object) -> list[str]:
    if not isinstance(record, dict):
        return ["Layered composition must be an object"]
    errors: list[str] = []
    required = (
        "schema_version",
        "workflow",
        "status",
        "master_reference",
        "master_policy",
        "layers",
        "current_layer_index",
        "approvals",
    )
    for field in required:
        if field not in record:
            errors.append(f"Missing composition field: {field}")
    if record.get("schema_version") != LAYERED_COMPOSITION_SCHEMA_VERSION:
        errors.append(
            f"schema_version must be {LAYERED_COMPOSITION_SCHEMA_VERSION}"
        )
    if record.get("workflow") != "master-guided-layer-creation":
        errors.append("workflow must be master-guided-layer-creation")
    if record.get("status") not in {
        "layer-plan-review-required",
        "layer-production",
        "recomposition-review-required",
        "ready-to-export",
    }:
        errors.append("unsupported composition status")
    if not isinstance(record.get("master_reference"), str) or not record.get(
        "master_reference"
    ):
        errors.append("master_reference must be a non-empty private reference")
    master_policy = record.get("master_policy")
    if not isinstance(master_policy, dict):
        errors.append("master_policy must be an object")
    elif master_policy.get("pixel_matching") is not False:
        errors.append("master_policy.pixel_matching must be false")
    layers = record.get("layers")
    if not isinstance(layers, list) or len(layers) < 2:
        errors.append("layers must contain at least two layers")
    else:
        ids: list[str] = []
        z_indices: list[int] = []
        for index, layer in enumerate(layers):
            errors.extend(
                f"layers[{index}]: {error}" for error in validate_layer_spec(layer)
            )
            if isinstance(layer, dict):
                ids.append(str(layer.get("id") or ""))
                if isinstance(layer.get("z_index"), int):
                    z_indices.append(layer["z_index"])
                if layer.get("status") not in {"pending", "active", "completed"}:
                    errors.append(f"layers[{index}]: unsupported status")
        if len(set(ids)) != len(ids):
            errors.append("layer ids must be unique")
        if len(set(z_indices)) != len(z_indices):
            errors.append("layer z_index values must be unique")
        if z_indices != sorted(z_indices):
            errors.append("layers must be ordered from bottom to top")
    return errors


def create_layered_composition(
    *,
    master_reference: str,
    theme_reference: str | None,
    layers: list[dict[str, Any]],
) -> dict[str, Any]:
    if not master_reference.strip():
        raise ValueError("master_reference must not be empty")
    prepared_layers: list[dict[str, Any]] = []
    for layer in sorted(deepcopy(layers), key=lambda item: item.get("z_index", 0)):
        errors = validate_layer_spec(layer)
        if errors:
            raise ValueError("Invalid layer: " + "; ".join(errors))
        layer["hard_constraints"] = _string_list(
            layer.get("hard_constraints", []), "hard_constraints"
        )
        layer["soft_guidance"] = _string_list(
            layer.get("soft_guidance", []), "soft_guidance"
        )
        layer.update(
            {
                "status": "pending",
                "artifact_id": None,
                "composite_artifact_id": None,
                "revision": 0,
            }
        )
        prepared_layers.append(layer)
    record: dict[str, Any] = {
        "schema_version": LAYERED_COMPOSITION_SCHEMA_VERSION,
        "workflow": "master-guided-layer-creation",
        "domain": "visual-production",
        "status": "layer-plan-review-required",
        "master_reference": master_reference,
        "theme_reference": theme_reference,
        "master_policy": {
            "role": "style-and-layout-guidance",
            "pixel_matching": False,
            "layout_anchors": "preserve",
            "style_intent": "preserve",
            "creative_interpretation": "allowed",
        },
        "creation_direction": "bottom-to-top",
        "layers": prepared_layers,
        "current_layer_index": 0,
        "approvals": {
            "layer_plan": "pending",
            "final_composition": "pending",
        },
    }
    errors = validate_layered_composition(record)
    if errors:
        raise ValueError("Invalid layered composition: " + "; ".join(errors))
    return record


def approve_layer_plan(record: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(record)
    errors = validate_layered_composition(result)
    if errors:
        raise ValueError("Invalid layered composition: " + "; ".join(errors))
    if result["status"] != "layer-plan-review-required":
        raise ValueError("Layer plan is not awaiting approval")
    result["approvals"]["layer_plan"] = "approved"
    result["status"] = "layer-production"
    result["layers"][0]["status"] = "active"
    return result


def current_layer_contract(record: dict[str, Any]) -> dict[str, Any]:
    errors = validate_layered_composition(record)
    if errors:
        raise ValueError("Invalid layered composition: " + "; ".join(errors))
    if record["status"] != "layer-production":
        raise ValueError("Composition is not producing a layer")
    layer = record["layers"][record["current_layer_index"]]
    if layer["status"] != "active":
        raise ValueError("Current layer is not active")
    completed = [
        item
        for item in record["layers"][: record["current_layer_index"]]
        if item["status"] == "completed"
    ]
    return {
        "schema_version": 1,
        "workflow": record["workflow"],
        "master_reference": record["master_reference"],
        "theme_reference": record.get("theme_reference"),
        "master_policy": deepcopy(record["master_policy"]),
        "current_composite_artifact_id": (
            completed[-1]["composite_artifact_id"] if completed else None
        ),
        "layer": deepcopy(layer),
        "future_layer_roles": [
            item["role"]
            for item in record["layers"][record["current_layer_index"] + 1 :]
        ],
        "output_contract": {
            "transparent_background": layer["role"] != "background",
            "preserve_canvas_coordinates": True,
            "exclude_other_layer_roles": True,
        },
    }


def complete_current_layer(
    record: dict[str, Any],
    *,
    artifact_id: str,
    composite_artifact_id: str,
) -> dict[str, Any]:
    if not artifact_id.strip() or not composite_artifact_id.strip():
        raise ValueError("Layer and composite Artifact IDs are required")
    result = deepcopy(record)
    contract = current_layer_contract(result)
    index = result["current_layer_index"]
    layer = result["layers"][index]
    if contract["layer"]["id"] != layer["id"]:
        raise ValueError("Layer contract no longer matches current layer")
    layer.update(
        {
            "status": "completed",
            "artifact_id": artifact_id,
            "composite_artifact_id": composite_artifact_id,
        }
    )
    if index + 1 < len(result["layers"]):
        result["current_layer_index"] = index + 1
        result["layers"][index + 1]["status"] = "active"
    else:
        result["status"] = "recomposition-review-required"
    return result


def request_layer_revision(
    record: dict[str, Any],
    *,
    layer_id: str,
) -> dict[str, Any]:
    result = deepcopy(record)
    indices = {
        layer["id"]: index for index, layer in enumerate(result.get("layers", []))
    }
    if layer_id not in indices:
        raise ValueError(f"Unknown layer: {layer_id}")
    index = indices[layer_id]
    for position, layer in enumerate(result["layers"]):
        if position < index:
            continue
        layer["status"] = "active" if position == index else "pending"
        layer["artifact_id"] = None
        layer["composite_artifact_id"] = None
        if position == index:
            layer["revision"] += 1
    result["current_layer_index"] = index
    result["status"] = "layer-production"
    result["approvals"]["final_composition"] = "pending"
    return result


def approve_final_composition(record: dict[str, Any]) -> dict[str, Any]:
    result = deepcopy(record)
    if result.get("status") != "recomposition-review-required":
        raise ValueError("Final composition is not awaiting review")
    if any(layer.get("status") != "completed" for layer in result["layers"]):
        raise ValueError("Every layer must be completed before final approval")
    result["approvals"]["final_composition"] = "approved"
    result["status"] = "ready-to-export"
    return result


def build_export_manifest(record: dict[str, Any]) -> dict[str, Any]:
    if record.get("status") != "ready-to-export":
        raise ValueError("Layered composition is not ready to export")
    return {
        "schema_version": 1,
        "workflow": record["workflow"],
        "domain": record["domain"],
        "creation_direction": record["creation_direction"],
        "master_reference": record["master_reference"],
        "layers": [
            {
                "id": layer["id"],
                "role": layer["role"],
                "z_index": layer["z_index"],
                "artifact_id": layer["artifact_id"],
                "creative_freedom": layer["creative_freedom"],
            }
            for layer in record["layers"]
        ],
        "composite_artifact_id": record["layers"][-1]["composite_artifact_id"],
    }
