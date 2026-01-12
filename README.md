# GitLab控制脚本设计文档

## 1. 脚本概述

GitLab控制脚本（glctl.py）是一个用于管理GitLab仓库的命令行工具，支持分支管理、Tag管理、保护规则管理和合并请求管理等功能。脚本采用模块化设计，支持简称映射管理，避免仓库列表维护时的行数误差问题。

## 2. 脚本特性

- **简化的脚本名称**：使用 `glctl.py`（GitLab Control Tool），简洁易记
- **默认配置支持**：可直接在脚本中维护GitLab URL和Token，避免每次命令都输入
- **简称映射管理**：支持一个完整路径对应一个自定义简称，避免行数误差
- **批量操作支持**：支持基于映射文件的批量操作和所有仓库的批量操作
- **完善的错误处理**：详细的错误信息和解决方案建议
- **详细的日志记录**：操作过程和结果均有日志记录
- **友好的命令帮助**：完整的命令行帮助文档和使用示例

## 3. 依赖安装

```bash
pip install python-gitlab
```

## 4. 脚本结构

```
glctl.py
├── 默认配置区域
├── 日志配置
├── GitLab API初始化
├── 简称映射文件管理（加载/保存）
├── 核心功能实现
│   ├── 仓库查找与解析
│   ├── 分支管理
│   ├── Tag管理
│   ├── 保护规则管理
│   └── 合并请求管理
├── 命令处理函数
│   ├── 映射管理命令处理
│   ├── 分支管理命令处理
│   ├── Tag管理命令处理
│   └── 合并请求管理命令处理
└── 命令行参数解析
```

## 5. 默认配置

在脚本顶部可以直接修改默认配置：

```python
# 默认配置 - 可以直接在脚本中修改
DEFAULT_GITLAB_URL = "https://gitlab.example.com"  # GitLab服务器URL
DEFAULT_GITLAB_TOKEN = "your-default-token"  # GitLab访问令牌
DEFAULT_MAPPING_FILE = "repo-mapping.txt"  # 映射文件路径
```

## 6. 命令行参数

### 6.1 全局选项

| 选项 | 描述 | 默认值 | 示例 |
|------|------|--------|------|
| `--url` | GitLab服务器URL | 脚本中配置的默认值 | `--url https://gitlab.example.com` |
| `--token` | GitLab访问令牌 | 脚本中配置的默认值 | `--token your-token` |
| `--mapping-file` | 简称映射文件路径 | `repo-mapping.txt` | `--mapping-file custom-mappings.txt` |
| `--verbose` | 详细日志输出 | `False` | `--verbose` |
| `-h, --help` | 显示帮助信息 | - | `--help` |

### 6.2 批量操作选项

| 选项 | 描述 | 示例 |
|------|------|------|
| `--list` | 使用映射文件中的所有仓库 | `branch create --list new-feature master` |
| `--all` | 使用所有可访问仓库 | `tag create --all v1.0.0 master` |

## 7. 映射管理命令

### 7.1 查看映射列表

**命令**：`mapping list`

**描述**：显示当前所有仓库简称映射关系

**示例**：

```bash
# 使用默认配置
python glctl.py mapping list

# 指定映射文件
python glctl.py --mapping-file custom-mappings.txt mapping list

# 详细日志
python glctl.py --verbose mapping list
```

### 7.2 添加映射

**命令**：`mapping add <full-path> <short-name> [<full-path> <short-name> ...]`

**描述**：添加新的仓库简称映射，支持一次添加多个映射对

**参数**：
- `full-path`：GitLab仓库完整路径（group/project）
- `short-name`：自定义简称

**示例**：

```bash
# 添加单个映射
python glctl.py mapping add group1/project1 proj1

# 添加多个映射（支持多个）
python glctl.py mapping add group1/project1 proj1 group2/project2 proj2
```

### 7.3 更新映射

**命令**：`mapping update <repo-identifier> <new-short-name>`

**描述**：更新现有仓库的简称

