from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from forgecore.core.models import Finding, RunContext, Severity, SkippedCheck
from forgecore.core.verify.runners.base import Runner

BATCH_SIZE = 100


class RuffRunner(Runner):
    """Executes Ruff linter and static security analysis on Python files."""

    def __init__(self) -> None:
        self.skipped: list[SkippedCheck] = []

    @property
    def name(self) -> str:
        return "ruff"

    def _find_binary(self, ctx: RunContext) -> str | None:
        # Check project .venv
        if sys.platform == "win32":
            venv_bin = ctx.project_root / ".venv" / "Scripts" / "ruff.exe"
        else:
            venv_bin = ctx.project_root / ".venv" / "bin" / "ruff"

        if venv_bin.is_file():
            return str(venv_bin)
        return shutil.which("ruff")

    def available(self, ctx: RunContext) -> bool:
        return self._find_binary(ctx) is not None

    def run(self, ctx: RunContext, files: list[Path]) -> list[Finding]:
        self.skipped = []
        bin_path = self._find_binary(ctx)
        if not bin_path:
            return []

        py_files = [f for f in files if f.suffix == ".py" and f.is_file()]
        if not py_files:
            return []

        findings: list[Finding] = []

        # Process in batches of BATCH_SIZE to stay well within OS command line limits
        batches = [py_files[i : i + BATCH_SIZE] for i in range(0, len(py_files), BATCH_SIZE)]

        for batch_idx, batch in enumerate(batches, start=1):
            file_args = [str(f.relative_to(ctx.project_root)) for f in batch]
            cmd = [bin_path, "check", "--force-exclude", "--output-format=json", *file_args]

            try:
                res = subprocess.run(
                    cmd,
                    cwd=str(ctx.project_root),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )

                # Ruff exit codes: 0 = clean, 1 = rule violations found, >1 = error
                if res.returncode not in (0, 1):
                    err_msg = res.stderr.strip() or f"exited with code {res.returncode}"
                    self.skipped.append(
                        SkippedCheck(
                            check="ruff",
                            reason=f"Batch {batch_idx}/{len(batches)} failed: {err_msg[:200]}",
                        )
                    )
                    continue

                stdout = res.stdout.strip()
                if not stdout:
                    continue

                try:
                    data = json.loads(stdout)
                except json.JSONDecodeError as jde:
                    self.skipped.append(
                        SkippedCheck(
                            check="ruff",
                            reason=f"Batch {batch_idx}/{len(batches)} output parsing failed: {jde}",
                        )
                    )
                    continue

                if not isinstance(data, list):
                    continue

                for item in data:
                    code = item.get("code", "")
                    msg = item.get("message", "")
                    filename = item.get("filename", "")
                    location = item.get("location", {})
                    line = location.get("row", 1)

                    # Determine severity: Security (S rules) and critical syntax/undefined (E9, F821) are High
                    severity = Severity.MEDIUM
                    if code.startswith("S") or code.startswith("E9") or code in {"F821", "F822", "F823"}:
                        severity = Severity.HIGH

                    try:
                        rel_file = str(Path(filename).relative_to(ctx.project_root)).replace("\\", "/")
                    except ValueError:
                        rel_file = filename.replace("\\", "/")

                    findings.append(
                        Finding(
                            rule_id=f"RUFF-{code}",
                            severity=severity,
                            file=rel_file,
                            line=line,
                            message=f"{code}: {msg}",
                            recommendation=f"Address Ruff finding {code} according to Python standards.",
                            verifier=self.name,
                            fix_hint=f"Run 'ruff check --fix {rel_file}' or inspect code at line {line}.",
                        )
                    )

            except subprocess.TimeoutExpired:
                self.skipped.append(
                    SkippedCheck(
                        check="ruff",
                        reason=f"Batch {batch_idx}/{len(batches)} timed out after 30s",
                    )
                )
            except Exception as e:
                self.skipped.append(
                    SkippedCheck(
                        check="ruff",
                        reason=f"Batch {batch_idx}/{len(batches)} execution error: {e}",
                    )
                )

        return findings
