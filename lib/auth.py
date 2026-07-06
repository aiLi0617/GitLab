from __future__ import annotations

import os
from dataclasses import dataclass

from lib.config import AppConfig


@dataclass
class AuthInfo:
    auth_type: str
    token: str | None
    ssh_key: str | None
    gitlab_url: str


def resolve_auth(config: AppConfig, url_override: str | None = None) -> AuthInfo:
    profile = config.profile
    auth_type = profile.get("auth_type", "pat")
    token_env = profile.get("token_env", "GITLAB_TOKEN")
    token = os.environ.get(token_env) or os.environ.get("GITLAB_TOKEN")
    ssh_key = os.environ.get("GITLAB_SSH_KEY")
    gitlab_url = url_override or config.gitlab_url
    if auth_type in ("pat", "oauth") and not token:
        raise RuntimeError(
            f"Missing token: set {token_env} or GITLAB_TOKEN in .env"
        )
    return AuthInfo(
        auth_type=auth_type,
        token=token,
        ssh_key=ssh_key,
        gitlab_url=gitlab_url.rstrip("/"),
    )


def https_clone_url(auth: AuthInfo, project_path: str) -> str:
    host = auth.gitlab_url.replace("https://", "").replace("http://", "")
    if auth.token:
        return f"https://oauth2:{auth.token}@{host}/{project_path}.git"
    return f"{auth.gitlab_url}/{project_path}.git"


def ssh_clone_url(auth: AuthInfo, project_path: str) -> str:
    host = auth.gitlab_url.replace("https://", "").replace("http://", "")
    return f"git@{host}:{project_path}.git"