**参数**：
- `repo-identifier`：仓库标识（完整路径或简称）
- `new-short-name`：新的简称

**示例**：

```bash
# 使用简称更新
python glctl.py mapping update proj1 new-proj1

# 使用完整路径更新
python glctl.py mapping update group1/project1 new-proj1
```

### 7.4 删除映射

**命令**：`mapping remove <repo-identifier>`

**描述**：删除现有仓库的简称映射

**参数**：
- `repo-identifier`：仓库标识（完整路径或简称）

**示例**：

```bash
# 使用简称删除
python glctl.py mapping remove proj1

# 使用完整路径删除
python glctl.py mapping remove group1/project1
```

### 7.5 清空映射

**命令**：`mapping clear`

**描述**：清空所有仓库简称映射

**示例**：

```bash
python glctl.py mapping clear
```

### 7.6 从GitLab同步仓库

**命令**：`mapping sync`

**描述**：从GitLab同步所有可访问仓库，并自动生成简称

**示例**：

```bash
python glctl.py mapping sync
```

### 7.7 检查映射完整性

**命令**：`mapping check`

**描述**：检查映射关系完整性，验证仓库是否存在

**示例**：

```bash
python glctl.py mapping check
```

## 8. 分支管理命令

### 8.1 创建分支

**命令**：`branch create [<single-repo-options>] <branch-name> <base-branch>`

**单仓库选项**（三选一）：
- `--repo <repo>`：指定单个仓库标识（完整路径或简称）
- `--list`：使用映射文件中的所有仓库
- `--all`：使用所有可访问仓库

**描述**：创建新分支

**参数**：
- `branch-name`：新分支名称
- `base-branch`：基础分支名称

**示例**：

```bash
# 使用简称创建分支
python glctl.py branch create --repo proj1 new-feature master

# 使用完整路径创建分支
python glctl.py branch create --repo group1/project1 new-feature master

# 基于映射文件中的所有仓库创建分支
python glctl.py branch create --list new-feature master

# 所有仓库创建分支
python glctl.py branch create --all new-feature master
```

### 8.2 保护分支

**命令**：`branch protect [<single-repo-options>] <branch-name> [--access-level <level>]`

**单仓库选项**（三选一）：
- `--repo <repo>`：指定单个仓库标识（完整路径或简称）
- `--list`：使用映射文件中的所有仓库
- `--all`：使用所有可访问仓库

**描述**：保护分支，设置访问级别

**参数**：
- `branch-name`：分支名称
- `--access-level`：访问级别，可选值：noone（无人可访问，默认）、maintainers（仅维护者可访问）、developers（开发者和维护者可访问）

**示例**：

```bash
# 保护单个仓库的分支（默认noone）
python glctl.py branch protect --repo proj1 master

# 保护分支，设置访问级别为maintainers
python glctl.py branch protect --repo proj1 master --access-level maintainers

# 保护分支，设置访问级别为developers
python glctl.py branch protect --repo proj1 master --access-level developers

# 基于映射文件中的所有仓库保护分支（默认noone）
python glctl.py branch protect --list master

# 基于映射文件中的所有仓库保护分支级别为maintainers
python glctl.py branch protect --list master --access-level maintainers

# 基于映射文件中的所有仓库保护分支级别为developers
python glctl.py branch protect --list master --access-level developers

# 所有仓库保护分支（默认noone）
python glctl.py branch protect --all master

# 所有仓库保护分支级别为maintainers
python glctl.py branch protect --all master --access-level maintainers

# 所有仓库保护分支级别为developers
python glctl.py branch protect --all master --access-level developers
```

### 8.3 取消分支保护

**命令**：`branch unprotect [<single-repo-options>] <branch-name>`

**单仓库选项**（三选一）：
- `--repo <repo>`：指定单个仓库标识（完整路径或简称）
- `--list`：使用映射文件中的所有仓库
- `--all`：使用所有可访问仓库

**描述**：取消分支保护

**参数**：
- `branch-name`：分支名称

**示例**：

