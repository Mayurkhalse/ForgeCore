"""Unified resource selector managing multi-provider discovery, ranking, and budget enforcement."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from forgecore.core.budget import BudgetManager
from forgecore.core.models import ProjectConfig
from forgecore.core.resources.conflict import ConflictResolver
from forgecore.core.resources.models import (
    CompatibilityStatus,
    ConflictResolutionReport,
    EngineeringResource,
    PrecedenceTier,
    SelectionTrace,
)

if TYPE_CHECKING:
    from forgecore.core.providers.registry import ProviderRegistry

FRAMEWORK_FAMILIES = [
    {"fastapi", "django", "flask", "tornado", "laravel", "rails", "spring"},
    {"react", "vue", "angular", "svelte", "nuxt"},
    {"react-native", "flutter", "android", "ios", "swift", "kotlin"},
    {"postgres", "mysql", "clickhouse", "sqlite", "mongodb"},
    {"python", "php", "ruby", "java", "golang", "rust", "csharp", "cpp"},
]


class UnifiedResourceSelector:
    """Selects, filters, conflict-resolves, and budget-caps resources across all providers."""

    def __init__(
        self,
        registry: ProviderRegistry | None = None,
        budget_manager: BudgetManager | None = None,
    ) -> None:
        if registry is None:
            from forgecore.core.providers.registry import ProviderRegistry

            registry = ProviderRegistry.create_default()
        self.registry = registry
        self.budget_manager = budget_manager or BudgetManager()

    def _is_cross_framework_conflict(self, resource: EngineeringResource, active_layers: set[str]) -> bool:
        """Excludes resources belonging to competing frameworks within the same family."""
        res_stacks = set(resource.applicable_stacks)
        for fam in FRAMEWORK_FAMILIES:
            active_in_fam = fam.intersection(active_layers)
            if active_in_fam:
                res_in_fam = fam.intersection(res_stacks)
                if res_in_fam and not res_in_fam.intersection(active_in_fam):
                    return True
        return False

    def _matches_task_keywords(self, resource: EngineeringResource, task: str) -> bool:
        """Heuristic check matching resource name, tags, and description against user task prompt."""
        if not task:
            return True
        task_lower = task.lower()
        words = [w for w in re.findall(r"\b[a-z]{3,}\b", task_lower) if w not in ["the", "and", "for", "with"]]
        if not words:
            return True

        res_text = f"{resource.id} {resource.name} {resource.description} {' '.join(resource.tags)}".lower()
        return any(word in res_text for word in words)

    def _calculate_relevance(
        self,
        resource: EngineeringResource,
        active_layers: set[str],
        task: str,
    ) -> int:
        """Calculates dynamic relevance score based on stack specificity and task keywords."""
        score = resource.priority

        # Non-universal stack match bonus
        specific_layers = active_layers - {"universal", "all", "common"}
        matching_specific = set(resource.applicable_stacks).intersection(specific_layers)
        if matching_specific:
            score += 35 * len(matching_specific)

        # Task prompt keyword bonus
        if task:
            task_lower = task.lower()
            res_text = f"{resource.id} {resource.name} {resource.description} {' '.join(resource.tags)}".lower()
            stop_words = {"the", "and", "for", "with", "using", "build", "module", "from", "create", "make"}
            for word in re.findall(r"\b[a-z]{3,}\b", task_lower):
                if word in stop_words:
                    continue
                if word in res_text:
                    score += 20

        return score

    def select_resources(
        self,
        active_layers: list[str],
        task: str = "",
        task_type: str = "feature",
        config: ProjectConfig | None = None,
        max_tokens: int = 3000,
        max_resources: int = 20,
    ) -> tuple[list[EngineeringResource], SelectionTrace, ConflictResolutionReport]:
        """Discovers, filters, conflict-resolves, and budgets engineering resources across all providers.

        Ensures relevant ECC skills and native standards are provided while strictly excluding
        irrelevant or deferred knowledge.
        """
        all_resources = self.registry.list_all_resources()
        active_set = set(active_layers)

        trace = SelectionTrace(
            task=task,
            task_type=task_type,
            active_layers=active_layers,
            total_evaluated=len(all_resources),
            token_limit=max_tokens,
        )

        candidates: list[EngineeringResource] = []

        # 1. Candidate Filtering
        for res in all_resources:
            # Exclude deferred or unsupported capabilities from active prompt context
            if res.compatibility in [CompatibilityStatus.DEFERRED, CompatibilityStatus.UNSUPPORTED]:
                continue

            # Stack Applicability (Irrelevant stack exclusion)
            if not res.is_stack_applicable(active_set):
                continue

            # Cross-framework mutual exclusion
            if self._is_cross_framework_conflict(res, active_set):
                continue

            # Task Applicability
            if not res.is_task_applicable(task_type):
                continue

            # For Tier 6 ECC generic skills, verify relevance to prompt or task
            if res.precedence_tier == int(PrecedenceTier.TIER_6_ECC_GUIDANCE):
                if "all" in res.applicable_stacks and not self._matches_task_keywords(res, task):
                    continue

            candidates.append(res)

        # 2. Score candidates by relevance and precedence (with deterministic secondary sort key)
        candidates.sort(
            key=lambda r: (
                r.precedence_tier,
                -self._calculate_relevance(r, active_set, task),
                r.id,
            )
        )

        # 3. Conflict Resolution (Precedence Tiers 1-6)
        resolver = ConflictResolver(config=config)
        resolved_candidates, conflict_report = resolver.resolve_conflicts(candidates)

        trace.conflicts_resolved = [c.model_dump(mode="json") for c in conflict_report.resolved]
        if conflict_report.rejected_attempts:
            trace.conflicts_resolved.extend(conflict_report.rejected_attempts)

        # 4. Balanced Layered Token Budgeting (<3000 tokens)
        selected: list[EngineeringResource] = []
        current_tokens = 0
        truncated = False

        # Allocate budget: Contract mandatory, Native standards ~50%, ECC guidance ~50%
        target_native_budget = int(max_tokens * 0.50)
        native_tokens = 0

        # Separate items by tier
        tier3_contract = [r for r in resolved_candidates if r.precedence_tier <= int(PrecedenceTier.TIER_3_CORE_CONTRACT)]
        tier4_5_native = [
            r for r in resolved_candidates
            if r.precedence_tier in [int(PrecedenceTier.TIER_4_PROJECT_CONFIG), int(PrecedenceTier.TIER_5_NATIVE_STANDARDS)]
        ]
        tier6_ecc = [r for r in resolved_candidates if r.precedence_tier >= int(PrecedenceTier.TIER_6_ECC_GUIDANCE)]

        # 4a. Core Contract (Mandatory)
        for res in tier3_contract:
            content = self.registry.get_content(res)
            est = self.budget_manager.estimate_tokens(content[:1500]) if content else 50
            selected.append(res)
            current_tokens += est

        # 4b. Top Native Standards (up to ~50% of budget)
        for res in tier4_5_native:
            if len(selected) >= max_resources:
                truncated = True
                break
            content = self.registry.get_content(res)
            est = self.budget_manager.estimate_tokens(content) if content else 50
            if native_tokens + est > target_native_budget and native_tokens > 0:
                truncated = True
                continue
            if current_tokens + est > max_tokens:
                truncated = True
                break
            selected.append(res)
            native_tokens += est
            current_tokens += est

        # 4c. Top Relevant ECC Skills & Guidance (remaining budget)
        for res in tier6_ecc:
            if len(selected) >= max_resources:
                truncated = True
                break
            content = self.registry.get_content(res)
            # Use concise representation for skills (~400 tokens) in selection
            est = min(self.budget_manager.estimate_tokens(content), 400) if content else 50
            if current_tokens + est > max_tokens:
                truncated = True
                break
            selected.append(res)
            current_tokens += est

        trace.total_selected = len(selected)
        trace.selected_resources = [r.id for r in selected]
        trace.token_count = current_tokens
        trace.truncated = truncated

        return selected, trace, conflict_report
