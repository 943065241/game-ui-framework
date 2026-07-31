from __future__ import annotations

from aipg.core import DomainPackDefinition


GUIF_VISUAL_DOMAIN = DomainPackDefinition(
    domain_id="visual-production",
    name="GUIF Visual Production",
    context_types=(
        "theme",
        "master-reference",
        "editable-source",
        "standalone-task",
    ),
    artifact_kinds=(
        "image",
        "mask",
        "layer",
        "composite",
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
        "visual-review",
        "resource-export",
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
)
