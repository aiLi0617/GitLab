from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

from lib.auth import https_clone_url, resolve_auth, ssh_clone_url
from lib.context import CLIContext
from lib.git_ops import GitRunner
from lib.gitlab_client import create_client, iter_group_projects
from lib.projects_loader import (
    filter_project_paths,
    load_projects_file,
    local_path_for_project,
    resolve_projects_path,
)
from lib.utils import BatchResult

console = Console()


def register(app: typer.Typer) -> None:
    @app.command("clone")
    def clone(
        ctx: typer.Context,
        project: Optional[list[str]] = typer.Option(None, "--project", "-p"),
        group: Optional[list[str]] = typer.Option(None, "--group", "-g"),
        dest: Optional[str] = typer.Option(None, "--dest", "-d"),
        projects_file: Optional[str] = typer.Option(None, "-f", "--file"),
        force: bool = typer.Option(False, "--force"),
        mirror: bool = typer.Option(False, "--mirror"),
        depth: Optional[int] = typer.Option(None, "--depth"),
        include_submodules: bool = typer.Option(False, "--include-submodules"),
        recursive: bool = typer.Option(False, "--recursive/--no-recursive"),
        exclude: Optional[list[str]] = typer.Option(None, "--exclude"),
        include: Optional[list[str]] = typer.Option(None, "--include"),
    ) -> None:
        """Batch clone from projects.yaml, --project, or --group."""
        cli: CLIContext = ctx.obj
        cfg = cli.config
        auth = None
        if not cli.dry_run or group:
            auth = resolve_auth(cfg, cli.url)
        base = cli.base_dir(dest)
        layout = cfg.layout
        shallow = depth if depth is not None else int(cfg.clone.get("shallow_depth", 0))
        result = BatchResult()

        paths: list[str] = list(project or [])
        pf = None
        pf_path = resolve_projects_path(projects_file or cli.projects_file, cfg)
        if pf_path:
            pf = load_projects_file(pf_path)
            layout = cli.layout(pf)
            paths.extend([e.path for e in pf.enabled_projects()])

        if group:
            if not auth:
                auth = resolve_auth(cfg, cli.url)
            gl = create_client(auth)
            for g in group:
                for p in iter_group_projects(gl, g, recursive=recursive):
                    paths.append(p.path_with_namespace)

        paths = list(dict.fromkeys(paths))
        inc = include or cfg.clone.get("include", [])
        exc = exclude or cfg.clone.get("exclude", [])
        paths = filter_project_paths(paths, inc or None, exc or None)

        if not paths:
            raise typer.BadParameter("Specify -f, --project, or --group")

        for project_path in paths:
            local = local_path_for_project(project_path, base, layout)
            try:
                if local.exists():
                    if force:
                        if cli.dry_run:
                            console.print(f"[dry-run] rm -rf {local}")
                        else:
                            shutil.rmtree(local)
                    else:
                        result.skipped.append(project_path)
                        continue
                url = (
                    ssh_clone_url(auth, project_path)
                    if cfg.use_ssh
                    else https_clone_url(auth, project_path)
                ) if auth else f"<clone-url>/{project_path}.git"
                if cli.dry_run:
                    console.print(f"[dry-run] git clone {url} -> {local}")
                    result.success.append(project_path)
                    continue
                GitRunner(local.parent, auth.ssh_key if auth else None).clone(
                    url, local, mirror=mirror, depth=shallow, recurse_submodules=include_submodules
                )
                if include_submodules and not mirror:
                    GitRunner(local, auth.ssh_key).submodule_update(init=True, recursive=True)
                result.success.append(project_path)
            except Exception as e:
                result.failed[project_path] = str(e)

        result.print_summary("Clone")
