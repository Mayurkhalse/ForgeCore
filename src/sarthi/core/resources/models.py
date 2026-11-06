"""Strongly typed polymorphic data models for engineering intelligence resources."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ResourceType(str, Enum):
    """Structural and functional classification of an engineering intelligence artifact."""

    RULE = "rule"
    SKILL = "skill"
    AGENT = "agent"
    COMMAND = "command"
    WORKFLOW = "workflow"
    CONTEXT = "context"
    HOOK = "hook"
    MCP_CONFIG = "mcp_config"
    SUPPORTING = "supporting"


class CompatibilityStatus(str, Enum):
    """Runtime portability across different host environments and IDEs."""

    NATIVE = "native"  # Runs natively across all IDEs via MCP text/prompt
    ADAPTED = "adapted"  # Adapted for Sarthi/Antigravity execution
    HOST_DEPENDENT = "host_dep"  # Requires specific host features (e.g., Claude Code subagents)
    DEFERRED = "deferred"  # Cataloged but inactive (e.g., shell hooks)
    UNSUPPORTED = "unsupported"  # Explicitly unsupported or dangerous


class TrustLevel(str, Enum):
    """Security trust level governing execution and override precedence."""

    CORE_SECURITY = "core_sec"  # Inviolable security and sandboxing invariants
    VERIFIED_NATIVE = "native"  # Native Sarthi standards and deterministic verifiers
    BUNDLED_ECC = "bundled_ecc"  # Pinned, audited ECC upstream resources
    WORKSPACE_LOCAL = "workspace"  # Project-specific local workspace rules


class Classification(str, Enum):
    """Source inventory classification required by Section 2 of ECC Integration."""

    DIRECTLY_REUSABLE = "directly_reusable"
    REQUIRES_NORMALIZATION = "requires_normalization"
    REQUIRES_ADAPTER = "requires_adapter"
    REQUIRES_UNSUPPORTED_CAPABILITY = "requires_unsupported_capability"
    DOCUMENTATION_ONLY = "documentation_only"
    EXCLUDED = "excluded"


class PrecedenceTier(int, Enum):
    """6-Tier Reconciled Precedence Hierarchy (Tier 1 is highest priority/inviolable)."""

    TIER_1_SECURITY = 1  # Mandatory Security & Sandboxing Invariants (Inviolable)
    TIER_2_VERIFICATION = 2  # Deterministic Machine Verification Outcomes (Hard Gate)
    TIER_3_CORE_CONTRACT = 3  # Mandatory Sarthi Core Contract Requirements (Core Governance)
    TIER_4_PROJECT_CONFIG = 4  # Project-Specific Requirements & Customizable Preferences
    TIER_5_NATIVE_STANDARDS = 5  # Sarthi Native Standards Library (85 YAML rules)
    TIER_6_ECC_GUIDANCE = 6  # Bundled ECC Engineering Guidance (Advisory)


class EngineeringResource(BaseModel):
    """Universal typed model for all engineering intelligence artifacts."""

    id: str = Field(..., description="Unique canonical identifier, e.g. 'ecc.skill.tdd-workflow'")
    provider_id: str = Field(..., description="Origin provider: 'native', 'ecc', 'workspace'")
    type: ResourceType = Field(..., description="Structural classification of the resource")
    classification: Classification = Field(
        default=Classification.DIRECTLY_REUSABLE,
        description="Source inventory classification",
    )
    name: str = Field(..., description="Human-readable title")
    description: str = Field(default="", description="Summary of capability or constraint")
    category: str = Field(default="general", description="Domain category, e.g. 'security', 'architecture'")

    # Provenance and Versioning
    source_path: str = Field(..., description="Path relative to bundle root")
    source_version: str = Field(default="2.2.3", description="Version of origin upstream")
    source_commit: str = Field(
        default="c05b2d6614f62f6db0047669aa4eefb223d478f9",
        description="Git commit SHA of origin snapshot",
    )
    license: str = Field(default="MIT", description="Applicable license")

    # Selection and Target Matching
    applicable_stacks: list[str] = Field(
        default_factory=list,
        description="Target layers: ['fastapi', 'react', 'python', 'universal']",
    )
    applicable_tasks: list[str] = Field(
        default_factory=list,
        description="Task types: ['feature', 'bugfix', 'refactor', 'new-project']",
    )
    tags: list[str] = Field(default_factory=list, description="Keywords for search and retrieval")
    dependencies: list[str] = Field(default_factory=list, description="IDs of prerequisite resources")
    required_tools: list[str] = Field(default_factory=list, description="Tools needed by the resource")
    required_capabilities: list[str] = Field(default_factory=list, description="Runtime host capabilities needed")

    # Execution & Safety Semantics
    compatibility: CompatibilityStatus = Field(default=CompatibilityStatus.NATIVE)
    trust_level: TrustLevel = Field(default=TrustLevel.BUNDLED_ECC)
    precedence_tier: int = Field(default=int(PrecedenceTier.TIER_6_ECC_GUIDANCE))
    priority: int = Field(default=10, description="Priority score within same tier (higher = more specific)")

    # Content Handling
    content_ref: str | None = Field(default=None, description="Path to markdown body or raw content")
    content_inline: str | None = Field(default=None, description="Inline content if small")

    # Conflict & Precedence
    supersedes: list[str] = Field(default_factory=list, description="Resource IDs overridden by this resource")
    activation_conditions: dict[str, Any] = Field(
        default_factory=dict,
        description="Dynamic conditions for resource activation",
    )

    def is_stack_applicable(self, active_layers: set[str]) -> bool:
        """Determines if the resource matches active architectural layers."""
        if not self.applicable_stacks or "all" in self.applicable_stacks or "universal" in self.applicable_stacks:
            return True
        return any(layer in active_layers for layer in self.applicable_stacks)

    def is_task_applicable(self, task_type: str | None) -> bool:
        """Determines if the resource matches the current task type."""
        if not task_type or not self.applicable_tasks or "all" in self.applicable_tasks:
            return True
        return task_type.lower() in [t.lower() for t in self.applicable_tasks]


class KnowledgeConflict(BaseModel):
    """Record of a resolved conflict between two overlapping knowledge resources."""

    winner_id: str
    overridden_id: str
    winner_tier: int
    overridden_tier: int
    reason: str


class ConflictResolutionReport(BaseModel):
    """Explainable conflict report detailing precedence decisions and rejected overrides."""

    total_conflicts: int = 0
    resolved: list[KnowledgeConflict] = Field(default_factory=list)
    rejected_attempts: list[dict[str, Any]] = Field(default_factory=list)


class SelectionTrace(BaseModel):
    """Deterministic trace of the knowledge selection and budgeting process."""

    task: str = ""
    task_type: str = ""
    active_layers: list[str] = Field(default_factory=list)
    total_evaluated: int = 0
    total_selected: int = 0
    selected_resources: list[str] = Field(default_factory=list)
    conflicts_resolved: list[dict[str, Any]] = Field(default_factory=list)
    token_count: int = 0
    token_limit: int = 3000
    truncated: bool = False


class CompiledContext(BaseModel):
    """Fully assembled, budget-enforced context payload delivered to the AI agent."""

    task_understanding: str
    active_layers: list[str] = Field(default_factory=list)
    security_invariants: list[str] = Field(default_factory=list)
    core_contract_rules: list[str] = Field(default_factory=list)
    native_standards: list[dict[str, Any]] = Field(default_factory=list)
    ecc_skills: list[dict[str, Any]] = Field(default_factory=list)
    ecc_commands: list[dict[str, Any]] = Field(default_factory=list)
    ecc_agents: list[dict[str, Any]] = Field(default_factory=list)
    verification_requirements: list[str] = Field(default_factory=list)
    provenance_records: list[dict[str, Any]] = Field(default_factory=list)
    selection_trace: SelectionTrace