```bash
# 取消单个仓库的分支保护
python glctl.py branch unprotect --repo proj1 master

# 基于映射文件中的所有仓库取消分支保护
python glctl.py branch unprotect --list master

# 所有仓库取消分支保护
python glctl.py branch unprotect --all master
```

## 9. Tag管理命令

### 9.1 创建Tag

**命令**：`tag create [<single-repo-options>] <tag-name> <ref>`

**单仓库选项**（三选一）：
- `--repo <repo>`：指定单个仓库标识（完整路径或简称）
- `--list`：使用映射文件中的所有仓库
- `--all`：使用所有可访问仓库

**描述**：创建新Tag

**参数**：
- `tag-name`：Tag名称
- `ref`：引用（分支名称或提交SHA）

**示例**：

```bash
# 使用简称创建Tag
python glctl.py tag create --repo proj1 v1.0.0 master

# 使用完整路径创建Tag
python glctl.py tag create --repo group1/project1 v1.0.0 master

# 基于映射文件中的所有仓库创建Tag
python glctl.py tag create --list v1.0.0 master

# 所有仓库创建Tag
python glctl.py tag create --all v1.0.0 master
```

### 9.2 保护Tag

**命令**：`tag protect [<single-repo-options>] <tag-pattern> [--access-level <level>]`

**单仓库选项**（三选一）：
- `--repo <repo>`：指定单个仓库标识（完整路径或简称）
- `--list`：使用映射文件中的所有仓库
- `--all`：使用所有可访问仓库

**描述**：保护Tag，设置访问级别

**参数**：
- `tag-pattern`：Tag名称模式（支持通配符，如v1.*）
- `--access-level`：访问级别，可选值：noone（无人可访问，默认）、maintainers（仅维护者可访问）、developers（开发者和维护者可访问）

**示例**：

```bash
# 保护单个仓库的Tag（默认noone）
python glctl.py tag protect --repo proj1 v1.*

# 保护Tag，设置访问级别为maintainers
python glctl.py tag protect --repo proj1 v1.* --access-level maintainers

# 保护Tag，设置访问级别为developers
python glctl.py tag protect --repo proj1 v1.* --access-level developers

# 基于映射文件中的所有仓库保护Tag（默认noone）
python glctl.py tag protect --list v1.*

# 基于映射文件中的所有仓库保护Tag级别为maintainers
python glctl.py tag protect --list v1.* --access-level maintainers

# 基于映射文件中的所有仓库保护Tag级别为developers
python glctl.py tag protect --list v1.* --access-level developers

# 所有仓库保护Tag（默认noone）
python glctl.py tag protect --all v1.*

# 所有仓库保护Tag级别为maintainers
python glctl.py tag protect --all v1.* --access-level maintainers

# 所有仓库保护Tag级别为developers
python glctl.py tag protect --all v1.* --access-level developers
```

### 9.3 取消Tag保护

**命令**：`tag unprotect [<single-repo-options>] <tag-pattern>`

**单仓库选项**（三选一）：
- `--repo <repo>`：指定单个仓库标识（完整路径或简称）
- `--list`：使用映射文件中的所有仓库
- `--all`：使用所有可访问仓库

**描述**：取消Tag保护

**参数**：
- `tag-pattern`：Tag名称模式

**示例**：

```bash
# 取消单个仓库的Tag保护
python glctl.py tag unprotect --repo proj1 v1.*

# 基于映射文件中的所有仓库取消Tag保护
python glctl.py tag unprotect --list v1.*

# 所有仓库取消Tag保护
python glctl.py tag unprotect --all v1.*
```

## 10. 合并请求管理命令

### 10.1 创建合并请求

**命令**：`merge-request create [<single-repo-options>] <source-branch> <target-branch> <title> [--assignee <assignee>] [--reviewer <reviewer>] [--assignee-id <assignee-id>] [--reviewer-id <reviewer-id>]`

**单仓库选项**（三选一）：
- `--repo <repo>`：指定单个仓库标识（完整路径或简称）
- `--list`：使用映射文件中的所有仓库
- `--all`：使用所有可访问仓库

