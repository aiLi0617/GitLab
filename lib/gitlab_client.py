from __future__ import annotations

import gitlab

from lib.auth import AuthInfo


def create_client(auth: AuthInfo) -> gitlab.Gitlab:
    if auth.auth_type == "oauth":
        gl = gitlab.Gitlab(auth.gitlab_url, oauth_token=auth.token)
    else:
        gl = gitlab.Gitlab(auth.gitlab_url, private_token=auth.token)
    return gl


def get_project(gl: gitlab.Gitlab, project_path: str):
    return gl.projects.get(project_path, lazy=False)


def iter_group_projects(
    gl: gitlab.Gitlab,
    group_path: str,
    recursive: bool = False,
):
    group = gl.groups.get(group_path)
    projects = group.projects.list(all=True, include_subgroups=recursive)
    for p in projects:
        yield p
