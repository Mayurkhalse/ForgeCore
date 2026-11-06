from pathlib import Path

from sarthi.core.models import Severity
from sarthi.core.verify.verifier import Verifier

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def test_verifier_catches_hardcoded_secrets():
    root = FIXTURES_DIR / "violations_app"
    verifier = Verifier(root)
    report = verifier.verify(scope="all")

    assert report.status == "failed"
    assert report.summary["critical"] > 0

    secret_findings = [f for f in report.findings if f.rule_id == "UNI-SEC-001"]
    assert len(secret_findings) > 0
    assert "AKIA1234567890ABCDEF" not in secret_findings[0].message  # Secret value never leaked!
    assert "auth.py" in secret_findings[0].file
    assert secret_findings[0].line == 2
    assert secret_findings[0].severity == Severity.CRITICAL


def test_verifier_clean_fixture():
    root = FIXTURES_DIR / "fastapi_app"
    verifier = Verifier(root)
    report = verifier.verify(scope="all")

    # fastapi_app has no seeded violations, so findings should be 0 critical/high
    assert report.summary["critical"] == 0
    assert report.summary["high"] == 0
    # Status may be incomplete if semgrep is not installed, but not failed!
    assert report.status in ("passed", "incomplete")


def test_ruff_runner_force_exclude_respects_config(tmp_path: Path) -> None:
    """Verifies RuffRunner passes --force-exclude so pyproject.toml exclusions are respected."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test-proj"\nversion = "0.1.0"\n\n[tool.ruff]\nextend-exclude = ["excluded_subdir/*.py"]\n',
        encoding="utf-8",
    )
    excluded_dir = tmp_path / "excluded_subdir"
    excluded_dir.mkdir(parents=True)
    bad_file = excluded_dir / "bad.py"
    bad_file.write_text("undefined_function_call()\n", encoding="utf-8")

    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True)
    clean_file = src_dir / "clean.py"
    clean_file.write_text("x = 42\n", encoding="utf-8")

    from sarthi.core.models import ProjectConfig, RunContext
    from sarthi.core.verify.runners.ruff import RuffRunner

    runner = RuffRunner()
    ctx = RunContext(
        project_root=tmp_path,
        active_layers=["fastapi"],
        config=ProjectConfig(),
    )
    findings = runner.run(ctx, [bad_file, clean_file])
    # The bad file was in extend-exclude, so --force-exclude must omit findings for it
    assert len(findings) == 0
    assert runner.skipped == []


def test_ruff_runner_batches_500_files(tmp_path: Path) -> None:
    """Verifies RuffRunner handles 500 files by chunking into ~100-file batches."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test-500"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    files: list[Path] = []
    for i in range(500):
        f = tmp_path / f"test_{i:03d}.py"
        if i == 450:
            f.write_text("undefined_variable_name_error()\n", encoding="utf-8")
        else:
            f.write_text(f"val = {i}\n", encoding="utf-8")
        files.append(f)

    from sarthi.core.models import ProjectConfig, RunContext
    from sarthi.core.verify.runners.ruff import RuffRunner

    runner = RuffRunner()
    ctx = RunContext(
        project_root=tmp_path,
        active_layers=["fastapi"],
        config=ProjectConfig(),
    )
    findings = runner.run(ctx, files)

    # 450 was in batch 5 (files 400-499)
    assert len(findings) == 1
    assert findings[0].rule_id == "RUFF-F821"
    assert "test_450.py" in findings[0].file
    assert runner.skipped == []


def test_ruff_runner_failed_batch_marks_report_incomplete(tmp_path: Path, monkeypatch) -> None:
    """Verifies any skipped or failed batch results in status 'incomplete', never clean."""
    import subprocess

    from sarthi.core.verify.verifier import Verifier

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        '[project]\nname = "test-fail-batch"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    test_file = tmp_path / "test_file.py"
    test_file.write_text("x = 1\n", encoding="utf-8")

    real_run = subprocess.run

    def mock_subprocess_run(cmd, *args, **kwargs):
        if "ruff" in str(cmd[0]):
            # Simulate a fatal linter crash / non-zero code > 1
            return subprocess.CompletedProcess(args=cmd, returncode=2, stdout="", stderr="Internal Ruff Error")
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

    verifier = Verifier(tmp_path)
    report = verifier.verify(scope="all", checks=["ruff"])

    # Must be incomplete, never clean ('passed')
    assert report.status == "incomplete"
    assert any("Batch 1/1 failed" in s.reason for s in report.skipped)


