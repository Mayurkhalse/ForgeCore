from forgecore.core.models import (
    Category,
    ProjectConfig,
    Rule,
    RuleAppliesWhen,
    RuleOverride,
    Severity,
    Tier,
)
from forgecore.core.rules import RuleSelector


def test_rule_selector_ranking_and_filtering():
    r_core = Rule(
        id="TEST-001",
        title="Core Rule",
        layer="fastapi",
        category=Category.ARCHITECTURE,
        severity=Severity.HIGH,
        tier=Tier.CORE,
        applies_when=RuleAppliesWhen(layers=["fastapi"]),
        rule="Core statement",
    )
    r_standard = Rule(
        id="TEST-002",
        title="Standard Rule",
        layer="fastapi",
        category=Category.ARCHITECTURE,
        severity=Severity.CRITICAL,
        tier=Tier.STANDARD,
        applies_when=RuleAppliesWhen(layers=["fastapi"]),
        rule="Critical statement",
    )
    r_universal = Rule(
        id="UNI-001",
        title="Universal Rule",
        layer="universal",
        category=Category.ARCHITECTURE,
        severity=Severity.MEDIUM,
        tier=Tier.STANDARD,
        applies_when=RuleAppliesWhen(layers=["universal"]),
        rule="Universal statement",
    )

    selector = RuleSelector([r_core, r_standard, r_universal])
    selected, truncated, _ = selector.select_rules(
        active_layers=["universal", "fastapi"],
        task="create endpoint",
    )

    assert len(selected) == 3
    # Critical should rank ahead of High
    assert selected[0].id == "TEST-002"
    assert selected[1].id == "TEST-001"
    assert selected[2].id == "UNI-001"


def test_rule_selector_user_disables_and_overrides():
    r1 = Rule(
        id="RULE-1",
        title="Rule 1",
        layer="universal",
        category=Category.SECURITY,
        severity=Severity.HIGH,
        rule="Rule 1",
    )
    r2 = Rule(
        id="RULE-2",
        title="Rule 2",
        layer="universal",
        category=Category.SECURITY,
        severity=Severity.MEDIUM,
        rule="Rule 2",
    )

    config = ProjectConfig()
    config.rules.disable = ["RULE-1"]
    config.rules.overrides = [RuleOverride(id="RULE-2", severity=Severity.CRITICAL)]

    selector = RuleSelector([r1, r2])
    selected, _, _ = selector.select_rules(
        active_layers=["universal"],
        config=config,
    )

    assert len(selected) == 1
    assert selected[0].id == "RULE-2"
    assert selected[0].severity == Severity.CRITICAL


def test_rule_selector_supersedes():
    r_base = Rule(
        id="BASE-001",
        title="Base rule",
        layer="universal",
        category=Category.ARCHITECTURE,
        severity=Severity.MEDIUM,
        rule="Base rule statement",
    )
    r_spec = Rule(
        id="SPEC-001",
        title="Specific rule",
        layer="fastapi",
        category=Category.ARCHITECTURE,
        severity=Severity.HIGH,
        rule="Specific rule statement",
        supersedes=["BASE-001"],
    )

    selector = RuleSelector([r_base, r_spec])
    selected, _, _ = selector.select_rules(
        active_layers=["universal", "fastapi"],
    )

    assert len(selected) == 1
    assert selected[0].id == "SPEC-001"


def test_standards_summary_table_generation():
    import subprocess
    import sys

    from forgecore.core.standards_linter import StandardsLinter

    linter = StandardsLinter()
    table = linter.generate_summary_table()
    assert "| Layer / Stack | Total Rules | Machine Verifiers | Status in v0.1 |" in table
    assert "| `react` | 12 | 6 (ESLint) | **Stable** |" in table
    assert "| `fastapi` | 13 | 3 (1 Semgrep, 2 Ruff) | **Experimental**" in table
    assert "| `spring-boot` | 12 | 0 (guidance / checklist) | **Experimental**" in table

    # Verify scripts/count_rules.py executes and outputs the exact same table
    res = subprocess.run([sys.executable, "scripts/count_rules.py"], capture_output=True, text=True, check=True)
    assert res.stdout.strip() == table.strip()
