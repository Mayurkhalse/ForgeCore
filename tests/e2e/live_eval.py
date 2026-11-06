"""Layer 4: Live AI Coding Agent Evaluation Extension Point.

This module re-exports LiveAIEvaluationRunner from sarthi.eval.runner.
By default, live AI evaluations are disabled and decoupled from mandatory PR CI,
ensuring PR CI is 100% deterministic, offline, and zero-cost.
"""

from __future__ import annotations

from sarthi.eval.runner import LiveAIEvaluationRunner

__all__ = ["LiveAIEvaluationRunner"]
