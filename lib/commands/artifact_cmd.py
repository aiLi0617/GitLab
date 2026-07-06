from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from lib.auth import resolve_auth
from lib.context import CLIContext
from lib.gitlab_client import create_client, get_project
from lib.utils import console


def register(app: typer.Typer) -> None:
    artifact_app = typer.Typer(help="CI artifacts")

    @artifact_app.command("list")
    def artifact_list(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        pipeline_id: int = typer.Option(..., "--pipeline-id"),
    ):
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        pipe = get_project(gl, project).pipelines.get(pipeline_id)
        for job in pipe.jobs.list(all=True):
            has = "yes" if getattr(job, "artifacts_file", None) or job.status == "success" else "?"
            console.print(f"{job.id}\t{job.name}\t{job.status}\tartifacts={has}")

    @artifact_app.command("download")
    def artifact_download(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        dest: str = typer.Option(..., "--dest", "-d"),
        job_id: Optional[int] = typer.Option(None, "--job-id"),
        pipeline_id: Optional[int] = typer.Option(None, "--pipeline-id"),
        job_name: Optional[str] = typer.Option(None, "--job-name"),
    ):
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        proj = get_project(gl, project)
        out_dir = Path(dest)
        out_dir.mkdir(parents=True, exist_ok=True)

        if job_id:
            job = proj.jobs.get(job_id)
            data = job.artifacts()
            out = out_dir / f"job-{job_id}-artifacts.zip"
            out.write_bytes(data)
            console.print(f"Saved {out}")
            return

        if pipeline_id and job_name:
            pipe = proj.pipelines.get(pipeline_id)
            for job in pipe.jobs.list(all=True):
                if job.name == job_name:
                    data = proj.jobs.get(job.id).artifacts()
                    out = out_dir / f"{job_name}-artifacts.zip"
                    out.write_bytes(data)
                    console.print(f"Saved {out}")
                    return
        raise typer.BadParameter("Specify --job-id or (--pipeline-id and --job-name)")

    app.add_typer(artifact_app, name="artifact")
