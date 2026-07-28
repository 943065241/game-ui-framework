from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from guif.adapters import get_adapter
from guif.asset_qa import validate_asset_against_manifest
from guif.paths import project_root
from guif.resource import load_resource_manifest, validate_resource_file


@dataclass(frozen=True)
class ExportedAsset:
    resource_id: str
    source: str
    destination: str
    manifest: str
    adapter: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ExportReport:
    project: str
    target_engine: str
    output_dir: str
    exported: tuple[ExportedAsset, ...]
    errors: tuple[str, ...]
    report_path: str

    @property
    def passed(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, object]:
        return {
            "project": self.project,
            "target_engine": self.target_engine,
            "output_dir": self.output_dir,
            "exported": [item.to_dict() for item in self.exported],
            "errors": list(self.errors),
            "passed": self.passed,
            "report_path": self.report_path,
        }


def _resolve_asset_path(root: Path, manifest_path: Path) -> Path:
    manifest = load_resource_manifest(manifest_path)
    if manifest.source:
        source = Path(manifest.source)
        return source if source.is_absolute() else root / source
    return manifest_path.parent / manifest.output_name


def export_project_assets(
    workspace: Path,
    project: str,
    *,
    target_engine: str = "generic",
    output_dir: Path | None = None,
    clean: bool = True,
) -> ExportReport:
    root = project_root(workspace, project)
    if not (root / "project.json").is_file():
        raise FileNotFoundError(f"Unknown project: {project}")

    adapter = get_adapter(target_engine)
    destination_root = output_dir or (root / "exports" / target_engine)
    if clean and destination_root.exists():
        shutil.rmtree(destination_root)
    destination_root.mkdir(parents=True, exist_ok=True)

    exported: list[ExportedAsset] = []
    errors: list[str] = []
    manifests = sorted((root / "production-assets").glob("*.resource.json"))

    for manifest_path in manifests:
        manifest_errors = validate_resource_file(manifest_path)
        if manifest_errors:
            errors.extend(f"{manifest_path.name}: {error}" for error in manifest_errors)
            continue

        manifest = load_resource_manifest(manifest_path)
        if manifest.target_engine not in {"generic", target_engine}:
            continue

        asset_path = _resolve_asset_path(root, manifest_path)
        try:
            validation = validate_asset_against_manifest(manifest_path, asset_path)
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            errors.append(f"{manifest.resource_id}: {exc}")
            continue
        if not validation.passed:
            errors.extend(f"{manifest.resource_id}: {error}" for error in validation.errors)
            continue

        destination = destination_root / manifest.output_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(asset_path, destination)
        try:
            adapter_result = adapter.prepare(destination, manifest)
        except (OSError, RuntimeError, ValueError) as exc:
            destination.unlink(missing_ok=True)
            errors.append(f"{manifest.resource_id}: adapter failed: {exc}")
            continue
        exported.append(
            ExportedAsset(
                resource_id=manifest.resource_id,
                source=str(asset_path),
                destination=str(destination),
                manifest=str(manifest_path),
                adapter=adapter_result.to_dict(),
            )
        )

    report_path = destination_root / "export-report.json"
    payload = {
        "schema_version": 2,
        "project": project,
        "target_engine": target_engine,
        "adapter": adapter.__class__.__name__,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(destination_root),
        "exported": [item.to_dict() for item in exported],
        "errors": errors,
        "passed": not errors,
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return ExportReport(
        project=project,
        target_engine=target_engine,
        output_dir=str(destination_root),
        exported=tuple(exported),
        errors=tuple(errors),
        report_path=str(report_path),
    )