def test_verifier_scope_in_git_repo(tmp_path: Path) -> None:
    """Verifies in a git repository, scope defaults to git diff HEAD + untracked files."""
    import subprocess

    from sarthi.core.verify.verifier import Verifier

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(tmp_path), capture_output=True, check=True)

    committed = tmp_path / "committed.py"
    committed.write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "committed.py"], cwd=str(tmp_path), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True, check=True)

    # Modify committed file and add an untracked file
    committed.write_text("x = 2\n", encoding="utf-8")
    untracked = tmp_path / "untracked.py"
    untracked.write_text("y = 3\n", encoding="utf-8")

    verifier = Verifier(tmp_path)
    changed_files, was_capped, total = verifier.get_changed_files()

    assert not was_capped
    assert total == 2
    changed_names = {f.name for f in changed_files}
    assert changed_names == {"committed.py", "untracked.py"}


def test_verifier_scope_non_git_repo_capped(tmp_path: Path) -> None:
    """Verifies outside git, files are capped at 500 (newest first) and report is marked incomplete."""
    from sarthi.core.verify.verifier import Verifier

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-cap"\nversion = "0.1.0"\n', encoding="utf-8")

    # Generate 550 files
    for i in range(550):
        f = tmp_path / f"file_{i:03d}.py"
        f.write_text(f"x = {i}\n", encoding="utf-8")

    verifier = Verifier(tmp_path)
    changed_files, was_capped, total = verifier.get_changed_files()

    assert was_capped is True
    assert total >= 550
    assert len(changed_files) == 500

    report = verifier.verify(scope="changed", checks=["secrets"])
    assert report.status == "incomplete"
    assert any(s.check == "scope" and "capped at 500 newest files" in s.reason for s in report.skipped)


def test_verifier_wall_clock_budget_expiry(tmp_path: Path) -> None:
    """Verifies wall-clock budget expiry returns partial results with status incomplete."""
    from sarthi.core.verify.verifier import Verifier

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-timeout"\nversion = "0.1.0"\n', encoding="utf-8")
    f = tmp_path / "sample.py"
    f.write_text("x = 1\n", encoding="utf-8")

    verifier = Verifier(tmp_path)
    # Give a tiny 0.000001s timeout to force immediate expiry
    report = verifier.verify(scope="all", timeout=0.000001)

    assert report.status == "incomplete"
    assert any("timeout" in s.reason or "budget" in s.reason for s in report.skipped)


def test_verifier_missing_optional_semgrep_produces_warning_and_passes(tmp_path: Path, monkeypatch) -> None:
    """Verifies missing optional semgrep produces a warning and report passes if required checks pass."""
    import shutil

    from sarthi.core.verify.verifier import Verifier

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-opt"\nversion = "0.1.0"\n', encoding="utf-8")
    f = tmp_path / "sample.py"
    f.write_text("x = 42\n", encoding="utf-8")

    # Simulate semgrep not found on PATH
    orig_which = shutil.which

    def mock_which(cmd, *args, **kwargs):
        if cmd == "semgrep":
            return None
        return orig_which(cmd, *args, **kwargs)

    monkeypatch.setattr(shutil, "which", mock_which)

    verifier = Verifier(tmp_path)
    report = verifier.verify(scope="all", checks=["secrets", "semgrep"])

    assert report.status == "passed"
    assert any(s.check == "semgrep" and not s.required for s in report.skipped)
    assert any("semgrep: optional tool not installed" in w for w in report.warnings)


def test_verifier_missing_required_tool_marks_incomplete(tmp_path: Path, monkeypatch) -> None:
    """Verifies missing required tool (e.g. ruff on python files) produces incomplete status."""
    from sarthi.core.verify.runners.ruff import RuffRunner
    from sarthi.core.verify.verifier import Verifier

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-req"\nversion = "0.1.0"\n', encoding="utf-8")
    f = tmp_path / "sample.py"
    f.write_text("x = 42\n", encoding="utf-8")

    # Simulate Ruff unavailable
    monkeypatch.setattr(RuffRunner, "available", lambda self, ctx: False)

    verifier = Verifier(tmp_path)
    report = verifier.verify(scope="all", checks=["ruff"])

    assert report.status == "incomplete"
    assert any(s.check == "ruff" and s.required for s in report.skipped)


