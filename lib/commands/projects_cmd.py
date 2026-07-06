from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from lib.context import CLIContext
from lib.i18n import t
from lib.projects_loader import load_projects_file, resolve_projects_path

console = Console()

app = typer.Typer(help=t("cmd.projects.help"))


@app.command("list", help=t("cmd.projects.list"))
def projects_list(
    ctx: typer.Context,
    projects_file: Optional[str] = typer.Option(None, "-f", "--file"),
    service: Optional[str] = typer.Option(None, "--service"),
    enabled_only: bool = typer.Option(False, "--enabled-only"),
) -> None:
    """List projects from projects.yaml."""
    cli: CLIContext = ctx.obj
    pf_path = resolve_projects_path(projects_file or cli.projects_file, cli.config)
    if not pf_path:
        raise typer.BadParameter("No projects.yaml found. Use -f or copy projects.example.yaml")
    pf = load_projects_file(pf_path)
    entries = pf.enabled_projects(service=service, enabled_only=enabled_only)
    table = Table(title=f"Projects ({pf.workspace or pf.path.name})")
    table.add_column("Path")
    table.add_column("Enabled")
    table.add_column("Services")
    table.add_column("Note")
    show = pf.projects
    if enabled_only:
        show = [e for e in show if e.enabled]
    if service:
        show = [e for e in show if service in e.services]
    for e in show:
        table.add_row(
            e.path,
            str(e.enabled),
            ", ".join(e.services),
            e.note,
        )
    console.print(table)


@app.command("show")
def projects_show(
    ctx: typer.Context,
    project_path: str = typer.Argument(..., help=t("cmd.projects.path")),
    projects_file: Optional[str] = typer.Option(None, "-f", "--file"),
) -> None:
    cli: CLIContext = ctx.obj
    pf_path = resolve_projects_path(projects_file or cli.projects_file, cli.config)
    if not pf_path:
        raise typer.BadParameter("No projects.yaml found")
    pf = load_projects_file(pf_path)
    for e in pf.projects:
        if e.path == project_path:
            console.print(e)
            return
    raise typer.BadParameter(f"Project not in manifest: {project_path}")