**描述**：创建新的合并请求

**参数**：
- `source-branch`：源分支名称
- `target-branch`：目标分支名称
- `title`：合并请求标题
- `--assignee`：指派人用户名或ID
- `--reviewer`：审核人用户名或ID
- `--assignee-id`：指派人ID（跳过用户查找）
- `--reviewer-id`：审核人ID（跳过用户查找）

**示例**：

```bash
# 使用简称创建合并请求
python glctl.py merge-request create --repo proj1 feature master "Feature merge"

# 使用简称创建合并请求（指派人）
python glctl.py merge-request create --repo proj1 feature master "Feature merge" --assignee john_doe

# 使用简称创建合并请求（审核人）
python glctl.py merge-request create --repo proj1 feature master "Feature merge" --reviewer john_doe

# 使用简称创建合并请求（指派人和审核人）
python glctl.py merge-request create --repo proj1 feature master "Feature merge" --assignee john_doe --reviewer jane_doe

# 使用完整路径创建合并请求
python glctl.py merge-request create --repo group1/project1 feature master "Feature merge"

# 使用完整路径创建合并请求（指派人）
python glctl.py merge-request create --repo group1/project1 feature master "Feature merge" --assignee john_doe

# 使用完整路径创建合并请求（审核人）
python glctl.py merge-request create --repo group1/project1 feature master "Feature merge" --reviewer john_doe

# 使用完整路径创建合并请求（指派人和审核人）
python glctl.py merge-request create --repo group1/project1 feature master "Feature merge" --assignee john_doe --reviewer jane_doe

# 基于映射文件中的所有仓库创建合并请求
python glctl.py merge-request create --list feature master "Feature merge"

# 基于映射文件中的所有仓库创建合并请求（指派人）
python glctl.py merge-request create --list feature master "Feature merge" --assignee john_doe

# 基于映射文件中的所有仓库创建合并请求（审核人）
python glctl.py merge-request create --list feature master "Feature merge" --reviewer john_doe

# 基于映射文件中的所有仓库创建合并请求（指派人和审核人）
python glctl.py merge-request create --list feature master "Feature merge" --assignee john_doe --reviewer jane_doe

# 所有仓库创建合并请求
python glctl.py merge-request create --all feature master "Feature merge"

# 所有仓库创建合并请求（指派人）
python glctl.py merge-request create --all feature master "Feature merge" --assignee john_doe

# 所有仓库创建合并请求（审核人）
python glctl.py merge-request create --all feature master "Feature merge" --reviewer jane_doe

# 所有仓库创建合并请求（指派人和审核人）
python glctl.py merge-request create --all feature master "Feature merge" --assignee john_doe --reviewer jane_doe
```

### 10.2 批准合并请求

**命令**：`merge-request approve [<single-repo-options>] (<mr-iid> | <source-branch> <target-branch>)`

**单仓库选项**（三选一）：
- `--repo <repo>`：指定单个仓库标识（完整路径或简称）
- `--list`：使用映射文件中的所有仓库
- `--all`：使用所有可访问仓库

**描述**：批准合并请求 - 支持通过IID或分支信息操作

**参数**：
- `mr-iid`：合并请求IID
- `source-branch`：源分支名称（当使用分支信息操作时）
- `target-branch`：目标分支名称（当使用分支信息操作时）

**示例**：

```bash
# ========== 通过IID操作合并请求 ==========
# 通过IID批准单个仓库的合并请求
python glctl.py merge-request approve --repo proj1 1

# 基于映射文件中的所有仓库，通过IID批准合并请求
python glctl.py merge-request approve --list 1

# 所有仓库，通过IID批准合并请求
python glctl.py merge-request approve --all 1

# ========== 通过分支信息操作合并请求 ==========
# 通过分支信息批准单个仓库的合并请求
python glctl.py merge-request approve --repo proj1 feature-1.0.0 master

# 基于映射文件中的所有仓库，通过分支信息批准合并请求
python glctl.py merge-request approve --list feature-1.0.0 master

# 所有仓库，通过分支信息批准合并请求
python glctl.py merge-request approve --all feature-1.0.0 master
```

