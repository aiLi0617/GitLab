from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import typer
from rich.console import Console
from rich.table import Table

from lib.auth import resolve_auth
from lib.context import CLIContext
from lib.git_ops import GitRunner
from lib.projects_loader import load_projects_file, resolve_projects_path
from lib.repo_scanner import filter_by_status, resolve_repo_targets
from lib.utils import BatchResult, confirm_action, console

git_app = typer.Typer(help="Batch git operations across repos")
branch_app = typer.Typer(help="Branch operations")
tag_app = typer.Typer(help="Tag operations")
remote_app = typer.Typer(help="Remote operations")
stash_app = typer.Typer(help="Stash operations")

git_app.add_typer(branch_app, name="branch")
git_app.add_typer(tag_app, name="tag")
git_app.add_typer(remote_app, name="remote")
git_app.add_typer(stash_app, name="stash")


def _resolve(ctx: typer.Context, dest, projects_file, repo, branch):
    cli: CLIContext = ctx.obj
    cfg = cli.config
    pf = None
    pf_path = resolve_projects_path(projects_file or cli.projects_file, cfg)
    if pf_path:
        pf = load_projects_file(pf_path)
    base = cli.base_dir(dest)
    layout = cli.layout(pf)
    br = branch or (pf.default_branch if pf else None) or cfg.default_branch
    targets = resolve_repo_targets(
        base if not pf and not repo else (Path(dest) if dest else None),
        repo,
        pf,
        base,
        layout,
    )
    auth = resolve_auth(cfg, cli.url)
    return cli, cfg, auth, targets, br


def _each_existing(targets, fn: Callable, dry_run: bool, label: str) -> BatchResult:
    result = BatchResult()
    for t in targets:
        if not t.path.exists() or not (t.path / ".git").exists():
            result.skipped.append(str(t.path))
            continue
        try:
            if dry_run:
                console.print(f"[dry-run] {label} {t.path}")
                result.success.append(str(t.path))
            else:
                fn(t)
                result.success.append(str(t.path))
        except Exception as e:
            result.failed[str(t.path)] = str(e)
    return result


@git_app.command("fetch")
def git_fetch(
    ctx: typer.Context,
    dest: Optional[str] = typer.Option(None, "--dest", "-d"),
    projects_file: Optional[str] = typer.Option(None, "-f", "--file"),
    repo: Optional[list[str]] = typer.Option(None, "--repo"),
    prune: bool = typer.Option(True, "--prune/--no-prune"),
):
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, projects_file, repo, None)

    def work(t):
        GitRunner(t.path, auth.ssh_key).fetch(prune=prune)

    _each_existing(targets, work, cli.dry_run, "fetch").print_summary("Fetch")


@git_app.command("pull")
def git_pull(
    ctx: typer.Context,
    dest: Optional[str] = typer.Option(None, "--dest", "-d"),
    projects_file: Optional[str] = typer.Option(None, "-f", "--file"),
    repo: Optional[list[str]] = typer.Option(None, "--repo"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b"),
    rebase: bool = typer.Option(False, "--rebase"),
    auto_stash: bool = typer.Option(False, "--auto-stash"),
):
    cli, cfg, auth, targets, br = _resolve(ctx, dest, projects_file, repo, branch)

    def work(t):
        GitRunner(t.path, auth.ssh_key).pull(
            branch=t.branch or br, rebase=rebase, auto_stash=auto_stash
        )

    _each_existing(targets, work, cli.dry_run, "pull").print_summary("Pull")


@git_app.command("push")
def git_push(
    ctx: typer.Context,
    dest: Optional[str] = typer.Option(None, "--dest", "-d"),
    projects_file: Optional[str] = typer.Option(None, "-f", "--file"),
    repo: Optional[list[str]] = typer.Option(None, "--repo"),
    branch: Optional[str] = typer.Option(None, "--branch", "-b"),
    set_upstream: bool = typer.Option(False, "--set-upstream", "-u"),
    tags: bool = typer.Option(False, "--tags"),
    force_with_lease: bool = typer.Option(False, "--force-with-lease"),
    confirm: bool = typer.Option(False, "--confirm"),
):
    cli, cfg, auth, targets, br = _resolve(ctx, dest, projects_file, repo, branch)
    if force_with_lease and not confirm_action("Force-with-lease push.", confirm):
        raise typer.Exit(1)

    def work(t):
        GitRunner(t.path, auth.ssh_key).push(
            branch=branch or br,
            set_upstream=set_upstream,
            tags=tags,
            force_with_lease=force_with_lease,
        )

    _each_existing(targets, work, cli.dry_run, "push").print_summary("Push")


@git_app.command("status")
def git_status(
    ctx: typer.Context,
    dest: Optional[str] = typer.Option(None, "--dest", "-d"),
    projects_file: Optional[str] = typer.Option(None, "-f", "--file"),
    repo: Optional[list[str]] = typer.Option(None, "--repo"),
    filter_name: Optional[str] = typer.Option(None, "--filter"),
    json_out: bool = typer.Option(False, "--json"),
):
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, projects_file, repo, None)
    targets = filter_by_status(targets, filter_name)
    table = Table(title="Git Status")
    table.add_column("Repo")
    table.add_column("Branch")
    table.add_column("Dirty")
    table.add_column("Ahead")
    table.add_column("Behind")
    rows = []
    for t in targets:
        if not t.path.exists() or not (t.path / ".git").exists():
            continue
        st = GitRunner(t.path, auth.ssh_key).status()
        rows.append(st)
        table.add_row(str(t.path), st.branch, str(st.dirty), str(st.ahead), str(st.behind))
    if json_out:
        import json
        console.print(json.dumps([r.__dict__ for r in rows], default=str))
    else:
        console.print(table)


