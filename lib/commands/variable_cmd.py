from __future__ import annotations

from typing import Optional

import typer

from lib.auth import resolve_auth
from lib.context import CLIContext
from lib.gitlab_client import create_client, get_project
from lib.utils import confirm_action, console


def register(app: typer.Typer) -> None:
    variable_app = typer.Typer(help="CI/CD variables")

    @variable_app.command("list")
    def variable_list(
        ctx: typer.Context,
        project: Optional[str] = typer.Option(None, "--project", "-p"),
        group: Optional[str] = typer.Option(None, "--group", "-g"),
    ):
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        if project:
            for v in get_project(gl, project).variables.list(all=True):
                val = "[masked]" if v.masked else v.value
                console.print(f"{v.key}={val}\tprotected={v.protected}")
        elif group:
            for v in gl.groups.get(group).variables.list(all=True):
                val = "[masked]" if v.masked else v.value
                console.print(f"{v.key}={val}\tprotected={v.protected}")
        else:
            raise typer.BadParameter("Specify --project or --group")

    @variable_app.command("set")
    def variable_set(
        ctx: typer.Context,
        key: str = typer.Option(..., "--key"),
        value: str = typer.Option(..., "--value"),
        project: Optional[str] = typer.Option(None, "--project", "-p"),
        group: Optional[str] = typer.Option(None, "--group", "-g"),
        protected: bool = typer.Option(False, "--protected"),
        masked: bool = typer.Option(False, "--masked"),
        raw: bool = typer.Option(False, "--raw"),
    ):
        cli: CLIContext = ctx.obj
        if cli.dry_run:
            console.print(f"[dry-run] set {key} on {project or group}")
            return
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        data = {"key": key, "value": value, "protected": protected, "masked": masked, "raw": raw}
        if project:
            get_project(gl, project).variables.create(data)
        elif group:
            gl.groups.get(group).variables.create(data)
        else:
            raise typer.BadParameter("Specify --project or --group")
        console.print(f"Set variable {key}")

    @variable_app.command("delete")
    def variable_delete(
        ctx: typer.Context,
        key: str = typer.Option(..., "--key"),
        project: Optional[str] = typer.Option(None, "--project", "-p"),
        group: Optional[str] = typer.Option(None, "--group", "-g"),
        confirm: bool = typer.Option(False, "--confirm"),
    ):
        if not confirm_action("Delete variable.", confirm):
            raise typer.Exit(1)
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        if project:
            get_project(gl, project).variables.delete(key)
        elif group:
            gl.groups.get(group).variables.delete(key)
        console.print(f"Deleted {key}")

    app.add_typer(variable_app, name="variable")
