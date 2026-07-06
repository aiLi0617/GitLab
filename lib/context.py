from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from lib.config import AppConfig, load_config
from lib.projects_loader import ProjectsFile, load_projects_file, resolve_projects_path


@dataclass
class CLIContext:
    profile: Optional[str] = None
    url: Optional[str] = None
    dry_run: bool = False
    config_path: Optional[str] = None
    projects_file: Optional[str] = None
    _config: Optional[AppConfig] = None
    _projects: Optional[ProjectsFile] = None

    @property
    def config(self) -> AppConfig:
        if self._config is None:
            self._config = load_config(self.profile, self.config_path)
        return self._config

    def get_projects(self, projects_file: str | None = None) -> ProjectsFile | None:
        pf = resolve_projects_path(projects_file or self.projects_file, self.config)
        if pf is None:
            return self._projects
        return load_projects_file(pf)

    def base_dir(self, dest: str | None) -> Path:
        return Path(dest) if dest else self.config.base_dir

    def layout(self, projects: ProjectsFile | None) -> str:
        if projects:
            return projects.layout or self.config.layout
        return self.config.layout
