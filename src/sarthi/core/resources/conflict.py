"""Deterministic conflict resolution engine implementing the 6-tier precedence hierarchy."""
from __future__ import annotations

from sarthi.core.models import ProjectConfig
from sarthi.core.resources.models import (
    ConflictResolutionReport,
    EngineeringResource,
    KnowledgeConflict,
    PrecedenceTier,
)


class ConflictResolver:
    """Enforces the reconciled 6-tier precedence hierarchy and resolves rule conflicts."""

    def __init__(self, config: ProjectConfig | None = None) -> None:
        self.config = config

    def resolve_conflicts(
        self,
        candidates: list[EngineeringResource],
    ) -> tuple[list[EngineeringResource], ConflictResolutionReport]:
        """Resolves conflicts among candidate resources using the 6-tier precedence hierarchy.

        Tier 1 (Security Invariants) > Tier 2 (Verifiers) > Tier 3 (Core Contract) >
        Tier 4 (Project Config) > Tier 5 (Native Standards) > Tier 6 (ECC Guidance).
        """
        report = ConflictResolutionReport()
        by_id: dict[str, EngineeringResource] = {r.id: r for r in candidates}
        suppressed_ids: set[str] = set()

        # 1. Check for explicit supersedes declarations
        for res in candidates:
            if not res.supersedes:
                continue

            for target_id in res.supersedes:
                target = by_id.get(target_id)
                if not target:
                    continue

                # Lower number = higher priority tier (Tier 1 > Tier 6)
                if res.precedence_tier <= target.precedence_tier:
                    # Valid override: higher or equal tier superseding lower tier
                    suppressed_ids.add(target_id)
                    conflict = KnowledgeConflict(
                        winner_id=res.id,
                        overridden_id=target_id,
                        winner_tier=res.precedence_tier,
                        overridden_tier=target.precedence_tier,
                        reason=(
                            f"Resource '{res.id}' (Tier {res.precedence_tier}) superseded "
                            f"'{target_id}' (Tier {target.precedence_tier}) via explicit declaration."
                        ),
                    )
                    report.resolved.append(conflict)
                else:
                    # Invalid override: lower tier attempting to override higher tier (e.g. ECC overriding Contract)
                    report.rejected_attempts.append({
                        "attempting_id": res.id,
                        "attempting_tier": res.precedence_tier,
                        "target_id": target_id,
                        "target_tier": target.precedence_tier,
                        "rejection_reason": (
                            f"Security Precedence Violation: Lower-priority resource '{res.id}' "
                            f"(Tier {res.precedence_tier}) cannot override higher-priority resource "
                            f"'{target_id}' (Tier {target.precedence_tier})."
                        ),
                    })

        # 2. Check for domain overlaps between Native standards (Tier 5) and ECC rules (Tier 6)
        # e.g. If native FastAPI/Security rules exist, subordinate overlapping generic ECC rules
        native_rules = [r for r in candidates if r.precedence_tier == int(PrecedenceTier.TIER_5_NATIVE_STANDARDS)]
        ecc_rules = [r for r in candidates if r.precedence_tier == int(PrecedenceTier.TIER_6_ECC_GUIDANCE)]

        for nr in native_rules:
            for er in ecc_rules:
                if er.id in suppressed_ids:
                    continue
                # Overlap detection: same specific stack and matching category or security topic
                if (
                    set(nr.applicable_stacks).intersection(set(er.applicable_stacks))
                    and (nr.category == er.category or ("security" in nr.tags and "security" in er.tags))
                ):
                    # Native machine-verified rule takes precedence over advisory ECC rule
                    if er.type == nr.type:
                        suppressed_ids.add(er.id)
                        conflict = KnowledgeConflict(
                            winner_id=nr.id,
                            overridden_id=er.id,
                            winner_tier=nr.precedence_tier,
                            overridden_tier=er.precedence_tier,
                            reason=(
                                f"Domain Precedence: Machine-verified Native Standard '{nr.id}' (Tier 5) "
                                f"takes precedence over advisory ECC guidance '{er.id}' (Tier 6)."
                            ),
                        )
                        report.resolved.append(conflict)

        # 3. Check for Project Config overrides (Tier 4)
        if self.config:
            # Check disabled rules
            for dis_id in self.config.rules.disable:
                target = by_id.get(dis_id)
                if not target:
                    continue

                # Project config cannot disable Tier 1 or Tier 3 (Core Contract / Inviolable Security)
                if target.precedence_tier in [
                    int(PrecedenceTier.TIER_1_SECURITY),
                    int(PrecedenceTier.TIER_3_CORE_CONTRACT),
                ]:
                    report.rejected_attempts.append({
                        "attempting_id": "project_config.rules.disable",
                        "attempting_tier": int(PrecedenceTier.TIER_4_PROJECT_CONFIG),
                        "target_id": dis_id,
                        "target_tier": target.precedence_tier,
                        "rejection_reason": (
                            f"Inviolable Governance: Project configuration cannot disable mandatory "
                            f"Tier {target.precedence_tier} rule '{dis_id}'."
                        ),
                    })
                else:
                    suppressed_ids.add(dis_id)
                    conflict = KnowledgeConflict(
                        winner_id="project_config.rules.disable",
                        overridden_id=dis_id,
                        winner_tier=int(PrecedenceTier.TIER_4_PROJECT_CONFIG),
                        overridden_tier=target.precedence_tier,
                        reason=f"Rule '{dis_id}' disabled by project configuration (.sarthi/project.yaml).",
                    )
                    report.resolved.append(conflict)

        # Filter out suppressed resources
        winning_resources = [r for r in candidates if r.id not in suppressed_ids]

        # Sort remaining by tier (ascending: 1 to 6), then by priority (descending: higher first)
        winning_resources.sort(key=lambda r: (r.precedence_tier, -r.priority))

        report.total_conflicts = len(report.resolved) + len(report.rejected_attempts)
        return winning_resources, report
