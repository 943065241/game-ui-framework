from __future__ import annotations

import io
import json
import tarfile
import zipfile
from pathlib import Path

import pytest

from guif import __version__
from guif.beta_readiness import bootstrap_workspace
from guif.compatibility import compatibility_contract
from guif.hardening import HardeningService, SOAK_PROFILES
from guif.pillow_compat import flattened_image_data
from guif.release_provenance import (
    ReleaseProvenanceError,
    generate_hash_provenance,
    verify_hash_provenance,
)

PROJECT = "FictionalBeta2Game"
CONVERSATION = "conversation-beta2-fixture"
COMMIT = "a" * 40


class _ModernImage:
    def __init__(self) -> None:
        self.modern_called = False

    def get_flattened_data(self):
        self.modern_called = True
        return (1, 2, 3)

    def getdata(self):
        raise AssertionError("legacy Pillow API must not be used when the modern API exists")


class _LegacyImage:
    def __init__(self) -> None:
        self.legacy_called = False

    def getdata(self):
        self.legacy_called = True
        return (4, 5, 6)


def _write_wheel(path: Path, *, version: str = __version__) -> None:
    metadata = f"Metadata-Version: 2.1\nName: game-ui-framework\nVersion: {version}\n\n"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            f"game_ui_framework-{version}.dist-info/METADATA",
            metadata,
        )
        archive.writestr("guif/__init__.py", f'__version__ = "{version}"\n')


def _write_sdist(path: Path, *, version: str = __version__) -> None:
    metadata = f"Metadata-Version: 2.1\nName: game-ui-framework\nVersion: {version}\n\n".encode()
    root = f"game_ui_framework-{version}"
    with tarfile.open(path, "w:gz") as archive:
        canonical = tarfile.TarInfo(f"{root}/PKG-INFO")
        canonical.size = len(metadata)
        archive.addfile(canonical, io.BytesIO(metadata))

        # Setuptools can include this additional copy. Provenance must select
        # only the canonical top-level PKG-INFO member.
        nested = tarfile.TarInfo(f"{root}/game_ui_framework.egg-info/PKG-INFO")
        nested.size = len(metadata)
        archive.addfile(nested, io.BytesIO(metadata))


def _dist_fixture(tmp_path: Path, *, wheel_version: str = __version__) -> Path:
    dist = tmp_path / "dist"
    dist.mkdir()
    _write_wheel(dist / f"game_ui_framework-{wheel_version}-py3-none-any.whl", version=wheel_version)
    _write_sdist(dist / f"game_ui_framework-{__version__}.tar.gz")
    return dist


def test_pillow_compat_prefers_modern_flattened_data_api() -> None:
    image = _ModernImage()
    assert list(flattened_image_data(image)) == [1, 2, 3]
    assert image.modern_called is True


def test_pillow_compat_keeps_explicit_legacy_path() -> None:
    image = _LegacyImage()
    assert list(flattened_image_data(image)) == [4, 5, 6]
    assert image.legacy_called is True


def test_release_hash_provenance_round_trip(tmp_path: Path) -> None:
    dist = _dist_fixture(tmp_path)
    generated = generate_hash_provenance(dist, git_commit=COMMIT)
    manifest = dist / "SHA256SUMS.json"

    assert generated["status"] == "generated"
    assert generated["provenance_kind"] == "hash-only"
    assert generated["signature_present"] is False
    assert generated["attestation_present"] is False
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    assert payload["package"] == {
        "name": "game-ui-framework",
        "version": "1.0.0b2",
    }
    assert {item["artifact_type"] for item in payload["artifacts"]} == {"wheel", "sdist"}

    verified = verify_hash_provenance(
        manifest,
        dist_dir=dist,
        expected_git_commit=COMMIT,
    )
    assert verified["status"] == "verified"
    assert verified["artifact_count"] == 2


def test_release_hash_provenance_detects_tampered_artifact(tmp_path: Path) -> None:
    dist = _dist_fixture(tmp_path)
    generate_hash_provenance(dist, git_commit=COMMIT)
    wheel = next(dist.glob("*.whl"))
    wheel.write_bytes(wheel.read_bytes() + b"tampered")

    with pytest.raises(ReleaseProvenanceError, match="hash or size mismatch"):
        verify_hash_provenance(dist / "SHA256SUMS.json", dist_dir=dist)


def test_release_hash_provenance_rejects_wheel_sdist_version_mismatch(tmp_path: Path) -> None:
    dist = _dist_fixture(tmp_path, wheel_version="9.9.9")
    with pytest.raises(ReleaseProvenanceError, match="metadata must match"):
        generate_hash_provenance(dist, git_commit=COMMIT)


def test_release_hash_provenance_rejects_non_commit_identity(tmp_path: Path) -> None:
    dist = _dist_fixture(tmp_path)
    with pytest.raises(ReleaseProvenanceError, match="40- or 64-character"):
        generate_hash_provenance(dist, git_commit="abc123")


def test_soak_profiles_are_bounded_and_non_mutating(tmp_path: Path) -> None:
    boot = bootstrap_workspace(tmp_path, PROJECT, CONVERSATION)
    report_path = tmp_path / "reports" / "quick-soak.json"
    report = HardeningService(
        tmp_path,
        bearer_token=boot["bearer_token"],
    ).soak(
        PROJECT,
        conversation_id=CONVERSATION,
        profile="quick",
        max_p95_ms=5000,
        persist=False,
        report_path=report_path,
    )

    assert SOAK_PROFILES == {"quick": 10, "standard": 100, "extended": 1000}
    assert report["status"] == "passed"
    assert report["profile"] == "quick"
    assert report["iterations"] == 10
    assert report["production_state_mutated"] is False
    assert report["machine_readable"] is True
    assert report_path.is_file()
    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    assert persisted["production_state_mutated"] is False


def test_soak_threshold_failure_is_classified_as_environment_evidence(tmp_path: Path) -> None:
    bootstrap_workspace(tmp_path, PROJECT, CONVERSATION)
    report = HardeningService(tmp_path).soak(
        PROJECT,
        profile="quick",
        max_p95_ms=0.000001,
        persist=False,
    )

    assert report["status"] == "failed"
    assert report["failure_classification"] == "environment-performance-threshold"
    assert report["performance_threshold_failed"] is True
    assert report["product_correctness_failed"] is False
    assert "not by itself proof" in report["threshold_interpretation"]


def test_beta2_preserves_frozen_public_contract() -> None:
    contract = compatibility_contract()
    assert contract["release"] == "1.0.0-alpha.28"
    assert contract["origin_release"] == "1.0.0-alpha.28"
    assert contract["current_release"] == "1.0.0-beta.2"
    assert contract["channel"] == "beta"
    assert contract["public_api_version"] == 1
    assert contract["compatibility_policy"]["legacy_provider_adapter"] == (
        "preserved as explicit compatibility mode"
    )
