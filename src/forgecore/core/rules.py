from __future__ import annotations

from pathlib import Path

import yaml

from forgecore.core.budget import BudgetManager
from forgecore.core.models import ProjectConfig, Rule, Severity

CROSS_CUTTING_LAYERS = ["universal", "security", "testing", "api-design", "observability"]


class RuleLoader:
    """Discovers and parses YAML rules and profiles from the standards library."""

    def __init__(self, standards_dir: Path | str | None = None) -> None:
        if standards_dir:
            self.standards_dir = Path(standards_dir).resolve()
        else:
            # Default to bundled standards directory relative to package root
            repo_root = Path(__file__).resolve().parent.parent.parent.parent
            self.standards_dir = repo_root / "standards"

    def load_profiles(self) -> dict[str, list[str]]:
        """Loads profile YAML files mapping profile id to layers list."""
        profiles_dir = self.standards_dir / "profiles"
        profiles: dict[str, list[str]] = {}
        if not profiles_dir.is_dir():
            return profiles

        for p_file in profiles_dir.glob("*.yaml"):
            try:
                data = yaml.safe_load(p_file.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "id" in data and "layers" in data:
                    profiles[data["id"]] = data["layers"]
            except Exception:
                pass
        return profiles

    def load_all_rules(self) -> list[Rule]:
        """Loads and parses all rules from standards directory."""
        rules: list[Rule] = []
        if not self.standards_dir.is_dir():
            return rules

        for yaml_file in self.standards_dir.rglob("*.yaml"):
            # Skip profiles and verifiers directories
            rel_parts = yaml_file.relative_to(self.standards_dir).parts
            if "profiles" in rel_parts or "verifiers" in rel_parts:
                continue

            try:
                content = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and "id" in item:
                            rules.append(Rule.model_validate(item))
                elif isinstance(content, dict) and "id" in content:
                    rules.append(Rule.model_validate(content))
            except Exception:
                # In strict mode (lint-standards) this will be caught explicitly
                pass

        return rules


class RuleSelector:
    """Selects, filters, ranks, and budgets rules based on active layers and task context."""

    def __init__(
        self,
        rules: list[Rule],
        profiles: dict[str, list[str]] | None = None,
        budget_manager: BudgetManager | None = None,
    ) -> None:
        self.rules_by_id: dict[str, Rule] = {r.id: r for r in rules}
        self.all_rules = rules
        self.profiles = profiles or {}
        self.budget_manager = budget_manager or BudgetManager()

    def get_rule(self, rule_id: str) -> Rule | None:
        return self.rules_by_id.get(rule_id)

    def resolve_active_layers(
        self,
        detected_layers: list[str],
        config: ProjectConfig | None = None,
        profile_override: str | None = None,
        explicit_layers: list[str] | None = None,
    ) -> list[str]:
        """
        Calculates final active layers from profile, detection, config overrides, and explicit request.
        """
        active = set(CROSS_CUTTING_LAYERS)

        # Profile layers
        target_profile = profile_override or (config.profile if config else None)
        if target_profile and target_profile in self.profiles:
            active.update(self.profiles[target_profile])
        else:
            active.update(detected_layers)

        # Config add / remove
        if config:
            active.update(config.layers.add)
            for rm in config.layers.remove:
                active.discard(rm)

        # Explicit layers override if passed
        if explicit_layers:
            active = set(explicit_layers)

        return sorted(list(active))

    def select_rules(
        self,
        active_layers: list[str],
        task: str = "",
        task_type: str | None = None,
        config: ProjectConfig | None = None,
        max_rules: int = 15,
    ) -> tuple[list[Rule], bool, str | None]:
        """
        Selects matching rules, applies config overrides, resolves supersedes conflicts,
        ranks them by priority, and enforces context budget.
        """
        active_set = set(active_layers)
        disabled_ids = set()
        severity_overrides: dict[str, Severity] = {}

        if config:
            disabled_ids.update(config.rules.disable)
            for override in config.rules.overrides:
                if override.disabled:
                    disabled_ids.add(override.id)
                elif override.severity:
                    severity_overrides[override.id] = override.severity

        # 1. Filter applicable rules
        candidates: list[Rule] = []
        for r in self.all_rules:
            if r.id in disabled_ids:
                continue

            # Layer check
            if r.applies_when.layers:
                # Must match at least one or all? Schema states: applies_when.layers ⊆ active_layers
                # or rule's own layer is active
                if not set(r.applies_when.layers).issubset(active_set) and r.layer not in active_set:
                    continue
            elif r.layer not in active_set:
                continue

            # Task check
            if task_type and r.applies_when.tasks:
                if task_type not in r.applies_when.tasks:
                    continue

            # Apply severity override if any
            if r.id in severity_overrides:
                r_copy = r.model_copy()
                r_copy.severity = severity_overrides[r.id]
                candidates.append(r_copy)
            else:
                candidates.append(r)

        # 2. Conflict resolution (supersedes)
        superseded_ids = set()
        for r in candidates:
            for s_id in r.supersedes:
                superseded_ids.add(s_id)

        candidates = [r for r in candidates if r.id not in superseded_ids]

        # 3. Ranking
        def sort_key(rule: Rule) -> tuple[int, int, int]:
            # Higher severity weight first
            sev_rank = rule.severity.weight()
            # Higher tier first
            tier_rank = rule.tier.rank()
            # Specific stack layer over universal cross-cutting layer
            specificity = 2 if rule.layer not in CROSS_CUTTING_LAYERS else 1
            return (sev_rank, tier_rank, specificity)

        candidates.sort(key=sort_key, reverse=True)

        # 4. Enforce Budget
        return self.budget_manager.enforce_rules_budget(
            candidates,
            max_rules=max_rules,
            budget_name="get_standards",
        )