@git_app.command("diff")
def git_diff(
    ctx: typer.Context,
    dest: Optional[str] = typer.Option(None, "--dest", "-d"),
    projects_file: Optional[str] = typer.Option(None, "-f", "--file"),
    stat: bool = typer.Option(False, "--stat"),
):
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, projects_file, None, None)
    for t in targets:
        if not (t.path / ".git").exists():
            continue
        out = GitRunner(t.path, auth.ssh_key).diff(stat=stat)
        if out.strip():
            console.print(f"\n[bold]{t.path}[/bold]\n{out}")


@git_app.command("log")
def git_log(
    ctx: typer.Context,
    dest: Optional[str] = typer.Option(None, "--dest", "-d"),
    projects_file: Optional[str] = typer.Option(None, "-f", "--file"),
    oneline: bool = typer.Option(False, "--oneline"),
    since: Optional[str] = typer.Option(None, "--since"),
    author: Optional[str] = typer.Option(None, "--author"),
    n: Optional[int] = typer.Option(None, "-n"),
):
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, projects_file, None, None)
    for t in targets:
        if not (t.path / ".git").exists():
            continue
        out = GitRunner(t.path, auth.ssh_key).log(oneline=oneline, since=since, author=author, n=n)
        if out.strip():
            console.print(f"\n[bold]{t.path}[/bold]\n{out}")


@branch_app.command("list")
def branch_list(ctx: typer.Context, dest: Optional[str] = None, projects_file: Optional[str] = typer.Option(None, "-f")):
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, projects_file, None, None)
    for t in targets:
        if not (t.path / ".git").exists():
            continue
        console.print(f"\n[bold]{t.path}[/bold]\n{GitRunner(t.path, auth.ssh_key).branch_list()}")


@branch_app.command("checkout")
def branch_checkout(ctx: typer.Context, branch: str, dest: Optional[str] = None, projects_file: Optional[str] = typer.Option(None, "-f")):
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, projects_file, None, None)

    def work(t):
        GitRunner(t.path, auth.ssh_key).checkout(branch)

    _each_existing(targets, work, cli.dry_run, f"checkout {branch}").print_summary("Checkout")


@branch_app.command("create")
def branch_create(
    ctx: typer.Context,
    branch: str,
    from_ref: str = typer.Option("HEAD", "--from"),
    dest: Optional[str] = None,
    projects_file: Optional[str] = typer.Option(None, "-f"),
    push: bool = typer.Option(True, "--push/--no-push"),
):
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, projects_file, None, None)

    def work(t):
        r = GitRunner(t.path, auth.ssh_key)
        r.branch_create(branch, from_ref)
        if push:
            r.push(branch=branch, set_upstream=True)

    _each_existing(targets, work, cli.dry_run, f"create {branch}").print_summary("Branch create")


