from pathlib import Path

from forgecore.core.models import Severity
from forgecore.core.verify.verifier import Verifier

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

    from forgecore.core.models import ProjectConfig, RunContext
    from forgecore.core.verify.runners.ruff import RuffRunner

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

    from forgecore.core.models import ProjectConfig, RunContext
    from forgecore.core.verify.runners.ruff import RuffRunner

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

    from forgecore.core.verify.verifier import Verifier

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

    from forgecore.core.verify.verifier import Verifier

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
    from forgecore.core.verify.verifier import Verifier

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
    from forgecore.core.verify.verifier import Verifier

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

    from forgecore.core.verify.verifier import Verifier

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
    from forgecore.core.verify.runners.ruff import RuffRunner
    from forgecore.core.verify.verifier import Verifier

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
    from forgecore.core.verify.verifier import Verifier

    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test-unapp"\nversion = "0.1.0"\n', encoding="utf-8")
    test_f = tmp_path / "test_sample.py"
    test_f.write_text("def test_ok(): pass\n", encoding="utf-8")

    verifier = Verifier(tmp_path)
    report = verifier.verify(scope="all", checks=["tests"])

    assert report.status == "incomplete"
    assert any(s.check == "tests" and s.required and "unapproved" in s.reason for s in report.skipped)



