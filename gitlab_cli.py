"""GitLab automation CLI entry point."""

from __future__ import annotations

# Initialize language before command modules load (they use t() in Typer help).
from lib.i18n import init_i18n, t

init_i18n()

from typing import Optional

import typer

from lib.context import CLIContext
from lib.commands import (
    approval_cmd,
    artifact_cmd,
    backup_cmd,
    branch_sync_cmd,
    clone_cmd,
    git_cmd,
    label_cmd,
    member_cmd,
    mr_cmd,
    pipeline_cmd,
    project_cmd,
    protect_cmd,
    release_cmd,
    search_cmd,
    stats_cmd,
    sync_cmd,
    variable_cmd,
)
from lib.commands import projects_cmd

app = typer.Typer(
    name="gitlab-tool",
    help=t("app.help"),
    no_args_is_help=True,
)


@app.callback()
def main(
    ctx: typer.Context,
    profile: Optional[str] = typer.Option(None, "--profile", help=t("opt.profile")),
    url: Optional[str] = typer.Option(None, "--url", help=t("opt.url")),
    dry_run: bool = typer.Option(False, "--dry-run", help=t("opt.dry_run")),
    config: Optional[str] = typer.Option(None, "--config", help=t("opt.config")),
    file: Optional[str] = typer.Option(None, "-f", "--file", help=t("opt.file")),
    lang: Optional[str] = typer.Option(None, "--lang", "-L", help=t("opt.lang")),
) -> None:
    ctx.obj = CLIContext(
        profile=profile,
        url=url,
        dry_run=dry_run,
        config_path=config,
        projects_file=file,
    )


# Register all command groups
clone_cmd.register(app)
sync_cmd.register(app)
app.add_typer(projects_cmd.app, name="projects")
git_cmd.register(app)
branch_sync_cmd.register(app)
protect_cmd.register(app)
approval_cmd.register(app)
mr_cmd.register(app)
pipeline_cmd.register(app)
artifact_cmd.register(app)
project_cmd.register(app)
search_cmd.register(app)
release_cmd.register(app)
variable_cmd.register(app)
label_cmd.register(app)
member_cmd.register(app)
backup_cmd.register(app)
stats_cmd.register(app)


def app_entry() -> None:
    app()


if __name__ == "__main__":
    app_entry()
