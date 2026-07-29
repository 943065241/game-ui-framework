from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from guif.backup_protection import (
    BackupProtectionError,
    BackupProtectionService,
    ExternalCommandProtectionAdapter,
)


def _source(tmp_path: Path) -> Path:
    path = tmp_path / "fictional-portable-backup.bin"
    path.write_bytes(b"fictional portable backup fixture")
    return path


def _script(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


def _adapter(
    tmp_path: Path,
    *,
    adapter_id: str = "fictional-protector",
    protect_body: str | None = None,
    unprotect_body: str | None = None,
    timeout_seconds: float = 2,
) -> ExternalCommandProtectionAdapter:
    copy_body = (
        "from pathlib import Path\n"
        "import sys\n"
        "Path(sys.argv[2]).write_bytes(Path(sys.argv[1]).read_bytes())\n"
    )
    protect = _script(tmp_path, f"{adapter_id}-protect.py", protect_body or copy_body)
    unprotect = _script(tmp_path, f"{adapter_id}-unprotect.py", unprotect_body or copy_body)
    return ExternalCommandProtectionAdapter(
        adapter_id=adapter_id,
        protect_argv=(sys.executable, str(protect), "{input}", "{output}"),
        unprotect_argv=(sys.executable, str(unprotect), "{input}", "{output}"),
        timeout_seconds=timeout_seconds,
    )


def test_adapter_timeout_fails_closed_and_cleans_output(tmp_path: Path) -> None:
    source = _source(tmp_path)
    destination = tmp_path / "protected.bin"
    body = "import time\ntime.sleep(1)\n"
    service = BackupProtectionService(
        _adapter(tmp_path, protect_body=body, timeout_seconds=0.01)
    )

    with pytest.raises(BackupProtectionError, match="could not complete"):
        service.protect(source, destination)

    assert source.is_file()
    assert not destination.exists()
    assert not destination.with_suffix(destination.suffix + ".protect.tmp").exists()


def test_adapter_nonzero_exit_fails_closed(tmp_path: Path) -> None:
    source = _source(tmp_path)
    destination = tmp_path / "protected.bin"
    body = "import sys\nsys.exit(23)\n"

    with pytest.raises(BackupProtectionError, match="exit code 23"):
        BackupProtectionService(_adapter(tmp_path, protect_body=body)).protect(
            source, destination
        )

    assert not destination.exists()


def test_adapter_empty_output_is_rejected(tmp_path: Path) -> None:
    source = _source(tmp_path)
    destination = tmp_path / "protected.bin"
    body = (
        "from pathlib import Path\n"
        "import sys\n"
        "Path(sys.argv[2]).write_bytes(b'')\n"
    )

    with pytest.raises(BackupProtectionError, match="empty output"):
        BackupProtectionService(_adapter(tmp_path, protect_body=body)).protect(
            source, destination
        )

    assert not destination.exists()


def test_adapter_missing_output_is_rejected(tmp_path: Path) -> None:
    source = _source(tmp_path)
    destination = tmp_path / "protected.bin"

    with pytest.raises(BackupProtectionError, match="regular output file"):
        BackupProtectionService(
            _adapter(tmp_path, protect_body="pass\n")
        ).protect(source, destination)

    assert not destination.exists()


def test_adapter_symlink_output_is_rejected(tmp_path: Path) -> None:
    source = _source(tmp_path)
    destination = tmp_path / "protected.bin"
    body = (
        "from pathlib import Path\n"
        "import sys\n"
        "Path(sys.argv[2]).symlink_to(Path(sys.argv[1]))\n"
    )

    with pytest.raises(BackupProtectionError, match="regular output file"):
        BackupProtectionService(_adapter(tmp_path, protect_body=body)).protect(
            source, destination
        )

    assert not destination.exists()
    assert not destination.with_suffix(destination.suffix + ".protect.tmp").exists()


def test_receipt_collision_is_rejected_without_adapter_execution(tmp_path: Path) -> None:
    source = _source(tmp_path)
    destination = tmp_path / "protected.bin"
    receipt = destination.with_suffix(destination.suffix + ".guif-protection.json")
    receipt.write_text("owner-controlled", encoding="utf-8")

    with pytest.raises(BackupProtectionError, match="receipt destination already exists"):
        BackupProtectionService(_adapter(tmp_path)).protect(source, destination)

    assert receipt.read_text(encoding="utf-8") == "owner-controlled"
    assert not destination.exists()


def test_destination_collision_is_rejected_without_overwrite(tmp_path: Path) -> None:
    source = _source(tmp_path)
    destination = tmp_path / "protected.bin"
    destination.write_bytes(b"owner-controlled")

    with pytest.raises(BackupProtectionError, match="already exists"):
        BackupProtectionService(_adapter(tmp_path)).protect(source, destination)

    assert destination.read_bytes() == b"owner-controlled"


def test_tampered_receipt_is_rejected(tmp_path: Path) -> None:
    source = _source(tmp_path)
    destination = tmp_path / "protected.bin"
    service = BackupProtectionService(_adapter(tmp_path))
    result = service.protect(source, destination)
    receipt = Path(result["receipt_path"])
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["protected"]["sha256"] = "0" * 64
    receipt.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BackupProtectionError, match="SHA-256"):
        service.verify(destination)


def test_wrong_adapter_identity_is_rejected(tmp_path: Path) -> None:
    source = _source(tmp_path)
    destination = tmp_path / "protected.bin"
    BackupProtectionService(
        _adapter(tmp_path, adapter_id="fictional-protector-one")
    ).protect(source, destination)

    with pytest.raises(BackupProtectionError, match="identity"):
        BackupProtectionService(
            _adapter(tmp_path, adapter_id="fictional-protector-two")
        ).verify(destination)


def test_unprotect_hash_mismatch_is_rejected_without_publication(tmp_path: Path) -> None:
    source = _source(tmp_path)
    protected = tmp_path / "protected.bin"
    recovered = tmp_path / "recovered.bin"
    wrong_body = (
        "from pathlib import Path\n"
        "import sys\n"
        "Path(sys.argv[2]).write_bytes(b'wrong recovered fixture')\n"
    )
    service = BackupProtectionService(
        _adapter(tmp_path, unprotect_body=wrong_body)
    )
    service.protect(source, protected)

    with pytest.raises(BackupProtectionError, match="does not match source evidence"):
        service.unprotect(protected, recovered)

    assert not recovered.exists()
    assert source.read_bytes() == b"fictional portable backup fixture"
