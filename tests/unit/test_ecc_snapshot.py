"""Unit tests for offline ECC v2.2.3 snapshot integrity and manifest."""

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
