"""A/B Comparative Evaluation Harness for Layer 4."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sarthi.core.config import ConfigLoader
from sarthi.core.models import VerifyReport
from sarthi.core.verify.trust import CommandTrustManager
from sarthi.core.verify.verifier import Verifier
from sarthi.eval.agent import AgentTrajectory, SandboxedAgentLoop
from sarthi.eval.budget import LiveEvalBudgetManager
from sarthi.eval.config import LiveEvalConfig
from sarthi.eval.providers.base import LLMProviderAdapter
from sarthi.eval.scenarios import (
    EvalScenario,
    prepare_condition_prompts,
    stage_scenario_workspace,
)


@dataclass
class ConditionResult:
    """Execution and verification outcome for one experimental condition."""

    condition_name: str  # "Baseline" or "Sarthi"
    workspace_root: Path
    trajectory: AgentTrajectory
    verify_report: VerifyReport
    duration_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "condition_name": self.condition_name,
            "steps": self.trajectory.steps,
            "completed": self.trajectory.completed,
            "tool_calls_count": self.trajectory.tool_calls_count,
            "error": self.trajectory.error,
            "budget_summary": self.trajectory.budget_summary,
            "verification_status": self.verify_report.status,
            "findings_count": len(self.verify_report.findings),
            "findings": [
                {
                    "rule_id": f.rule_id,
                    "severity": f.severity,
                    "file": f.file,
                    "message": f.message,
                }
                for f in self.verify_report.findings
            ],
            "skipped_checks": [
                {"check": sc.check, "reason": sc.reason, "required": sc.required}
                for sc in self.verify_report.skipped
            ],
            "duration_seconds": round(self.duration_seconds, 2),
        }


@dataclass
class ExperimentResult:
    """Comparative outcome between Baseline and Sarthi-guided agent runs."""

    scenario: EvalScenario
    provider_name: str
    model_name: str
    baseline: ConditionResult
    sarthi: ConditionResult
    timestamp: float = 0.0

    @property
    def findings_delta(self) -> int:
        """Reduction in verification findings achieved by Sarthi (positive = improvement)."""
        return len(self.baseline.verify_report.findings) - len(self.sarthi.verify_report.findings)

    @property
    def passed_cleanly_delta(self) -> bool:
        """True if Sarthi passed cleanly while baseline failed or remained incomplete."""
        return self.sarthi.verify_report.status == "passed" and self.baseline.verify_report.status != "passed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario.id,
            "scenario_title": self.scenario.title,
            "provider": self.provider_name,
            "model": self.model_name,
            "findings_reduction": self.findings_delta,
            "sarthi_passed_cleanly": self.sarthi.verify_report.status == "passed",
            "baseline_passed_cleanly": self.baseline.verify_report.status == "passed",
            "baseline": self.baseline.to_dict(),
            "sarthi": self.sarthi.to_dict(),
            "timestamp": self.timestamp or time.time(),
        }


class ComparativeEvaluationHarness:
    """Orchestrates side-by-side A/B evaluation runs."""

    def _preapprove_test_commands(self, workspace_root: Path, trust_mgr: CommandTrustManager) -> None:
        """Pre-approves default/configured test commands in the ephemeral test workspace."""
        config_loader = ConfigLoader(workspace_root)
        cfg = config_loader.load()
        if cfg.verify and cfg.verify.commands:
            trust_mgr.approve(workspace_root, cfg.verify.commands)
        else:
            # Default test command for python/pytest
            trust_mgr.approve(workspace_root, {"tests": "pytest -q"})

    def _execute_condition(
        self,
        name: str,
        workspace_root: Path,
        system_prompt: str,
        user_prompt: str,
        provider: LLMProviderAdapter,
        config: LiveEvalConfig,
    ) -> ConditionResult:
        start_t = time.perf_counter()

        # Ephemeral isolated trust store
        trust_mgr = CommandTrustManager(workspace_root / ".eval_approvals.json")
        self._preapprove_test_commands(workspace_root, trust_mgr)

        budget_mgr = LiveEvalBudgetManager()
        loop = SandboxedAgentLoop(workspace_root)

        trajectory = loop.run(
            provider=provider,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            budget_manager=budget_mgr,
            config=config,
        )

        # Deterministic verification of the workspace state
        verifier = Verifier(workspace_root, trust_mgr=trust_mgr)
        verify_report = verifier.verify(scope="all", timeout=45.0)

        elapsed = time.perf_counter() - start_t
        return ConditionResult(
            condition_name=name,
            workspace_root=workspace_root,
            trajectory=trajectory,
            verify_report=verify_report,
            duration_seconds=elapsed,
        )

    def run_experiment(
        self,
        scenario: EvalScenario,
        provider: LLMProviderAdapter,
        config: LiveEvalConfig,
        parent_dir: Path,
    ) -> ExperimentResult:
        """Executes Condition A (Baseline) and Condition B (Sarthi) on clean workspace copies."""
        parent_dir = parent_dir.resolve()
        parent_dir.mkdir(parents=True, exist_ok=True)

        ws_baseline = stage_scenario_workspace(
            scenario=scenario,
            destination_dir=parent_dir / f"{scenario.id}_baseline",
        )
        ws_sarthi = stage_scenario_workspace(
            scenario=scenario,
            destination_dir=parent_dir / f"{scenario.id}_sarthi",
        )

        # Prepare condition-specific prompts
        (base_sys, base_user), (sarthi_sys, sarthi_user) = prepare_condition_prompts(scenario, ws_sarthi)

        # Execute Condition A: Baseline
        res_baseline = self._execute_condition(
            name="Baseline",
            workspace_root=ws_baseline,
            system_prompt=base_sys,
            user_prompt=base_user,
            provider=provider,
            config=config,
        )

        # Execute Condition B: Sarthi-Guided
        res_sarthi = self._execute_condition(
            name="Sarthi",
            workspace_root=ws_sarthi,
            system_prompt=sarthi_sys,
            user_prompt=sarthi_user,
            provider=provider,
            config=config,
        )

        model_name = getattr(provider, "model", config.model_name)
        return ExperimentResult(
            scenario=scenario,
            provider_name=provider.name,
            model_name=model_name,
            baseline=res_baseline,
            sarthi=res_sarthi,
            timestamp=time.time(),
        )
