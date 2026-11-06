"""Unit tests for A/B Comparative Evaluation Harness and Reporter."""

from __future__ import annotations

import json
from pathlib import Path

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
    assert "commit_sha" in parsed
    assert "ecc_version" in parsed
    assert "statistical_disclaimer" in parsed
    assert "Single-trial paired comparison (n=1)" in parsed["statistical_disclaimer"]

    # 2. Markdown Report
    md_str = EvaluationReporter.generate_markdown_report(results)
    assert "# Sarthi Layer 4: Live AI Coding Agent Evaluation Report" in md_str
    assert "Provenance & Metadata" in md_str
    assert "Statistical Disclaimer:" in md_str
    assert "Single-trial paired comparison (n=1)" in md_str
    assert SCENARIO_FASTAPI_RATE_LIMIT.id in md_str

    # 3. Save to disk
    out_dir = tmp_path / "output_reports"
    json_path, md_path = EvaluationReporter.save_reports(results, out_dir)
    assert json_path.is_file()
    assert md_path.is_file()
    assert json_path.stat().st_size > 0
    assert md_path.stat().st_size > 0


def test_evaluation_reporter_graceful_missing_git(tmp_path):
    """Verifies REP-01: unversioned workspaces handle missing commit SHAs gracefully."""
    harness = ComparativeEvaluationHarness()
    provider = MockProviderAdapter()
    config = LiveEvalConfig(max_agent_steps=1)
    work_dir = tmp_path / "reporter_no_git"

    result = harness.run_experiment(
        scenario=SCENARIO_FASTAPI_RATE_LIMIT,
        provider=provider,
        config=config,
        parent_dir=work_dir,
    )
    # Simulate missing git commit SHA
    result.commit_sha = None

    json_str = EvaluationReporter.generate_json_report([result])
    parsed = json.loads(json_str)
    assert parsed["commit_sha"] is None
    assert "Single-trial paired comparison (n=1)" in parsed["statistical_disclaimer"]

    md_str = EvaluationReporter.generate_markdown_report([result])
    assert "- **Repository Commit SHA:** `unknown`" in md_str
    assert "Single-trial paired comparison (n=1)" in md_str



def test_preapprove_test_commands_matches_test_runner(tmp_path):
    """Verifies ARCH-01: pre-approved command key 'test' matches TestRunner expectation."""
    from sarthi.core.models import ProjectConfig, RunContext
    from sarthi.core.verify.runners.tests import TestRunner
    from sarthi.core.verify.trust import CommandTrustManager

    workspace = tmp_path / "ws"
    workspace.mkdir()
    (workspace / "tests").mkdir()
    (workspace / "tests" / "test_dummy.py").write_text("def test_ok(): pass\n", encoding="utf-8")

    trust_mgr = CommandTrustManager(workspace / ".eval_approvals.json")
    harness = ComparativeEvaluationHarness()
    harness._preapprove_test_commands(workspace, trust_mgr)

    ctx = RunContext(
        project_root=workspace,
        config=ProjectConfig(project_name="eval_test"),
        active_layers=["universal"],
        task="verify",
        task_type="test",
        all_rules=[],
    )
    runner = TestRunner(trust_mgr=trust_mgr)
    trusted, reason = runner.check_trust(ctx)
    assert trusted is True, f"Command trust check failed: {reason}"


def test_benchmark_fixture_test_execution_and_failure_reporting(tmp_path):
    """Verifies EXP-01: benchmark fixture tests run, pass initially, and failing tests generate findings."""
    from sarthi.core.verify.trust import CommandTrustManager
    from sarthi.core.verify.verifier import Verifier
    from sarthi.eval.scenarios import SCENARIO_FASTAPI_RATE_LIMIT, stage_scenario_workspace

    ws = stage_scenario_workspace(
        scenario=SCENARIO_FASTAPI_RATE_LIMIT,
        destination_dir=tmp_path / "staged_app",
    )
    assert (ws / "tests" / "test_main.py").is_file()

    trust_mgr = CommandTrustManager(ws / ".eval_approvals.json")
    harness = ComparativeEvaluationHarness()
    harness._preapprove_test_commands(ws, trust_mgr)

    # 1. Clean verification: tests execute and pass
    verifier = Verifier(ws, trust_mgr=trust_mgr)
    report_pass = verifier.verify(scope="all")
    test_skipped = [s for s in report_pass.skipped if s.check == "tests"]
    assert len(test_skipped) == 0, "Tests check should NOT be skipped"
    assert report_pass.status in ("passed", "incomplete")

    # 2. Break main.py so test fails
    (ws / "main.py").write_text(
        "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/health')\ndef health():\n    return {'status': 'broken'}\n",
        encoding="utf-8",
    )
    report_fail = verifier.verify(scope="all")
    test_findings = [f for f in report_fail.findings if f.rule_id == "test.failure" or f.verifier == "tests"]
    assert len(test_findings) > 0, "Failing test must generate a test failure finding"
    assert report_fail.status == "failed"


def test_root_pytest_collection_excludes_fixtures_and_runs_in_test_runner(tmp_path: Path):
    """Verifies CFG-01: repo-root pytest collection excludes fixtures while TestRunner executes them."""
    from sarthi.core.models import ProjectConfig, RunContext
    from sarthi.core.verify.runners.tests import TestRunner
    from sarthi.core.verify.trust import CommandTrustManager

    # 1. Verify TestRunner executes against fixture directly
    fixture_root = Path(__file__).resolve().parent.parent.parent / "fixtures" / "fastapi_app"
    assert fixture_root.is_dir()
    assert (fixture_root / "tests" / "test_main.py").is_file()

    trust_mgr = CommandTrustManager(tmp_path / ".eval_approvals")
    harness = ComparativeEvaluationHarness()
    harness._preapprove_test_commands(fixture_root, trust_mgr)

    ctx = RunContext(
        project_root=fixture_root,
        config=ProjectConfig(project_name="fastapi_app"),
        active_layers=["fastapi"],
        task="verify",
        task_type="test",
        all_rules=[],
    )
    runner = TestRunner(trust_mgr=trust_mgr)
    findings = runner.run(ctx, [])
    assert len(findings) == 0, f"Clean fixture should pass with 0 findings, got: {findings}"


