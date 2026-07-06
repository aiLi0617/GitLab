from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from lib.config import AppConfig


@dataclass
class ProjectEntry:
    path: str
    enabled: bool = True
    services: list[str] = field(default_factory=list)
    note: str = ""
    branch: str | None = None
    role: str | None = None


@dataclass
class ProjectsFile:
    raw: dict[str, Any]
    path: Path
    workspace: str = ""
    defaults: dict[str, Any] = field(default_factory=dict)
    projects: list[ProjectEntry] = field(default_factory=list)

    @property
    def layout(self) -> str:
        return self.defaults.get("layout", "nested")

    @property
    def default_branch(self) -> str | None:
        return self.defaults.get("branch")

    def enabled_projects(
        self,
        service: str | None = None,
        enabled_only: bool = True,
    ) -> list[ProjectEntry]:
        result = []
        for p in self.projects:
            if enabled_only and not p.enabled:
                continue
            if service and service not in p.services:
                continue
            result.append(p)
        return result


def load_projects_file(path: str | Path) -> ProjectsFile:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Projects file not found: {p}")
    with p.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    entries = []
    for item in raw.get("projects", []):
        if isinstance(item, str):
            entries.append(ProjectEntry(path=item))
        else:
            entries.append(
                ProjectEntry(
                    path=item["path"],
                    enabled=item.get("enabled", True),
                    services=list(item.get("services", [])),
                    note=item.get("note", ""),
                    branch=item.get("branch"),
                    role=item.get("role"),
                )
            )
    return ProjectsFile(
        raw=raw,
        path=p,
        workspace=raw.get("workspace", ""),
        defaults=raw.get("defaults", {}),
        projects=entries,
    )


def resolve_projects_path(
    projects_file: str | None,
    config: AppConfig | None = None,
) -> Path | None:
    if projects_file:
        return Path(projects_file)
    if config:
        default = config.default_projects_file
        if Path(default).exists():
            return Path(default)
    if Path("projects.yaml").exists():
        return Path("projects.yaml")
    return None


def local_path_for_project(
    project_path: str,
    base_dir: Path,
    layout: str = "nested",
) -> Path:
    if layout == "flat":
        name = project_path.split("/")[-1]
        return base_dir / name
    return base_dir / project_path


def match_glob(name: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(name, pat) or fnmatch.fnmatch(name.split("/")[-1], pat):
            return True
    return False


def filter_project_paths(
    paths: list[str],
    include: list[str] | None = None,
    exclude: list[str] | None = None,
) -> list[str]:
    include = include or []
    exclude = exclude or []
    if include:
        paths = [p for p in paths if match_glob(p, include) or p in include]
    if exclude:
        paths = [p for p in paths if not match_glob(p, exclude) and p not in exclude]
    return paths
