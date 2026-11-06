"""Structured E2E Test Reporter for Sarthi.

Formats and outputs comprehensive observability records for each executed E2E scenario,
covering all 12 mandatory evaluation dimensions.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class E2EScenarioReport:
    """Complete 12-dimensional report for an E2E workflow scenario."""

    scenario_id: str
    description: str
    prompt: str
    detected_stack: dict[str, Any]
    active_layers: list[str]
    context_state: dict[str, Any]
    selected_resources: list[str]
    instruction_validations: dict[str, bool]
    token_budget: dict[str, Any]
    host_interaction: dict[str, Any]
    simulated_code_changes: str
    verification_report: dict[str, Any]
    expected_outcome: str
    actual_outcome: str
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def format_markdown(self) -> str:
        status_tag = "PASS" if self.passed else "FAIL"
        md = [
            f"# Scenario Report: [{status_tag}] {self.scenario_id}",
            f"**Description:** {self.description}\n",
            "### 1. Task Prompt",
            f"```\n{self.prompt}\n```\n",
            "### 2. Detected Stack & Active Layers",
            f"- **Stack:** {json.dumps(self.detected_stack)}",
            f"- **Active Layers:** {', '.join(self.active_layers)}\n",
            "### 3. Context & Resource Selection",
            f"- **Selected Rules ({len(self.selected_resources)}):** {', '.join(self.selected_resources)}",
            f"- **Token Budget Status:** {json.dumps(self.token_budget)}\n",
            "### 4. Instruction Invariants & Host Trace",
            f"- **Instruction Validations:** {json.dumps(self.instruction_validations, indent=2)}",
            f"- **Simulated Code Changes:** {self.simulated_code_changes}\n",
            "### 5. Verification & Final Status",
            f"- **Verification Status:** {self.verification_report.get('status', 'unknown')}",
            f"- **Findings Count:** {len(self.verification_report.get('findings', []))}",
            f"- **Expected Outcome:** {self.expected_outcome}",
            f"- **Actual Outcome:** {self.actual_outcome}",
            f"- **Overall Result:** **{status_tag}**",
        ]
        return "\n".join(md)

    def save_report(self, output_dir: Path | str) -> Path:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        file_path = out_path / f"{self.scenario_id}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        return file_path