@branch_app.command("delete")
def branch_delete(
    ctx: typer.Context,
    branch: str,
    dest: Optional[str] = None,
    projects_file: Optional[str] = typer.Option(None, "-f"),
    remote: bool = typer.Option(False, "--remote"),
    force: bool = typer.Option(False, "--force"),
    confirm: bool = typer.Option(False, "--confirm"),
):
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, projects_file, None, None)
    if remote and not confirm_action("Delete remote branch.", confirm):
        raise typer.Exit(1)

    def work(t):
        r = GitRunner(t.path, auth.ssh_key)
        r.branch_delete(branch, force=force)
        if remote:
            r.push_delete_remote_branch(branch)

    _each_existing(targets, work, cli.dry_run, f"delete {branch}").print_summary("Branch delete")


@branch_app.command("prune")
def branch_prune(
    ctx: typer.Context,
    merged_into: str = typer.Option("main", "--merged-into"),
    dest: Optional[str] = None,
    projects_file: Optional[str] = typer.Option(None, "-f"),
    confirm: bool = typer.Option(False, "--confirm"),
):
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, projects_file, None, None)
    for t in targets:
        if not (t.path / ".git").exists():
            continue
        r = GitRunner(t.path, auth.ssh_key)
        branches = r.merged_branches(merged_into)
        console.print(f"{t.path}: {branches}")
        if confirm and not cli.dry_run:
            for b in branches:
                r.branch_delete(b, force=True)


@git_app.command("merge")
def git_merge(
    ctx: typer.Context,
    source: str,
    into: Optional[str] = None,
    repo: Optional[list[str]] = typer.Option(None, "--repo"),
    dest: Optional[str] = None,
):
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, None, repo, None)

    def work(t):
        GitRunner(t.path, auth.ssh_key).merge(source, into)

    _each_existing(targets, work, cli.dry_run, f"merge {source}").print_summary("Merge")


@git_app.command("rebase")
def git_rebase(
    ctx: typer.Context,
    onto: str,
    branch: Optional[str] = None,
    dest: Optional[str] = None,
    projects_file: Optional[str] = typer.Option(None, "-f"),
):
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, projects_file, None, None)

    def work(t):
        GitRunner(t.path, auth.ssh_key).rebase_onto(onto, branch)

    _each_existing(targets, work, cli.dry_run, f"rebase onto {onto}").print_summary("Rebase")


@git_app.command("cherry-pick")
def git_cherry_pick(
    ctx: typer.Context,
    commit: str,
    branch: Optional[str] = None,
    repo: Optional[list[str]] = typer.Option(None, "--repo"),
):
    cli, cfg, auth, targets, _ = _resolve(ctx, None, None, repo, branch)

    def work(t):
        r = GitRunner(t.path, auth.ssh_key)
        if branch:
            r.checkout(branch)
        r.cherry_pick(commit)

    _each_existing(targets, work, cli.dry_run, f"cherry-pick {commit}").print_summary("Cherry-pick")


@stash_app.callback(invoke_without_command=True)
def stash_push(ctx: typer.Context, dest: Optional[str] = None, projects_file: Optional[str] = typer.Option(None, "-f")):
    if ctx.invoked_subcommand:
        return
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, projects_file, None, None)

    def work(t):
        GitRunner(t.path, auth.ssh_key).stash_push()

    _each_existing(targets, work, cli.dry_run, "stash").print_summary("Stash")


@stash_app.command("list")
def stash_list(ctx: typer.Context, dest: Optional[str] = None, projects_file: Optional[str] = typer.Option(None, "-f")):
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, projects_file, None, None)
    for t in targets:
        if not (t.path / ".git").exists():
            continue
        console.print(f"\n{t.path}\n{GitRunner(t.path, auth.ssh_key).stash_list()}")


@stash_app.command("pop")
def stash_pop(ctx: typer.Context, dest: Optional[str] = None, projects_file: Optional[str] = typer.Option(None, "-f")):
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, projects_file, None, None)

    def work(t):
        GitRunner(t.path, auth.ssh_key).stash_pop()

    _each_existing(targets, work, cli.dry_run, "stash pop").print_summary("Stash pop")


@stash_app.command("drop")
def stash_drop(ctx: typer.Context, all_: bool = typer.Option(False, "--all"), dest: Optional[str] = None, projects_file: Optional[str] = typer.Option(None, "-f")):
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, projects_file, None, None)

    def work(t):
        if all_:
            GitRunner(t.path, auth.ssh_key).stash_drop_all()

    _each_existing(targets, work, cli.dry_run, "stash drop").print_summary("Stash drop")


@tag_app.command("list")
def tag_list(ctx: typer.Context, dest: Optional[str] = None, projects_file: Optional[str] = typer.Option(None, "-f")):
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, projects_file, None, None)
    for t in targets:
        if not (t.path / ".git").exists():
            continue
        console.print(f"\n{t.path}\n{GitRunner(t.path, auth.ssh_key).tag_list()}")


