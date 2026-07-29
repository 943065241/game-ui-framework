from __future__ import annotations

import hashlib
import json
import os
import stat
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from guif.compatibility import MVP_RELEASE
from guif.private_data import PrivateDataLayout

PRIVATE_BACKUP_SCHEMA_VERSION = 1
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
PORTABLE_CATEGORIES = (
    "themes",
    "conversation-theme-bindings",
    "conversation-workflows",
    "project-theme-bindings",
    "runs",
    "plans",
    "host-work",
    "migrations",
    "privacy-reports",
)
SENSITIVE_CATEGORIES = (
    "host-credentials",
    "operation-ledger",
    "gateway-requests",
    "operation-audit",
)
BACKUP_PROFILES = {
    "portable": PORTABLE_CATEGORIES,
    "full-local": PORTABLE_CATEGORIES + SENSITIVE_CATEGORIES,
}


class PrivateBackupError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _canonical_hash(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _set_private_permissions(path: Path) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _safe_archive_name(value: str) -> str:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "" in path.parts:
        raise PrivateBackupError(f"Unsafe archive member path: {value}")
    normalized = path.as_posix()
    if normalized != value.replace("\\", "/"):
        raise PrivateBackupError(f"Non-canonical archive member path: {value}")
    return normalized


def _safe_relative_file(root: Path, path: Path) -> str:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise PrivateBackupError(f"Private file escaped its data root: {path}") from exc
    if path.is_symlink():
        raise PrivateBackupError(f"Private backups do not follow symbolic links: {path}")
    if not path.is_file():
        raise PrivateBackupError(f"Private backup entry is not a regular file: {path}")
    return relative.as_posix()


class PrivateBackupService:
    """Create, verify, plan, and explicitly apply private-data backups.

    The default portable profile deliberately excludes Host credentials,
    credential verifiers, signed-ledger keys, and operational request receipts.
    A full-local archive requires an explicit include_sensitive=True decision.
    Archives are integrity checked but are not encrypted at rest.
    """

    def __init__(
        self,
        workspace: Path,
        *,
        data_root: Path | None = None,
        max_file_bytes: int = 512 * 1024 * 1024,
        max_total_bytes: int = 2 * 1024 * 1024 * 1024,
    ) -> None:
        self.workspace = workspace.resolve()
        self.layout = PrivateDataLayout(self.workspace, data_root)
        self.max_file_bytes = max_file_bytes
        self.max_total_bytes = max_total_bytes

    @property
    def root(self) -> Path:
        return self.layout.root

    def _categories(self, profile: str, include_sensitive: bool) -> tuple[str, ...]:
        if profile not in BACKUP_PROFILES:
            raise ValueError(f"Unknown backup profile: {profile}")
        if profile == "full-local" and not include_sensitive:
            raise PrivateBackupError(
                "full-local backup contains authentication or signing material; "
                "set include_sensitive=True only for a protected local destination"
            )
        return tuple(BACKUP_PROFILES[profile])

    def _iter_files(self, categories: Iterable[str]) -> tuple[tuple[str, Path], ...]:
        records: list[tuple[str, Path]] = []
        total = 0
        for category in categories:
            root = self.root / category
            if not root.exists():
                continue
            if root.is_symlink() or not root.is_dir():
                raise PrivateBackupError(f"Private category is not a regular directory: {root}")
            for path in sorted(root.rglob("*")):
                if path.is_dir():
                    if path.is_symlink():
                        raise PrivateBackupError(
                            f"Private backups do not follow symbolic-link directories: {path}"
                        )
                    continue
                relative = _safe_relative_file(self.root, path)
                size = path.stat().st_size
                if size > self.max_file_bytes:
                    raise PrivateBackupError(
                        f"Private file exceeds backup limit ({self.max_file_bytes} bytes): {relative}"
                    )
                total += size
                if total > self.max_total_bytes:
                    raise PrivateBackupError(
                        f"Private backup exceeds total limit ({self.max_total_bytes} bytes)"
                    )
                records.append((relative, path))
        return tuple(records)

    def create(
        self,
        destination: Path,
        *,
        profile: str = "portable",
        include_sensitive: bool = False,
    ) -> dict[str, Any]:
        categories = self._categories(profile, include_sensitive)
        raw_destination = destination.expanduser()
        if raw_destination.is_symlink():
            raise PrivateBackupError("Private backup destination must not be a symbolic link")
        destination = raw_destination.resolve()
        try:
            destination.relative_to(self.workspace)
        except ValueError:
            pass
        else:
            raise PrivateBackupError(
                "Private backup destination must be outside the framework/project workspace"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        records = self._iter_files(categories)
        files: list[dict[str, Any]] = []
        for relative, path in records:
            files.append(
                {
                    "path": relative,
                    "archive_member": f"data/{relative}",
                    "sha256": _sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
            )
        manifest: dict[str, Any] = {
            "schema_version": PRIVATE_BACKUP_SCHEMA_VERSION,
            "created_at": _now(),
            "created_by_release": MVP_RELEASE,
            "profile": profile,
            "sensitive_material_included": include_sensitive,
            "source": {
                "workspace_name": self.workspace.name,
                "private_root_name": self.root.name,
            },
            "categories": list(categories),
            "file_count": len(files),
            "total_size_bytes": sum(int(item["size_bytes"]) for item in files),
            "files": files,
            "encryption": "none",
            "restore_requires_explicit_apply": True,
        }
        manifest["manifest_sha256"] = _canonical_hash(manifest)
        manifest_bytes = (
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        ).encode("utf-8")
        if len(manifest_bytes) > MAX_MANIFEST_BYTES:
            raise PrivateBackupError("Private backup manifest exceeds its size limit")
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        if temporary.exists():
            temporary.unlink()
        try:
            with zipfile.ZipFile(
                temporary,
                "w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=6,
                allowZip64=True,
            ) as archive:
                archive.writestr("manifest.json", manifest_bytes)
                by_relative = {relative: path for relative, path in records}
                for item in files:
                    archive.write(
                        by_relative[str(item["path"])],
                        arcname=str(item["archive_member"]),
                    )
            _set_private_permissions(temporary)
            temporary.replace(destination)
            _set_private_permissions(destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        verification = self.verify(destination)
        return {
            "schema_version": 1,
            "status": "created",
            "archive": str(destination),
            "profile": profile,
            "sensitive_material_included": include_sensitive,
            "file_count": manifest["file_count"],
            "total_size_bytes": manifest["total_size_bytes"],
            "archive_sha256": _sha256_file(destination),
            "verification": verification,
        }

    def _read_verified(self, archive_path: Path) -> tuple[dict[str, Any], dict[str, bytes]]:
        raw_archive_path = archive_path.expanduser()
        if raw_archive_path.is_symlink():
            raise PrivateBackupError("Private backup archive must not be a symbolic link")
        archive_path = raw_archive_path.resolve()
        if not archive_path.is_file():
            raise FileNotFoundError(f"Unknown private backup: {archive_path}")
        members: dict[str, bytes] = {}
        with zipfile.ZipFile(archive_path, "r") as archive:
            infos = archive.infolist()
            names: set[str] = set()
            declared_total = 0
            for info in infos:
                name = _safe_archive_name(info.filename)
                if name in names:
                    raise PrivateBackupError(f"Duplicate archive member: {name}")
                names.add(name)
                mode = (info.external_attr >> 16) & 0o170000
                if mode == stat.S_IFLNK:
                    raise PrivateBackupError(f"Symbolic link archive member is not allowed: {name}")
                if info.is_dir():
                    raise PrivateBackupError(f"Directory archive member is not allowed: {name}")
                if info.file_size > self.max_file_bytes and name != "manifest.json":
                    raise PrivateBackupError(f"Archive member exceeds file limit: {name}")
                if name == "manifest.json" and info.file_size > MAX_MANIFEST_BYTES:
                    raise PrivateBackupError("Private backup manifest exceeds its size limit")
                declared_total += info.file_size
                if declared_total > self.max_total_bytes + MAX_MANIFEST_BYTES:
                    raise PrivateBackupError("Private backup exceeds total extraction limit")
            for info in infos:
                members[info.filename] = archive.read(info)
        raw_manifest = members.get("manifest.json")
        if raw_manifest is None:
            raise PrivateBackupError("Private backup is missing manifest.json")
        try:
            manifest = json.loads(raw_manifest.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PrivateBackupError("Private backup manifest is not valid UTF-8 JSON") from exc
        if not isinstance(manifest, dict):
            raise PrivateBackupError("Private backup manifest must be an object")
        if manifest.get("schema_version") != PRIVATE_BACKUP_SCHEMA_VERSION:
            raise PrivateBackupError(
                f"Unsupported private backup schema: {manifest.get('schema_version')}"
            )
        expected_manifest_hash = str(manifest.get("manifest_sha256") or "")
        hash_input = dict(manifest)
        hash_input.pop("manifest_sha256", None)
        if not expected_manifest_hash or expected_manifest_hash != _canonical_hash(hash_input):
            raise PrivateBackupError("Private backup manifest hash mismatch")
        file_records = manifest.get("files")
        if not isinstance(file_records, list):
            raise PrivateBackupError("Private backup manifest files must be an array")
        expected_names = {"manifest.json"}
        total = 0
        seen_paths: set[str] = set()
        for item in file_records:
            if not isinstance(item, dict):
                raise PrivateBackupError("Private backup file record must be an object")
            relative = _safe_archive_name(str(item.get("path") or ""))
            member = _safe_archive_name(str(item.get("archive_member") or ""))
            if member != f"data/{relative}":
                raise PrivateBackupError(f"Backup member does not match private path: {member}")
            if relative in seen_paths:
                raise PrivateBackupError(f"Duplicate private backup path: {relative}")
            seen_paths.add(relative)
            expected_names.add(member)
            content = members.get(member)
            if content is None:
                raise PrivateBackupError(f"Private backup member is missing: {member}")
            size = int(item.get("size_bytes", -1))
            if size != len(content):
                raise PrivateBackupError(f"Private backup size mismatch: {relative}")
            if str(item.get("sha256") or "") != _sha256_bytes(content):
                raise PrivateBackupError(f"Private backup SHA-256 mismatch: {relative}")
            total += size
            if total > self.max_total_bytes:
                raise PrivateBackupError("Private backup exceeds total extraction limit")
        if set(members) != expected_names:
            unexpected = sorted(set(members) - expected_names)
            raise PrivateBackupError(
                "Private backup contains unmanifested members: " + ", ".join(unexpected)
            )
        if manifest.get("file_count") != len(file_records):
            raise PrivateBackupError("Private backup file count mismatch")
        if manifest.get("total_size_bytes") != total:
            raise PrivateBackupError("Private backup total size mismatch")
        return manifest, members

    def verify(self, archive_path: Path) -> dict[str, Any]:
        manifest, _ = self._read_verified(archive_path)
        return {
            "schema_version": 1,
            "status": "verified",
            "archive": str(archive_path.expanduser().resolve()),
            "archive_sha256": _sha256_file(archive_path.expanduser().resolve()),
            "profile": manifest.get("profile"),
            "sensitive_material_included": manifest.get("sensitive_material_included"),
            "file_count": manifest.get("file_count"),
            "total_size_bytes": manifest.get("total_size_bytes"),
            "manifest_sha256": manifest.get("manifest_sha256"),
        }

    def _validate_restore_root(self, value: Path) -> Path:
        root = value.expanduser().resolve()
        try:
            root.relative_to(self.workspace)
        except ValueError:
            pass
        else:
            raise PrivateBackupError(
                "Private restore target must be outside the framework/project workspace"
            )
        if root.is_symlink():
            raise PrivateBackupError("Private restore target must not be a symbolic link")
        if root.exists() and not root.is_dir():
            raise PrivateBackupError("Private restore target must be a directory")
        return root

    def plan_restore(
        self,
        archive_path: Path,
        *,
        target_root: Path | None = None,
        conflict: str = "fail",
    ) -> dict[str, Any]:
        if conflict not in {"fail", "skip", "replace"}:
            raise ValueError("conflict must be fail, skip, or replace")
        manifest, _ = self._read_verified(archive_path)
        root = self._validate_restore_root(target_root or self.root)
        actions: list[dict[str, Any]] = []
        conflicts: list[str] = []
        for item in manifest["files"]:
            relative = Path(str(item["path"]))
            destination = (root / relative).resolve()
            try:
                destination.relative_to(root)
            except ValueError as exc:
                raise PrivateBackupError(f"Restore target escaped private root: {relative}") from exc
            exists = destination.exists() or destination.is_symlink()
            regular_file = exists and destination.is_file() and not destination.is_symlink()
            current_sha256 = _sha256_file(destination) if regular_file else None
            same = regular_file and current_sha256 == item["sha256"]
            if same:
                action = "unchanged"
            elif exists and not regular_file:
                if conflict == "skip":
                    action = "skip"
                else:
                    action = "conflict"
                    conflicts.append(relative.as_posix())
            elif exists and conflict == "skip":
                action = "skip"
            elif exists and conflict == "replace":
                action = "replace"
            elif exists:
                action = "conflict"
                conflicts.append(relative.as_posix())
            else:
                action = "create"
            actions.append(
                {
                    "path": relative.as_posix(),
                    "action": action,
                    "expected_sha256": item["sha256"],
                    "current_sha256": current_sha256,
                }
            )
        return {
            "schema_version": 1,
            "status": "blocked" if conflicts else "ready",
            "archive": str(archive_path.expanduser().resolve()),
            "profile": manifest.get("profile"),
            "target_root": str(root),
            "conflict_policy": conflict,
            "actions": actions,
            "conflicts": conflicts,
            "apply_required": True,
        }

    def restore(
        self,
        archive_path: Path,
        *,
        target_root: Path | None = None,
        conflict: str = "fail",
        apply: bool = False,
        create_pre_restore_backup: bool = True,
    ) -> dict[str, Any]:
        manifest, members = self._read_verified(archive_path)
        plan = self.plan_restore(
            archive_path,
            target_root=target_root,
            conflict=conflict,
        )
        if not apply:
            return {**plan, "status": "planned" if not plan["conflicts"] else "blocked"}
        if plan["conflicts"]:
            raise PrivateBackupError(
                "Restore conflicts require conflict='skip' or conflict='replace': "
                + ", ".join(plan["conflicts"])
            )
        root = Path(plan["target_root"])
        root.mkdir(parents=True, exist_ok=True)
        pre_restore: dict[str, Any] | None = None
        has_replacements = any(item["action"] == "replace" for item in plan["actions"])
        if has_replacements and create_pre_restore_backup:
            pre_service = PrivateBackupService(
                self.workspace,
                data_root=root,
                max_file_bytes=self.max_file_bytes,
                max_total_bytes=self.max_total_bytes,
            )
            destination = root / "backups" / f"pre-restore-{_timestamp()}.guif-private.zip"
            pre_restore = pre_service.create(destination, profile="portable")
        applied: list[dict[str, Any]] = []
        by_path = {str(item["path"]): item for item in manifest["files"]}
        for action in plan["actions"]:
            kind = action["action"]
            if kind in {"unchanged", "skip"}:
                applied.append(dict(action))
                continue
            relative = str(action["path"])
            item = by_path[relative]
            content = members[str(item["archive_member"])]
            destination = (root / relative).resolve()
            try:
                destination.relative_to(root)
            except ValueError as exc:
                raise PrivateBackupError(f"Restore target escaped private root: {relative}") from exc
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(destination.suffix + ".restore.tmp")
            temporary.write_bytes(content)
            _set_private_permissions(temporary)
            temporary.replace(destination)
            _set_private_permissions(destination)
            if _sha256_file(destination) != item["sha256"]:
                raise PrivateBackupError(f"Restored file verification failed: {relative}")
            applied.append(dict(action))
        return {
            **plan,
            "status": "restored",
            "applied": applied,
            "pre_restore_backup": pre_restore,
            "completed_at": _now(),
        }


__all__ = [
    "BACKUP_PROFILES",
    "MAX_MANIFEST_BYTES",
    "PORTABLE_CATEGORIES",
    "PRIVATE_BACKUP_SCHEMA_VERSION",
    "PrivateBackupError",
    "PrivateBackupService",
    "SENSITIVE_CATEGORIES",
]