def test_verifier_unapproved_tests_mark_incomplete(tmp_path: Path) -> None:
    """Verifies unapproved test suite produces incomplete status with required=True."""
    from sarthi.core.verify.verifier import Verifier

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-unapp"\nversion = "0.1.0"\n', encoding="utf-8")
    test_f = tmp_path / "test_sample.py"
    test_f.write_text("def test_ok(): pass\n", encoding="utf-8")

    verifier = Verifier(tmp_path)
    report = verifier.verify(scope="all", checks=["tests"])

    assert report.status == "incomplete"
    assert any(s.check == "tests" and s.required and "unapproved" in s.reason for s in report.skipped)


def test_checklist_cap_and_ranking(tmp_path: Path) -> None:
    """Verifies ChecklistRunner caps items at 8, ranked by severity and relevance to changed files."""
    from sarthi.core.models import (
        Category,
        ProjectConfig,
        Rule,
        RuleVerifier,
        RunContext,
        Severity,
        VerifierType,
    )
    from sarthi.core.verify.runners.checklist import ChecklistRunner

    # Create 12 checklist rules of varying severities and layers
    rules: list[Rule] = []
    # 2 LOW rules
    for i in range(2):
        rules.append(
            Rule(
                id=f"LOW-00{i}",
                title=f"Low rule {i}",
                layer="general",
                category=Category.ARCHITECTURE,
                severity=Severity.LOW,
                rule="low guidance",
                verify=RuleVerifier(type=VerifierType.CHECKLIST, prompt=f"Prompt low {i}"),
            )
        )
    # 3 MEDIUM rules
    for i in range(3):
        rules.append(
            Rule(
                id=f"MED-00{i}",
                title=f"Med rule {i}",
                layer="general",
                category=Category.ARCHITECTURE,
                severity=Severity.MEDIUM,
                rule="med guidance",
                verify=RuleVerifier(type=VerifierType.CHECKLIST, prompt=f"Prompt med {i}"),
            )
        )
    # 5 HIGH rules, one of which is security-relevant to auth
    for i in range(5):
        is_sec = i == 0
        rules.append(
            Rule(
                id=f"HIGH-00{i}",
                title="Auth token protection" if is_sec else f"High rule {i}",
                layer="security" if is_sec else "general",
                category=Category.SECURITY if is_sec else Category.ARCHITECTURE,
                severity=Severity.HIGH,
                rule="high guidance",
                verify=RuleVerifier(type=VerifierType.CHECKLIST, prompt="Prompt high auth" if is_sec else f"Prompt high {i}"),
            )
        )
    # 2 CRITICAL rules
    for i in range(2):
        rules.append(
            Rule(
                id=f"CRIT-00{i}",
                title=f"Crit rule {i}",
                layer="database",
                category=Category.SECURITY,
                severity=Severity.CRITICAL,
                rule="crit guidance",
                verify=RuleVerifier(type=VerifierType.CHECKLIST, prompt=f"Prompt crit {i}"),
            )
        )

    # Total 12 checklist rules created
    assert len(rules) == 12

    # Run with changed file = src/auth/token.py
    ctx = RunContext(
        project_root=tmp_path,
        changed_files=[tmp_path / "src" / "auth" / "token.py"],
        config=ProjectConfig(),
    )

    runner = ChecklistRunner(rules)
    items = runner.get_checklist_items(ctx)

    # Must be capped at exactly 8
    assert len(items) == 8

    # The 2 CRITICAL rules must come first
    assert items[0].rule_id == "CRIT-000"
    assert items[1].rule_id == "CRIT-001"

    # Among HIGH rules, HIGH-000 (security auth rule) has highest relevance to src/auth/token.py
    assert items[2].rule_id == "HIGH-000"

    # The 2 LOW rules should be cut off by the cap of 8 (2 CRIT + 5 HIGH + 1 MED = 8)
    returned_ids = [it.rule_id for it in items]
    assert "LOW-000" not in returned_ids
    assert "LOW-001" not in returned_ids




