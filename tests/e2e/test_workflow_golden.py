"""Golden End-to-End Workflow Scenario Test for Sarthi.

Exercises Stages A through I of Sarthi's pipeline against a realistic FastAPI login
microservice implementing rate limiting, verifying context detection, instruction delivery,
code simulation, and deterministic verification.
"""

from __future__ import annotations

from pathlib import Path

from forgecore.core.verify.trust import CommandTrustManager

from .fixtures import VALID_RATE_LIMIT_PATCH, create_login_api_fixture
from .host_adapter import DeterministicHostAgentAdapter
from .reporter import E2EScenarioReport

GOLDEN_PROMPT = (
    "Add rate limiting to the login API. Follow the existing project architecture, "
    "use secure defaults, handle invalid requests safely, add appropriate unit and integration tests, "
    "and update relevant documentation."
)


def test_golden_e2e_rate_limiting_workflow(tmp_path: Path):
    """Executes the full golden scenario pipeline from prompt to deterministic verification."""
    # 1. Setup isolated fixture and trust manager
    fixture_root = tmp_path / "login_service"
    trust_dir = tmp_path / "trust_store"
    trust_mgr = CommandTrustManager(trust_dir)

    create_login_api_fixture(fixture_root, trust_mgr=trust_mgr)

    # 2. Initialize host agent adapter
    adapter = DeterministicHostAgentAdapter(project_root=fixture_root, trust_mgr=trust_mgr)

    # 3. Execute Stages A through H
    trace, verify_report = adapter.run_workflow_pipeline(
        task_prompt=GOLDEN_PROMPT,
        patch=VALID_RATE_LIMIT_PATCH,
        task_type="feature",
        verify_scope="all",
    )

    # 4. Invariant Assertions
    # Stage B: Detection invariants
    context = trace.context_received
    assert context["status"] == "initialized"
    active_layers = context["active_layers"]
    assert "fastapi" in active_layers
    assert "security" in active_layers

    detected_stack = context["detected_stack"]
    assert "python" in detected_stack["languages"]
    assert "pytest" in detected_stack["test_frameworks"]

    # Stage C & D: Resource selection & Token budget
    standards = trace.standards_received
    assert len(standards) > 0
    rule_ids = [r["id"] for r in standards]
    assert any("FAPI" in rid or "SEC" in rid or "UNI" in rid for rid in rule_ids)

    # Stage E & F: Instruction invariants
    assert trace.is_all_assertions_passed()
    assert trace.instruction_assertions["core_contract_present"] is True
    assert trace.instruction_assertions["fastapi_layer_active"] is True
    assert trace.instruction_assertions["security_layer_active"] is True
    assert trace.instruction_assertions["testing_guidance_present"] is True

    # Stage G & H: Deterministic verification invariants
    assert verify_report["status"] == "passed", f"Verification failed with: {verify_report}"
    assert len(verify_report["findings"]) == 0
    assert "verification checks passed" in verify_report.get("next_action", "")
    assert "Ready for review" in verify_report.get("next_action", "")

    # 5. Build and validate 12-dimensional structured report
    report = E2EScenarioReport(
        scenario_id="E2E-GOLDEN-01",
        description="Golden Developer Scenario: Add rate limiting to login API",
        prompt=GOLDEN_PROMPT,
        detected_stack=detected_stack,
        active_layers=active_layers,
        context_state={"context_version": context.get("context_version")},
        selected_resources=rule_ids,
        instruction_validations=trace.instruction_assertions,
        token_budget={"rules_returned": len(standards), "truncated": False},
        host_interaction={"patch_summary": trace.applied_patch_summary},
        simulated_code_changes=trace.applied_patch_summary,
        verification_report=verify_report,
        expected_outcome="All verification checks pass and rate limiting protects login endpoint",
        actual_outcome=f"Status: {verify_report['status']}, Findings: {len(verify_report['findings'])}",
        passed=True,
    )

    # Save artifact report
    report_file = report.save_report(tmp_path / "reports")
    assert report_file.is_file()
    md_content = report.format_markdown()
    assert "PASS" in md_content
    assert "E2E-GOLDEN-01" in md_content
