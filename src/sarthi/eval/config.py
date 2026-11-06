"""Configuration for Layer 4 Live AI Coding Agent Evaluation."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LiveEvalConfig:
    """Runtime configuration and security/budget bounds for live agent evaluation."""

    enabled: bool = False
    provider: str = "mock"
    model_name: str = "mock-model"
    max_tokens_per_call: int = 4096
    max_total_tokens: int = 16384
    cost_cap_usd: float = 0.50
    timeout_seconds: int = 180
    max_agent_steps: int = 6
    output_dir: Path = Path("eval_results")

    @classmethod
    def from_env(cls, output_dir: Path | None = None) -> LiveEvalConfig:
        """Resolves configuration from environment variables with safe defaults."""
        enabled = os.environ.get("SARTHI_LIVE_EVAL_ENABLED", "0").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        provider = os.environ.get("SARTHI_LIVE_EVAL_PROVIDER", "mock").strip().lower()
        model_name = os.environ.get("SARTHI_LIVE_EVAL_MODEL", "").strip()
        if not model_name:
            if provider == "anthropic":
                model_name = "claude-3-5-sonnet-20241022"
            elif provider == "gemini":
                model_name = "gemini-1.5-pro-latest"
            elif provider == "openai":
                model_name = "gpt-4o"
            else:
                model_name = "mock-model"

        try:
            cost_cap = float(os.environ.get("SARTHI_LIVE_EVAL_COST_CAP", "0.50"))
        except ValueError:
            cost_cap = 0.50

        try:
            timeout_sec = int(os.environ.get("SARTHI_LIVE_EVAL_TIMEOUT", "180"))
        except ValueError:
            timeout_sec = 180

        try:
            max_steps = int(os.environ.get("SARTHI_LIVE_EVAL_MAX_STEPS", "6"))
        except ValueError:
            max_steps = 6

        out_path = output_dir or Path(os.environ.get("SARTHI_LIVE_EVAL_OUTPUT_DIR", "eval_results"))

        return cls(
            enabled=enabled,
            provider=provider,
            model_name=model_name,
            cost_cap_usd=cost_cap,
            timeout_seconds=timeout_sec,
            max_agent_steps=max_steps,
            output_dir=out_path,
        )

    def validate_credentials(self) -> tuple[bool, str]:
        """Validates that necessary provider credentials are present."""
        if not self.enabled and self.provider != "mock":
            return False, "Live evaluation disabled (set SARTHI_LIVE_EVAL_ENABLED=1)"

        if self.provider == "mock":
            return True, "Mock provider requires no credentials"
        elif self.provider == "anthropic":
            if not os.environ.get("ANTHROPIC_API_KEY"):
                return False, "Missing ANTHROPIC_API_KEY environment variable"
        elif self.provider == "gemini":
            if not os.environ.get("GEMINI_API_KEY"):
                return False, "Missing GEMINI_API_KEY environment variable"
        elif self.provider == "openai":
            if not os.environ.get("OPENAI_API_KEY"):
                return False, "Missing OPENAI_API_KEY environment variable"
        else:
            return False, f"Unsupported provider: '{self.provider}'"

        return True, f"Credentials verified for provider '{self.provider}'"

