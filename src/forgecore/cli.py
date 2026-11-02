from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from forgecore.adapters.antigravity.adapter import AntigravityAdapter
from forgecore.adapters.base import InstallOpts
from forgecore.core.config import ConfigLoader
from forgecore.core.context import ContextBuilder
from forgecore.core.rules import RuleLoader, RuleSelector
from forgecore.core.standards_linter import StandardsLinter
from forgecore.core.verify.reporter import Reporter
from forgecore.core.verify.verifier import Verifier
from forgecore.mcp.server import run_server

app = typer.Typer(
    name="forgecore",
    help="Production engineering standards for AI coding agents.",
    no_args_is_help=True,
)
install_app = typer.Typer(name="install", help="Install client integrations.")
uninstall_app = typer.Typer(name="uninstall", help="Uninstall client integrations.")
app.add_typer(install_app)
app.add_typer(uninstall_app)

console = Console()


@app.command()
def init(
    path: str = typer.Argument(".", help="Path to project root."),
    force: bool = typer.Option(False, "--force", "-f", help="Force refresh even if fingerprint is unchanged."),
) -> None:
    """Detect stack, scaffold .forgecore/project.yaml, and generate cached context."""
    root_path = Path(path).resolve()
    console.print(f"[bold cyan]Initializing ForgeCore in:[/bold cyan] {root_path}")

    builder = ContextBuilder(root_path)
    profile, config, version, refreshed = builder.build_context(force=force)

    # Ensure config file exists
    loader = ConfigLoader(root_path)
    if not loader.exists():
        cfg = loader.create_default(
            project_name=root_path.name,
            profile=profile.suggested_profile,
        )
        saved = loader.save(cfg)
        console.print(f"[green]Created config file:[/green] {saved.relative_to(root_path)}")

    console.print(f"[bold green]Initialized context v{version}![/bold green] (Refreshed: {refreshed})")
    console.print(f"Detected Languages: {', '.join(profile.languages) or 'None'}")
    console.print(f"Package Managers: {', '.join(profile.package_managers) or 'None'}")
    console.print(f"Test Frameworks: {', '.join(profile.test_frameworks) or 'None'}")
    console.print(f"Detected Layers: {', '.join(profile.layer_names()) or 'None'}")
    console.print(f"Suggested Profile: [bold]{profile.suggested_profile or 'None'}[/bold]")


@app.command()
def context(
    path: str = typer.Argument(".", help="Path to project root."),
) -> None:
    """Print the human-readable project context."""
    root_path = Path(path).resolve()
    builder = ContextBuilder(root_path)
    profile, config, version, _ = builder.build_context(force=False)

    context_file = root_path / ".forgecore" / "cache" / "context.md"
    if context_file.is_file():
        console.print(context_file.read_text(encoding="utf-8"))
    else:
        console.print(f"# Project Context (v{version})\nLanguages: {', '.join(profile.languages)}")


@app.command()
def standards(
    path: str = typer.Argument(".", help="Path to project root."),
    task: str = typer.Option(..., "--task", "-t", help="Description of task to retrieve standards for."),
    task_type: str = typer.Option("feature", "--type", help="Task type (feature, bugfix, refactor, new-project)."),
    layers: Optional[str] = typer.Option(None, "--layers", "-l", help="Comma-separated layer overrides."),
    max_rules: int = typer.Option(15, "--max-rules", "-m", help="Maximum rules to return."),
) -> None:
    """Display the ranked, budgeted standards an agent would receive for a task."""
    root_path = Path(path).resolve()
    builder = ContextBuilder(root_path)
    profile, config, _, _ = builder.build_context(force=False)

    layer_list = [lyr.strip() for lyr in layers.split(",")] if layers else None
    loader = RuleLoader()
    all_rules = loader.load_all_rules()
    selector = RuleSelector(all_rules, loader.load_profiles())

    active_layers = selector.resolve_active_layers(
        detected_layers=profile.layer_names(),
        config=config,
        explicit_layers=layer_list,
    )

    selected_rules, truncated, hint = selector.select_rules(
        active_layers=active_layers,
        task=task,
        task_type=task_type,
        config=config,
        max_rules=max_rules,
    )

    console.print(f"\n[bold]Task:[/bold] {task} ([cyan]{task_type}[/cyan])")
    console.print(f"[bold]Active Layers:[/bold] {', '.join(active_layers)}")
    console.print(f"[bold]Standards Returned:[/bold] {len(selected_rules)} (Truncated: {truncated})\n")

    table = Table(show_lines=True)
    table.add_column("Severity", style="bold", width=10)
    table.add_column("ID", width=15)
    table.add_column("Layer", width=14)
    table.add_column("Rule Title & Statement")

    for r in selected_rules:
        sev_color = "red" if r.severity.value in ("critical", "high") else "yellow"
        body = f"[bold]{r.title}[/bold]\n{r.rule.strip()}"
        table.add_row(f"[{sev_color}]{r.severity.value.upper()}[/{sev_color}]", r.id, r.layer, body)

    console.print(table)
    if hint:
        console.print(f"[dim]{hint}[/dim]\n")


