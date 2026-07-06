from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, TypeVar

from rich.console import Console
from rich.table import Table

console = Console()
logger = logging.getLogger("gitlab-tool")

T = TypeVar("T")

ACCESS_LEVELS = {
    "no_one": 0,
    "developer": 30,
    "maintainer": 40,
    "admin": 60,
}

MEMBER_ACCESS = {
    "guest": 10,
    "reporter": 20,
    "developer": 30,
    "maintainer": 40,
    "owner": 50,
}


@dataclass
class BatchResult:
    success: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)

    def print_summary(self, title: str = "Summary") -> None:
        table = Table(title=title)
        table.add_column("Status")
        table.add_column("Count")
        table.add_row("Success", str(len(self.success)))
        table.add_row("Skipped", str(len(self.skipped)))
        table.add_row("Failed", str(len(self.failed)))
        console.print(table)
        for path, err in self.failed.items():
            console.print(f"[red]FAIL[/red] {path}: {err}")


def run_parallel(
    items: list[T],
    fn: Callable[[T], None],
    jobs: int = 4,
    continue_on_error: bool = True,
) -> BatchResult:
    result = BatchResult()
    if not items:
        return result

    def wrapper(item: T) -> tuple[T, str | None]:
        try:
            fn(item)
            return item, None
        except Exception as e:
            return item, str(e)

    with ThreadPoolExecutor(max_workers=max(1, jobs)) as pool:
        futures = {pool.submit(wrapper, item): item for item in items}
        for fut in as_completed(futures):
            item, err = fut.result()
            key = str(item)
            if err is None:
                result.success.append(key)
            else:
                result.failed[key] = err
                if not continue_on_error:
                    raise RuntimeError(f"{key}: {err}")
    return result


def confirm_action(message: str, confirm_flag: bool) -> bool:
    if confirm_flag:
        return True
    console.print(f"[yellow]{message}[/yellow] Use --confirm to proceed.")
    return False


def export_projects_yaml(path: Path, project_paths: list[str]) -> None:
    import yaml

    data = {
        "version": 1,
        "defaults": {"layout": "nested", "branch": "main"},
        "projects": [
            {"path": p, "enabled": True, "services": [], "note": ""}
            for p in sorted(project_paths)
        ],
    }
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False)
