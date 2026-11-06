from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from sarthi.core.models import Finding, RunContext, Severity
from sarthi.core.verify.runners.base import Runner
from sarthi.core.verify.trust import build_sanitized_subprocess_env


class SemgrepRunner(Runner):
    """Executes Semgrep against Sarthi custom rules and community packs."""

    @property
    def name(self) -> str:
        return "semgrep"

    @property
    def required(self) -> bool:
        return False

    def available(self, ctx: RunContext) -> bool:
        return shutil.which("semgrep") is not None

    def _get_rule_configs(self, ctx: RunContext) -> list[Path]:
        standards_dir = Path(__file__).resolve().parent.parent.parent.parent.parent / "standards"
        configs: list[Path] = []
        verifiers_dir = standards_dir / "verifiers" / "semgrep"
        if verifiers_dir.is_dir():
            configs.extend(verifiers_dir.glob("*.yaml"))
            configs.extend(verifiers_dir.glob("*.yml"))
        return configs

    def run(self, ctx: RunContext, files: list[Path]) -> list[Finding]:
        if not self.available(ctx):
            return []

        rule_configs = self._get_rule_configs(ctx)
        if not rule_configs:
            return []

        target_files = [f for f in files if f.is_file()]
        if not target_files:
            return []

        findings: list[Finding] = []
        safe_env = build_sanitized_subprocess_env(ctx.project_root)
        for config_path in rule_configs:
            cmd = [
                "semgrep",
                f"--config={config_path}",
                "--json",
                "--quiet",
                *[str(f.relative_to(ctx.project_root)) for f in target_files],
            ]
            try:
                res = subprocess.run(
                    cmd,
                    cwd=str(ctx.project_root),
                    env=safe_env,
                    capture_output=True,
                    text=True,
                    timeout=45,
                )
                if not res.stdout.strip():
                    continue

                data = json.loads(res.stdout)
                results = data.get("results", [])
                for item in results:
                    check_id = item.get("check_id", "SEMGREP")
                    msg = item.get("extra", {}).get("message", "")
                    raw_sev = item.get("extra", {}).get("severity", "WARNING").upper()
                    sev_map = {
                        "ERROR": Severity.HIGH,
                        "WARNING": Severity.MEDIUM,
                        "INFO": Severity.LOW,
                    }
                    severity = sev_map.get(raw_sev, Severity.MEDIUM)
                    path = item.get("path", "")
                    line = item.get("start", {}).get("line", 1)

                    findings.append(
                        Finding(
                            rule_id=check_id,
                            severity=severity,
                            file=path.replace("\\", "/"),
                            line=line,
                            message=msg,
                            recommendation="Refactor the code according to the architecture and security rules.",
                            verifier=self.name,
                            fix_hint=f"Check rule definition for {check_id}.",
                        )
                    )
            except Exception:
                pass

        return findings
