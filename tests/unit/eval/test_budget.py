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


def test_can_dispatch_call_pre_dispatch_reservation():
    """Verifies FIN-01: worst-case reservation halts execution before dispatch."""
    mgr = LiveEvalBudgetManager()
    # Claude 3.5 Sonnet: $3/M in, $15/M out
    # 1000 input tokens = $0.003
    # 4000 output tokens = $0.060
    # Worst-case cost per call = $0.063
    config = LiveEvalConfig(cost_cap_usd=0.05, max_tokens_per_call=4000)

    # 1. Budget of $0.05 cannot afford worst-case $0.063
    allowed, reason = mgr.can_dispatch_call(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4000,
        estimated_input_tokens=1000,
        config=config,
    )
    assert allowed is False
    assert "Pre-dispatch budget reservation failed" in (reason or "")

    # 2. Generous budget allows dispatch
    generous_config = LiveEvalConfig(cost_cap_usd=5.00, max_tokens_per_call=4000)
    allowed_ok, reason_ok = mgr.can_dispatch_call(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4000,
        estimated_input_tokens=1000,
        config=generous_config,
    )
    assert allowed_ok is True
    assert reason_ok is None

    # 3. Token reservation check
    tight_token_config = LiveEvalConfig(max_total_tokens=2000, cost_cap_usd=10.0)
    allowed_tok, reason_tok = mgr.can_dispatch_call(
        model="mock-model",
        max_tokens=3000,
        estimated_input_tokens=500,
        config=tight_token_config,
    )
    assert allowed_tok is False
    assert "Pre-dispatch token reservation failed" in (reason_tok or "")


def test_record_usage_defensive_defaults():
    """Verifies FIN-01: missing or None token counts safely use defensive defaults without crashing."""
    mgr = LiveEvalBudgetManager()
    mgr.record_usage(
        model="claude-3-5-sonnet-20241022",
        prompt_tokens=None,
        completion_tokens=None,
    )
    summary = mgr.summary()
    assert summary["prompt_tokens"] == 1000
    assert summary["completion_tokens"] == 500
    assert summary["total_tokens"] == 1500
    assert summary["estimated_cost_usd"] > 0.0


