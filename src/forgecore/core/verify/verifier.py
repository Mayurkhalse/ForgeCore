from __future__ import annotations

import subprocess
import time
from pathlib import Path

from forgecore.core.context import ContextBuilder
from forgecore.core.detectors.base import SKIP_DIRS
from forgecore.core.models import (
    Finding,
    RunContext,
    SkippedCheck,
    VerifyReport,
)
from forgecore.core.pathguard import PathGuard
from forgecore.core.rules import RuleLoader, RuleSelector
from forgecore.core.verify.runners import (
    ChecklistRunner,
    ESLintRunner,
    RuffRunner,
    SecretsRunner,
    SemgrepRunner,
    TestRunner,
)
from forgecore.core.verify.trust import (
    CommandTrustError,
    CommandTrustManager,
    parse_and_validate_command,
)


class Verifier:
    """Orchestrates deterministic verification checks across changed or all project files."""

    def __init__(
        self,
        root: Path | str,
        trust_mgr: CommandTrustManager | None = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.pathguard = PathGuard(self.root)
        self.context_builder = ContextBuilder(self.root)
        self.rule_loader = RuleLoader()
        self.trust_mgr = trust_mgr or CommandTrustManager()

    def _is_git_repo(self) -> bool:
        """Checks if the project root is inside a valid git repository."""
        if (self.root / ".git").is_dir():
            return True
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=5,
            )
            return res.returncode == 0 and res.stdout.strip() == "true"
        except Exception:
            return False

    def get_changed_files(self) -> tuple[list[Path], bool, int]:
        """Detects changed files.

        Returns (files, was_capped, total_candidates).
        - In a git repo: defaults to `git diff --name-only HEAD` + untracked files from `git status --porcelain`.
        - Outside git: falls back to sorting files by mtime (newest first), capped at 500 files.
        """
        if self._is_git_repo():
            changed: set[Path] = set()
            try:
                # 1. Staged and unstaged diff against HEAD
                res1 = subprocess.run(
                    ["git", "diff", "--name-only", "HEAD"],
                    cwd=str(self.root),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if res1.returncode == 0:
                    for line in res1.stdout.splitlines():
                        trimmed = line.strip().strip('"')
                        if trimmed:
                            p = self.root / trimmed
                            if p.is_file():
                                changed.add(p.resolve())

                # 2. Untracked files via status
                res2 = subprocess.run(
                    ["git", "status", "--porcelain"],
                    cwd=str(self.root),
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if res2.returncode == 0:
                    for line in res2.stdout.splitlines():
                        if len(line) > 3:
                            path_str = line[3:].strip().strip('"')
                            p = self.root / path_str
                            if p.is_file():
                                changed.add(p.resolve())

                file_list = sorted(list(changed))
                return file_list, False, len(file_list)
            except Exception:
                pass

        # Outside git: scan all files, sort newest first, and cap at 500
        all_files = self.get_all_files()
        total_candidates = len(all_files)

        def _safe_mtime(f: Path) -> float:
            try:
                return f.stat().st_mtime
            except Exception:
                return 0.0

        sorted_files = sorted(all_files, key=_safe_mtime, reverse=True)
        if len(sorted_files) > 500:
            return sorted_files[:500], True, total_candidates
        return sorted_files, False, total_candidates

    def get_all_files(self) -> list[Path]:
        """Scans project files ignoring common build/dependency directories."""
        files: list[Path] = []

        def _walk(curr: Path):
            try:
                for item in curr.iterdir():
                    if item.name in SKIP_DIRS or item.name.startswith("."):
                        continue
                    if item.is_file():
                        files.append(item.resolve())
                    elif item.is_dir():
                        _walk(item)
            except (PermissionError, FileNotFoundError):
                pass

        _walk(self.root)
        return files

    def verify(
        self,
        scope: str = "changed",
        checks: list[str] | None = None,
        timeout: float = 60.0,
    ) -> VerifyReport:
        start_time = time.perf_counter()
        deadline = start_time + timeout
        timed_out = False

        profile, config, context_version, _ = self.context_builder.build_context()
        active_layers = RuleSelector(self.rule_loader.load_all_rules()).resolve_active_layers(
            detected_layers=profile.layer_names(),
            config=config,
        )

        skipped: list[SkippedCheck] = []
        was_capped = False
        total_candidates = 0

        if scope == "changed":
            target_files, was_capped, total_candidates = self.get_changed_files()
            if was_capped:
                skipped.append(
                    SkippedCheck(
                        check="scope",
                        reason=f"Non-git repository scan capped at 500 newest files (out of {total_candidates} total files).",
                    )
                )
        else:
            target_files = self.get_all_files()

        ctx = RunContext(
            project_root=self.root,
            active_layers=active_layers,
            changed_files=target_files,
            config=config,
            deadline=deadline,
        )

        # Build list of runners
        all_rules = self.rule_loader.load_all_rules()
        active_rules = [r for r in all_rules if r.layer in active_layers]
        checklist_runner = ChecklistRunner(active_rules)
        all_runners = [
            SecretsRunner(),
            RuffRunner(),
            SemgrepRunner(),
            ESLintRunner(),
            TestRunner(self.trust_mgr),
            checklist_runner,
        ]

        if checks:
            check_names = set(checks)
            runners = [r for r in all_runners if r.name in check_names]
        else:
            runners = all_runners

        findings: list[Finding] = []

        for runner in runners:
            if runner.name == "checklist":
                continue

            # Check wall-clock budget before starting runner
            elapsed = time.perf_counter() - start_time
            if elapsed >= timeout:
                timed_out = True
                skipped.append(
                    SkippedCheck(
                        check=runner.name,
                        reason=f"Verification exceeded wall-clock budget of {timeout:.1f}s (elapsed: {elapsed:.1f}s); skipped remaining checks.",
                    )
                )
                continue

            # Check if applicable and available
            # Note: ESLint is only applicable if JS/TS files or layers exist
            is_js_ts = any(lyr in active_layers for lyr in ["react", "react-native", "node-express"]) or any(
                f.suffix in {".js", ".jsx", ".ts", ".tsx"} for f in target_files
            )
            is_python = any(lyr in active_layers for lyr in ["fastapi", "python-ml"]) or any(
                f.suffix == ".py" for f in target_files
            )

            if runner.name == "eslint" and not is_js_ts:
                continue
            if runner.name == "ruff" and not is_python:
                continue

            if hasattr(runner, "check_trust"):
                trusted, untrusted_reason = runner.check_trust(ctx)
                if not trusted:
                    skipped.append(
                        SkippedCheck(
                            check=runner.name,
                            reason=untrusted_reason or "untrusted command",
                        )
                    )
                    continue

            if not runner.available(ctx):
                skipped.append(SkippedCheck(check=runner.name, reason="not installed or not configured in environment"))
                continue

            runner_findings = runner.run(ctx, target_files)
            findings.extend(runner_findings)
            if hasattr(runner, "skipped") and runner.skipped:
                skipped.extend(runner.skipped)

            # Check wall-clock budget after runner finished
            elapsed = time.perf_counter() - start_time
            if elapsed >= timeout and not timed_out:
                timed_out = True

        # Check any non-test custom commands defined in project config
        if config.verify.commands:
            for cmd_name, cmd_str in config.verify.commands.items():
                if cmd_name == "test":
                    continue
                try:
                    parse_and_validate_command(cmd_str, project_root=self.root)
                except CommandTrustError as err:
                    skipped.append(
                        SkippedCheck(
                            check=f"custom:{cmd_name}",
                            reason=f"Rejected: {err}",
                        )
                    )
                    continue

                if not self.trust_mgr.is_approved(self.root, config.verify.commands):
                    skipped.append(
                        SkippedCheck(
                            check=f"custom:{cmd_name}",
                            reason=(
                                f"Custom command '{cmd_str}' from .forgecore/project.yaml is untrusted. "
                                f"Run 'forgecore approve \"{self.root}\"' to review and approve execution."
                            ),
                        )
                    )

        # Collect checklist items
        checklist_items = checklist_runner.get_checklist_items(ctx)

        # Calculate summary
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for f in findings:
            sev_key = f.severity.value.lower()
            summary[sev_key] = summary.get(sev_key, 0) + 1

        # Determine status
        fail_on = config.verify.fail_on
        blocking_findings = [f for f in findings if f.severity >= fail_on]

        if blocking_findings:
            status = "failed"
            next_action = f"Fix {len(blocking_findings)} findings at severity >= {fail_on.value}, then call verify_project again."
        elif skipped or timed_out or was_capped:
            status = "incomplete"
            reasons: list[str] = []
            if timed_out:
                reasons.append(f"wall-clock timeout ({timeout:.1f}s) exceeded")
            if was_capped:
                reasons.append("non-git scan capped at 500 files")
            other_skips = [s.check for s in skipped if s.check not in {"scope", "timeout"}]
            if other_skips:
                reasons.append(f"{len(other_skips)} check(s) skipped ({', '.join(other_skips)})")
            next_action = f"Verification incomplete: {'; '.join(reasons) if reasons else 'checks skipped'}. Address findings or resolve skipped checks."
        else:
            status = "passed"
            next_action = "All deterministic verification checks passed. Ready for review."

        return VerifyReport(
            status=status,
            context_version=context_version,
            summary=summary,
            findings=findings,
            checklist=checklist_items,
            skipped=skipped,
            next_action=next_action,
        )
