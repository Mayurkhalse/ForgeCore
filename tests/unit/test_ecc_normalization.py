"""Tests for ECC knowledge normalization, typed models, and schema validation."""
from __future__ import annotations

from forgecore.core.providers.ecc import ECCBundledProvider
from forgecore.core.providers.native import SarthiNativeProvider
from forgecore.core.resources.models import (
    Classification,
    CompatibilityStatus,
    PrecedenceTier,
    ResourceType,
    TrustLevel,
)


def test_normalization_all_resource_types_present():
    """Verifies that all 9 resource types are represented in the normalized catalog."""
    provider = ECCBundledProvider()
    provider.initialize()

    types_found = {r.type for r in provider.list_resources()}

    # All structural types should be indexed
    expected_types = {
        ResourceType.RULE,
        ResourceType.SKILL,
        ResourceType.AGENT,
        ResourceType.COMMAND,
        ResourceType.WORKFLOW,
        ResourceType.CONTEXT,
        ResourceType.HOOK,
        ResourceType.MCP_CONFIG,
        ResourceType.SUPPORTING,
    }
    assert expected_types.issubset(types_found), f"Missing types: {expected_types - types_found}"


def test_normalization_native_standards_mapping():
    """Verifies mapping of Sarthi 85 YAML standards and Core Contract into EngineeringResource."""
    native = SarthiNativeProvider()
    native.initialize()

    contract = native.get_resource("native.contract.core")
    assert contract is not None
    assert contract.type == ResourceType.RULE
    assert contract.precedence_tier == int(PrecedenceTier.TIER_3_CORE_CONTRACT)
    assert contract.trust_level == TrustLevel.CORE_SECURITY
    assert "16-Point" in contract.name

    # Check a sample YAML standard
    fapi_rule = native.get_resource("FAPI-ARCH-001")
    assert fapi_rule is not None
    assert fapi_rule.type == ResourceType.RULE
    assert fapi_rule.precedence_tier == int(PrecedenceTier.TIER_5_NATIVE_STANDARDS)
    assert fapi_rule.trust_level == TrustLevel.VERIFIED_NATIVE
    assert "fastapi" in fapi_rule.applicable_stacks


def test_normalization_ecc_skills_and_provenance():
    """Verifies normalization of ECC procedural skills with complete metadata and provenance."""
    provider = ECCBundledProvider()
    provider.initialize()

    tdd = provider.get_resource("ecc.skill.tdd-workflow")
    assert tdd is not None
    assert tdd.type == ResourceType.SKILL
    assert tdd.provider_id == "ecc"
    assert tdd.source_version == "2.2.3"
    assert tdd.source_commit == "c05b2d6614f62f6db0047669aa4eefb223d478f9"
    assert tdd.license == "MIT"
    assert tdd.compatibility == CompatibilityStatus.NATIVE
    assert tdd.precedence_tier == int(PrecedenceTier.TIER_6_ECC_GUIDANCE)
    assert "Test-driven development" in tdd.description
    assert len(provider.get_content(tdd)) > 5000  # Full text preserved


def test_normalization_ecc_commands_and_agents():
    """Verifies normalization of ECC slash commands and agent persona templates."""
    provider = ECCBundledProvider()
    provider.initialize()

    cmd = provider.get_resource("ecc.command.fastapi-review")
    assert cmd is not None
    assert cmd.type == ResourceType.COMMAND
    assert cmd.compatibility == CompatibilityStatus.ADAPTED
    assert "FastAPI" in cmd.description

    agent = provider.get_resource("ecc.agent.planner")
    assert agent is not None
    assert agent.type == ResourceType.AGENT
    assert agent.compatibility == CompatibilityStatus.ADAPTED
    assert len(agent.required_tools) > 0


def test_normalization_deferred_hooks_and_mcp_safety():
    """Verifies that ECC hooks and external SaaS MCP configs are cataloged as DEFERRED."""
    provider = ECCBundledProvider()
    provider.initialize()

    hooks = [r for r in provider.list_resources(ResourceType.HOOK)]
    assert len(hooks) > 0
    for h in hooks:
        assert h.compatibility == CompatibilityStatus.DEFERRED
        assert h.classification == Classification.REQUIRES_UNSUPPORTED_CAPABILITY

    mcps = [r for r in provider.list_resources(ResourceType.MCP_CONFIG)]
    assert len(mcps) > 0
    for m in mcps:
        assert m.compatibility == CompatibilityStatus.DEFERRED


def test_normalization_malformed_frontmatter_resilience():
    """Verifies that malformed frontmatter in markdown files does not crash provider initialization."""
    provider = ECCBundledProvider()
    malformed_text = "---\ninvalid: [yaml\n---\n# Title\nBody"
    fm, body = provider._parse_frontmatter(malformed_text)
    assert fm == {}
    assert "Title" in body
