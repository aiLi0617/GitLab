from __future__ import annotations

from typing import Optional

import typer

from lib.auth import resolve_auth
from lib.commands.protect_cmd import _project_paths
from lib.context import CLIContext
from lib.gitlab_client import create_client, get_project
from lib.utils import confirm_action, console, BatchResult


def register(app: typer.Typer) -> None:
    label_app = typer.Typer(help="Project labels")

    @label_app.command("list")
    def label_list(ctx: typer.Context, project: str = typer.Option(..., "--project", "-p")):
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        for lb in get_project(gl, project).labels.list(all=True):
            console.print(f"{lb.name}\t{lb.color}\t{lb.description or ''}")

    @label_app.command("create")
    def label_create(
        ctx: typer.Context,
        name: str = typer.Option(..., "--name"),
        color: str = typer.Option("#6699cc", "--color"),
        description: str = typer.Option("", "--description"),
        project: Optional[str] = typer.Option(None, "--project", "-p"),
        group: Optional[list[str]] = typer.Option(None, "--group", "-g"),
        projects_file: Optional[str] = typer.Option(None, "-f", "--file"),
    ):
        cli: CLIContext = ctx.obj
        paths = _project_paths(ctx, [project] if project else None, group, projects_file)
        if project and project not in paths:
            paths = [project]
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        result = BatchResult()
        for pp in paths:
            try:
                if cli.dry_run:
                    result.success.append(pp)
                    continue
                get_project(gl, pp).labels.create({"name": name, "color": color, "description": description})
                result.success.append(pp)
            except Exception as e:
                result.failed[pp] = str(e)
        result.print_summary("Label create")

    @label_app.command("delete")
    def label_delete(
        ctx: typer.Context,
        name: str = typer.Option(..., "--name"),
        project: str = typer.Option(..., "--project", "-p"),
        confirm: bool = typer.Option(False, "--confirm"),
    ):
        if not confirm_action("Delete label.", confirm):
            raise typer.Exit(1)
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        get_project(gl, project).labels.delete(name)
        console.print(f"Deleted label {name}")

    app.add_typer(label_app, name="label")
