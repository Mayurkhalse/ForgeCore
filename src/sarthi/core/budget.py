from __future__ import annotations

import json
from typing import Any

from sarthi.core.models import Rule

DEFAULT_BUDGETS = {
    "core_contract": 2000,
    "initialize_project": 1500,
    "get_standards": 3000,
    "get_workflow": 1200,
}

MAX_RULES_DEFAULT = 15


class BudgetManager:
    """Manages token budgeting and truncates responses to prevent context pollution."""

    def __init__(self, budgets: dict[str, int] | None = None) -> None:
        self.budgets = dict(DEFAULT_BUDGETS)
        if budgets:
            self.budgets.update(budgets)

    @staticmethod
    def estimate_tokens(text_or_data: str | Any) -> int:
        """Approximates tokens as ceil(len(text) / 4)."""
        if isinstance(text_or_data, str):
            text = text_or_data
        else:
            text = json.dumps(text_or_data, default=str)
        return max(1, (len(text) + 3) // 4)

    def enforce_rules_budget(
        self,
        rules: list[Rule],
        max_rules: int = MAX_RULES_DEFAULT,
        budget_name: str = "get_standards",
    ) -> tuple[list[Rule], bool, str | None]:
        """
        Truncates the list of rules to fit within both max_rules and token budget.
        Returns: (selected_rules, truncated_flag, hint_message).
        """
        token_cap = self.budgets.get(budget_name, 3000)
        selected: list[Rule] = []
        truncated = False

        # First truncate by max_rules
        candidate_rules = rules[:max_rules]
        if len(rules) > max_rules:
            truncated = True

        # Truncate by token budget
        for rule in candidate_rules:
            rule_dict = rule.model_dump(mode="json")
            candidate_tokens = self.estimate_tokens([r.model_dump(mode="json") for r in selected] + [rule_dict])
            if candidate_tokens <= token_cap:
                selected.append(rule)
            else:
                truncated = True
                break

        hint = None
        if truncated:
            hint = (
                f"Showing {len(selected)} of {len(rules)} relevant rules within budget ({token_cap} tokens). "
                "Call get_rule(rule_id) for specific rule details, or specify narrower layers."
            )

        return selected, truncated, hint
