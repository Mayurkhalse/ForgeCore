"""Unit tests for offline ECC v2.2.3 snapshot integrity and manifest."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.verify_ecc_snapshot import (  # noqa: E402
    EXPECTED_COMMIT,
    EXPECTED_TAG,
    EXPECTED_TAG_OBJECT,
    verify_snapshot,
)


def test_ecc_snapshot_verification_invariants():
    """Validates all 10 snapshot verification invariants offline."""
    results = verify_snapshot(REPO_ROOT)

    for check, passed in results.items():
        assert passed is True, f"Snapshot invariant failed: {check}"


def test_ecc_manifest_schema_and_metadata():
    """Validates structure and required fields of manifest.json."""
    manifest_path = REPO_ROOT / "resources" / "ecc" / "manifest.json"
    assert manifest_path.is_file(), "manifest.json must exist"

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["schema_version"] == "1.0.0"

    upstream = manifest["upstream"]
    assert upstream["repository"] == "https://github.com/affaan-m/ECC.git"
    assert upstream["release_tag"] == EXPECTED_TAG
    assert upstream["release_tag_sha"] == EXPECTED_TAG_OBJECT
    assert upstream["commit_sha"] == EXPECTED_COMMIT
    assert upstream["abbreviated_commit"] == "c05b2d6"
    assert upstream["license"] == "MIT"

    summary = manifest["summary"]
    assert summary["counts_by_decision"]["include"] > 0
    assert summary["total_snapshot_files"] > 300


def test_ecc_license_and_notice_preservation():
    """Validates that MIT License and attribution notices are preserved."""
    ecc_dir = REPO_ROOT / "resources" / "ecc"

    license_file = ecc_dir / "LICENSE"
    notice_file = ecc_dir / "NOTICE"

    assert license_file.is_file()
    assert notice_file.is_file()

    license_text = license_file.read_text(encoding="utf-8")
    assert "Affaan Mustafa" in license_text
    assert "MIT License" in license_text

    notice_text = notice_file.read_text(encoding="utf-8")
    assert EXPECTED_COMMIT in notice_text


def _setup_mock_snapshot(base_dir: Path, commit_sha: str = EXPECTED_COMMIT) -> tuple[Path, Path]:
    """Helper to create a fully valid minimal mock ECC snapshot for negative testing."""
    ecc_dir = base_dir / "resources" / "ecc"
    ecc_dir.mkdir(parents=True, exist_ok=True)

    lic_content = "MIT License Affaan Mustafa"
    not_content = f"Notice with {commit_sha}"
    inv_content = "{}"
    sample_content = "# Sample resource content"

    (ecc_dir / "LICENSE").write_text(lic_content, encoding="utf-8")
    (ecc_dir / "NOTICE").write_text(not_content, encoding="utf-8")
    (ecc_dir / "inventory.json").write_text(inv_content, encoding="utf-8")

    sample_file = ecc_dir / "sample.md"
    sample_file.write_text(sample_content, encoding="utf-8")

    manifest = {
        "schema_version": "1.0.0",
        "upstream": {
            "repository": "https://github.com/affaan-m/ECC.git",
            "release_tag": EXPECTED_TAG,
            "release_tag_sha": EXPECTED_TAG_OBJECT,
            "commit_sha": commit_sha,
        },
        "files": {
            "sample.md": {"sha256": hashlib.sha256(sample_content.encode()).hexdigest()},
            "LICENSE": {"sha256": hashlib.sha256(lic_content.encode()).hexdigest()},
            "NOTICE": {"sha256": hashlib.sha256(not_content.encode()).hexdigest()},
            "inventory.json": {"sha256": hashlib.sha256(inv_content.encode()).hexdigest()},
        },
    }
    (ecc_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return base_dir, sample_file


def test_detects_corrupted_file(tmp_path: Path):
    """Negative Test: Verifier must detect modified file contents via SHA-256 mismatch."""
    repo_root, sample_file = _setup_mock_snapshot(tmp_path)
    sample_file.write_text("# Corrupted contents altering hash", encoding="utf-8")

    results = verify_snapshot(repo_root)
    assert results["5_checksums_match_identically"] is False


def test_detects_missing_file(tmp_path: Path):
    """Negative Test: Verifier must detect physically deleted files recorded in manifest."""
    repo_root, sample_file = _setup_mock_snapshot(tmp_path)
    sample_file.unlink()

    results = verify_snapshot(repo_root)
    assert results["3_all_recorded_files_exist"] is False


def test_detects_unexpected_file(tmp_path: Path):
    """Negative Test: Verifier must detect unrecorded extraneous files in snapshot dir."""
    repo_root, _ = _setup_mock_snapshot(tmp_path)
    rogue_file = repo_root / "resources" / "ecc" / "unrecorded_payload.sh"
    rogue_file.write_text("echo rogue", encoding="utf-8")

    results = verify_snapshot(repo_root)
    assert results["4_no_unexpected_files"] is False


def test_detects_invalid_commit_sha(tmp_path: Path):
    """Negative Test: Verifier must fail if pinned upstream commit SHA is tampered."""
    tampered_commit = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
    repo_root, _ = _setup_mock_snapshot(tmp_path, commit_sha=tampered_commit)

    results = verify_snapshot(repo_root)
    assert results["1_pinned_commit_verified"] is False


def test_detects_credential_leak(tmp_path: Path):
    """Negative Test: Verifier must detect credential/env files inside snapshot."""
    repo_root, _ = _setup_mock_snapshot(tmp_path)
    ecc_dir = repo_root / "resources" / "ecc"
    env_file = ecc_dir / ".env"
    env_file.write_text("SECRET=leaked", encoding="utf-8")

    manifest_path = ecc_dir / "manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    manifest["files"][".env"] = {"sha256": hashlib.sha256(b"SECRET=leaked").hexdigest()}
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f)

    results = verify_snapshot(repo_root)
    assert results["7_no_credentials_copied"] is False
