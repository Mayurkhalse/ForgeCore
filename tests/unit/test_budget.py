from sarthi.core.budget import BudgetManager
from sarthi.core.models import Category, Rule, Severity


def test_budget_manager_truncation():
    mgr = BudgetManager(budgets={"get_standards": 100})  # Tiny token cap ~400 chars

    rules = [
        Rule(
            id=f"RULE-{i}",
            title=f"Rule number {i}",
            layer="universal",
            category=Category.ARCHITECTURE,
            severity=Severity.HIGH,
            rule=f"Detailed rule statement for rule {i} with some extra padding to consume tokens...",
        )
        for i in range(10)
    ]

    selected, truncated, hint = mgr.enforce_rules_budget(rules, max_rules=15)
    assert len(selected) < 10
    assert truncated is True
    assert hint is not None
    assert "Call get_rule" in hint


def test_budget_manager_max_rules():
    mgr = BudgetManager(budgets={"get_standards": 50000})

    rules = [
        Rule(
            id=f"R-{i}",
            title=f"Rule {i}",
            layer="universal",
            category=Category.SECURITY,
            severity=Severity.LOW,
            rule="Short rule",
        )
        for i in range(20)
    ]

    selected, truncated, _ = mgr.enforce_rules_budget(rules, max_rules=5)
    assert len(selected) == 5
    assert truncated is True
