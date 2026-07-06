from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from lib.auth import resolve_auth
from lib.context import CLIContext
from lib.gitlab_client import create_client, get_project, iter_group_projects
from lib.utils import confirm_action, console, export_projects_yaml


def register(app: typer.Typer) -> None:
    project_app = typer.Typer(help="GitLab projects")

    @project_app.command("list")
    def project_list(
        ctx: typer.Context,
        group: Optional[str] = typer.Option(None, "--group", "-g"),
        archived: bool = typer.Option(False, "--archived"),
        recursive: bool = typer.Option(False, "--recursive"),
        export: Optional[str] = typer.Option(None, "--export"),
    ):
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        paths = []
        table = Table(title="Projects")
        table.add_column("Path")
        table.add_column("Default Branch")
        if group:
            for p in iter_group_projects(gl, group, recursive=recursive):
                if archived and not getattr(p, "archived", False):
                    continue
                paths.append(p.path_with_namespace)
                table.add_row(p.path_with_namespace, getattr(p, "default_branch", ""))
        else:
            for p in gl.projects.list(all=True, archived=archived):
                paths.append(p.path_with_namespace)
                table.add_row(p.path_with_namespace, getattr(p, "default_branch", ""))
        console.print(table)
        if export:
            export_projects_yaml(Path(export), paths)
            console.print(f"Exported to {export}")

    @project_app.command("create")
    def project_create(
        ctx: typer.Context,
        group: str = typer.Option(..., "--group", "-g"),
        name: str = typer.Option(..., "--name"),
        visibility: str = typer.Option("private", "--visibility"),
        description: str = typer.Option("", "--description"),
    ):
        cli: CLIContext = ctx.obj
        if cli.dry_run:
            console.print(f"[dry-run] create {group}/{name}")
            return
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        g = gl.groups.get(group)
        p = gl.projects.create({"name": name, "namespace_id": g.id, "visibility": visibility, "description": description})
        console.print(f"Created {p.path_with_namespace}")

    @project_app.command("archive")
    def project_archive(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        confirm: bool = typer.Option(False, "--confirm"),
    ):
        if not confirm_action("Archive project.", confirm):
            raise typer.Exit(1)
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        get_project(gl, project).archive()
        console.print(f"Archived {project}")

    @project_app.command("unarchive")
    def project_unarchive(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
    ):
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        get_project(gl, project).unarchive()
        console.print(f"Unarchived {project}")

    @project_app.command("delete")
    def project_delete(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        confirm: bool = typer.Option(False, "--confirm"),
    ):
        if not confirm_action("Delete project permanently.", confirm):
            raise typer.Exit(1)
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        get_project(gl, project).delete()
        console.print(f"Deleted {project}")

    app.add_typer(project_app, name="project")
