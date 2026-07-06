from __future__ import annotations

from typing import Optional

import typer

from lib.auth import resolve_auth
from lib.context import CLIContext
from lib.gitlab_client import create_client, get_project
from lib.utils import console


def register(app: typer.Typer) -> None:
    @app.command("branch-sync")
    def branch_sync(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        from_branch: str = typer.Option(..., "--from"),
        to_branch: str = typer.Option(..., "--to"),
        create_mr: bool = typer.Option(False, "--create-mr"),
        strategy: str = typer.Option("merge", "--strategy"),
        title: str = typer.Option("", "--title"),
    ):
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        proj = get_project(gl, project)
        compare = proj.repository_compare(from_branch, to_branch)
        commits = compare.get("commits", [])
        console.print(f"Commits to sync ({from_branch} -> {to_branch}): {len(commits)}")
        if cli.dry_run:
            return
        if create_mr:
            mr_title = title or f"Sync {from_branch} into {to_branch}"
            mr = proj.mergerequests.create(
                {
                    "source_branch": from_branch,
                    "target_branch": to_branch,
                    "title": mr_title,
                }
            )
            console.print(f"Created MR !{mr.iid}: {mr.web_url}")
        else:
            console.print("Use --create-mr to open merge request for sync")
