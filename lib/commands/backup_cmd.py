from __future__ import annotations

import typer

from lib.utils import console


def register(app: typer.Typer) -> None:
    backup_app = typer.Typer(help="Project backup (phase 2)")

    @backup_app.command("export")
    def backup_export():
        console.print("[yellow]backup export: not implemented yet.[/yellow]")
        console.print("Planned: projects.export API -> tar.gz")
        raise typer.Exit(2)

    app.add_typer(backup_app, name="backup")
