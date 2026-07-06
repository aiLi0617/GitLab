from __future__ import annotations

from typing import Optional

import typer

from lib.auth import resolve_auth
from lib.context import CLIContext
from lib.gitlab_client import create_client, get_project
from lib.commands.protect_cmd import _project_paths
from lib.utils import confirm_action, console, BatchResult


def register(app: typer.Typer) -> None:
    approval_app = typer.Typer(help="MR approval rules")

    @approval_app.command("set")
    def approval_set(
        ctx: typer.Context,
        branch: str = typer.Option(..., "--branch", "-b"),
        approvals_required: int = typer.Option(1, "--approvals-required"),
        project: Optional[list[str]] = typer.Option(None, "--project", "-p"),
        group: Optional[list[str]] = typer.Option(None, "--group", "-g"),
        projects_file: Optional[str] = typer.Option(None, "-f", "--file"),
        rule_name: str = typer.Option("default", "--rule-name"),
        reset_on_push: bool = typer.Option(True, "--reset-approvals-on-push/--no-reset-approvals-on-push"),
    ):
        cli: CLIContext = ctx.obj
        paths = _project_paths(ctx, project, group, projects_file)
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        result = BatchResult()
        for pp in paths:
            try:
                if cli.dry_run:
                    result.success.append(pp)
                    continue
                proj = get_project(gl, pp)
                proj.approvalrules.create(
                    {
                        "name": rule_name,
                        "approvals_required": approvals_required,
                        "protected_branch_ids": [],
                        "rule_type": "regular",
                    }
                )
                result.success.append(pp)
            except Exception as e:
                result.failed[pp] = str(e)
        result.print_summary("Approval set")

    @approval_app.command("list")
    def approval_list(ctx: typer.Context, project: str = typer.Option(..., "--project", "-p")):
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        for r in get_project(gl, project).approvalrules.list(all=True):
            console.print(f"{r.name}\tapprovals={r.approvals_required}")

    @approval_app.command("remove")
    def approval_remove(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
        rule_id: int = typer.Option(..., "--id"),
        confirm: bool = typer.Option(False, "--confirm"),
    ):
        if not confirm_action("Remove approval rule.", confirm):
            raise typer.Exit(1)
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        get_project(gl, project).approvalrules.delete(rule_id)

    app.add_typer(approval_app, name="approval")
