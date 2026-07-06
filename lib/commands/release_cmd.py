from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from lib.auth import resolve_auth
from lib.context import CLIContext
from lib.gitlab_client import create_client, get_project
from lib.utils import confirm_action, console


def register(app: typer.Typer) -> None:
    release_app = typer.Typer(help="GitLab releases")

    @release_app.command("create")
    def release_create(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        tag: str = typer.Option(..., "--tag"),
        name: str = typer.Option("", "--name"),
        notes: str = typer.Option("", "--notes"),
        notes_file: Optional[str] = typer.Option(None, "--notes-file"),
        ref: Optional[str] = typer.Option(None, "--ref"),
    ):
        cli: CLIContext = ctx.obj
        body = notes
        if notes_file:
            body = Path(notes_file).read_text(encoding="utf-8")
        if cli.dry_run:
            console.print(f"[dry-run] release {project} {tag}")
            return
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        data = {"name": name or tag, "tag_name": tag, "description": body}
        if ref:
            data["ref"] = ref
        rel = get_project(gl, project).releases.create(data)
        console.print(f"Release {rel.tag_name}: {rel.name}")

    @release_app.command("list")
    def release_list(ctx: typer.Context, project: str = typer.Option(..., "--project", "-p")):
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        for r in get_project(gl, project).releases.list(all=True):
            console.print(f"{r.tag_name}\t{r.name}")

    @release_app.command("delete")
    def release_delete(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        tag: str = typer.Option(..., "--tag"),
        confirm: bool = typer.Option(False, "--confirm"),
    ):
        if not confirm_action("Delete release.", confirm):
            raise typer.Exit(1)
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        get_project(gl, project).releases.delete(tag)
        console.print(f"Deleted release {tag}")

    app.add_typer(release_app, name="release")
