from __future__ import annotations

import re
from pathlib import Path

from forgecore.core.models import Finding, RunContext, Severity
from forgecore.core.verify.runners.base import Runner

SECRET_PATTERNS = [
    (
        "AWS Access Key ID",
        re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
        "Critical AWS access key exposed in source code.",
    ),
    (
        "Private Key",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
        "Unencrypted private key committed directly into source code.",
    ),
    (
        "GitHub Access Token",
        re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{36,})\b"),
        "Hardcoded GitHub token found.",
    ),
    (
        "Slack Token",
        re.compile(r"\b(xox[baprs]-[0-9a-zA-Z]{10,48})\b"),
        "Hardcoded Slack API token found.",
    ),
    (
        "Generic Secret/Password",
        re.compile(r"""(?i)\b(api[_-]?key|secret[_-]?key|password|bearer|auth[_-]?token)\s*[:=]\s*['"]([A-Za-z0-9+/=_\-\.]{16,})['"]"""),
        "Potential hardcoded secret or credential credential string found.",
    ),
]

IGNORE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".woff", ".woff2",
    ".ttf", ".eot", ".zip", ".tar", ".gz", ".pyc", ".class", ".exe", ".dll",
}


class SecretsRunner(Runner):
    """Deterministic regex-based scanner for hardcoded secrets."""

    @property
    def name(self) -> str:
        return "secrets"

    def available(self, ctx: RunContext) -> bool:
        return True

    def run(self, ctx: RunContext, files: list[Path]) -> list[Finding]:
        findings: list[Finding] = []

        for f in files:
            if not f.is_file() or f.suffix.lower() in IGNORE_EXTENSIONS:
                continue

            try:
                # Do not report secret files themselves if blocked by PathGuard; scan regular project code
                rel = str(f.relative_to(ctx.project_root)).replace("\\", "/")
                # Skip .forgecore/cache
                if ".forgecore" in rel:
                    continue

                content = f.read_text(encoding="utf-8", errors="ignore")
                for line_idx, line in enumerate(content.splitlines(), start=1):
                    stripped = line.strip()
                    # Skip pure comment lines
                    if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("/*"):
                        continue

                    for label, pattern, msg in SECRET_PATTERNS:
                        match = pattern.search(line)
                        if match:
                            # CRITICAL: Do NOT include match value in the finding!
                            findings.append(
                                Finding(
                                    rule_id="UNI-SEC-001",
                                    severity=Severity.CRITICAL,
                                    file=rel,
                                    line=line_idx,
                                    message=f"{msg} ({label})",
                                    recommendation="Never commit secrets to source control. Read credentials from environment variables or a secret vault.",
                                    verifier=self.name,
                                    fix_hint="Replace with os.environ.get(...) or process.env[...].",
                                )
                            )
                            break
            except Exception:
                pass

        return findings
