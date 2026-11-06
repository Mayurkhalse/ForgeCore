"""Generates machine-readable ECC traceability matrix JSON in resources/ecc/."""
from __future__ import annotations

import json
from pathlib import Path

from forgecore.core.providers.ecc import ECCBundledProvider

REPO_ROOT = Path(__file__).resolve().parent.parent
INVENTORY_FILE = REPO_ROOT / "resources" / "ecc" / "inventory.json"
MANIFEST_FILE = REPO_ROOT / "resources" / "ecc" / "manifest.json"
OUTPUT_FILE = REPO_ROOT / "resources" / "ecc" / "traceability-matrix.json"


def generate_json_matrix() -> None:
    with open(INVENTORY_FILE, "r", encoding="utf-8") as f:
        inv = json.load(f)

    with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
        _ = json.load(f)

    prov = ECCBundledProvider()
    prov.initialize()
    indexed_res = {r.id: r for r in prov.list_resources()}

    records = []
    for item in inv:
        up_path = item.get("upstream_path", "")
        res_type = item.get("resource_type", "supporting")
        decision = item.get("decision", "reject")
        sha256 = item.get("sha256", "")
        snap_path = item.get("snapshot_path", "")
        reason = item.get("reason", "")

        # Determine stable ID
        stable_id = None
        if decision == "include":
            for r_id, r in indexed_res.items():
                if r.source_path == snap_path:
                    stable_id = r_id
                    break
            if not stable_id:
                clean_name = Path(up_path).stem.replace("-", "_")
                stable_id = f"ecc.{res_type}.{clean_name}"
        elif decision == "defer":
            clean_up = up_path.replace("/", ".").replace("-", "_")
            stable_id = f"ecc.deferred.{clean_up}"
        else:
            clean_up = up_path.replace("/", ".").replace("-", "_")
            stable_id = f"ecc.rejected.{clean_up}"

        is_indexed = stable_id in indexed_res
        is_retrievable = is_indexed and decision == "include"

        # Adapter status
        if res_type in ["agent", "command"]:
            adapter_status = "adapted"
        elif res_type in ["rule", "skill", "context"]:
            adapter_status = "direct"
        elif res_type in ["workflow"]:
            adapter_status = "host_dependent"
        elif res_type in ["hook", "mcp_config"]:
            adapter_status = "unsupported"
        else:
            adapter_status = "documentation_only" if decision == "include" else "none"

        # Enforcement status
        if decision == "include":
            if res_type in ["rule", "skill"]:
                enforcement = "guidance_advisory"
            elif res_type in ["context"]:
                enforcement = "reference_only"
            elif res_type in ["command", "agent"]:
                enforcement = "prompt_template"
            else:
                enforcement = "passive_reference"
        elif decision == "defer":
            enforcement = "deferred_inactive"
        else:
            enforcement = "excluded"

        records.append({
            "resource_id": stable_id,
            "upstream_path": up_path,
            "resource_type": res_type,
            "upstream_sha256": sha256,
            "snapshot_path": snap_path if decision == "include" else None,
            "snapshot_sha256": sha256 if decision == "include" else None,
            "decision": decision,
            "decision_rationale": reason,
            "normalization": "EngineeringResource" if is_indexed else None,
            "registry_status": "indexed" if is_indexed else "not_indexed",
            "retrieval_status": "retrievable" if is_retrievable else "not_retrievable",
            "adapter_status": adapter_status,
            "runtime_status": "executable_via_context"
            if is_retrievable and res_type in ["rule", "skill"]
            else (
                "template_delivery"
                if is_retrievable and res_type in ["command", "agent"]
                else "documentation_only"
                if is_retrievable
                else "inactive"
            ),
            "enforcement_status": enforcement,
            "test_evidence": "tests/unit/test_ecc_normalization.py::test_ecc_normalization_resource_types"
            if is_indexed
            else "tests/unit/test_ecc_acquisition.py::test_ecc_acquisition_valid_snapshot",
        })

    traceability_data = {
        "schema_version": "1.0.0",
        "upstream_version": "v2.2.3",
        "upstream_commit": "c05b2d6614f62f6db0047669aa4eefb223d478f9",
        "total_evaluated": len(records),
        "summary": {
            "included": sum(1 for r in records if r["decision"] == "include"),
            "deferred": sum(1 for r in records if r["decision"] == "defer"),
            "rejected": sum(1 for r in records if r["decision"] == "reject"),
            "indexed": sum(1 for r in records if r["registry_status"] == "indexed"),
            "retrievable": sum(1 for r in records if r["retrieval_status"] == "retrievable"),
        },
        "items": records,
    }

    OUTPUT_FILE.write_text(json.dumps(traceability_data, indent=2), encoding="utf-8")
    print(f"Generated {OUTPUT_FILE} with {len(records)} items.")


if __name__ == "__main__":
    generate_json_matrix()

