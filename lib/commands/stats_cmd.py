from __future__ import annotations

import typer

from lib.utils import console


def register(app: typer.Typer) -> None:
    stats_app = typer.Typer(help="Commit statistics (phase 2)")

    @stats_app.command("commits")
    def stats_commits():
        console.print("[yellow]stats commits: not implemented yet.[/yellow]")
        console.print("Use: gitlab-tool git log -f projects.yaml --since ... for local stats")
        raise typer.Exit(2)

    app.add_typer(stats_app, name="stats")
