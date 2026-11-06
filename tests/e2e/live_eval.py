"""Layer 4: Live AI Coding Agent Evaluation Extension Point.

This module provides the architectural extension point for running live AI coding agent
evaluations against Sarthi. By default, live AI evaluations are disabled and decoupled
from mandatory PR CI, ensuring PR CI is 100% deterministic, offline, and zero-cost.

Activation requires:
1. Environment variable: SARTHI_LIVE_EVAL_ENABLED=1
2. Provider API key: ANTHROPIC_API_KEY, GEMINI_API_KEY, or OPENAI_API_KEY (or provider="mock")
3. Explicit execution and token/cost caps.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from sarthi.eval.config import LiveEvalConfig
from sarthi.eval.experiment import ComparativeEvaluationHarness, ExperimentResult
from sarthi.eval.providers import get_provider
from sarthi.eval.reporter import EvaluationReporter
from sarthi.eval.scenarios import (
    BENCHMARK_SCENARIOS,
    SCENARIO_FASTAPI_RATE_LIMIT,
    EvalScenario,
)


class LiveAIEvaluationRunner:
    """Extension runner for Layer 4 live model evaluations."""

    def __init__(self, config: LiveEvalConfig | None = None) -> None:
        self.config = config or LiveEvalConfig.from_env()
        self.harness = ComparativeEvaluationHarness()

    def is_enabled(self) -> bool:
        return self.config.enabled

    def check_prerequisites(self) -> tuple[bool, str]:
        return self.config.validate_credentials()

    def run_live_scenario(
        self,
        scenario: EvalScenario | str | None = None,
        workspace_parent: Path | None = None,
    ) -> dict[str, Any]:
        """Executes a live model evaluation scenario using the assembled prompt and context."""
        ready, reason = self.check_prerequisites()
        if not ready:
            return {
                "status": "skipped",
                "reason": reason,
                "cost_usd": 0.0,
            }

        target_scenario: EvalScenario
        if isinstance(scenario, str):
            target_scenario = BENCHMARK_SCENARIOS.get(scenario, SCENARIO_FASTAPI_RATE_LIMIT)
        elif isinstance(scenario, EvalScenario):
            target_scenario = scenario
        else:
            target_scenario = SCENARIO_FASTAPI_RATE_LIMIT

        provider = get_provider(self.config)

        if workspace_parent is None:
            temp_dir = tempfile.TemporaryDirectory(prefix="sarthi_live_eval_")
            work_dir = Path(temp_dir.name)
        else:
            work_dir = workspace_parent
            temp_dir = None

        try:
            exp_result: ExperimentResult = self.harness.run_experiment(
                scenario=target_scenario,
                provider=provider,
                config=self.config,
                parent_dir=work_dir,
            )

            # Save report to configured output directory
            json_path, md_path = EvaluationReporter.save_reports([exp_result], self.config.output_dir)

            return {
                "status": "executed",
                "scenario_id": target_scenario.id,
                "provider": self.config.provider,
                "model": self.config.model_name,
                "findings_reduction": exp_result.findings_delta,
                "sarthi_passed_cleanly": exp_result.sarthi.verify_report.status == "passed",
                "baseline_passed_cleanly": exp_result.baseline.verify_report.status == "passed",
                "json_report_path": str(json_path),
                "markdown_report_path": str(md_path),
                "result": exp_result.to_dict(),
            }
        finally:
            if temp_dir is not None:
                temp_dir.cleanup()