@app.command()
def verify(
    path: str = typer.Argument(".", help="Path to project root."),
    all_files: bool = typer.Option(False, "--all", "-a", help="Verify all files instead of just changed files."),
    as_json: bool = typer.Option(False, "--json", help="Output report as structured JSON."),
) -> None:
    """Execute the deterministic verification loop and output findings."""
    root_path = Path(path).resolve()
    scope = "all" if all_files else "changed"

    verifier = Verifier(root_path)
    report = verifier.verify(scope=scope)

    if as_json:
        console.print(json.dumps(report.model_dump(mode="json"), indent=2))
    else:
        reporter = Reporter(console)
        reporter.print_report(report)

    if report.status == "failed":
        sys.exit(1)


@install_app.command(name="antigravity")
def install_antigravity(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing configuration."),
    no_scaffold: bool = typer.Option(False, "--no-scaffold", help="Do not create project.yaml in current directory."),
) -> None:
    """One-time setup for Google Antigravity (MCP server + global Core Contract)."""
    adapter = AntigravityAdapter()
    opts = InstallOpts(
        workspace_root=Path.cwd(),
        force=force,
        with_scaffold=not no_scaffold,
    )
    res = adapter.install(opts)
    if res.success:
        console.print(f"[bold green]Success:[/bold green] {res.message}")
    else:
        console.print(f"[bold red]Failed:[/bold red] {res.message}")
        sys.exit(1)


@uninstall_app.command(name="antigravity")
def uninstall_antigravity() -> None:
    """Revert changes installed for Google Antigravity."""
    adapter = AntigravityAdapter()
    res = adapter.uninstall()
    if res.success:
        console.print(f"[bold green]Success:[/bold green] {res.message}")
    else:
        console.print(f"[bold red]Failed:[/bold red] {res.message}")
        sys.exit(1)


@app.command()
def doctor() -> None:
    """Diagnose environment, installed tools, and client configuration."""
    console.print("[bold cyan]Running ForgeCore Environment Diagnostics...[/bold cyan]\n")

    adapter = AntigravityAdapter()
    checks = adapter.doctor()

    table = Table(show_lines=True)
    table.add_column("Status", width=8)
    table.add_column("Check", width=30)
    table.add_column("Details")

    all_passed = True
    for c in checks:
        if c.passed:
            status = "[bold green]PASS[/bold green]"
            msg = c.message
        else:
            status = "[bold yellow]WARN[/bold yellow]"
            msg = f"{c.message}\n[dim]Hint: {c.hint}[/dim]" if c.hint else c.message
            all_passed = False
        table.add_row(status, c.name, msg)

    console.print(table)
    if all_passed:
        console.print("\n[bold green]All core diagnostics passed cleanly![/bold green]")
    else:
        console.print("\n[yellow]Some optional tools or client configurations can be improved (see hints above).[/yellow]")


@app.command(name="lint-standards")
def lint_standards() -> None:
    """Validate standards library against schema, uniqueness, and references."""
    console.print("[bold cyan]Linting ForgeCore Standards Library...[/bold cyan]")
    linter = StandardsLinter()
    errors = linter.lint()

    if errors:
        console.print(f"\n[bold red]Found {len(errors)} standards error(s):[/bold red]")
        for err in errors:
            console.print(f"  [red]x[/red] {err}")
        sys.exit(1)
    else:
        console.print("[bold green]All standards, profiles, and verifiers passed schema validation![/bold green]")


@app.command()
def serve() -> None:
    """Start the ForgeCore MCP server over stdio."""
    run_server()


if __name__ == "__main__":
    app()
