from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from sarthi.core.models import Finding, RunContext, Severity
from sarthi.core.verify.runners.base import Runner
from sarthi.core.verify.trust import build_sanitized_subprocess_env


class ESLintRunner(Runner):
    """Executes ESLint on JavaScript and TypeScript source files."""

    @property
    def name(self) -> str:
        return "eslint"

    @property
    def required(self) -> bool:
        return True

    def _find_binary(self, ctx: RunContext) -> list[str] | None:
        local_bin = ctx.project_root / "node_modules" / ".bin" / ("eslint.cmd" if subprocess.os.name == "nt" else "eslint")
        if local_bin.is_file():
            return [str(local_bin)]
        if shutil.which("eslint"):
            return ["eslint"]
        if shutil.which("npx"):
            return ["npx", "eslint"]
        return None

    def available(self, ctx: RunContext) -> bool:
        has_js_ts = any(ext in ctx.active_layers for ext in ["react", "react-native", "node-express"])
        return has_js_ts and (self._find_binary(ctx) is not None)

    def run(self, ctx: RunContext, files: list[Path]) -> list[Finding]:
        cmd_prefix = self._find_binary(ctx)
        if not cmd_prefix:
            return []

        js_ts_files = [f for f in files if f.suffix in {".js", ".jsx", ".ts", ".tsx"} and f.is_file()]
        if not js_ts_files:
            return []

        findings: list[Finding] = []
        file_args = [str(f.relative_to(ctx.project_root)) for f in js_ts_files]

        cmd = [*cmd_prefix, "--format=json", *file_args]
        safe_env = build_sanitized_subprocess_env(ctx.project_root)
        try:
            res = subprocess.run(
                cmd,
                cwd=str(ctx.project_root),
                env=safe_env,
                capture_output=True,
                text=True,
                timeout=45,
            )
            stdout = res.stdout.strip()
            if not stdout:
                return []

            data = json.loads(stdout)
            for file_result in data:
                file_path = file_result.get("filePath", "")
                try:
                    rel_path = str(Path(file_path).relative_to(ctx.project_root)).replace("\\", "/")
                except ValueError:
                    rel_path = file_path.replace("\\", "/")

                for msg in file_result.get("messages", []):
                    rule_id = msg.get("ruleId") or "ESLINT-SYNTAX"
                    sev_num = msg.get("severity", 1)  # 1 = warning, 2 = error
                    severity = Severity.HIGH if sev_num == 2 else Severity.MEDIUM

                    findings.append(
                        Finding(
                            rule_id=f"ESLINT-{rule_id}",
                            severity=severity,
                            file=rel_path,
                            line=msg.get("line", 1),
                            message=msg.get("message", ""),
                            recommendation="Fix ESLint issue according to project style guide.",
                            verifier=self.name,
                            fix_hint=f"Run eslint --fix on {rel_path} or address rule {rule_id}.",
                        )
                    )
        except Exception:
            pass

        return findings