### 10.3 合并合并请求

**命令**：`merge-request merge [<single-repo-options>] (<mr-iid> | <source-branch> <target-branch>)`

**单仓库选项**（三选一）：
- `--repo <repo>`：指定单个仓库标识（完整路径或简称）
- `--list`：使用映射文件中的所有仓库
- `--all`：使用所有可访问仓库

**描述**：合并合并请求 - 支持通过IID或分支信息操作

**参数**：
- `mr-iid`：合并请求IID
- `source-branch`：源分支名称（当使用分支信息操作时）
- `target-branch`：目标分支名称（当使用分支信息操作时）

**示例**：

```bash
# ========== 通过IID操作合并请求 ==========
# 通过IID合并单个仓库的合并请求
python glctl.py merge-request merge --repo proj1 1

# 基于映射文件中的所有仓库，通过IID合并合并请求
python glctl.py merge-request merge --list 1

# 所有仓库，通过IID合并合并请求
python glctl.py merge-request merge --all 1

# ========== 通过分支信息操作合并请求 ==========
# 通过分支信息合并单个仓库的合并请求
python glctl.py merge-request merge --repo proj1 feature-1.0.0 master

# 基于映射文件中的所有仓库，通过分支信息合并合并请求
python glctl.py merge-request merge --list feature-1.0.0 master

# 所有仓库，通过分支信息合并合并请求
python glctl.py merge-request merge --all feature-1.0.0 master
```

### 10.4 关闭合并请求

**命令**：`merge-request close [<single-repo-options>] (<mr-iid> | <source-branch> <target-branch>)`

**单仓库选项**（三选一）：
- `--repo <repo>`：指定单个仓库标识（完整路径或简称）
- `--list`：使用映射文件中的所有仓库
- `--all`：使用所有可访问仓库

**描述**：关闭合并请求 - 支持通过IID或分支信息操作

**参数**：
- `mr-iid`：合并请求IID
- `source-branch`：源分支名称（当使用分支信息操作时）
- `target-branch`：目标分支名称（当使用分支信息操作时）

**示例**：

```bash
# ========== 通过IID操作合并请求 ==========
# 通过IID关闭单个仓库的合并请求
python glctl.py merge-request close --repo proj1 1

# 基于映射文件中的所有仓库，通过IID关闭合并请求
python glctl.py merge-request close --list 1

# 所有仓库，通过IID关闭合并请求
python glctl.py merge-request close --all 1

# ========== 通过分支信息操作合并请求 ==========
# 通过分支信息关闭单个仓库的合并请求
python glctl.py merge-request close --repo proj1 feature-1.0.0 master

# 基于映射文件中的所有仓库，通过分支信息关闭合并请求
python glctl.py merge-request close --list feature-1.0.0 master

# 所有仓库，通过分支信息关闭合并请求
python glctl.py merge-request close --all feature-1.0.0 master
```

### 10.5 批准并合并合并请求

**命令**：`merge-request approve-and-merge [<single-repo-options>] (<mr-iid> | <source-branch> <target-branch>)`

**单仓库选项**（三选一）：
- `--repo <repo>`：指定单个仓库标识（完整路径或简称）
- `--list`：使用映射文件中的所有仓库
- `--all`：使用所有可访问仓库

**描述**：批准并合并合并请求 - 支持通过IID或分支信息操作

**参数**：
- `mr-iid`：合并请求IID
- `source-branch`：源分支名称（当使用分支信息操作时）
- `target-branch`：目标分支名称（当使用分支信息操作时）

**示例**：

