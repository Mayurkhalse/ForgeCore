"""Tests for ECC knowledge acquisition, snapshot verification, and upstream change tracking."""
from __future__ import annotations

import json
from pathlib import Path

from forgecore.core.resources.lifecycle import ECCLifecycleManager


def test_ecc_acquisition_valid_snapshot():
    """Verifies that the pinned ECC v2.2.3 snapshot satisfies all 10 invariants."""
    mgr = ECCLifecycleManager()
    results = mgr.verify_integrity()
    assert all(results.values())
    assert results["1_pinned_commit_verified"] is True
    assert results["5_checksums_match_identically"] is True
    assert results["10_offline_verifiable"] is True


def test_ecc_acquisition_manifest_metadata():
    """Verifies upstream commit metadata, author, and licensing."""
    mgr = ECCLifecycleManager()
    manifest = mgr.load_manifest()

    assert manifest["schema_version"] == "1.0.0"
    upstream = manifest["upstream"]
    assert upstream["commit_sha"] == "c05b2d6614f62f6db0047669aa4eefb223d478f9"
    assert upstream["release_tag"] == "v2.2.3"
    assert upstream["license"] == "MIT"
    assert upstream["author"] == "Affaan Mustafa"


def test_ecc_acquisition_missing_source_assets(tmp_path: Path):
    """Detects missing assets when a required snapshot file is absent."""
    fake_ecc = tmp_path / "resources" / "ecc"
    fake_ecc.mkdir(parents=True)

    manifest_data = {
        "schema_version": "1.0.0",
        "upstream": {
            "commit_sha": ECCLifecycleManager.EXPECTED_COMMIT,
            "release_tag": ECCLifecycleManager.EXPECTED_TAG,
            "release_tag_sha": ECCLifecycleManager.EXPECTED_TAG_OBJECT,
        },
        "files": {
            "missing.md": {"sha256": "0" * 64},
        },
    }
    (fake_ecc / "manifest.json").write_text(json.dumps(manifest_data), encoding="utf-8")
    (fake_ecc / "inventory.json").write_text("[]", encoding="utf-8")
    (fake_ecc / "LICENSE").write_text("MIT", encoding="utf-8")
    (fake_ecc / "NOTICE").write_text(f"Notice {ECCLifecycleManager.EXPECTED_COMMIT}", encoding="utf-8")

    mgr = ECCLifecycleManager(repo_root=tmp_path)
    res = mgr.verify_integrity()
    assert res["3_all_recorded_files_exist"] is False


def test_ecc_acquisition_upstream_change_detection(tmp_path: Path):
    """Detects added, modified, and removed files when comparing against upstream candidate."""
    candidate_dir = tmp_path / "candidate_upstream"
    candidate_dir.mkdir()

    # Write a new added file
    (candidate_dir / "new_skill.md").write_text("# New upstream skill", encoding="utf-8")

    mgr = ECCLifecycleManager()
    diff = mgr.detect_changes(candidate_dir)

    assert diff["added_count"] >= 1
    assert "new_skill.md" in diff["added_files"]
    assert diff["removed_count"] > 300  # Pinned files absent in candidate
    assert diff["upstream_commit"] == ECCLifecycleManager.EXPECTED_COMMIT


def test_ecc_acquisition_traceability_metrics():
    """Validates the mathematical precision of the denominator-defined traceability report."""
    mgr = ECCLifecycleManager()
    report = mgr.generate_traceability_report()

    metrics = report["metrics"]
    assert metrics["discovery_coverage_percent"] == 100.0
    assert metrics["preservation_coverage_percent"] == 100.0
    assert metrics["total_upstream_evaluated"] == 962
    assert metrics["included_entries"] == 391
    assert metrics["deferred_entries"] == 248
    assert metrics["rejected_entries"] == 323
    assert metrics["runtime_accessibility_count"] > 500
