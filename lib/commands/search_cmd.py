from __future__ import annotations

from typing import Optional

import typer
from rich.table import Table

from lib.auth import resolve_auth
from lib.context import CLIContext
from lib.gitlab_client import create_client
from lib.utils import console


def register(app: typer.Typer) -> None:
    search_app = typer.Typer(help="Search GitLab")

    @search_app.command("project")
    def search_project(
        ctx: typer.Context,
        query: str = typer.Option(..., "--query", "-q"),
        group: Optional[str] = typer.Option(None, "--group", "-g"),
        visibility: Optional[str] = typer.Option(None, "--visibility"),
    ):
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        kwargs = {"search": query, "all": True}
        if visibility:
            kwargs["visibility"] = visibility
        table = Table(title=f"Search: {query}")
        table.add_column("Path")
        table.add_column("Description")
        for p in gl.projects.list(**kwargs):
            if group and not p.path_with_namespace.startswith(group + "/"):
                continue
            table.add_row(p.path_with_namespace, (p.description or "")[:60])
        console.print(table)

    app.add_typer(search_app, name="search")
