from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass
class GitResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass
class RepoStatus:
    path: Path
    branch: str
    dirty: bool
    ahead: int
    behind: int
    detached: bool


class GitRunner:
    def __init__(self, repo_path: Path, ssh_key: str | None = None):
        self.repo_path = Path(repo_path)
        self.ssh_key = ssh_key
        self.env = os.environ.copy()
        if ssh_key:
            self.env["GIT_SSH_COMMAND"] = f'ssh -i "{ssh_key}" -o StrictHostKeyChecking=accept-new'

    def run(self, *args: str, check: bool = True, cwd: Path | None = None) -> GitResult:
        cmd = ["git", *args]
        proc = subprocess.run(
            cmd,
            cwd=cwd or self.repo_path,
            env=self.env,
            capture_output=True,
            text=True,
        )
        if check and proc.returncode != 0:
            raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"git failed: {args}")
        return GitResult(proc.returncode, proc.stdout, proc.stderr)

    def clone(
        self,
        url: str,
        dest: Path,
        mirror: bool = False,
        depth: int = 0,
        recurse_submodules: bool = False,
    ) -> None:
        args = ["clone"]
        if mirror:
            args.append("--mirror")
        if depth > 0:
            args.extend(["--depth", str(depth)])
        if recurse_submodules:
            args.append("--recurse-submodules")
        args.extend([url, str(dest)])
        dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", *args],
            env=self.env,
            check=True,
            capture_output=True,
            text=True,
        )

    def fetch(self, prune: bool = True) -> None:
        args = ["fetch", "--all"]
        if prune:
            args.append("--prune")
        self.run(*args)

    def pull(self, branch: str | None = None, rebase: bool = False, auto_stash: bool = False) -> None:
        if auto_stash:
            st = self.status()
            if st.dirty:
                self.run("stash", "push", "-u", "-m", "gitlab-tool auto-stash")
        args = ["pull"]
        if rebase:
            args.append("--rebase")
        if branch:
            args.extend(["origin", branch])
        self.run(*args)

    def push(
        self,
        branch: str | None = None,
        set_upstream: bool = False,
        tags: bool = False,
        force_with_lease: bool = False,
    ) -> None:
        args = ["push"]
        if set_upstream:
            args.append("-u")
        if tags:
            args.append("--tags")
        if force_with_lease:
            args.append("--force-with-lease")
        if branch:
            args.extend(["origin", branch])
        self.run(*args)

    def status(self) -> RepoStatus:
        branch = "HEAD"
        detached = False
        try:
            branch = self.run("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
            detached = branch == "HEAD"
        except RuntimeError:
            detached = True

        dirty = bool(self.run("status", "--porcelain", check=False).stdout.strip())

        ahead, behind = 0, 0
        if not detached:
            try:
                out = self.run("rev-list", "--left-right", "--count", f"origin/{branch}...HEAD").stdout.strip()
                parts = out.split()
                if len(parts) == 2:
                    behind, ahead = int(parts[0]), int(parts[1])
            except RuntimeError:
                pass

        return RepoStatus(
            path=self.repo_path,
            branch=branch,
            dirty=dirty,
            ahead=ahead,
            behind=behind,
            detached=detached,
        )

    def diff(self, stat: bool = False) -> str:
        args = ["diff"]
        if stat:
            args.append("--stat")
        return self.run(*args, check=False).stdout

    def log(
        self,
        oneline: bool = False,
        since: str | None = None,
        author: str | None = None,
        n: int | None = None,
    ) -> str:
        args = ["log"]
        if oneline:
            args.append("--oneline")
        if since:
            args.extend(["--since", since])
        if author:
            args.extend(["--author", author])
        if n:
            args.extend(["-n", str(n)])
        return self.run(*args, check=False).stdout

    def branch_list(self) -> str:
        return self.run("branch", "-a", check=False).stdout

    def checkout(self, branch: str) -> None:
        self.run("checkout", branch)

    def branch_create(self, branch: str, from_ref: str = "HEAD") -> None:
        self.run("checkout", "-b", branch, from_ref)

    def branch_delete(self, branch: str, force: bool = False) -> None:
        self.run("branch", "-D" if force else "-d", branch)

    def push_delete_remote_branch(self, branch: str) -> None:
        self.run("push", "origin", "--delete", branch)

    def merge(self, source: str, into: str | None = None) -> None:
        if into:
            self.checkout(into)
        self.run("merge", source)

    def rebase_onto(self, onto: str, branch: str | None = None) -> None:
        if branch:
            self.checkout(branch)
        self.run("rebase", onto)

    def cherry_pick(self, commit: str) -> None:
        self.run("cherry-pick", commit)

    def stash_push(self) -> None:
        self.run("stash", "push", "-u")

    def stash_list(self) -> str:
        return self.run("stash", "list", check=False).stdout

    def stash_pop(self) -> None:
        self.run("stash", "pop")

    def stash_drop_all(self) -> None:
        self.run("stash", "clear")

    def tag_list(self) -> str:
        return self.run("tag", "-l", check=False).stdout

    def tag_create(self, name: str, message: str = "", push: bool = False) -> None:
        if message:
            self.run("tag", "-a", name, "-m", message)
        else:
            self.run("tag", name)
        if push:
            self.run("push", "origin", name)

    def tag_delete(self, name: str, remote: bool = False) -> None:
        self.run("tag", "-d", name)
        if remote:
            self.run("push", "origin", f":refs/tags/{name}")

    def clean(self, untracked: bool = True) -> None:
        args = ["clean", "-fd"] if untracked else ["clean", "-f"]
        self.run(*args)

    def reset_hard(self, ref: str) -> None:
        self.run("reset", "--hard", ref)

    def remote_list(self) -> str:
        return self.run("remote", "-v", check=False).stdout

    def remote_set_url(self, name: str, new_url: str) -> None:
        self.run("remote", "set-url", name, new_url)

    def submodule_update(self, init: bool = False, recursive: bool = False, remote: bool = False) -> None:
        args = ["submodule", "update"]
        if init:
            args.append("--init")
        if recursive:
            args.append("--recursive")
        if remote:
            args.append("--remote")
        self.run(*args)

    def merged_branches(self, merged_into: str = "main") -> list[str]:
        out = self.run("branch", "--merged", merged_into, check=False).stdout
        branches = []
        for line in out.splitlines():
            b = line.strip().lstrip("* ")
            if b and b != merged_into:
                branches.append(b)
        return branches
