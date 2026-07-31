from __future__ import annotations

import pytest

from guif.layered_workflow import (
    approve_final_composition,
    approve_layer_plan,
    build_export_manifest,
    complete_current_layer,
    create_layered_composition,
    current_layer_contract,
    request_layer_revision,
    validate_layered_composition,
)


def _layers() -> list[dict[str, object]]:
    return [
        {
            "id": "background",
            "name": "Starport atmosphere",
            "role": "background",
            "z_index": 0,
            "creative_freedom": "high",
            "hard_constraints": ["fill the approved canvas"],
            "soft_guidance": ["interpret the neon market atmosphere freely"],
        },
        {
            "id": "shop-panel",
            "name": "Central shop panel",
            "role": "container",
            "z_index": 20,
            "creative_freedom": "medium",
            "hard_constraints": ["preserve the central layout anchor"],
            "soft_guidance": ["invent frame materials that fit the Theme"],
        },
        {
            "id": "buy-control",
            "name": "Purchase control",
            "role": "control",
            "z_index": 40,
            "creative_freedom": "low",
            "hard_constraints": ["remain independently clickable"],
            "soft_guidance": ["refine the button silhouette"],
        },
        {
            "id": "foreground-effects",
            "name": "Foreground particles",
            "role": "effect",
            "z_index": 60,
            "creative_freedom": "high",
            "hard_constraints": ["do not obscure price readability"],
            "soft_guidance": ["add restrained depth and celebration"],
        },
    ]


def test_layered_workflow_runs_bottom_to_top_and_exports_manifest() -> None:
    record = create_layered_composition(
        master_reference="private-master-reference",
        theme_reference="private-theme-reference",
        layers=list(reversed(_layers())),
    )
    assert record["status"] == "layer-plan-review-required"
    assert [layer["id"] for layer in record["layers"]] == [
        "background",
        "shop-panel",
        "buy-control",
        "foreground-effects",
    ]
    assert validate_layered_composition(record) == []

    record = approve_layer_plan(record)
    for index, layer_id in enumerate(
        ("background", "shop-panel", "buy-control", "foreground-effects")
    ):
        contract = current_layer_contract(record)
        assert contract["layer"]["id"] == layer_id
        assert contract["master_policy"]["pixel_matching"] is False
        assert contract["output_contract"]["transparent_background"] is (
            index != 0
        )
        record = complete_current_layer(
            record,
            artifact_id=f"artifact-{layer_id}",
            composite_artifact_id=f"composite-{index}",
        )

    assert record["status"] == "recomposition-review-required"
    record = approve_final_composition(record)
    manifest = build_export_manifest(record)
    assert record["status"] == "ready-to-export"
    assert manifest["creation_direction"] == "bottom-to-top"
    assert manifest["composite_artifact_id"] == "composite-3"
    assert [layer["z_index"] for layer in manifest["layers"]] == [0, 20, 40, 60]


def test_layer_revision_invalidates_only_selected_and_downstream_layers() -> None:
    record = approve_layer_plan(
        create_layered_composition(
            master_reference="private-master-reference",
            theme_reference=None,
            layers=_layers(),
        )
    )
    for index in range(4):
        layer_id = record["layers"][index]["id"]
        record = complete_current_layer(
            record,
            artifact_id=f"artifact-{layer_id}",
            composite_artifact_id=f"composite-{index}",
        )

    record = request_layer_revision(record, layer_id="shop-panel")
    assert record["status"] == "layer-production"
    assert record["current_layer_index"] == 1
    assert record["layers"][0]["status"] == "completed"
    assert record["layers"][0]["artifact_id"] == "artifact-background"
    assert record["layers"][1]["status"] == "active"
    assert record["layers"][1]["revision"] == 1
    assert all(
        layer["artifact_id"] is None for layer in record["layers"][1:]
    )


def test_layered_workflow_rejects_missing_asset_boundaries() -> None:
    layers = _layers()
    layers[1]["creative_freedom"] = "unbounded"
    with pytest.raises(ValueError, match="creative_freedom"):
        create_layered_composition(
            master_reference="private-master-reference",
            theme_reference=None,
            layers=layers,
        )
