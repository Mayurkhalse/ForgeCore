from __future__ import annotations

from pathlib import Path

from forgecore.core.models import ChecklistItem, Finding, Rule, RunContext, VerifierType
from forgecore.core.verify.runners.base import Runner


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
        items: list[ChecklistItem] = []
        for r in self.rules:
            if r.verify and r.verify.type == VerifierType.CHECKLIST:
                prompt_text = r.verify.prompt or f"Confirm compliance with {r.id}: {r.title}"
                items.append(ChecklistItem(rule_id=r.id, prompt=prompt_text))
        return items

    def run(self, ctx: RunContext, files: list[Path]) -> list[Finding]:
        # Checklist items are returned in the VerifyReport's checklist field, not as error findings
        return []
