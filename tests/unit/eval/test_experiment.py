"""Unit tests for A/B Comparative Evaluation Harness and Reporter."""

from __future__ import annotations

import json

from sarthi.eval.config import LiveEvalConfig
from sarthi.eval.experiment import ComparativeEvaluationHarness, ExperimentResult
from sarthi.eval.providers.base import ProviderResponse, ToolCall
from sarthi.eval.providers.mock import MockProviderAdapter
from sarthi.eval.reporter import EvaluationReporter
from sarthi.eval.scenarios import SCENARIO_FASTAPI_RATE_LIMIT


def test_comparative_evaluation_harness(tmp_path):
    harness = ComparativeEvaluationHarness()
    provider = MockProviderAdapter()

    # Provide canned response so agent immediately signals task completion
    provider.enqueue_response(
        ProviderResponse(
            content="Task completed without edits.",
            tool_calls=[ToolCall(id="tc_c", name="complete_task", arguments={"summary": "all done"})],
            prompt_tokens=100,
            completion_tokens=20,
        )
    )
    provider.enqueue_response(
        ProviderResponse(
            content="Task completed without edits.",
            tool_calls=[ToolCall(id="tc_c2", name="complete_task", arguments={"summary": "all done"})],
            prompt_tokens=150,
            completion_tokens=30,
        )
    )

    config = LiveEvalConfig(max_agent_steps=2)
    work_dir = tmp_path / "exp_work"

    result = harness.run_experiment(
        scenario=SCENARIO_FASTAPI_RATE_LIMIT,
        provider=provider,
        config=config,
        parent_dir=work_dir,
    )

    assert isinstance(result, ExperimentResult)
    assert result.scenario.id == SCENARIO_FASTAPI_RATE_LIMIT.id
    assert result.baseline.condition_name == "Baseline"
    assert result.sarthi.condition_name == "Sarthi"
    assert result.baseline.trajectory.completed is True
    assert result.sarthi.trajectory.completed is True
    assert result.baseline.verify_report is not None
    assert result.sarthi.verify_report is not None

    d = result.to_dict()
    assert d["scenario_id"] == SCENARIO_FASTAPI_RATE_LIMIT.id
    assert "baseline" in d
    assert "sarthi" in d


def test_evaluation_reporter(tmp_path):
    harness = ComparativeEvaluationHarness()
    provider = MockProviderAdapter()
    config = LiveEvalConfig(max_agent_steps=1)
    work_dir = tmp_path / "reporter_work"

    result = harness.run_experiment(
        scenario=SCENARIO_FASTAPI_RATE_LIMIT,
        provider=provider,
        config=config,
        parent_dir=work_dir,
    )

    results = [result]

    # 1. JSON Report
    json_str = EvaluationReporter.generate_json_report(results)
    parsed = json.loads(json_str)
    assert parsed["version"] == "1.0.0"
    assert parsed["total_scenarios"] == 1
    assert len(parsed["experiments"]) == 1

    # 2. Markdown Report
    md_str = EvaluationReporter.generate_markdown_report(results)
    assert "# Sarthi Layer 4: Live AI Coding Agent Evaluation Report" in md_str
    assert SCENARIO_FASTAPI_RATE_LIMIT.id in md_str

    # 3. Save to disk
    out_dir = tmp_path / "output_reports"
    json_path, md_path = EvaluationReporter.save_reports(results, out_dir)
    assert json_path.is_file()
    assert md_path.is_file()
    assert json_path.stat().st_size > 0
    assert md_path.stat().st_size > 0

