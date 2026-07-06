from __future__ import annotations

from typing import Optional

import typer
from rich.table import Table

from lib.auth import resolve_auth
from lib.context import CLIContext
from lib.gitlab_client import create_client, get_project
from lib.utils import console


def register(app: typer.Typer) -> None:
    mr_app = typer.Typer(help="Merge requests")

    @mr_app.command("create")
    def mr_create(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        source: str = typer.Option(..., "--source"),
        target: str = typer.Option(..., "--target"),
        title: str = typer.Option(..., "--title"),
        description: str = typer.Option("", "--description"),
        remove_source_branch: bool = typer.Option(False, "--remove-source-branch"),
        labels: Optional[str] = typer.Option(None, "--labels"),
    ):
        cli: CLIContext = ctx.obj
        if cli.dry_run:
            console.print(f"[dry-run] MR {project} {source}->{target}")
            return
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        data = {
            "source_branch": source,
            "target_branch": target,
            "title": title,
            "description": description,
            "remove_source_branch": remove_source_branch,
        }
        if labels:
            data["labels"] = labels
        mr = get_project(gl, project).mergerequests.create(data)
        console.print(f"Created MR !{mr.iid}: {mr.web_url}")

    @mr_app.command("list")
    def mr_list(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        state: str = typer.Option("opened", "--state"),
    ):
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        table = Table(title=f"MRs ({project})")
        table.add_column("IID")
        table.add_column("Title")
        table.add_column("Source")
        table.add_column("Target")
        table.add_column("State")
        for mr in get_project(gl, project).mergerequests.list(state=state, all=True):
            table.add_row(str(mr.iid), mr.title, mr.source_branch, mr.target_branch, mr.state)
        console.print(table)

    @mr_app.command("update")
    def mr_update(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        iid: int = typer.Option(..., "--iid"),
        title: Optional[str] = typer.Option(None, "--title"),
        description: Optional[str] = typer.Option(None, "--description"),
        labels: Optional[str] = typer.Option(None, "--labels"),
    ):
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        mr = get_project(gl, project).mergerequests.get(iid)
        data = {}
        if title:
            data["title"] = title
        if description is not None:
            data["description"] = description
        if labels:
            data["labels"] = labels
        if data:
            mr.save(**data)
        console.print(f"Updated MR !{iid}")

    @mr_app.command("approve")
    def mr_approve(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        iid: int = typer.Option(..., "--iid"),
    ):
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        mr = get_project(gl, project).mergerequests.get(iid)
        mr.approve()
        console.print(f"Approved MR !{iid}")

    @mr_app.command("merge")
    def mr_merge(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        iid: int = typer.Option(..., "--iid"),
        when_pipeline_succeeds: bool = typer.Option(False, "--when-pipeline-succeeds"),
    ):
        cli: CLIContext = ctx.obj
        if cli.dry_run:
            console.print(f"[dry-run] merge !{iid}")
            return
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        mr = get_project(gl, project).mergerequests.get(iid)
        mr.merge(merge_when_pipeline_succeeds=when_pipeline_succeeds)
        console.print(f"Merged MR !{iid}")

    @mr_app.command("rebase")
    def mr_rebase(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        iid: int = typer.Option(..., "--iid"),
    ):
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        mr = get_project(gl, project).mergerequests.get(iid)
        mr.rebase()
        console.print(f"Rebased MR !{iid}")

    @mr_app.command("close")
    def mr_close(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        iid: int = typer.Option(..., "--iid"),
    ):
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        mr = get_project(gl, project).mergerequests.get(iid)
        mr.state_event = "close"
        mr.save()
        console.print(f"Closed MR !{iid}")

    app.add_typer(mr_app, name="mr")
