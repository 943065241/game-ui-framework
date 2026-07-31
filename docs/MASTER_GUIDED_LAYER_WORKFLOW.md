# Master-Guided Layer Creation

## Intent

Create reusable visual layers from bottom to top while a master effect image
guides style and layout. AI is allowed to interpret and improve local visual
details.

## Stages

1. Confirm Theme and master.
2. Analyze coarse semantic layers.
3. Approve the layer plan and creative freedom.
4. Produce layers from bottom to top.
5. Recompose after each real layer.
6. Perform semantic visual review.
7. Revise the selected layer and downstream composites when needed.
8. Approve the complete composition.
9. Export assets and the composition manifest.

## Constraint policy

Hard constraints cover functional roles, layout anchors, asset boundaries,
protected content, transparency, and output contracts.

Soft guidance covers shape details, materials, texture, lighting, decoration,
and local color interpretation. Each layer has low, medium, or high creative
freedom.

The master uses `style-and-layout-guidance` policy with `pixel_matching=false`.

## Fictional regression fixture

The public fixture is a fictional “Starport Night Market” game shop containing
a neon background, central shop panel, independent purchase control, price
text, frame decoration, and foreground particles. It contains no user asset or
private Theme.
