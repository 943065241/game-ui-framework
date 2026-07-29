from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from guif.adapters import get_adapter
from guif.paths import project_root
from guif.resource import ResourceManifest, validate_resource_data
from guif.runtime.store import TaskStore

GATED_EXPORT_SCHEMA_VERSION = 1
GATED_EXPORT_STATE_SCHEMA_VERSION = 1
TERMINAL_REVISION_STATUSES = {"resolved", "rejected"}


class GatedExportError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical_hash(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _copy_atomic(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    shutil.copy2(source, temporary)
    temporary.replace(destination)


def _safe_run_file(run_dir: Path, artifact: dict[str, Any]) -> tuple[Path | None, str | None]:
    file_data = artifact.get("file") if isinstance(artifact.get("file"), dict) else {}
    value = file_data.get("path")
    if not isinstance(value, str) or not value.strip():
        return None, "Artifact file path is missing."
    root = run_dir.resolve()
    candidate = (run_dir / value).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None, "Artifact file path escapes the persisted Run directory."
    if not candidate.is_file():
        return None, "Artifact file does not exist in the persisted Run."
    expected = str(file_data.get("sha256") or "")
    actual = _sha256(candidate.read_bytes())
    if not expected or expected != actual:
        return None, "Artifact file SHA-256 does not match the registered record."
    return candidate, None


def _resource_manifest(value: dict[str, Any], *, source: str) -> dict[str, Any]:
    manifest = {
        "schema_version": value.get("schema_version", 1),
        "id": value.get("id"),
        "type": value.get("type"),
        "width": value.get("width"),
        "height": value.get("height"),
        "format": value.get("format"),
        "alpha_required": value.get("alpha_required"),
        "target_engine": value.get("target_engine"),
        "output_name": value.get("output_name"),
        "source": source,
        "import_settings": dict(value.get("import_settings", {}))
        if isinstance(value.get("import_settings"), dict)
        else {},
    }
    errors = validate_resource_data(manifest)
    if errors:
        raise ValueError("Invalid approved Resource manifest: " + "; ".join(errors))
    return manifest


def _manifest_contract_key(value: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value.get(key)
        for key in (
            "schema_version",
            "id",
            "type",
            "width",
            "height",
            "format",
            "alpha_required",
            "target_engine",
            "output_name",
            "import_settings",
        )
    }


def _check(check_id: str, passed: bool, reason: str, **details: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": check_id,
        "status": "passed" if passed else "failed",
        "reason": reason,
    }
    if details:
        payload["details"] = details
    return payload


def _state(task: Any) -> dict[str, Any]:
    state = task.state.get("gated_exports")
    if not isinstance(state, dict):
        state = {
            "schema_version": GATED_EXPORT_STATE_SCHEMA_VERSION,
            "task_id": task.task_id,
            "project": task.project,
            "records": [],
            "latest_by_target": {},
            "updated_at": _now(),
        }
        task.state["gated_exports"] = state
    return state


def _replace_output(task: Any, export_id: str, record: dict[str, Any]) -> None:
    for output in task.outputs:
        if (
            isinstance(output, dict)
            and output.get("type") == "gated-export-record"
            and isinstance(output.get("value"), dict)
            and output["value"].get("export_id") == export_id
        ):
            output["value"] = record
            return
    task.add_output("gated-export-record", record, agent="export")


class GatedExportService:
    """Materialize only reviewed active Artifacts into Project truth and Engine exports."""

    def __init__(self, workspace: Path, *, store: TaskStore | None = None) -> None:
        self.workspace = workspace
        self.store = store or TaskStore(workspace)

    def _build_plan(
        self,
        project: str,
        task_id: str,
        *,
        target_engine: str | None = None,
    ) -> tuple[Any, dict[str, Any]]:
        task = self.store.load(project, task_id)
        root = project_root(self.workspace, project)
        run_dir = self.store.run_dir(project, task_id)
        qa = task.state.get("qa_report") if isinstance(task.state.get("qa_report"), dict) else {}
        approval = (
            task.state.get("approval_state")
            if isinstance(task.state.get("approval_state"), dict)
            else {}
        )
        resource_bundle = (
            task.state.get("resource_contracts")
            if isinstance(task.state.get("resource_contracts"), dict)
            else {}
        )
        resolved_target = str(
            target_engine
            or resource_bundle.get("target_engine")
            or task.state.get("plan", {}).get("target_engine")
            or "generic"
        )
        get_adapter(resolved_target)

        registry = (
            task.state.get("artifact_registry")
            if isinstance(task.state.get("artifact_registry"), dict)
            else {}
        )
        records = [item for item in registry.get("records", []) if isinstance(item, dict)]
        active = [item for item in records if item.get("status") == "registered"]
        production = [item for item in active if item.get("artifact_kind") == "production-asset"]
        excluded = [
            {
                "artifact_id": item.get("artifact_id"),
                "artifact_kind": item.get("artifact_kind"),
                "reason": "Only active production-asset Artifacts are materialized into Project truth.",
            }
            for item in active
            if item.get("artifact_kind") != "production-asset"
        ]

        candidate_by_id: dict[str, dict[str, Any]] = {}
        for item in resource_bundle.get("manifest_candidates", []):
            if isinstance(item, dict) and isinstance(item.get("manifest"), dict):
                resource_id = str(item["manifest"].get("id") or item.get("resource_id") or "")
                if resource_id:
                    candidate_by_id[resource_id] = dict(item["manifest"])

        assets: list[dict[str, Any]] = []
        asset_errors: list[str] = []
        seen_resources: dict[str, str] = {}
        for artifact in production:
            artifact_id = str(artifact.get("artifact_id") or "")
            contract = artifact.get("output_contract") if isinstance(artifact.get("output_contract"), dict) else {}
            resource_id = str(contract.get("id") or artifact.get("job_id") or "")
            if not resource_id:
                asset_errors.append(f"{artifact_id}: Resource ID is missing from the Output Contract.")
                continue
            if resource_id in seen_resources:
                asset_errors.append(
                    f"{resource_id}: multiple active Artifacts exist ({seen_resources[resource_id]}, {artifact_id}); supersession must resolve the ambiguity."
                )
                continue
            seen_resources[resource_id] = artifact_id
            approved = candidate_by_id.get(resource_id)
            if approved is None:
                asset_errors.append(f"{resource_id}: no approved Resource manifest candidate is present.")
                continue
            if _manifest_contract_key(contract) != _manifest_contract_key(approved):
                asset_errors.append(f"{resource_id}: Artifact Output Contract differs from the approved Resource manifest.")
                continue
            if approved.get("target_engine") not in {"generic", resolved_target}:
                asset_errors.append(
                    f"{resource_id}: Resource target {approved.get('target_engine')} is incompatible with export target {resolved_target}."
                )
                continue
            if artifact.get("simulation") is True or artifact.get("visual") is not True:
                asset_errors.append(f"{resource_id}: simulation or non-visual Artifact cannot enter production export.")
                continue
            artifact_qa = artifact.get("qa") if isinstance(artifact.get("qa"), dict) else {}
            if artifact_qa.get("status") != "passed":
                asset_errors.append(f"{resource_id}: Artifact visual review status is {artifact_qa.get('status') or 'not-run'}.")
                continue
            source_path, source_error = _safe_run_file(run_dir, artifact)
            if source_error or source_path is None:
                asset_errors.append(f"{resource_id}: {source_error}")
                continue
            output_name = str(approved.get("output_name") or "")
            materialized_source = f"production-assets/files/{output_name}"
            try:
                manifest = _resource_manifest(approved, source=materialized_source)
            except ValueError as exc:
                asset_errors.append(f"{resource_id}: {exc}")
                continue
            assets.append(
                {
                    "resource_id": resource_id,
                    "artifact_id": artifact_id,
                    "job_id": artifact.get("job_id"),
                    "review_id": artifact_qa.get("review_id"),
                    "source_run_path": str(source_path.relative_to(run_dir)),
                    "source_sha256": artifact.get("file", {}).get("sha256"),
                    "materialized_asset": materialized_source,
                    "materialized_manifest": f"production-assets/{resource_id}.resource.json",
                    "engine_output": output_name,
                    "manifest": manifest,
                }
            )

        revision_state = (
            task.state.get("revision_plans")
            if isinstance(task.state.get("revision_plans"), dict)
            else {}
        )
        unresolved_revisions = [
            {
                "revision_id": item.get("revision_id"),
                "status": item.get("status"),
                "source_artifact_id": item.get("source_artifact_id"),
            }
            for item in revision_state.get("records", [])
            if isinstance(item, dict) and item.get("status") not in TERMINAL_REVISION_STATUSES
        ]

        checks = [
            _check(
                "task-completed",
                task.status == "completed",
                "Task must be completed before production materialization.",
                actual=task.status,
            ),
            _check(
                "approval-gate",
                approval.get("status") in {"approved", "not-required"},
                "Initial production Approval must be approved or not required.",
                actual=approval.get("status"),
            ),
            _check(
                "contract-qa",
                qa.get("status") == "passed",
                "Contract QA must pass.",
                actual=qa.get("status"),
            ),
            _check(
                "visual-export-gate",
                isinstance(qa.get("export_gate"), dict) and qa["export_gate"].get("allowed") is True,
                "Aggregate Export Gate must allow export after every active visual Artifact passes review.",
                actual=qa.get("export_gate"),
            ),
            _check(
                "active-production-artifacts",
                bool(production),
                "At least one active production-asset Artifact is required.",
                active_artifact_count=len(active),
                production_artifact_count=len(production),
            ),
            _check(
                "resource-contract-status",
                resource_bundle.get("status") in {"ready", "review-required"}
                and approval.get("status") in {"approved", "not-required"},
                "Resource contracts must exist and their required approvals must be satisfied.",
                actual=resource_bundle.get("status"),
            ),
            _check(
                "artifact-resource-integrity",
                not asset_errors and len(assets) == len(production),
                "Every active production Artifact must have one approved matching Resource contract, passing review, and valid SHA-256 identity.",
                errors=asset_errors,
            ),
            _check(
                "revision-resolution",
                not unresolved_revisions,
                "All Revision Plans must be resolved or rejected before export.",
                unresolved=unresolved_revisions,
            ),
        ]
        blockers = [item for item in checks if item["status"] == "failed"]
        identity = {
            "task_id": task.task_id,
            "target_engine": resolved_target,
            "artifacts": [
                {"artifact_id": item["artifact_id"], "sha256": item["source_sha256"]}
                for item in assets
            ],
        }
        export_id = "export-" + _canonical_hash(identity)[:16]
        record = {
            "schema_version": GATED_EXPORT_SCHEMA_VERSION,
            "export_id": export_id,
            "task_id": task.task_id,
            "project": project,
            "target_engine": resolved_target,
            "status": "ready" if not blockers else "blocked",
            "checks": checks,
            "blockers": blockers,
            "assets": assets,
            "excluded_artifacts": excluded,
            "gate_snapshot": {
                "task_status": task.status,
                "approval_status": approval.get("status"),
                "qa_status": qa.get("status"),
                "artifact_review_status": qa.get("artifact_review", {}).get("status")
                if isinstance(qa.get("artifact_review"), dict)
                else None,
                "export_allowed": qa.get("export_gate", {}).get("allowed")
                if isinstance(qa.get("export_gate"), dict)
                else False,
                "revision_plan_count": len(revision_state.get("records", []))
                if isinstance(revision_state.get("records"), list)
                else 0,
            },
            "project_truth": {
                "root": str(root),
                "materialization_root": "production-assets",
                "mutated": False,
            },
            "engine_output_dir": f"exports/{resolved_target}/{export_id}",
            "created_at": _now(),
            "updated_at": _now(),
            "completed_at": None,
            "error": None,
            "rollback": None,
        }
        return task, record

    def _persist(self, task: Any, record: dict[str, Any]) -> dict[str, Any]:
        state = _state(task)
        records = state.setdefault("records", [])
        latest = state.setdefault("latest_by_target", {})
        if not isinstance(records, list) or not isinstance(latest, dict):
            raise ValueError("Invalid persisted gated Export state")
        existing = next(
            (
                item
                for item in records
                if isinstance(item, dict) and item.get("export_id") == record["export_id"]
            ),
            None,
        )
        if existing is None:
            records.append(record)
            persisted = record
        else:
            terminal = existing.get("status") in {"completed", "rolled-back"}
            if terminal and record.get("status") in {"ready", "blocked"}:
                persisted = existing
            else:
                existing.clear()
                existing.update(record)
                persisted = existing
        latest[str(record["target_engine"])] = record["export_id"]
        state["updated_at"] = _now()
        _replace_output(task, record["export_id"], persisted)
        self.store.save(task)
        return persisted

    def prepare(
        self,
        project: str,
        task_id: str,
        *,
        target_engine: str | None = None,
    ) -> dict[str, Any]:
        task, record = self._build_plan(project, task_id, target_engine=target_engine)
        task.record(
            "export",
            record["status"],
            f"Gated Export {record['export_id']} prepared with status {record['status']}.",
        )
        return dict(self._persist(task, record))

    def execute(
        self,
        project: str,
        task_id: str,
        *,
        target_engine: str | None = None,
        actor: str = "host",
    ) -> dict[str, Any]:
        normalized_actor = actor.strip()
        if not normalized_actor:
            raise ValueError("actor must not be empty")
        task, candidate = self._build_plan(project, task_id, target_engine=target_engine)
        state = _state(task)
        existing = next(
            (
                item
                for item in state.get("records", [])
                if isinstance(item, dict) and item.get("export_id") == candidate["export_id"]
            ),
            None,
        )
        if isinstance(existing, dict) and existing.get("status") == "completed":
            return dict(existing)
        record = self._persist(task, candidate)
        task = self.store.load(project, task_id)
        if record.get("status") != "ready":
            reasons = "; ".join(str(item.get("reason")) for item in record.get("blockers", []))
            raise GatedExportError(f"Gated Export is blocked: {reasons}")

        root = project_root(self.workspace, project)
        run_dir = self.store.run_dir(project, task_id)
        export_dir = root / str(record["engine_output_dir"])
        history_dir = root / "export-history" / str(record["export_id"])
        backup_dir = history_dir / "backups"
        adapter = get_adapter(str(record["target_engine"]))
        mutations: list[dict[str, Any]] = []
        exported_assets: list[dict[str, Any]] = []

        def backup(path: Path) -> dict[str, Any]:
            relative = path.relative_to(root)
            before_exists = path.is_file()
            before_sha = _sha256(path.read_bytes()) if before_exists else None
            backup_path = backup_dir / relative
            if before_exists:
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup_path)
            return {
                "path": str(relative),
                "before_exists": before_exists,
                "before_sha256": before_sha,
                "backup_path": str(backup_path.relative_to(root)) if before_exists else None,
                "after_sha256": None,
            }

        try:
            export_dir.mkdir(parents=True, exist_ok=True)
            for item in record["assets"]:
                source = run_dir / str(item["source_run_path"])
                truth_asset = root / str(item["materialized_asset"])
                truth_manifest = root / str(item["materialized_manifest"])
                asset_mutation = backup(truth_asset)
                manifest_mutation = backup(truth_manifest)
                mutations.extend((asset_mutation, manifest_mutation))

                _copy_atomic(source, truth_asset)
                _write_json(truth_manifest, item["manifest"])
                asset_mutation["after_sha256"] = _sha256(truth_asset.read_bytes())
                manifest_mutation["after_sha256"] = _sha256(truth_manifest.read_bytes())

                engine_asset = export_dir / str(item["engine_output"])
                _copy_atomic(truth_asset, engine_asset)
                manifest_data = item["manifest"]
                resource = ResourceManifest(
                    resource_id=str(manifest_data["id"]),
                    resource_type=str(manifest_data["type"]),
                    width=int(manifest_data["width"]),
                    height=int(manifest_data["height"]),
                    file_format=str(manifest_data["format"]),
                    alpha_required=bool(manifest_data["alpha_required"]),
                    target_engine=str(manifest_data["target_engine"]),
                    output_name=str(manifest_data["output_name"]),
                    source=str(manifest_data["source"]),
                    import_settings=dict(manifest_data.get("import_settings", {})),
                )
                adapter_result = adapter.prepare(engine_asset, resource)
                exported_assets.append(
                    {
                        **item,
                        "engine_asset": str(engine_asset.relative_to(root)),
                        "engine_asset_sha256": _sha256(engine_asset.read_bytes()),
                        "adapter": adapter_result.to_dict(),
                    }
                )

            manifest_payload = {
                "schema_version": 1,
                "export_id": record["export_id"],
                "task_id": task_id,
                "project": project,
                "target_engine": record["target_engine"],
                "actor": normalized_actor,
                "gate_snapshot": record["gate_snapshot"],
                "assets": exported_assets,
                "created_at": _now(),
            }
            export_manifest = export_dir / "export-manifest.json"
            _write_json(export_manifest, manifest_payload)
            transaction = {
                "schema_version": 1,
                "export_id": record["export_id"],
                "project": project,
                "task_id": task_id,
                "actor": normalized_actor,
                "status": "completed",
                "mutations": mutations,
                "engine_output_dir": str(export_dir.relative_to(root)),
                "export_manifest": str(export_manifest.relative_to(root)),
                "created_at": _now(),
            }
            transaction_path = history_dir / "transaction.json"
            _write_json(transaction_path, transaction)
        except Exception as exc:
            for mutation in reversed(mutations):
                destination = root / str(mutation["path"])
                if mutation.get("before_exists"):
                    backup_path = root / str(mutation["backup_path"])
                    if backup_path.is_file():
                        _copy_atomic(backup_path, destination)
                else:
                    destination.unlink(missing_ok=True)
            if export_dir.exists():
                shutil.rmtree(export_dir)
            record["status"] = "failed"
            record["error"] = {"type": type(exc).__name__, "message": str(exc)}
            record["rollback"] = {"status": "automatic", "completed_at": _now()}
            record["updated_at"] = _now()
            task.record("export", "failed", f"Gated Export {record['export_id']} failed and was rolled back: {exc}")
            self._persist(task, record)
            raise GatedExportError(f"Gated Export failed and was rolled back: {exc}") from exc

        record["status"] = "completed"
        record["assets"] = exported_assets
        record["project_truth"]["mutated"] = True
        record["actor"] = normalized_actor
        record["export_manifest"] = str(export_manifest.relative_to(root))
        record["transaction"] = str(transaction_path.relative_to(root))
        record["completed_at"] = _now()
        record["updated_at"] = record["completed_at"]
        task.record(
            "export",
            "completed",
            f"Gated Export {record['export_id']} materialized {len(exported_assets)} approved production asset(s).",
        )
        return dict(self._persist(task, record))

    def list(self, project: str, task_id: str) -> tuple[dict[str, Any], ...]:
        task = self.store.load(project, task_id)
        state = task.state.get("gated_exports")
        if not isinstance(state, dict):
            return ()
        return tuple(item for item in state.get("records", []) if isinstance(item, dict))

    def get(self, project: str, task_id: str, export_id: str) -> dict[str, Any]:
        for record in self.list(project, task_id):
            if record.get("export_id") == export_id:
                return dict(record)
        raise ValueError(f"Unknown gated Export: {export_id}")

    def rollback(
        self,
        project: str,
        task_id: str,
        export_id: str,
        *,
        actor: str,
        reason: str,
        force: bool = False,
    ) -> dict[str, Any]:
        normalized_actor = actor.strip()
        normalized_reason = reason.strip()
        if not normalized_actor or not normalized_reason:
            raise ValueError("actor and reason must not be empty")
        task = self.store.load(project, task_id)
        state = _state(task)
        record = next(
            (
                item
                for item in state.get("records", [])
                if isinstance(item, dict) and item.get("export_id") == export_id
            ),
            None,
        )
        if not isinstance(record, dict):
            raise ValueError(f"Unknown gated Export: {export_id}")
        if record.get("status") == "rolled-back":
            return dict(record)
        if record.get("status") != "completed":
            raise ValueError(f"Only completed gated Exports can be rolled back: {record.get('status')}")

        root = project_root(self.workspace, project)
        transaction_path = root / str(record.get("transaction") or "")
        if not transaction_path.is_file():
            raise GatedExportError("Export transaction record is missing; rollback cannot proceed safely")
        transaction = json.loads(transaction_path.read_text(encoding="utf-8"))
        mutations = transaction.get("mutations", []) if isinstance(transaction, dict) else []
        if not isinstance(mutations, list):
            raise GatedExportError("Export transaction mutations are invalid")

        conflicts: list[str] = []
        for mutation in mutations:
            if not isinstance(mutation, dict):
                continue
            destination = root / str(mutation.get("path") or "")
            expected_after = mutation.get("after_sha256")
            actual = _sha256(destination.read_bytes()) if destination.is_file() else None
            if expected_after != actual:
                conflicts.append(str(mutation.get("path")))
        if conflicts and not force:
            raise GatedExportError(
                "Rollback would overwrite Project changes made after export: " + ", ".join(conflicts)
            )

        for mutation in reversed(mutations):
            if not isinstance(mutation, dict):
                continue
            destination = root / str(mutation.get("path") or "")
            if mutation.get("before_exists"):
                backup_path = root / str(mutation.get("backup_path") or "")
                if not backup_path.is_file():
                    raise GatedExportError(f"Rollback backup is missing: {backup_path}")
                _copy_atomic(backup_path, destination)
            else:
                destination.unlink(missing_ok=True)

        output_dir = root / str(record.get("engine_output_dir") or "")
        if output_dir.exists():
            shutil.rmtree(output_dir)
        rollback = {
            "status": "completed",
            "actor": normalized_actor,
            "reason": normalized_reason,
            "force": force,
            "conflicts_overridden": conflicts,
            "completed_at": _now(),
        }
        record["status"] = "rolled-back"
        record["rollback"] = rollback
        record["updated_at"] = rollback["completed_at"]
        task.record("export", "rolled-back", f"Gated Export {export_id} was rolled back by {normalized_actor}.")
        self._persist(task, record)
        transaction["status"] = "rolled-back"
        transaction["rollback"] = rollback
        _write_json(transaction_path, transaction)
        return dict(record)


__all__ = ["GatedExportError", "GatedExportService"]
