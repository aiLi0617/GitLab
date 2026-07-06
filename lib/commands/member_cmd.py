from __future__ import annotations

from typing import Optional

import typer
from rich.table import Table

from lib.auth import resolve_auth
from lib.context import CLIContext
from lib.gitlab_client import create_client, get_project
from lib.utils import MEMBER_ACCESS, confirm_action, console


def register(app: typer.Typer) -> None:
    member_app = typer.Typer(help="Project members")

    @member_app.command("list")
    def member_list(ctx: typer.Context, project: str = typer.Option(..., "--project", "-p")):
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        table = Table()
        table.add_column("User")
        table.add_column("Access")
        for m in get_project(gl, project).members_all.list(all=True):
            table.add_row(str(m.username), str(m.access_level))
        console.print(table)

    @member_app.command("add")
    def member_add(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        user: Optional[str] = typer.Option(None, "--user"),
        user_id: Optional[int] = typer.Option(None, "--user-id"),
        access_level: str = typer.Option("developer", "--access-level"),
    ):
        cli: CLIContext = ctx.obj
        lvl = MEMBER_ACCESS.get(access_level.lower(), 30)
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        uid = user_id
        if user and not uid:
            uid = gl.users.list(username=user)[0].id
        get_project(gl, project).members.create({"user_id": uid, "access_level": lvl})
        console.print(f"Added member to {project}")

    @member_app.command("update")
    def member_update(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        user: str = typer.Option(..., "--user"),
        access_level: str = typer.Option(..., "--access-level"),
    ):
        cli: CLIContext = ctx.obj
        lvl = MEMBER_ACCESS.get(access_level.lower(), 30)
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        uid = gl.users.list(username=user)[0].id
        get_project(gl, project).members.get(uid).access_level = lvl
        get_project(gl, project).members.get(uid).save()
        console.print(f"Updated {user} on {project}")

    @member_app.command("remove")
    def member_remove(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        user: str = typer.Option(..., "--user"),
        confirm: bool = typer.Option(False, "--confirm"),
    ):
        if not confirm_action("Remove member.", confirm):
            raise typer.Exit(1)
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        uid = gl.users.list(username=user)[0].id
        get_project(gl, project).members.delete(uid)
        console.print(f"Removed {user} from {project}")

    app.add_typer(member_app, name="member")