def test_evaluation_threshold_tampering_blocked(tmp_path: Path):
    """Verifies EXP-02: agent cannot weaken evaluation verification threshold via .sarthi/project.yaml."""
    from sarthi.core.models import Severity
    from sarthi.core.verify.trust import CommandTrustManager
    from sarthi.core.verify.verifier import Verifier
    from sarthi.eval.scenarios import BENCHMARK_SCENARIOS, stage_scenario_workspace

    scenario = BENCHMARK_SCENARIOS["FASTAPI-RATELIMIT-01"]
    ws = stage_scenario_workspace(scenario, tmp_path / "ws_tamper")

    trust_mgr = CommandTrustManager(tmp_path / "trust_store")
    harness = ComparativeEvaluationHarness()
    harness._preapprove_test_commands(ws, trust_mgr)

    # Add a failing test generating a HIGH finding (UNI-TEST-001)
    failing_test = ws / "tests" / "test_tamper_fail.py"
    failing_test.write_text("def test_will_fail():\n    assert False, 'Expected high-severity test failure'\n")

    # Agent tampers with .sarthi/project.yaml to set fail_on: critical (suppressing HIGH)
    project_yaml = ws / ".sarthi" / "project.yaml"
    project_yaml.parent.mkdir(parents=True, exist_ok=True)
    project_yaml.write_text(
        "project_name: fastapi_app\n"
        "verify:\n"
        "  fail_on: critical\n",
        encoding="utf-8",
    )

    # 1. Normal non-evaluation Verifier (no override) respects project.yaml threshold
    verifier_normal = Verifier(ws, trust_mgr=trust_mgr)
    report_normal = verifier_normal.verify(scope="all", timeout=45.0)
    assert any(f.severity == Severity.HIGH for f in report_normal.findings)
    # Because fail_on is CRITICAL, HIGH findings do not block in normal mode
    assert report_normal.status != "failed"

    # 2. Evaluation Verifier enforces immutable harness threshold (Severity.HIGH)
    verifier_eval = Verifier(ws, trust_mgr=trust_mgr, fail_on_override=Severity.HIGH)
    report_eval = verifier_eval.verify(scope="all", timeout=45.0)
    assert any(f.severity == Severity.HIGH for f in report_eval.findings)
    # Under evaluation override, HIGH findings cause verification failure
    assert report_eval.status == "failed"


def test_evaluation_harness_enforces_immutable_threshold_during_agent_tampering(tmp_path: Path):
    """Verifies EXP-02: ComparativeEvaluationHarness._execute_condition uses immutable threshold."""
    from sarthi.core.models import Severity
    from sarthi.eval.config import LiveEvalConfig
    from sarthi.eval.providers.base import LLMProviderAdapter, ProviderResponse, ToolCall
    from sarthi.eval.scenarios import BENCHMARK_SCENARIOS, stage_scenario_workspace

    scenario = BENCHMARK_SCENARIOS["FASTAPI-RATELIMIT-01"]
    ws = stage_scenario_workspace(scenario, tmp_path / "ws_harness_tamper")

    # A mock provider that simulates an adversarial agent:
    # Step 1: Write a failing test AND tamper with .sarthi/project.yaml to set fail_on: critical
    # Step 2: Complete the task
    class AdversarialTamperingProvider(LLMProviderAdapter):
        step = 0

        @property
        def name(self) -> str:
            return "adversarial-mock"

        def generate(self, messages, tools=None, max_tokens=4096, temperature=0.0):
            self.step += 1
            if self.step == 1:
                return ProviderResponse(
                    content="Tampering with config and adding failing test",
                    tool_calls=[
                        ToolCall(
                            id="tc1",
                            name="write_file",
                            arguments={
                                "path": ".sarthi/project.yaml",
                                "content": "project_name: fastapi_app\nverify:\n  fail_on: critical\n",
                            },
                        ),
                        ToolCall(
                            id="tc2",
                            name="write_file",
                            arguments={
                                "path": "tests/test_agent_fail.py",
                                "content": "def test_fail():\n    assert False, 'adversarial agent test fail'\n",
                            },
                        ),
                    ],
                    prompt_tokens=50,
                    completion_tokens=50,
                )
            return ProviderResponse(
                content="Task completed",
                tool_calls=[ToolCall(id="tc3", name="complete", arguments={"summary": "I am done"})],
                prompt_tokens=50,
                completion_tokens=50,
            )

    harness = ComparativeEvaluationHarness()
    cfg = LiveEvalConfig(max_agent_steps=5, cost_cap_usd=1.0)
    cond_res = harness._execute_condition(
        name="AdversarialTest",
        workspace_root=ws,
        system_prompt="system",
        user_prompt="user",
        provider=AdversarialTamperingProvider(),
        config=cfg,
    )

    # Even though .sarthi/project.yaml was overwritten with fail_on: critical,
    # the evaluation harness must report status == 'failed' due to the failing test
    assert any(f.severity == Severity.HIGH for f in cond_res.verify_report.findings)
    assert cond_res.verify_report.status == "failed"