@tag_app.command("create")
def tag_create(
    ctx: typer.Context,
    name: str,
    message: str = "",
    push: bool = typer.Option(False, "--push"),
    dest: Optional[str] = None,
    projects_file: Optional[str] = typer.Option(None, "-f"),
):
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, projects_file, None, None)

    def work(t):
        GitRunner(t.path, auth.ssh_key).tag_create(name, message, push=push)

    _each_existing(targets, work, cli.dry_run, f"tag {name}").print_summary("Tag create")


@tag_app.command("delete")
def tag_delete(
    ctx: typer.Context,
    name: str,
    remote: bool = typer.Option(False, "--remote"),
    dest: Optional[str] = None,
    confirm: bool = typer.Option(False, "--confirm"),
    projects_file: Optional[str] = typer.Option(None, "-f"),
):
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, projects_file, None, None)
    if not confirm_action("Delete tag.", confirm):
        raise typer.Exit(1)

    def work(t):
        GitRunner(t.path, auth.ssh_key).tag_delete(name, remote=remote)

    _each_existing(targets, work, cli.dry_run, f"tag delete {name}").print_summary("Tag delete")


@git_app.command("clean")
def git_clean(
    ctx: typer.Context,
    dest: Optional[str] = None,
    untracked: bool = typer.Option(True, "--untracked"),
    confirm: bool = typer.Option(False, "--confirm"),
    projects_file: Optional[str] = typer.Option(None, "-f"),
):
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, projects_file, None, None)
    if not confirm_action("Clean untracked files.", confirm):
        raise typer.Exit(1)

    def work(t):
        GitRunner(t.path, auth.ssh_key).clean(untracked=untracked)

    _each_existing(targets, work, cli.dry_run, "clean").print_summary("Clean")


@git_app.command("reset")
def git_reset(
    ctx: typer.Context,
    ref: str = typer.Argument("origin/main"),
    dest: Optional[str] = None,
    confirm: bool = typer.Option(False, "--confirm"),
    projects_file: Optional[str] = typer.Option(None, "-f"),
):
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, projects_file, None, None)
    if not confirm_action(f"Hard reset to {ref}.", confirm):
        raise typer.Exit(1)

    def work(t):
        GitRunner(t.path, auth.ssh_key).reset_hard(ref)

    _each_existing(targets, work, cli.dry_run, f"reset {ref}").print_summary("Reset")


@remote_app.command("list")
def remote_list(ctx: typer.Context, dest: Optional[str] = None, projects_file: Optional[str] = typer.Option(None, "-f")):
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, projects_file, None, None)
    for t in targets:
        if not (t.path / ".git").exists():
            continue
        console.print(f"\n{t.path}\n{GitRunner(t.path, auth.ssh_key).remote_list()}")


@remote_app.command("set-url")
def remote_set_url(
    ctx: typer.Context,
    from_url: str = typer.Option(..., "--from"),
    to_url: str = typer.Option(..., "--to"),
    name: str = typer.Option("origin", "--name"),
    dest: Optional[str] = None,
    projects_file: Optional[str] = typer.Option(None, "-f"),
):
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, projects_file, None, None)
    for t in targets:
        if not (t.path / ".git").exists():
            continue
        r = GitRunner(t.path, auth.ssh_key)
        remotes = r.remote_list()
        if from_url in remotes:
            if cli.dry_run:
                console.print(f"[dry-run] set-url {t.path}")
            else:
                r.remote_set_url(name, to_url)


@git_app.command("submodule")
def git_submodule(
    ctx: typer.Context,
    dest: Optional[str] = None,
    init: bool = typer.Option(False, "--init"),
    recursive: bool = typer.Option(False, "--recursive"),
    remote: bool = typer.Option(False, "--remote"),
    projects_file: Optional[str] = typer.Option(None, "-f"),
):
    cli, cfg, auth, targets, _ = _resolve(ctx, dest, projects_file, None, None)

    def work(t):
        GitRunner(t.path, auth.ssh_key).submodule_update(init=init, recursive=recursive, remote=remote)

    _each_existing(targets, work, cli.dry_run, "submodule").print_summary("Submodule")


@git_app.command("worktree")
def git_worktree_stub():
    raise typer.BadParameter("git worktree: not implemented yet (phase 2)")


def register(app: typer.Typer) -> None:
    app.add_typer(git_app, name="git")