```bash
# ========== 通过IID操作合并请求 ==========
# 通过IID批准并合并单个仓库的合并请求
python glctl.py merge-request approve-and-merge --repo proj1 1

# 基于映射文件中的所有仓库，通过IID批准并合并合并请求
python glctl.py merge-request approve-and-merge --list 1

# 所有仓库，通过IID批准并合并合并请求
python glctl.py merge-request approve-and-merge --all 1

# ========== 通过分支信息操作合并请求 ==========
# 通过分支信息批准并合并单个仓库的合并请求
python glctl.py merge-request approve-and-merge --repo proj1 feature-1.0.0 master

# 基于映射文件中的所有仓库，通过分支信息批准并合并合并请求
python glctl.py merge-request approve-and-merge --list feature-1.0.0 master

# 所有仓库，通过分支信息批准并合并合并请求
python glctl.py merge-request approve-and-merge --all feature-1.0.0 master
```

## 11. 映射文件格式

映射文件（默认：repo-mapping.txt）采用以下格式：

```
# Full Path       Short Name
group1/project1  proj1
group2/project2  proj2
broker/backend-v2/test  backend-test
```

**格式说明**：
- 每行一个映射对，格式为`完整路径 简称`
- 支持注释行（以`#`开头）
- 支持空行（自动忽略）
- 简称唯一约束：不允许重复简称
- 完整路径唯一约束：不允许重复完整路径

## 12. 访问级别映射

| 访问级别字符串 | GitLab API数值 | 描述 |
|---------------|----------------|------|
| noone         | 0              | 无人可访问 |
| maintainers   | 40             | 仅维护者可访问 |
| developers    | 30             | 开发者和维护者可访问 |

## 13. 示例工作流

### 13.1 基础工作流

```bash
# 1. 修改脚本中的默认配置
# DEFAULT_GITLAB_URL = "https://your-gitlab.com"
# DEFAULT_GITLAB_TOKEN = "your-actual-token"

# 2. 查看映射列表
python glctl.py mapping list

# 3. 添加新映射
python glctl.py mapping add group1/project1 proj1
python glctl.py mapping add group2/project2 proj2

# 4. 创建分支
python glctl.py branch create --repo proj1 feature master
python glctl.py branch create --repo proj2 feature master

# 5. 保护分支
python glctl.py branch protect --repo proj1 master
python glctl.py branch protect --repo proj2 master

# 6. 创建合并请求
python glctl.py merge-request create --repo proj1 feature master "Feature merge"
python glctl.py merge-request create --repo proj2 feature master "Feature merge"

# 7. 批准合并请求 - 通过IID
python glctl.py merge-request approve --repo proj1 1
python glctl.py merge-request approve --repo proj2 1

# 或者通过分支信息
python glctl.py merge-request approve --repo proj1 feature master
python glctl.py merge-request approve --repo proj2 feature master

# 8. 合并合并请求 - 通过IID
python glctl.py merge-request merge --repo proj1 1
python glctl.py merge-request merge --repo proj2 1

# 或者通过分支信息
python glctl.py merge-request merge --repo proj1 feature master
python glctl.py merge-request merge --repo proj2 feature master

# 9. 创建Tag
python glctl.py tag create --repo proj1 v1.0.0 master
python glctl.py tag create --repo proj2 v1.0.0 master

# 10. 保护Tag
python glctl.py tag protect --repo proj1 v1.*
python glctl.py tag protect --repo proj2 v1.*
```

### 13.2 批量操作工作流（基于映射文件）

```bash
# 1. 基于映射文件中的所有仓库创建分支
python glctl.py branch create --list feature master

# 2. 基于映射文件中的所有仓库创建Tag
python glctl.py tag create --list v1.0.0 master

# 3. 基于映射文件中的所有仓库保护分支
python glctl.py branch protect --list master

# 4. 基于映射文件中的所有仓库保护Tag
python glctl.py tag protect --list v1.*

# 5. 基于映射文件中的所有仓库创建合并请求
python glctl.py merge-request create --list feature master "Feature merge"

# 6. 基于映射文件中的所有仓库，通过分支信息批准合并请求
python glctl.py merge-request approve --list feature master

# 7. 基于映射文件中的所有仓库，通过分支信息合并合并请求
python glctl.py merge-request merge --list feature master
```

### 13.3 批量操作工作流

