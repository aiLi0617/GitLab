"""CLI help text internationalization (zh / en)."""

from __future__ import annotations

import locale
import os
import sys

_LANG = "en"

MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "app.help": "Cross-platform GitLab automation CLI",
        "opt.profile": "Config profile name",
        "opt.url": "Override GitLab URL",
        "opt.dry_run": "Print actions without executing",
        "opt.config": "Path to config.yaml",
        "opt.file": "Path to projects.yaml",
        "opt.lang": "UI language: zh or en (default: auto from system)",
        "cmd.clone.help": "Batch clone from projects.yaml, --project, or --group",
        "cmd.sync.help": "Fetch + pull all repos from projects.yaml or --dest",
        "cmd.branch_sync.help": "Sync branches via GitLab API compare and optional MR",
        "cmd.projects.help": "Local projects manifest (projects.yaml)",
        "cmd.projects.list": "List projects from projects.yaml",
        "cmd.projects.path": "GitLab project path, e.g. group/repo",
        "cmd.git.help": "Batch git operations across repos",
        "cmd.git.branch": "Branch operations",
        "cmd.git.tag": "Tag operations",
        "cmd.git.remote": "Remote operations",
        "cmd.git.stash": "Stash operations",
        "cmd.protect.help": "Protected branches and tags",
        "cmd.protect.tag": "Protected tags",
        "cmd.approval.help": "MR approval rules",
        "cmd.mr.help": "Merge requests",
        "cmd.pipeline.help": "CI/CD pipelines",
        "cmd.artifact.help": "CI artifacts",
        "cmd.project.help": "GitLab projects",
        "cmd.search.help": "Search GitLab",
        "cmd.release.help": "GitLab releases",
        "cmd.variable.help": "CI/CD variables",
        "cmd.label.help": "Project labels",
        "cmd.member.help": "Project members",
        "cmd.backup.help": "Project backup (phase 2)",
        "cmd.stats.help": "Commit statistics (phase 2)",
        "stub.backup": "backup export: not implemented yet (phase 2)",
        "stub.stats": "stats commits: not implemented yet (phase 2)",
        "stub.worktree": "git worktree: not implemented yet (phase 2)",
    },
    "zh": {
        "app.help": "跨平台 GitLab 自动化 CLI",
        "opt.profile": "配置 profile 名称",
        "opt.url": "覆盖 GitLab 地址",
        "opt.dry_run": "仅预览，不执行实际操作",
        "opt.config": "config.yaml 路径",
        "opt.file": "projects.yaml 项目清单路径",
        "opt.lang": "界面语言：zh 或 en（默认按系统自动选择）",
        "cmd.clone.help": "批量克隆（projects.yaml / --project / --group）",
        "cmd.sync.help": "批量 fetch + pull（projects.yaml 或 --dest）",
        "cmd.branch_sync.help": "跨分支同步（API 对比，可选创建 MR）",
        "cmd.projects.help": "本地项目清单（projects.yaml）",
        "cmd.projects.list": "列出 projects.yaml 中的项目",
        "cmd.projects.path": "GitLab 项目路径，如 group/repo",
        "cmd.git.help": "多仓库批量 Git 操作",
        "cmd.git.branch": "分支操作",
        "cmd.git.tag": "标签操作",
        "cmd.git.remote": "远程仓库操作",
        "cmd.git.stash": "暂存操作",
        "cmd.protect.help": "保护分支与保护标签",
        "cmd.protect.tag": "保护标签",
        "cmd.approval.help": "MR 合并审批规则",
        "cmd.mr.help": "合并请求（Merge Request）",
        "cmd.pipeline.help": "CI/CD 流水线",
        "cmd.artifact.help": "CI 构建产物",
        "cmd.project.help": "GitLab 项目管理",
        "cmd.search.help": "搜索 GitLab 资源",
        "cmd.release.help": "GitLab Release 发版",
        "cmd.variable.help": "CI/CD 变量",
        "cmd.label.help": "项目 Label 标签",
        "cmd.member.help": "项目成员管理",
        "cmd.backup.help": "项目备份（第二阶段）",
        "cmd.stats.help": "提交统计（第二阶段）",
        "stub.backup": "backup export：尚未实现（第二阶段）",
        "stub.stats": "stats commits：尚未实现（第二阶段）",
        "stub.worktree": "git worktree：尚未实现（第二阶段）",
    },
}


def _normalize_lang(value: str | None) -> str:
    if not value:
        return "en"
    v = value.lower().replace("_", "-")
    if v.startswith("zh"):
        return "zh"
    return "en"


def _detect_system_lang() -> str:
    for getter in (locale.getlocale, locale.getdefaultlocale):
        try:
            loc = getter()
            if loc and loc[0]:
                return _normalize_lang(loc[0])
        except Exception:
            continue
    for env_key in ("LANG", "LC_ALL", "LANGUAGE"):
        if os.environ.get(env_key):
            return _normalize_lang(os.environ[env_key])
    return "en"


def _lang_from_argv(argv: list[str]) -> str | None:
    for i, arg in enumerate(argv):
        if arg in ("--lang", "-L") and i + 1 < len(argv):
            return _normalize_lang(argv[i + 1])
        if arg.startswith("--lang="):
            return _normalize_lang(arg.split("=", 1)[1])
    return None


def init_i18n(argv: list[str] | None = None) -> str:
    """Detect language from argv, env GITLAB_TOOL_LANG, or system locale."""
    global _LANG
    argv = argv if argv is not None else sys.argv[1:]
    lang = _lang_from_argv(argv)
    if not lang and os.environ.get("GITLAB_TOOL_LANG"):
        lang = _normalize_lang(os.environ.get("GITLAB_TOOL_LANG"))
    if not lang:
        lang = _detect_system_lang()
    _LANG = lang if lang in MESSAGES else "en"
    return _LANG


def get_lang() -> str:
    return _LANG


def t(key: str) -> str:
    return MESSAGES.get(_LANG, MESSAGES["en"]).get(key, MESSAGES["en"].get(key, key))
