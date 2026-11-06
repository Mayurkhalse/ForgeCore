from __future__ import annotations

from rich.console import Console
from rich.table import Table

from sarthi.core.models import Severity, VerifyReport


class Reporter:
    """Formats and prints verification reports for human and machine consumption."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def print_report(self, report: VerifyReport) -> None:
        status_colors = {
            "passed": "bold green",
            "failed": "bold red",
            "incomplete": "bold yellow",
        }
        color = status_colors.get(report.status, "white")
        self.console.print(f"\n[{color}]Verification Status: {report.status.upper()}[/{color}] (Context v{report.context_version})\n")

        # Summary counts
        summary = report.summary
        self.console.print(
            f"Findings: [red]Critical: {summary.get('critical', 0)}[/red] | "
            f"[bold red]High: {summary.get('high', 0)}[/bold red] | "
            f"[yellow]Medium: {summary.get('medium', 0)}[/yellow] | "
            f"[blue]Low: {summary.get('low', 0)}[/blue]"
        )

        if report.findings:
            table = Table(title="Verification Findings", show_lines=True)
            table.add_column("Severity", style="bold", width=10)
            table.add_column("Rule ID", width=15)
            table.add_column("Location", width=25)
            table.add_column("Message")

            for f in report.findings:
                sev_color = "red" if f.severity in (Severity.CRITICAL, Severity.HIGH) else "yellow"
                loc = f"{f.file}:{f.line}" if f.line > 0 else f.file
                table.add_row(f"[{sev_color}]{f.severity.value.upper()}[/{sev_color}]", f.rule_id, loc, f.message)

            self.console.print(table)

        if report.checklist:
            self.console.print("\n[bold]Checklist Items to Confirm:[/bold]")
            for item in report.checklist:
                self.console.print(f"  [ ] [{item.rule_id}] {item.prompt}")

        if report.skipped:
            self.console.print("\n[yellow]Skipped Checks:[/yellow]")
            for s in report.skipped:
                opt_tag = " [dim](optional)[/dim]" if not s.required else " [red](required)[/red]"
                self.console.print(f"  - {s.check}{opt_tag}: {s.reason}")

        if report.warnings:
            self.console.print("\n[yellow]Warnings:[/yellow]")
            for w in report.warnings:
                self.console.print(f"  [yellow]![/yellow] {w}")

        if report.next_action:
            self.console.print(f"\n[bold cyan]Next Action:[/bold cyan] {report.next_action}\n")
