"""Tests for 6-tier precedence hierarchy and explainable conflict resolution."""
from __future__ import annotations

from sarthi.core.models import ProjectConfig, RulesConfig
from sarthi.core.resources.conflict import ConflictResolver
from sarthi.core.resources.models import (
    EngineeringResource,
    PrecedenceTier,
    ResourceType,
    TrustLevel,
)


def test_conflict_security_inviolability():
    """Verifies that project configuration CANNOT disable Tier 1 Security or Tier 3 Core Contract."""
    config = ProjectConfig(
        rules=RulesConfig(disable=["native.contract.core", "UNI-SEC-001"])
    )
    resolver = ConflictResolver(config=config)

    contract_res = EngineeringResource(
        id="native.contract.core",
        provider_id="native",
        type=ResourceType.RULE,
        name="Core Contract",
        source_path="standards/contract.md",
        precedence_tier=int(PrecedenceTier.TIER_3_CORE_CONTRACT),
        trust_level=TrustLevel.CORE_SECURITY,
    )

    remaining, report = resolver.resolve_conflicts([contract_res])

    # Inviolable: Contract must NOT be suppressed
    assert len(remaining) == 1
    assert remaining[0].id == "native.contract.core"
    assert len(report.rejected_attempts) == 1
    assert "Inviolable Governance" in report.rejected_attempts[0]["rejection_reason"]


def test_conflict_lower_tier_cannot_supersede_higher_tier():
    """Verifies that an ECC rule (Tier 6) cannot supersede a Native standard (Tier 5) or Contract (Tier 3)."""
    resolver = ConflictResolver()

    native_std = EngineeringResource(
        id="FAPI-SEC-001",
        provider_id="native",
        type=ResourceType.RULE,
        name="FastAPI Security",
        source_path="standards/fastapi/FAPI-SEC-001.yaml",
        precedence_tier=int(PrecedenceTier.TIER_5_NATIVE_STANDARDS),
    )

    rogue_ecc = EngineeringResource(
        id="ecc.rule.rogue-override",
        provider_id="ecc",
        type=ResourceType.RULE,
        name="Rogue ECC Rule",
        source_path="rules/python/rogue.md",
        precedence_tier=int(PrecedenceTier.TIER_6_ECC_GUIDANCE),
        supersedes=["FAPI-SEC-001"],  # Attempt to override native rule
    )

    remaining, report = resolver.resolve_conflicts([native_std, rogue_ecc])

    # FAPI-SEC-001 must NOT be overridden
    remaining_ids = [r.id for r in remaining]
    assert "FAPI-SEC-001" in remaining_ids
    assert len(report.rejected_attempts) == 1
    assert "Security Precedence Violation" in report.rejected_attempts[0]["rejection_reason"]


def test_conflict_valid_higher_tier_supersedes_lower():
    """Verifies that a higher tier resource cleanly supersedes a lower tier resource."""
    resolver = ConflictResolver()

    project_rule = EngineeringResource(
        id="workspace.fastapi-custom",
        provider_id="workspace",
        type=ResourceType.RULE,
        name="Custom FastAPI Rule",
        source_path=".sarthi/rules/fastapi.yaml",
        precedence_tier=int(PrecedenceTier.TIER_4_PROJECT_CONFIG),
        supersedes=["ecc.rule.python.fastapi"],
    )

    ecc_rule = EngineeringResource(
        id="ecc.rule.python.fastapi",
        provider_id="ecc",
        type=ResourceType.RULE,
        name="ECC Python FastAPI",
        source_path="rules/python/fastapi.md",
        precedence_tier=int(PrecedenceTier.TIER_6_ECC_GUIDANCE),
    )

    remaining, report = resolver.resolve_conflicts([project_rule, ecc_rule])

    remaining_ids = [r.id for r in remaining]
    assert "workspace.fastapi-custom" in remaining_ids
    assert "ecc.rule.python.fastapi" not in remaining_ids
    assert len(report.resolved) == 1
    assert report.resolved[0].winner_id == "workspace.fastapi-custom"


def test_conflict_domain_overlap_native_over_ecc():
    """Verifies that machine-verified Native standards take precedence over overlapping generic ECC rules."""
    resolver = ConflictResolver()

    native_sec = EngineeringResource(
        id="UNI-SEC-001",
        provider_id="native",
        type=ResourceType.RULE,
        name="Universal Secrets Detection",
        category="security",
        applicable_stacks=["universal"],
        source_path="standards/universal/UNI-SEC-001.yaml",
        precedence_tier=int(PrecedenceTier.TIER_5_NATIVE_STANDARDS),
        tags=["security"],
    )

    ecc_sec = EngineeringResource(
        id="ecc.rule.common.security",
        provider_id="ecc",
        type=ResourceType.RULE,
        name="Common Security Advice",
        category="security",
        applicable_stacks=["universal"],
        source_path="rules/common/security.md",
        precedence_tier=int(PrecedenceTier.TIER_6_ECC_GUIDANCE),
        tags=["security"],
    )

    remaining, report = resolver.resolve_conflicts([native_sec, ecc_sec])

    remaining_ids = [r.id for r in remaining]
    assert "UNI-SEC-001" in remaining_ids
    assert "ecc.rule.common.security" not in remaining_ids
    assert any(c.winner_id == "UNI-SEC-001" for c in report.resolved)
