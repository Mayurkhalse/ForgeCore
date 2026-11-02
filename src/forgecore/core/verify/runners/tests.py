from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from forgecore.core.models import Finding, RunContext, Severity
from forgecore.core.verify.runners.base import Runner


class TestRunner(Runner):
    """Executes test suites (pytest, npm test, etc.) and reports test failures."""

    @property
    def name(self) -> str:
        return "tests"

    def _resolve_command(self, ctx: RunContext) -> list[str] | None:
        custom_cmd = ctx.config.verify.commands.get("test")
        if custom_cmd:
            return shlex.split(custom_cmd)

        # Auto-detect test runner
        # 1. Python pytest
        if sys.platform == "win32":
            venv_pytest = ctx.project_root / ".venv" / "Scripts" / "pytest.exe"
        else:
            venv_pytest = ctx.project_root / ".venv" / "bin" / "pytest"

        if venv_pytest.is_file():
            return [str(venv_pytest), "-q"]
        if shutil.which("pytest") and any(ctx.project_root.glob("test_*.py")):
            return ["pytest", "-q"]

        # 2. Node npm test
        pkg_json = ctx.project_root / "package.json"
        if pkg_json.is_file() and shutil.which("npm"):
            return ["npm", "test", "--", "--watchAll=false"]

        return None

    def available(self, ctx: RunContext) -> bool:
        return self._resolve_command(ctx) is not None

    def run(self, ctx: RunContext, files: list[Path]) -> list[Finding]:
        cmd = self._resolve_command(ctx)
        if not cmd:
            return []

        findings: list[Finding] = []
        try:
            res = subprocess.run(
                cmd,
                cwd=str(ctx.project_root),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if res.returncode != 0:
                summary = res.stderr.strip() or res.stdout.strip()
                last_lines = "\n".join(summary.splitlines()[-6:]) if summary else "Tests exited with error"
                findings.append(
                    Finding(
                        rule_id="UNI-TEST-001",
                        severity=Severity.HIGH,
                        file="tests",
                        line=0,
                        message=f"Test suite failed:\n{last_lines}",
                        recommendation="Fix failing unit or integration tests before declaring task complete.",
                        verifier=self.name,
                        fix_hint=f"Execute '{' '.join(cmd)}' locally to inspect test output.",
                    )
                )
        except subprocess.TimeoutExpired:
            findings.append(
                Finding(
                    rule_id="UNI-TEST-001",
                    severity=Severity.HIGH,
                    file="tests",
                    line=0,
                    message="Test suite execution timed out after 60 seconds.",
                    recommendation="Ensure tests terminate promptly and do not hang waiting on external I/O.",
                    verifier=self.name,
                    fix_hint="Check for infinite loops or blocked network calls in test code.",
                )
            )
        except Exception as e:
            findings.append(
                Finding(
                    rule_id="UNI-TEST-001",
                    severity=Severity.HIGH,
                    file="tests",
                    line=0,
                    message=f"Error running test suite: {e}",
                    recommendation="Ensure test framework and dependencies are installed.",
                    verifier=self.name,
                )
            )

        return findings
