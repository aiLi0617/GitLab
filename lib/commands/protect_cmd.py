from __future__ import annotations

from typing import Optional

import typer

from lib.auth import resolve_auth
from lib.context import CLIContext
from lib.gitlab_client import create_client, get_project, iter_group_projects
from lib.projects_loader import load_projects_file, resolve_projects_path
from lib.utils import ACCESS_LEVELS, BatchResult, confirm_action, console


def _project_paths(ctx: typer.Context, project, group, projects_file) -> list[str]:
    cli: CLIContext = ctx.obj
    paths: list[str] = list(project or [])
    pf_path = resolve_projects_path(projects_file or cli.projects_file, cli.config)
    if pf_path:
        pf = load_projects_file(pf_path)
        paths.extend([e.path for e in pf.enabled_projects()])
    if group:
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        for g in group:
            for p in iter_group_projects(gl, g, recursive=True):
                paths.append(p.path_with_namespace)
    return list(dict.fromkeys(paths))


def register(app: typer.Typer) -> None:
    protect_app = typer.Typer(help="Protected branches and tags")
    tag_app = typer.Typer(help="Protected tags")
    protect_app.add_typer(tag_app, name="tag")

    @protect_app.command("set")
    def protect_set(
        ctx: typer.Context,
        branch: str = typer.Option(..., "--branch", "-b"),
        project: Optional[list[str]] = typer.Option(None, "--project", "-p"),
        group: Optional[list[str]] = typer.Option(None, "--group", "-g"),
        projects_file: Optional[str] = typer.Option(None, "-f", "--file"),
        preset: Optional[str] = typer.Option(None, "--preset"),
        push_access_level: Optional[str] = typer.Option(None, "--push-access-level"),
        merge_access_level: Optional[str] = typer.Option(None, "--merge-access-level"),
        allow_force_push: Optional[bool] = typer.Option(None, "--allow-force-push"),
        skip_existing: bool = typer.Option(False, "--skip-existing"),
    ):
        cli: CLIContext = ctx.obj
        cfg = cli.config
        presets = cfg.protect.get("presets", {})
        pre = presets.get(preset, {}) if preset else {}
        push_lvl = ACCESS_LEVELS.get(
            (push_access_level or pre.get("push_access_level", "maintainer")).lower(), 40
        )
        merge_lvl = ACCESS_LEVELS.get(
            (merge_access_level or pre.get("merge_access_level", "developer")).lower(), 30
        )
        force = allow_force_push if allow_force_push is not None else pre.get("allow_force_push", False)
        paths = _project_paths(ctx, project, group, projects_file)
        if not paths:
            raise typer.BadParameter("Specify --project, --group, or -f")
        auth = resolve_auth(cfg, cli.url)
        gl = create_client(auth)
        result = BatchResult()
        for pp in paths:
            try:
                if cli.dry_run:
                    console.print(f"[dry-run] protect {pp} branch={branch}")
                    result.success.append(pp)
                    continue
                proj = get_project(gl, pp)
                existing = {b.name: b for b in proj.protectedbranches.list(all=True)}
                if branch in existing and skip_existing:
                    result.skipped.append(pp)
                    continue
                if branch in existing:
                    existing[branch].delete()
                proj.protectedbranches.create(
                    {
                        "name": branch,
                        "push_access_level": push_lvl,
                        "merge_access_level": merge_lvl,
                        "allow_force_push": force,
                    }
                )
                result.success.append(pp)
            except Exception as e:
                result.failed[pp] = str(e)
        result.print_summary("Protect set")

    @protect_app.command("remove")
    def protect_remove(
        ctx: typer.Context,
        branch: str = typer.Option(..., "--branch", "-b"),
        project: Optional[list[str]] = typer.Option(None, "--project", "-p"),
        group: Optional[list[str]] = typer.Option(None, "--group", "-g"),
        projects_file: Optional[str] = typer.Option(None, "-f", "--file"),
        confirm: bool = typer.Option(False, "--confirm"),
    ):
        if not confirm_action("Remove branch protection.", confirm):
            raise typer.Exit(1)
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
                get_project(gl, pp).protectedbranches.delete(branch)
                result.success.append(pp)
            except Exception as e:
                result.failed[pp] = str(e)
        result.print_summary("Protect remove")

    @protect_app.command("list")
    def protect_list(
        ctx: typer.Context,
        project: Optional[list[str]] = typer.Option(None, "--project", "-p"),
        group: Optional[list[str]] = typer.Option(None, "--group", "-g"),
        projects_file: Optional[str] = typer.Option(None, "-f", "--file"),
        branch: Optional[str] = typer.Option(None, "--branch", "-b"),
    ):
        cli: CLIContext = ctx.obj
        paths = _project_paths(ctx, project, group, projects_file)
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        for pp in paths:
            proj = get_project(gl, pp)
            for rule in proj.protectedbranches.list(all=True):
                if branch and rule.name != branch:
                    continue
                console.print(f"{pp}\t{rule.name}\tpush={rule.push_access_levels}\tmerge={rule.merge_access_levels}")

    @tag_app.command("set")
    def tag_set(
        ctx: typer.Context,
        wildcard: str = typer.Option(..., "--wildcard"),
        project: Optional[list[str]] = typer.Option(None, "--project", "-p"),
        group: Optional[list[str]] = typer.Option(None, "--group", "-g"),
        projects_file: Optional[str] = typer.Option(None, "-f", "--file"),
        create_access_level: str = typer.Option("maintainer", "--create-access-level"),
    ):
        cli: CLIContext = ctx.obj
        lvl = ACCESS_LEVELS.get(create_access_level.lower(), 40)
        paths = _project_paths(ctx, project, group, projects_file)
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        result = BatchResult()
        for pp in paths:
            try:
                if cli.dry_run:
                    result.success.append(pp)
                    continue
                get_project(gl, pp).protectedtags.create({"name": wildcard, "create_access_level": lvl})
                result.success.append(pp)
            except Exception as e:
                result.failed[pp] = str(e)
        result.print_summary("Protect tag set")

    @tag_app.command("remove")
    def tag_remove(
        ctx: typer.Context,
        name: str = typer.Option(..., "--name"),
        project: Optional[list[str]] = typer.Option(None, "--project", "-p"),
        confirm: bool = typer.Option(False, "--confirm"),
        projects_file: Optional[str] = typer.Option(None, "-f", "--file"),
    ):
        if not confirm_action("Remove tag protection.", confirm):
            raise typer.Exit(1)
        cli: CLIContext = ctx.obj
        paths = _project_paths(ctx, project, None, projects_file)
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        for pp in paths:
            get_project(gl, pp).protectedtags.delete(name)

    @tag_app.command("list")
    def tag_list(
        ctx: typer.Context,
        project: str = typer.Option(..., "--project", "-p"),
    ):
        cli: CLIContext = ctx.obj
        auth = resolve_auth(cli.config, cli.url)
        gl = create_client(auth)
        for t in get_project(gl, project).protectedtags.list(all=True):
            console.print(f"{t.name}\tcreate={t.create_access_levels}")

    app.add_typer(protect_app, name="protect")
