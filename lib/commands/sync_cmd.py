from __future__ import annotations

from typing import Optional

import typer

from lib.auth import resolve_auth
from lib.context import CLIContext
from lib.git_ops import GitRunner
from lib.projects_loader import resolve_projects_path, load_projects_file
from lib.repo_scanner import resolve_repo_targets, filter_by_status
from lib.utils import BatchResult, console


def register(app: typer.Typer) -> None:
    @app.command("sync")
    def sync(
        ctx: typer.Context,
        dest: Optional[str] = typer.Option(None, "--dest", "-d"),
        projects_file: Optional[str] = typer.Option(None, "-f", "--file"),
        branch: Optional[str] = typer.Option(None, "--branch", "-b"),
        rebase: bool = typer.Option(False, "--rebase"),
        auto_stash: bool = typer.Option(False, "--auto-stash"),
        jobs: Optional[int] = typer.Option(None, "--jobs", "-j"),
        continue_on_error: bool = typer.Option(True, "--continue-on-error/--no-continue-on-error"),
    ) -> None:
        """Fetch + pull all repos from projects.yaml or --dest."""
        cli: CLIContext = ctx.obj
        cfg = cli.config
        auth = None if cli.dry_run else resolve_auth(cfg, cli.url)
        pf = None
        pf_path = resolve_projects_path(projects_file or cli.projects_file, cfg)
        if pf_path:
            pf = load_projects_file(pf_path)
        base = cli.base_dir(dest)
        layout = cli.layout(pf)
        default_branch = branch or (pf.default_branch if pf else None) or cfg.default_branch
        targets = resolve_repo_targets(base if not pf else None, None, pf, base, layout)
        result = BatchResult()

        for t in targets:
            if not t.path.exists() or not (t.path / ".git").exists():
                result.skipped.append(str(t.path))
                continue
            br = t.branch or default_branch
            try:
                if cli.dry_run:
                    console.print(f"[dry-run] sync {t.path} branch={br}")
                    result.success.append(str(t.path))
                    continue
                if auth is None:
                    auth = resolve_auth(cfg, cli.url)
                runner = GitRunner(t.path, auth.ssh_key)
                runner.fetch(prune=True)
                runner.pull(branch=br, rebase=rebase, auto_stash=auto_stash or cfg.git.get("auto_stash", False))
                result.success.append(str(t.path))
            except Exception as e:
                result.failed[str(t.path)] = str(e)
                if not continue_on_error:
                    break

        result.print_summary("Sync")
