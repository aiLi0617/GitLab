from __future__ import annotations

from typing import Optional

import typer
from rich.table import Table

from lib.auth import resolve_auth
from lib.commands.protect_cmd import _project_paths
from lib.context import CLIContext
from lib.gitlab_client import create_client, get_project
from lib.utils import BatchResult, confirm_action, console


def register(app: typer.Typer) -> None:
    pipeline_app = typer.Typer(help="CI/CD pipelines")

    @pipeline_app.command("list")
    def pipeline_list(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        status: Optional[str] = typer.Option(None, "--status"),
    ):
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        kwargs = {"all": True}
        if status:
            kwargs["status"] = status
        table = Table()
        table.add_column("ID")
        table.add_column("Ref")
        table.add_column("Status")
        table.add_column("Web")
        for p in get_project(gl, project).pipelines.list(**kwargs):
            table.add_row(str(p.id), p.ref, p.status, p.web_url)
        console.print(table)

    @pipeline_app.command("run")
    def pipeline_run(
        ctx: typer.Context,
        project: Optional[str] = typer.Option(None, "--project", "-p"),
        group: Optional[list[str]] = typer.Option(None, "--group", "-g"),
        ref: str = typer.Option("main", "--ref"),
        var: Optional[list[str]] = typer.Option(None, "--var"),
        projects_file: Optional[str] = typer.Option(None, "-f", "--file"),
    ):
        cli: CLIContext = ctx.obj
        paths = _project_paths(ctx, [project] if project else None, group, projects_file)
        if project and project not in paths:
            paths.insert(0, project)
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        variables = {}
        for v in var or []:
            k, _, val = v.partition("=")
            variables[k] = val
        result = BatchResult()
        for pp in paths:
            try:
                if cli.dry_run:
                    console.print(f"[dry-run] pipeline run {pp} ref={ref}")
                    result.success.append(pp)
                    continue
                pipe = get_project(gl, pp).pipelines.create({"ref": ref, "variables": variables or None})
                console.print(f"{pp}: pipeline {pipe.id} {pipe.status}")
                result.success.append(pp)
            except Exception as e:
                result.failed[pp] = str(e)
        result.print_summary("Pipeline run")

    @pipeline_app.command("status")
    def pipeline_status(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        pipeline_id: int = typer.Option(..., "--id"),
        wait: bool = typer.Option(False, "--wait"),
    ):
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        pipe = get_project(gl, project).pipelines.get(pipeline_id)
        console.print(f"Pipeline {pipe.id}: {pipe.status} ref={pipe.ref}")
        for job in pipe.jobs.list(all=True):
            console.print(f"  job {job.name}: {job.status}")

    @pipeline_app.command("retry")
    def pipeline_retry(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        pipeline_id: int = typer.Option(..., "--id"),
    ):
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        pipe = get_project(gl, project).pipelines.get(pipeline_id)
        pipe.retry()
        console.print(f"Retried pipeline {pipeline_id}")

    @pipeline_app.command("cancel")
    def pipeline_cancel(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        pipeline_id: int = typer.Option(..., "--id"),
        confirm: bool = typer.Option(False, "--confirm"),
    ):
        if not confirm_action("Cancel pipeline.", confirm):
            raise typer.Exit(1)
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        get_project(gl, project).pipelines.get(pipeline_id).cancel()
        console.print(f"Cancelled pipeline {pipeline_id}")

    @pipeline_app.command("jobs")
    def pipeline_jobs(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        pipeline_id: int = typer.Option(..., "--id"),
    ):
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        pipe = get_project(gl, project).pipelines.get(pipeline_id)
        for job in pipe.jobs.list(all=True):
            console.print(f"{job.id}\t{job.name}\t{job.status}\t{job.stage}")

    app.add_typer(pipeline_app, name="pipeline")