```bash
# 1. 所有仓库创建分支
python glctl.py branch create --all feature master

# 2. 所有仓库创建Tag
python glctl.py tag create --all v1.0.0 master

# 3. 所有仓库保护分支
python glctl.py branch protect --all master

# 4. 所有仓库保护Tag
python glctl.py tag protect --all v1.*

# 5. 所有仓库创建合并请求
python glctl.py merge-request create --all feature master "Feature merge"

# 6. 所有仓库，通过分支信息批准合并请求
python glctl.py merge-request approve --all feature master

# 7. 所有仓库，通过分支信息合并合并请求
python glctl.py merge-request merge --all feature master
```

## 14. 日志级别

| 日志级别 | 描述 |
|----------|------|
| INFO     | 默认级别，显示操作过程和结果 |
| DEBUG    | 详细级别，显示更多调试信息，使用`--verbose`选项启用 |

## 15. 错误处理

脚本包含完善的错误处理机制，常见错误场景包括：

- **重复简称**：尝试添加重复简称时，会显示错误信息并退出
- **重复完整路径**：尝试添加重复完整路径时，会显示错误信息并退出
- **仓库不存在**：指定的仓库不存在时，会显示错误信息并退出
- **分支不存在**：尝试操作不存在的分支时，会显示错误信息
- **Tag不存在**：尝试操作不存在的Tag时，会显示错误信息
- **合并请求不存在**：尝试操作不存在的合并请求时，会显示错误信息

## 16. 命令帮助

### 16.1 获取全局帮助

```bash
python glctl.py --help
```

### 16.2 获取子命令帮助

```bash
# 获取mapping子命令帮助
python glctl.py mapping --help

# 获取branch子命令帮助
python glctl.py branch --help

# 获取tag子命令帮助
python glctl.py tag --help

# 获取merge-request子命令帮助
python glctl.py merge-request --help
```

### 16.3 获取子命令的子命令帮助

```bash
# 获取branch create命令帮助
python glctl.py branch create --help

# 获取tag protect命令帮助
python glctl.py tag protect --help

# 获取merge-request create命令帮助
python glctl.py merge-request create --help
```

## 17. 维护与更新

### 17.1 更新脚本

```bash
# 备份现有脚本
cp glctl.py glctl.py.backup

# 下载更新后的脚本
# wget https://example.com/glctl.py

# 恢复默认配置
# 编辑glctl.py，修改默认配置
```

### 17.2 备份映射文件

```bash
cp repo-mapping.txt repo-mapping.txt.backup
```

### 17.3 恢复映射文件

```bash
cp repo-mapping.txt.backup repo-mapping.txt
```

## 18. 注意事项

1. **安全性**：请确保脚本文件的访问权限设置正确，避免Token泄露
2. **编码问题**：映射文件使用UTF-8编码，建议使用支持UTF-8的编辑器查看和编辑
3. **权限要求**：确保您的GitLab Token具有足够的权限执行相应操作
4. **分支名称**：分支名称应符合GitLab的命名规则
5. **Tag名称**：Tag名称应符合GitLab的命名规则
6. **批量操作**：批量操作时请谨慎，确保操作的正确性
7. **日志记录**：建议保留日志记录，以便排查问题

## 19. 支持的GitLab版本

脚本使用python-gitlab库，支持GitLab 11.0及以上版本。具体支持版本请参考python-gitlab库的文档。

## 20. 故障排除

### 20.1 连接问题

- 检查GitLab URL是否正确
- 检查GitLab Token是否有效
- 检查网络连接是否正常
- 检查GitLab服务器是否可达

### 20.2 权限问题

- 检查GitLab Token是否具有足够的权限
- 检查仓库是否存在
- 检查您是否有权访问该仓库

### 20.3 映射文件问题

- 检查映射文件格式是否正确
- 检查是否有重复简称或重复完整路径
- 检查映射文件编码是否正确

### 20.4 其他问题

- 使用`--verbose`选项获取详细日志
- 检查GitLab服务器日志
- 检查python-gitlab库版本是否兼容
