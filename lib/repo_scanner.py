from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lib.git_ops import GitRunner, RepoStatus
from lib.projects_loader import (
    ProjectEntry,
    ProjectsFile,
    local_path_for_project,
)


@dataclass
class RepoTarget:
    path: Path
    project_path: str | None = None
    branch: str | None = None


def find_git_repos(root: Path) -> list[Path]:
    if not root.exists():
        return []
    repos: list[Path] = []
    if (root / ".git").exists():
        return [root]
    for child in root.rglob(".git"):
        if child.is_dir():
            repos.append(child.parent)
    return sorted(set(repos))


def resolve_repo_targets(
    dest: Path | None,
    repos: list[str] | None,
    projects: ProjectsFile | None,
    base_dir: Path,
    layout: str,
    enabled_only: bool = True,
) -> list[RepoTarget]:
    if projects:
        entries = projects.enabled_projects(enabled_only=enabled_only)
        targets = []
        for entry in entries:
            local = local_path_for_project(entry.path, base_dir, layout)
            targets.append(
                RepoTarget(path=local, project_path=entry.path, branch=entry.branch)
            )
        return targets

    if repos:
        return [RepoTarget(path=Path(r).resolve()) for r in repos]

    if dest:
        return [RepoTarget(path=p) for p in find_git_repos(dest)]

    return [RepoTarget(path=p) for p in find_git_repos(base_dir)]


def filter_by_status(
    targets: list[RepoTarget],
    status_filter: str | None,
) -> list[RepoTarget]:
    if not status_filter:
        return targets
    filtered = []
    for t in targets:
        if not t.path.exists() or not (t.path / ".git").exists():
            continue
        st = GitRunner(t.path).status()
        if status_filter == "dirty" and st.dirty:
            filtered.append(t)
        elif status_filter == "ahead" and st.ahead > 0:
            filtered.append(t)
        elif status_filter == "behind" and st.behind > 0:
            filtered.append(t)
    return filtered
