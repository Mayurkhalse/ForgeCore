"""Budget and Cost Tracking for Live AI Agent Evaluations."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from sarthi.eval.config import LiveEvalConfig

# Approximate rates per 1,000,000 tokens (USD)
MODEL_PRICING: dict[str, tuple[float, float]] = {
    # (cost_per_million_input, cost_per_million_output)
    "claude-3-5-sonnet-20241022": (3.00, 15.00),
    "claude-3-5-haiku-20241022": (0.80, 4.00),
    "gemini-1.5-pro-latest": (1.25, 5.00),
    "gemini-1.5-flash-latest": (0.075, 0.30),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "mock-model": (0.00, 0.00),
}


class BudgetExceededError(RuntimeError):
    """Raised when an agent evaluation run exceeds allocated token, cost, or step limits."""


@dataclass
class LiveEvalBudgetManager:
    """Enforces financial, token, step, and timeout constraints during evaluations."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    steps_count: int = 0
    start_time: float = field(default_factory=time.time)

    def calculate_call_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Estimates USD cost based on model token rates."""
        rates = MODEL_PRICING.get(model, (3.00, 15.00))  # Default to Claude 3.5 Sonnet rates as safe baseline
        input_cost = (prompt_tokens / 1_000_000.0) * rates[0]
        output_cost = (completion_tokens / 1_000_000.0) * rates[1]
        return input_cost + output_cost

    def can_dispatch_call(
        self,
        model: str,
        max_tokens: int,
        estimated_input_tokens: int = 1000,
        config: LiveEvalConfig | None = None,
    ) -> tuple[bool, str | None]:
        """Validates that remaining budget can cover worst-case call expenditure before dispatch."""
        if config is None:
            return True, None

        # 1. Elapsed time check
        if self.elapsed_seconds() > config.timeout_seconds:
            return False, f"Wall-clock timeout exceeded before dispatch: {self.elapsed_seconds():.1f}s > {config.timeout_seconds}s"

        # 2. Worst-case cost check
        worst_case_cost = self.calculate_call_cost(model, estimated_input_tokens, max_tokens)
        if self.estimated_cost_usd + worst_case_cost > config.cost_cap_usd:
            return False, (
                f"Pre-dispatch budget reservation failed: estimated worst-case cost "
                f"${worst_case_cost:.4f} exceeds remaining budget "
                f"(${max(0.0, config.cost_cap_usd - self.estimated_cost_usd):.4f})"
            )

        # 3. Worst-case token check
        worst_case_tokens = estimated_input_tokens + max_tokens
        if self.total_tokens + worst_case_tokens > config.max_total_tokens:
            return False, (
                f"Pre-dispatch token reservation failed: worst-case tokens "
                f"{worst_case_tokens} exceeds remaining allowance "
                f"({max(0, config.max_total_tokens - self.total_tokens)})"
            )

        return True, None

    def record_usage(
        self,
        model: str,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        config: LiveEvalConfig | None = None,
    ) -> None:
        """Records token consumption and updates financial cost."""
        safe_prompt = prompt_tokens if (prompt_tokens is not None and prompt_tokens >= 0) else 1000
        safe_completion = completion_tokens if (completion_tokens is not None and completion_tokens >= 0) else 500

        call_cost = self.calculate_call_cost(model, safe_prompt, safe_completion)
        self.prompt_tokens += safe_prompt
        self.completion_tokens += safe_completion
        self.total_tokens += safe_prompt + safe_completion
        self.estimated_cost_usd += call_cost

        if config is not None:
            exhausted, reason = self.check_budget_exhausted(config)
            if exhausted:
                raise BudgetExceededError(reason)

    def record_step(self, config: LiveEvalConfig | None = None) -> None:
        """Increments step count and validates limits."""
        self.steps_count += 1
        if config is not None:
            exhausted, reason = self.check_budget_exhausted(config)
            if exhausted:
                raise BudgetExceededError(reason)

    def elapsed_seconds(self) -> float:
        """Returns elapsed wall-clock seconds since budget initiation."""
        return time.time() - self.start_time

    def check_budget_exhausted(self, config: LiveEvalConfig) -> tuple[bool, str | None]:
        """Checks if any budget threshold has been exceeded."""
        if self.estimated_cost_usd > config.cost_cap_usd:
            return True, f"Cost cap exceeded: ${self.estimated_cost_usd:.4f} > ${config.cost_cap_usd:.2f}"

        if self.total_tokens > config.max_total_tokens:
            return True, f"Token limit exceeded: {self.total_tokens} > {config.max_total_tokens}"

        if self.steps_count > config.max_agent_steps:
            return True, f"Agent step limit exceeded: {self.steps_count} > {config.max_agent_steps}"

        if self.elapsed_seconds() > config.timeout_seconds:
            return True, f"Wall-clock timeout exceeded: {self.elapsed_seconds():.1f}s > {config.timeout_seconds}s"

        return False, None

    def summary(self) -> dict[str, Any]:
        """Returns dictionary summary of resource consumption."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 5),
            "steps_count": self.steps_count,
            "elapsed_seconds": round(self.elapsed_seconds(), 2),
        }

