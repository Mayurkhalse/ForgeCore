"""Unit tests for Live AI Evaluation Budget and Cost Management."""

from __future__ import annotations

import pytest

from sarthi.eval.budget import BudgetExceededError, LiveEvalBudgetManager
from sarthi.eval.config import LiveEvalConfig


def test_budget_manager_initial_state():
    mgr = LiveEvalBudgetManager()
    summary = mgr.summary()
    assert summary["prompt_tokens"] == 0
    assert summary["completion_tokens"] == 0
    assert summary["total_tokens"] == 0
    assert summary["estimated_cost_usd"] == 0.0
    assert summary["steps_count"] == 0
    assert summary["elapsed_seconds"] >= 0.0


def test_budget_manager_records_usage_and_cost():
    mgr = LiveEvalBudgetManager()
    # 100,000 input tokens, 20,000 output tokens for claude-3-5-sonnet ($3/M in, $15/M out)
    # 100k * 3/M = 0.30, 20k * 15/M = 0.30 -> Total $0.60
    mgr.record_usage(
        model="claude-3-5-sonnet-20241022",
        prompt_tokens=100_000,
        completion_tokens=20_000,
    )

    summary = mgr.summary()
    assert summary["prompt_tokens"] == 100_000
    assert summary["completion_tokens"] == 20_000
    assert summary["total_tokens"] == 120_000
    assert pytest.approx(summary["estimated_cost_usd"], 0.01) == 0.60


def test_budget_manager_cost_cap_enforcement():
    config = LiveEvalConfig(cost_cap_usd=0.25)
    mgr = LiveEvalBudgetManager()

    # Consuming $0.60 exceeds $0.25 cap
    with pytest.raises(BudgetExceededError, match="Cost cap exceeded"):
        mgr.record_usage(
            model="claude-3-5-sonnet-20241022",
            prompt_tokens=100_000,
            completion_tokens=20_000,
            config=config,
        )


def test_budget_manager_total_token_limit_enforcement():
    config = LiveEvalConfig(max_total_tokens=1000, cost_cap_usd=10.0)
    mgr = LiveEvalBudgetManager()

    with pytest.raises(BudgetExceededError, match="Token limit exceeded"):
        mgr.record_usage(
            model="mock-model",
            prompt_tokens=600,
            completion_tokens=500,
            config=config,
        )


def test_budget_manager_step_limit_enforcement():
    config = LiveEvalConfig(max_agent_steps=3)
    mgr = LiveEvalBudgetManager()

    mgr.record_step(config)
    mgr.record_step(config)
    mgr.record_step(config)

    with pytest.raises(BudgetExceededError, match="Agent step limit exceeded"):
        mgr.record_step(config)


def test_budget_manager_timeout_enforcement():
    config = LiveEvalConfig(timeout_seconds=0)  # Immediate expiry
    mgr = LiveEvalBudgetManager()
    # Artificial small elapsed time
    mgr.start_time -= 5.0

    exhausted, reason = mgr.check_budget_exhausted(config)
    assert exhausted is True
    assert "Wall-clock timeout exceeded" in (reason or "")

