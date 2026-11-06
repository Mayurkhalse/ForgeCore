"""Structured Reporting and Scorecard Generation for Layer 4 Evaluations."""

from __future__ import annotations

import json
from pathlib import Path

from sarthi.eval.experiment import ExperimentResult


class EvaluationReporter:
    """Generates machine-readable and human-readable evaluation scorecards."""

    @staticmethod
    def generate_json_report(results: list[ExperimentResult]) -> str:
        """Serializes experiment results into structured JSON."""
        data = {
            "version": "1.0.0",
            "total_scenarios": len(results),
            "sarthi_clean_passes": sum(1 for r in results if r.sarthi.verify_report.status == "passed"),
            "baseline_clean_passes": sum(1 for r in results if r.baseline.verify_report.status == "passed"),
            "net_findings_reduction": sum(r.findings_delta for r in results),
            "experiments": [r.to_dict() for r in results],
        }
        return json.dumps(data, indent=2)

    @staticmethod
    def generate_markdown_report(results: list[ExperimentResult]) -> str:
        """Renders comprehensive Markdown evaluation scorecard."""
        total = len(results)
        sarthi_passes = sum(1 for r in results if r.sarthi.verify_report.status == "passed")
        base_passes = sum(1 for r in results if r.baseline.verify_report.status == "passed")
        total_findings_delta = sum(r.findings_delta for r in results)

        md = "# Sarthi Layer 4: Live AI Coding Agent Evaluation Report\n\n"
        md += "## 1. Executive Summary & Comparative Scorecard\n\n"
        md += f"- **Total Evaluated Scenarios:** {total}\n"
        md += f"- **Sarthi Clean Pass Rate:** {sarthi_passes}/{total} ({((sarthi_passes/total)*100) if total else 0:.1f}%)\n"
        md += f"- **Baseline Clean Pass Rate:** {base_passes}/{total} ({((base_passes/total)*100) if total else 0:.1f}%)\n"
        md += f"- **Net Verification Findings Reduction:** {total_findings_delta:+d}\n\n"

        md += "### Benchmark Results Table\n\n"
        md += "| Scenario ID | Title | Provider / Model | Baseline Status | Sarthi Status | Findings Delta |\n"
        md += "| :--- | :--- | :--- | :--- | :--- | :--- |\n"
        for r in results:
            base_status = f"`{r.baseline.verify_report.status}` ({len(r.baseline.verify_report.findings)} issues)"
            sarthi_status = f"`{r.sarthi.verify_report.status}` ({len(r.sarthi.verify_report.findings)} issues)"
            delta_str = f"**{r.findings_delta:+d}**" if r.findings_delta != 0 else "0"
            md += (
                f"| `{r.scenario.id}` | {r.scenario.title} | {r.provider_name} ({r.model_name}) | "
                f"{base_status} | {sarthi_status} | {delta_str} |\n"
            )

        md += "\n---\n\n"
        md += "## 2. Detailed Scenario Analysis\n\n"

        for idx, r in enumerate(results, start=1):
            md += f"### {idx}. Scenario: {r.scenario.title} (`{r.scenario.id}`)\n\n"
            md += f"**Task:** {r.scenario.task_prompt}\n\n"

            md += "#### Comparative Metrics\n\n"
            md += "| Metric | Baseline (Unguided) | Sarthi (Guided) | Delta |\n"
            md += "| :--- | :--- | :--- | :--- |\n"
            md += (
                f"| Verification Status | `{r.baseline.verify_report.status}` | "
                f"`{r.sarthi.verify_report.status}` | "
                f"{'Improved' if r.passed_cleanly_delta else 'Equivalent'} |\n"
            )
            md += (
                f"| Total Findings | {len(r.baseline.verify_report.findings)} | "
                f"{len(r.sarthi.verify_report.findings)} | {r.findings_delta:+d} |\n"
            )
            b_cost = r.baseline.trajectory.budget_summary.get("estimated_cost_usd", 0.0)
            s_cost = r.sarthi.trajectory.budget_summary.get("estimated_cost_usd", 0.0)
            md += f"| Estimated Cost (USD) | ${b_cost:.4f} | ${s_cost:.4f} | ${s_cost - b_cost:+.4f} |\n"
            b_tok = r.baseline.trajectory.budget_summary.get("total_tokens", 0)
            s_tok = r.sarthi.trajectory.budget_summary.get("total_tokens", 0)
            md += f"| Total Tokens | {b_tok} | {s_tok} | {s_tok - b_tok:+d} |\n"
            md += f"| Execution Steps | {r.baseline.trajectory.steps} | {r.sarthi.trajectory.steps} | {r.sarthi.trajectory.steps - r.baseline.trajectory.steps:+d} |\n\n"

            if r.sarthi.verify_report.findings:
                md += "#### Remaining Sarthi Findings\n\n"
                for f in r.sarthi.verify_report.findings:
                    md += f"- **[{f.severity.upper()}]** `{f.rule_id}` in `{f.file}`: {f.message}\n"
                md += "\n"

            if r.baseline.verify_report.findings:
                md += "#### Baseline Findings\n\n"
                for f in r.baseline.verify_report.findings:
                    md += f"- **[{f.severity.upper()}]** `{f.rule_id}` in `{f.file}`: {f.message}\n"
                md += "\n"

        return md

    @classmethod
    def save_reports(
        cls,
        results: list[ExperimentResult],
        output_dir: Path,
    ) -> tuple[Path, Path]:
        """Saves JSON and Markdown reports to specified directory."""
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        json_path = output_dir / "evaluation_report.json"
        md_path = output_dir / "evaluation_report.md"

        json_content = cls.generate_json_report(results)
        md_content = cls.generate_markdown_report(results)

        json_path.write_text(json_content, encoding="utf-8")
        md_path.write_text(md_content, encoding="utf-8")

        return json_path, md_path

