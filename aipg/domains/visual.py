from __future__ import annotations

from .model import DomainPackDefinition


GUIF_VISUAL_DOMAIN = DomainPackDefinition(
    domain_id="visual-production",
    name="GUIF Visual Production",
    description=(
        "Game UI and visual asset production governed by AIPG. "
        "GUIF remains the compatible visual-domain name."
    ),
    context_types=(
        "theme",
        "master-reference",
        "editable-source",
        "standalone-task",
    ),
    artifact_kinds=(
        "effect-image",
        "production-asset",
        "image",
        "mask",
        "layer",
        "layer-artifact",
        "composite",
        "composition-preview",
        "layer-manifest",
        "visual-diff-report",
        "figma-node-mapping",
        "export-package",
    ),
    workflow_ids=(
        "effect-image",
        "localized-repaint",
        "image-layering",
        "master-guided-layer-creation",
        "figma-sync",
        "planning",
        "quality-assurance",
        "resource-production",
        "resource-export",
        "theme-direction",
        "ui-production",
        "visual-review",
    ),
    capability_ids=(
        "image-generation",
        "image-editing",
        "mask-generation",
        "vision-analysis",
        "ocr",
        "background-removal",
        "image-composition",
        "visual-diff",
        "figma-design",
        "engine-export",
    ),
    legacy_names=("GUIF", "Game UI Framework"),
)
