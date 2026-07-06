# GitLab Tool

跨平台 GitLab 自动化 CLI：`clone` / `sync`、批量 `git` 子命令、`projects.yaml` 工作区清单，以及 GitLab API（MR、保护分支、流水线等）。

## 安装

```bash
cd Git脚本
py -3 -m venv .venv

# Windows
.\.venv\Scripts\Activate.ps1
pip install -e .

# Mac / Linux
source .venv/bin/activate
pip install -e .
```

安装后使用 `gitlab-tool`，或通过 `run.ps1` / `run.sh` 调用。

## 配置

```bash
copy config.example.yaml config.yaml    # Windows
copy .env.example .env                  # 填入 GITLAB_TOKEN

copy projects.example.yaml projects.yaml  # 维护你要处理的项目清单
```

### projects.yaml（主配置）

显式列出要处理的项目，未写入的不参与批量操作：

```yaml
projects:
  - path: broker-common/broker-common-email
    enabled: true
    services: [email]
    note: 日常必 sync
```

## 常用命令

```bash
# 查看本地项目清单
gitlab-tool projects list -f projects.yaml

# 按清单克隆（预览：--dry-run 放在子命令前）
gitlab-tool --dry-run clone -f projects.yaml --dest ./repos
gitlab-tool clone -f projects.yaml --dest ./repos

# 批量更新
gitlab-tool sync -f projects.yaml

# 批量 git 状态
gitlab-tool git status -f projects.yaml

# GitLab API 示例
gitlab-tool mr list --project group/repo
gitlab-tool protect set --project group/repo --branch main
```

> **注意**：`--dry-run` 是全局参数，需写在子命令前面，例如 `gitlab-tool --dry-run clone ...`。

## 推送到 GitHub

本地已初始化 git 并完成首次提交。你在本机执行：

```bash
cd "D:\CPHC\Desktop\Git脚本"
git push -u origin main --force
```

远程仓库：https://github.com/aiLi0617/GitLab.git

`--force` 会用当前目录内容覆盖远程历史（符合「清空远程后上传」的需求）。
