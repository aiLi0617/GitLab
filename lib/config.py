from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

DEFAULT_CONFIG_NAMES = ("config.yaml", "config.example.yaml")


@dataclass
class AppConfig:
    raw: dict[str, Any]
    config_path: Path
    profile_name: str

    @property
    def profile(self) -> dict[str, Any]:
        profiles = self.raw.get("profiles", {})
        return profiles.get(self.profile_name, {})

    @property
    def gitlab_url(self) -> str:
        return os.environ.get("GITLAB_URL") or self.profile.get("url", "https://gitlab.com")

    @property
    def clone(self) -> dict[str, Any]:
        return self.raw.get("clone", {})

    @property
    def git(self) -> dict[str, Any]:
        return self.raw.get("git", {})

    @property
    def scope(self) -> dict[str, Any]:
        return self.raw.get("scope", {})

    @property
    def protect(self) -> dict[str, Any]:
        return self.raw.get("protect", {})

    @property
    def default_projects_file(self) -> str:
        return self.scope.get("default_projects_file", "projects.yaml")

    @property
    def base_dir(self) -> Path:
        return Path(self.clone.get("base_dir", "./repos"))

    @property
    def layout(self) -> str:
        return self.clone.get("layout", "nested")

    @property
    def use_ssh(self) -> bool:
        return bool(self.clone.get("use_ssh", True))

    @property
    def default_branch(self) -> str:
        return self.git.get("default_branch", "main")

    @property
    def parallel_jobs(self) -> int:
        return int(self.git.get("parallel_jobs", 4))


def find_config_path(explicit: str | None = None) -> Path:
    if explicit:
        p = Path(explicit)
        if not p.exists():
            raise FileNotFoundError(f"Config not found: {p}")
        return p
    for name in DEFAULT_CONFIG_NAMES:
        p = Path(name)
        if p.exists():
            return p
    raise FileNotFoundError(
        "No config.yaml found. Copy config.example.yaml to config.yaml"
    )


def load_config(
    profile: str | None = None,
    config_path: str | None = None,
    env_file: str | None = None,
) -> AppConfig:
    load_dotenv(env_file or ".env")
    path = find_config_path(config_path)
    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    profile_name = profile or raw.get("default_profile", "default")
    return AppConfig(raw=raw, config_path=path, profile_name=profile_name)
