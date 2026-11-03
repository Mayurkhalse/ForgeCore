from __future__ import annotations

from pathlib import Path

from forgecore.core.models import ChecklistItem, Finding, Rule, RunContext, VerifierType
from forgecore.core.verify.runners.base import Runner

MAX_CHECKLIST_ITEMS = 8


def compute_checklist_relevance(rule: Rule, changed_files: list[Path]) -> int:
    """Computes a deterministic relevance score for a rule against changed files."""
    if not changed_files:
        return 0

    score = 0
    file_strs = [str(f).lower().replace("\\", "/") for f in changed_files]
    suffixes = {f.suffix.lower() for f in changed_files}

    # 1. Layer-to-file matching
    layer = rule.layer.lower()
    if layer in ("fastapi", "python-ml") and ".py" in suffixes:
        score += 5
    elif layer in ("react", "react-native", "node-express") and any(
        ext in suffixes for ext in (".js", ".jsx", ".ts", ".tsx")
    ):
        score += 5
    elif layer == "testing" and any("test" in s for s in file_strs):
        score += 5
    elif layer == "database" and any(any(db_kw in s for db_kw in ("db", "sql", "migration", "model")) for s in file_strs):
        score += 5
    elif layer == "api-design" and any(
        any(api_kw in s for api_kw in ("api", "route", "endpoint", "controller")) for s in file_strs
    ):
        score += 5
    elif layer == "security" and any(
        any(sec_kw in s for sec_kw in ("auth", "security", "token", "cred", "login", "secret")) for s in file_strs
    ):
        score += 5

    # 2. Category matching
    cat = rule.category.value.lower()
    if cat == "testing" and any("test" in s for s in file_strs):
        score += 3
    elif cat == "security" and any(
        any(sec_kw in s for sec_kw in ("auth", "sec", "token", "cred", "pass", "key")) for s in file_strs
    ):
        score += 3
    elif cat == "api" and any(
        any(api_kw in s for api_kw in ("api", "route", "controller", "endpoint")) for s in file_strs
    ):
        score += 3

    # 3. Keyword / tag matching
    rule_keywords = set(rule.tags)
    rule_keywords.add(rule.layer.lower())
    rule_parts = rule.id.lower().split("-")
    rule_keywords.update(rule_parts)

    for kw in rule_keywords:
        if len(kw) >= 3:
            for s in file_strs:
                if kw in s:
                    score += 2
                    break

    return score


class ChecklistRunner(Runner):
    """Gathers checklist verification items that require agent or developer confirmation."""

    def __init__(self, rules: list[Rule] | None = None) -> None:
        self.rules = rules or []

    @property
    def name(self) -> str:
        return "checklist"

    @property
    def required(self) -> bool:
        return False

    def available(self, ctx: RunContext) -> bool:
        return True

    def get_checklist_items(self, ctx: RunContext) -> list[ChecklistItem]:
        checklist_rules = [
            r for r in self.rules if r.verify and r.verify.type == VerifierType.CHECKLIST
        ]

        # Rank by severity (descending), relevance to changed files (descending), and rule ID (ascending tie-breaker)
        sorted_rules = sorted(
            checklist_rules,
            key=lambda r: (
                -r.severity.weight(),
                -compute_checklist_relevance(r, ctx.changed_files),
                r.id,
            ),
        )

        capped_rules = sorted_rules[:MAX_CHECKLIST_ITEMS]

        items: list[ChecklistItem] = []
        for r in capped_rules:
            assert r.verify is not None
            prompt_text = r.verify.prompt or f"Confirm compliance with {r.id}: {r.title}"
            items.append(ChecklistItem(rule_id=r.id, prompt=prompt_text))
        return items

    def run(self, ctx: RunContext, files: list[Path]) -> list[Finding]:
        # Checklist items are returned in the VerifyReport's checklist field, not as error findings
        return []
