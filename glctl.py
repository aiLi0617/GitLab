#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GitLab控制脚本（glctl.py）
用于管理GitLab仓库的命令行工具，支持分支管理、Tag管理、保护规则管理和合并请求管理等功能
"""

import argparse
import logging
import os
import re
import sys
from typing import Dict, List, Optional, Set, Tuple, Union

import gitlab

# 默认配置 - 可以直接在脚本中修改
DEFAULT_GITLAB_URL = "http://139.159.207.40:29080/"  # GitLab服务器URL
DEFAULT_GITLAB_TOKEN = "xxxxx"  # GitLab访问令牌
DEFAULT_MAPPING_FILE = "repo-mapping.txt"  # 映射文件路径

# 访问级别映射
ACCESS_LEVEL_MAP = {
    "noone": 0,
    "maintainers": 40,
    "developers": 30
}

# 设置日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class GitLabController:
    """GitLab控制器类，处理所有GitLab相关操作"""
    
    def __init__(self, gitlab_url: str, gitlab_token: str):
        """初始化GitLab控制器"""
        self.gitlab_url = gitlab_url
        self.gitlab_token = gitlab_token
        self.gl = None
        self._connect()
    
    def _connect(self):
        """连接到GitLab服务器"""
        try:
            self.gl = gitlab.Gitlab(self.gitlab_url, private_token=self.gitlab_token, keep_base_url=True)
            self.gl.auth()
            logger.info(f"成功连接到GitLab服务器: {self.gitlab_url}")
        except gitlab.exceptions.GitlabConnectionError as e:
            logger.error(f"连接GitLab服务器失败: {e}")
            logger.error("请检查GitLab URL是否正确，网络连接是否正常")
            sys.exit(1)
        except gitlab.exceptions.GitlabAuthenticationError as e:
            logger.error(f"GitLab认证失败: {e}")
            logger.error("请检查GitLab Token是否有效")
            sys.exit(1)
    
    def get_project(self, project_path: str):
        """获取GitLab项目"""
        try:
            project = self.gl.projects.get(project_path)
            return project
        except gitlab.exceptions.GitlabGetError as e:
            logger.error(f"获取项目失败: {e}")
            logger.error(f"请检查项目路径是否正确: {project_path}")
            return None
    
    def get_all_projects(self):
        """获取所有可访问的GitLab项目"""
        try:
            projects = self.gl.projects.list(all=True)
            return projects
        except Exception as e:
            logger.error(f"获取所有项目失败: {e}")
            return []


class RepoMappingManager:
    """仓库简称映射管理器"""
    
    def __init__(self, mapping_file: str):
        """初始化映射管理器"""
        self.mapping_file = mapping_file
        self._load_mappings()
    
    def _load_mappings(self):
        """从文件加载映射关系"""
        self.full_to_short: Dict[str, str] = {}
        self.short_to_full: Dict[str, str] = {}
        
        if not os.path.exists(self.mapping_file):
            logger.info(f"映射文件不存在，将创建新文件: {self.mapping_file}")
            # 创建空的映射文件
            self._save_mappings()
            return
        
        try:
            with open(self.mapping_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    # 跳过注释行和空行
                    if not line or line.startswith('#'):
                        continue
                    
                    # 解析行，支持多个空格分隔
                    parts = re.split(r'\s+', line)
                    if len(parts) != 2:
                        logger.warning(f"映射文件第{line_num}行格式错误: {line}")
                        continue
                    
                    full_path, short_name = parts
                    
                    # 检查重复
                    if full_path in self.full_to_short:
                        logger.warning(f"映射文件第{line_num}行: 重复的完整路径 {full_path}")
                        continue
                    if short_name in self.short_to_full:
                        logger.warning(f"映射文件第{line_num}行: 重复的简称 {short_name}")
                        continue
                    
                    self.full_to_short[full_path] = short_name
                    self.short_to_full[short_name] = full_path
            
            logger.info(f"成功加载 {len(self.full_to_short)} 个映射关系")
        except Exception as e:
            logger.error(f"加载映射文件失败: {e}")
            sys.exit(1)
    
    def _save_mappings(self):
        """保存映射关系到文件"""
        try:
            # 使用明确的文本模式和编码
            with open(self.mapping_file, 'wt', encoding='utf-8', newline='') as f:
                header = "# Full Path       Short Name\n"
                f.write(header)
                logger.debug(f"写入文件头: {repr(header)}")
                
                for full_path, short_name in self.full_to_short.items():
                    line = f"{full_path} {short_name}\n"
                    f.write(line)
                    logger.debug(f"写入映射行: {repr(line)}")
            
            logger.info(f"成功保存映射关系到文件: {self.mapping_file}")
            
            # 验证文件内容
            with open(self.mapping_file, 'rt', encoding='utf-8') as f:
                content = f.read()
                logger.debug(f"文件内容: {repr(content[:100])}...")
                
        except Exception as e:
            logger.error(f"保存映射文件失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            sys.exit(1)
    
    def add_mapping(self, full_path: str, short_name: str):
        """添加映射关系"""
        # 检查重复
        if full_path in self.full_to_short:
            logger.error(f"完整路径已存在: {full_path}")
            logger.error(f"当前简称: {self.full_to_short[full_path]}")
            return False
        if short_name in self.short_to_full:
            logger.error(f"简称已存在: {short_name}")
            logger.error(f"当前完整路径: {self.short_to_full[short_name]}")
            return False
        
        self.full_to_short[full_path] = short_name
        self.short_to_full[short_name] = full_path
        self._save_mappings()
        logger.info(f"成功添加映射: {full_path} -> {short_name}")
        return True
    
    def update_mapping(self, repo_identifier: str, new_short_name: str):
        """更新映射关系"""
        # 查找现有映射
        full_path = None
        old_short_name = None
        
        if repo_identifier in self.full_to_short:
            full_path = repo_identifier
            old_short_name = self.full_to_short[repo_identifier]
        elif repo_identifier in self.short_to_full:
            old_short_name = repo_identifier
            full_path = self.short_to_full[repo_identifier]
        else:
            logger.error(f"仓库标识不存在: {repo_identifier}")
            return False
        
        # 检查新简称是否已存在
        if new_short_name in self.short_to_full:
            logger.error(f"新简称已存在: {new_short_name}")
            logger.error(f"当前完整路径: {self.short_to_full[new_short_name]}")
            return False
        
        # 更新映射
        del self.full_to_short[full_path]
        del self.short_to_full[old_short_name]
        
        self.full_to_short[full_path] = new_short_name
        self.short_to_full[new_short_name] = full_path
        
        self._save_mappings()
        logger.info(f"成功更新映射: {full_path} -> {old_short_name} -> {new_short_name}")
        return True
    
    def remove_mapping(self, repo_identifier: str):
        """删除映射关系"""
        # 查找现有映射
        full_path = None
        short_name = None
        
        if repo_identifier in self.full_to_short:
            full_path = repo_identifier
            short_name = self.full_to_short[repo_identifier]
        elif repo_identifier in self.short_to_full:
            short_name = repo_identifier
            full_path = self.short_to_full[repo_identifier]
        else:
            logger.error(f"仓库标识不存在: {repo_identifier}")
            return False
        
        # 删除映射
        del self.full_to_short[full_path]
        del self.short_to_full[short_name]
        
        self._save_mappings()
        logger.info(f"成功删除映射: {full_path} -> {short_name}")
        return True
    
    def clear_mappings(self):
        """清空所有映射关系"""
        self.full_to_short.clear()
        self.short_to_full.clear()
        self._save_mappings()
        logger.info("成功清空所有映射关系")
        return True
    
    def get_full_path(self, repo_identifier: str) -> Optional[str]:
        """根据仓库标识获取完整路径"""
        if repo_identifier in self.short_to_full:
            return self.short_to_full[repo_identifier]
        return repo_identifier
    
    def list_mappings(self):
        """列出所有映射关系"""
        if not self.full_to_short:
            logger.info("当前没有映射关系")
            return
        
        logger.info("\n当前映射关系：")
        logger.info("-" * 50)
        logger.info(f"{'完整路径':<40} {'简称':<20}")
        logger.info("-" * 50)
        for full_path, short_name in sorted(self.full_to_short.items()):
            logger.info(f"{full_path:<40} {short_name:<20}")
        logger.info("-" * 50)
    
    def sync_mappings(self, gl_controller: GitLabController):
        """从GitLab同步仓库并生成映射"""
        logger.info("开始从GitLab同步仓库...")
        projects = gl_controller.get_all_projects()
        
        if not projects:
            logger.error("获取GitLab项目失败")
            return False
        
        new_mappings = 0
        for project in projects:
            full_path = project.path_with_namespace
            # 自动生成简称：使用项目名，如果有连字符则转换为驼峰命名
            short_name = project.name.replace('-', ' ').title().replace(' ', '')
            
            # 如果简称已存在，添加数字后缀
            original_short_name = short_name
            counter = 1
            while short_name in self.short_to_full or short_name in [p.name for p in projects]:
                short_name = f"{original_short_name}{counter}"
                counter += 1
            
            # 检查是否已存在映射
            if full_path not in self.full_to_short:
                self.full_to_short[full_path] = short_name
                self.short_to_full[short_name] = full_path
                new_mappings += 1
                logger.info(f"添加映射: {full_path} -> {short_name}")
        
        if new_mappings > 0:
            self._save_mappings()
            logger.info(f"成功同步 {new_mappings} 个新映射")
        else:
            logger.info("没有新的映射需要同步")
        
        return True
    
    def check_mappings(self, gl_controller: GitLabController):
        """检查映射关系完整性"""
        logger.info("开始检查映射关系完整性...")
        valid_count = 0
        invalid_count = 0
        
        for full_path, short_name in self.full_to_short.items():
            project = gl_controller.get_project(full_path)
            if project:
                logger.info(f"✓ 有效映射: {full_path} -> {short_name}")
                valid_count += 1
            else:
                logger.error(f"✗ 无效映射: {full_path} -> {short_name} (仓库不存在)")
                invalid_count += 1
        
        logger.info("\n检查结果：")
        logger.info(f"- 有效映射: {valid_count}")
        logger.info(f"- 无效映射: {invalid_count}")
        logger.info(f"- 总映射数: {valid_count + invalid_count}")
        
        return invalid_count == 0
    
    def get_all_full_paths(self):
        """获取所有完整路径"""
        return list(self.full_to_short.keys())


class BranchManager:
    """分支管理器"""
    
    @staticmethod
    def create_branch(project, branch_name: str, base_branch: str) -> bool:
        """创建分支"""
        try:
            project.branches.create({
                'branch': branch_name,
                'ref': base_branch
            })
            logger.info(f"成功创建分支: {branch_name} (基于 {base_branch})")
            return True
        except gitlab.exceptions.GitlabCreateError as e:
            if "already exists" in str(e).lower():
                logger.warning(f"分支已存在: {branch_name}")
                return True
            logger.error(f"创建分支失败: {e}")
            return False
    
    @staticmethod
    def protect_branch(project, branch_name: str, access_level: int) -> bool:
        """保护分支"""
        try:
            project.protectedbranches.create({
                'name': branch_name,
                'push_access_level': access_level,
                'merge_access_level': access_level
            })
            logger.info(f"成功保护分支: {branch_name} (访问级别: {access_level})")
            return True
        except gitlab.exceptions.GitlabCreateError as e:
            if "already exists" in str(e).lower():
                # 更新现有保护规则
                try:
                    protected_branches = project.protectedbranches.list()
                    for pb in protected_branches:
                        if pb.name == branch_name:
                            pb.push_access_level = access_level
                            pb.merge_access_level = access_level
                            pb.save()
                            logger.info(f"成功更新分支保护: {branch_name} (访问级别: {access_level})")
                            return True
                except Exception as update_e:
                    logger.error(f"更新分支保护失败: {update_e}")
                    return False
            logger.error(f"保护分支失败: {e}")
            return False
    
    @staticmethod
    def unprotect_branch(project, branch_name: str) -> bool:
        """取消分支保护"""
        try:
            protected_branches = project.protectedbranches.list()
            for pb in protected_branches:
                if pb.name == branch_name:
                    pb.delete()
                    logger.info(f"成功取消分支保护: {branch_name}")
                    return True
            logger.warning(f"分支未被保护: {branch_name}")
            return True
        except Exception as e:
            logger.error(f"取消分支保护失败: {e}")
            return False


class TagManager:
    """Tag管理器"""
    
    @staticmethod
    def create_tag(project, tag_name: str, ref: str) -> bool:
        """创建Tag"""
        try:
            project.tags.create({
                'tag_name': tag_name,
                'ref': ref
            })
            logger.info(f"成功创建Tag: {tag_name} (基于 {ref})")
            return True
        except gitlab.exceptions.GitlabCreateError as e:
            if "already exists" in str(e).lower():
                logger.warning(f"Tag已存在: {tag_name}")
                return True
            logger.error(f"创建Tag失败: {e}")
            return False
    
    @staticmethod
    def protect_tag(project, tag_pattern: str, access_level: int) -> bool:
        """保护Tag"""
        try:
            project.protectedtags.create({
                'name': tag_pattern,
                'create_access_level': access_level
            })
            logger.info(f"成功保护Tag: {tag_pattern} (访问级别: {access_level})")
            return True
        except gitlab.exceptions.GitlabCreateError as e:
            if "already exists" in str(e).lower():
                # 更新现有保护规则
                try:
                    protected_tags = project.protectedtags.list()
                    for pt in protected_tags:
                        if pt.name == tag_pattern:
                            pt.create_access_level = access_level
                            pt.save()
                            logger.info(f"成功更新Tag保护: {tag_pattern} (访问级别: {access_level})")
                            return True
                except Exception as update_e:
                    logger.error(f"更新Tag保护失败: {update_e}")
                    return False
            logger.error(f"保护Tag失败: {e}")
            return False
    
    @staticmethod
    def unprotect_tag(project, tag_pattern: str) -> bool:
        """取消Tag保护"""
        try:
            protected_tags = project.protectedtags.list()
            for pt in protected_tags:
                if pt.name == tag_pattern:
                    pt.delete()
                    logger.info(f"成功取消Tag保护: {tag_pattern}")
                    return True
            logger.warning(f"Tag未被保护: {tag_pattern}")
            return True
        except Exception as e:
            logger.error(f"取消Tag保护失败: {e}")
            return False


class MergeRequestManager:
    """合并请求管理器"""
    
    @staticmethod
    def create_merge_request(project, source_branch: str, target_branch: str, title: str, 
                           assignee: Optional[str] = None, reviewer: Optional[str] = None, 
                           assignee_id: Optional[str] = None, reviewer_id: Optional[str] = None) -> bool:
        """创建合并请求"""
        try:
            # 1. 检查分支间是否有差异
            logger.info(f"检查分支差异: {source_branch} -> {target_branch}")

            # 使用兼容不同python-gitlab版本的方式进行分支比较
            if hasattr(project, 'compare'):
                # 新版本使用compare方法
                compare_result = project.compare(from_branch=source_branch, to_branch=target_branch)
            else:
                # 旧版本使用repository_compare方法
                compare_result = project.repository_compare(source_branch, target_branch)

            # 检查是否有实际差异

            # 1. 首先检查compare_same_ref字段 - 这是GitLab API判断分支是否相同的直接标志
            if compare_result.get('compare_same_ref', False):
                logger.info(f"分支指向相同的提交，跳过创建合并请求: {source_branch} -> {target_branch}")
                return True

            # 2. 检查是否有实际差异 - 使用get()方法处理可能缺失的键
            stats = compare_result.get('stats', {})
            additions = stats.get('additions', 0)
            deletions = stats.get('deletions', 0)
            diffs = compare_result.get('diffs', [])

            # 3. 检查双向差异 - 关键修复：如果反向比较没有差异，说明目标分支已经包含源分支的所有更改
            try:
                if hasattr(project, 'compare'):
                    reverse_compare = project.compare(from_branch=target_branch, to_branch=source_branch)
                else:
                    reverse_compare = project.repository_compare(target_branch, source_branch)

                # 检查反向比较是否有差异
                reverse_stats = reverse_compare.get('stats', {})
                reverse_additions = reverse_stats.get('additions', 0)
                reverse_deletions = reverse_stats.get('deletions', 0)
                reverse_diffs = reverse_compare.get('diffs', [])

                # 如果反向比较没有差异，说明目标分支已经包含源分支的所有更改
                # 这就是UI显示"合并请求不包含任何更改"的情况
                if reverse_additions == 0 and reverse_deletions == 0 and len(reverse_diffs) == 0:
                    logger.info(f"目标分支已包含源分支的所有更改，跳过创建合并请求: {source_branch} -> {target_branch}")
                    logger.debug(f"正向比较: {len(diffs)} 个差异，反向比较: {len(reverse_diffs)} 个差异")
                    return True
            except Exception as e:
                logger.warning(f"反向比较失败: {e}，继续使用正向比较结果")

            # 4. 只有当有实际的文件差异（additions/deletions > 0 或 diffs列表非空）时，才认为有需要合并的差异
            has_actual_changes = additions > 0 or deletions > 0 or len(diffs) > 0

            if not has_actual_changes:
                logger.info(f"分支间无实际差异，跳过创建合并请求: {source_branch} -> {target_branch}")
                return True

            # 分支有差异，继续创建合并请求
            logger.info(f"分支间存在差异，准备创建合并请求: {source_branch} -> {target_branch}")
            logger.debug(f"差异统计: {additions} 新增, {deletions} 删除")

            mr_data = {
                'source_branch': source_branch,
                'target_branch': target_branch,
                'title': title
            }
            
            # 已知用户ID映射（从测试脚本中获取）
            KNOWN_USER_IDS = {
                # 'renguoqiang': 37  # 从测试中获取的ID
            }
            
            logger.info(f"创建合并请求: {source_branch} -> {target_branch} (标题: {title})")
            
            def find_user_by_identifier(identifier: str) -> Optional[object]:
                """查找用户，返回用户对象或None"""
                logger.info(f"查找用户: {identifier}")
                
                # 获取GitLab实例
                gl_instance = project.manager.gitlab
                
                # 1. 检查是否为已知用户
                if identifier.lower() in KNOWN_USER_IDS:
                    user_id = KNOWN_USER_IDS[identifier.lower()]
                    try:
                        user = gl_instance.users.get(user_id)
                        logger.info(f"✓ 已知用户 {identifier}，找到用户: {user.username} (ID: {user.id})")
                        return user
                    except Exception as e:
                        logger.warning(f"✗ 已知用户ID获取失败: {e}")
                
                # 2. 尝试作为数字ID处理
                try:
                    user_id = int(identifier)
                    logger.info(f"✓ 尝试将 {identifier} 作为用户ID处理")
                    user = gl_instance.users.get(user_id)
                    logger.info(f"✓ 通过ID找到用户: {user.username} (ID: {user.id})")
                    return user
                except (ValueError, Exception) as e:
                    logger.debug(f"✗ 将 {identifier} 作为ID处理失败: {e}")
                
                # 3. 尝试获取当前用户（如果是查找自己）
                try:
                    current_user = gl_instance.user
                    logger.info(f"✓ 当前登录用户: {current_user.username} (ID: {current_user.id})")
                    if current_user.username == identifier or current_user.name == identifier:
                        logger.info(f"✓ 找到当前用户匹配: {identifier}")
                        # 添加到已知用户映射
                        KNOWN_USER_IDS[identifier.lower()] = current_user.id
                        return current_user
                except Exception as e:
                    logger.debug(f"✗ 获取当前用户失败: {e}")
                
                # 4. 尝试使用username参数直接过滤（测试验证有效）
                try:
                    users = gl_instance.users.list(username=identifier, per_page=5)
                    logger.info(f"✓ 使用username参数找到 {len(users)} 个用户")
                    for user in users:
                        logger.debug(f"  - {user.username} (ID: {user.id}, 名称: {user.name})")
                        if user.username == identifier:
                            logger.info(f"✓ 通过username参数找到用户: {user.username} (ID: {user.id})")
                            # 添加到已知用户映射
                            KNOWN_USER_IDS[identifier.lower()] = user.id
                            return user
                except Exception as e:
                    logger.debug(f"✗ 使用username参数查找失败: {e}")
                
                # 5. 尝试使用search参数查找用户（测试验证有效）
                try:
                    users = gl_instance.users.list(search=identifier, per_page=10)
                    logger.info(f"✓ 使用search参数找到 {len(users)} 个用户")
                    for user in users:
                        logger.debug(f"  - {user.username} (ID: {user.id}, 名称: {user.name})")
                        if user.username == identifier:
                            logger.info(f"✓ 通过search参数找到用户: {user.username} (ID: {user.id})")
                            # 添加到已知用户映射
                            KNOWN_USER_IDS[identifier.lower()] = user.id
                            return user
                    # 如果精确匹配失败，尝试模糊匹配
                    for user in users:
                        if identifier in user.username or identifier in user.name:
                            logger.info(f"✓ 通过search参数模糊匹配找到用户: {user.username} (ID: {user.id})")
                            # 添加到已知用户映射
                            KNOWN_USER_IDS[identifier.lower()] = user.id
                            return user
                except Exception as e:
                    logger.debug(f"✗ 使用search参数查找失败: {e}")
                
                logger.warning(f"✗ 未找到用户: {identifier}")
                return None
            
            # 处理指派人
            assigned = False
            if assignee_id:
                # 直接使用提供的ID
                try:
                    mr_data['assignee_id'] = int(assignee_id)
                    logger.info(f"直接使用指派人ID: {assignee_id}")
                    assigned = True
                except ValueError:
                    logger.warning(f"无效的指派人ID: {assignee_id}")
            elif assignee:
                # 通过标识符查找用户
                try:
                    user = find_user_by_identifier(assignee)
                    if user:
                        mr_data['assignee_id'] = user.id
                        logger.info(f"找到指派人 {assignee}，ID: {user.id}")
                        assigned = True
                    else:
                        logger.warning(f"未找到指派人: {assignee}")
                except Exception as e:
                    logger.warning(f"获取指派人失败: {e}")
            
            if assigned:
                logger.info(f"将合并请求指派给: {assignee or assignee_id}")
            
            # 处理审核人 - 在创建合并请求时直接指定reviewer_ids参数
            reviewers = []
            if reviewer_id:
                # 直接使用提供的ID
                try:
                    reviewers.append(int(reviewer_id))
                    logger.info(f"直接使用审核人ID: {reviewer_id}")
                except ValueError:
                    logger.warning(f"无效的审核人ID: {reviewer_id}")
            elif reviewer:
                # 通过标识符查找用户
                try:
                    user = find_user_by_identifier(reviewer)
                    if user:
                        reviewers.append(user.id)
                        logger.info(f"找到审核人 {reviewer}，ID: {user.id}")
                    else:
                        logger.warning(f"未找到审核人: {reviewer}")
                except Exception as e:
                    logger.warning(f"获取审核人失败: {e}")
            
            # 如果有审核人，添加到mr_data
            if reviewers:
                mr_data['reviewer_ids'] = reviewers
                logger.info(f"为合并请求添加审核人: {reviewer or reviewer_id}")
            
            # 创建合并请求
            mr = project.mergerequests.create(mr_data)
            
            logger.info(f"成功创建合并请求: {source_branch} -> {target_branch} (标题: {title})")
            return True
        except gitlab.exceptions.GitlabCreateError as e:
            if "already exists" in str(e).lower():
                logger.warning(f"合并请求已存在: {source_branch} -> {target_branch}")
                return True
            logger.error(f"创建合并请求失败: {e}")
            return False
    
    @staticmethod
    def find_merge_request_by_branches(project, source_branch: str, target_branch: str):
        """通过分支查找合并请求"""
        try:
            mrs = project.mergerequests.list(state='opened', all=True)
            for mr in mrs:
                if mr.source_branch == source_branch and mr.target_branch == target_branch:
                    # 使用get()方法获取完整的合并请求对象，确保所有属性都可用
                    # 注意：这里使用的是iid，而不是id
                    full_mr = project.mergerequests.get(mr.iid)
                    return full_mr
            return None
        except Exception as e:
            logger.error(f"查找合并请求失败: {e}")
            return None
    
    @staticmethod
    def approve_merge_request(project, mr) -> bool:
        """批准合并请求"""
        try:
            # 在调用API方法前保存需要的属性
            mr_iid = mr.iid
            mr_title = mr.title
            
            mr.approve()
            logger.info(f"成功批准合并请求: #{mr_iid} - {mr_title}")
            return True
        except gitlab.exceptions.GitlabCreateError as e:
            # 在异常处理中也先保存属性
            if hasattr(mr, 'iid') and hasattr(mr, 'title'):
                mr_iid = mr.iid
                logger.warning(f"合并请求已批准: #{mr_iid}")
            else:
                logger.warning(f"合并请求已批准")
            return True
        except Exception as e:
            logger.error(f"批准合并请求失败: {e}")
            return False
    
    @staticmethod
    def merge_merge_request(project, mr) -> bool:
        """合并合并请求"""
        try:
            # 在调用API方法前保存需要的属性
            mr_iid = mr.iid
            mr_title = mr.title
            
            mr.merge()
            logger.info(f"成功合并合并请求: #{mr_iid} - {mr_title}")
            return True
        except gitlab.exceptions.GitlabCreateError as e:
            # 在异常处理中也先保存属性
            if hasattr(mr, 'iid') and hasattr(mr, 'title'):
                mr_iid = mr.iid
                logger.warning(f"合并请求已合并: #{mr_iid}")
            else:
                logger.warning(f"合并请求已合并")
            return True
        except Exception as e:
            logger.error(f"合并合并请求失败: {e}")
            return False
    
    @staticmethod
    def close_merge_request(project, mr) -> bool:
        """关闭合并请求"""
        try:
            # 在调用API方法前保存需要的属性
            mr_iid = mr.iid
            mr_title = mr.title
            
            mr.state_event = 'close'
            mr.save()
            logger.info(f"成功关闭合并请求: #{mr_iid} - {mr_title}")
            return True
        except Exception as e:
            logger.error(f"关闭合并请求失败: {e}")
            return False
    
    @staticmethod
    def get_merge_request(project, mr_iid: int):
        """通过IID获取合并请求"""
        try:
            return project.mergerequests.get(mr_iid)
        except gitlab.exceptions.GitlabGetError as e:
            logger.error(f"获取合并请求失败: {e}")
            return None


def get_target_projects(
    gl_controller: GitLabController,
    mapping_manager: RepoMappingManager,
    repo: Optional[str] = None,
    use_list: bool = False,
    use_all: bool = False
) -> List[str]:
    """获取目标项目列表"""
    target_projects = []
    
    if use_all:
        # 使用所有可访问仓库
        projects = gl_controller.get_all_projects()
        target_projects = [project.path_with_namespace for project in projects]
    elif use_list:
        # 使用映射文件中的所有仓库
        target_projects = mapping_manager.get_all_full_paths()
    elif repo:
        # 使用指定仓库
        full_path = mapping_manager.get_full_path(repo)
        target_projects = [full_path]
    else:
        logger.error("请指定仓库，或使用 --list 或 --all 选项")
        return []
    
    return target_projects


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='GitLab控制脚本 - 用于管理GitLab仓库的命令行工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 映射管理
  python glctl.py mapping list
  python glctl.py mapping add group1/project1 proj1
  
  # 分支管理
  python glctl.py branch create --repo proj1 feature main
  python glctl.py branch protect --list master
  
  # Tag管理
  python glctl.py tag create --all v1.0.0 master
  python glctl.py tag protect --repo proj1 v1.*
  
  # 合并请求管理
  python glctl.py merge-request create --repo proj1 feature main "Feature merge"
  python glctl.py merge-request approve --repo proj1 1
        """
    )
    
    # 全局选项
    parser.add_argument('--url', default=DEFAULT_GITLAB_URL, help='GitLab服务器URL')
    parser.add_argument('--token', default=DEFAULT_GITLAB_TOKEN, help='GitLab访问令牌')
    parser.add_argument('--mapping-file', default=DEFAULT_MAPPING_FILE, help='简称映射文件路径')
    parser.add_argument('--verbose', action='store_true', help='详细日志输出')
    
    # 子命令
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # ========== 映射管理命令 ==========
    mapping_parser = subparsers.add_parser('mapping', help='仓库简称映射管理')
    mapping_subparsers = mapping_parser.add_subparsers(dest='mapping_command', help='映射管理子命令')
    
    # mapping list
    mapping_subparsers.add_parser('list', help='查看映射列表')
    
    # mapping add
    mapping_add_parser = mapping_subparsers.add_parser('add', help='添加映射')
    mapping_add_parser.add_argument('pairs', nargs='+', help='完整路径和简称对，格式: full_path short_name [full_path short_name ...]')
    
    # mapping update
    mapping_update_parser = mapping_subparsers.add_parser('update', help='更新映射')
    mapping_update_parser.add_argument('repo_identifier', help='仓库标识（完整路径或简称）')
    mapping_update_parser.add_argument('new_short_name', help='新的简称')
    
    # mapping remove
    mapping_remove_parser = mapping_subparsers.add_parser('remove', help='删除映射')
    mapping_remove_parser.add_argument('repo_identifier', help='仓库标识（完整路径或简称）')
    
    # mapping clear
    mapping_subparsers.add_parser('clear', help='清空映射')
    
    # mapping sync
    mapping_subparsers.add_parser('sync', help='从GitLab同步仓库')
    
    # mapping check
    mapping_subparsers.add_parser('check', help='检查映射完整性')
    
    # ========== 分支管理命令 ==========
    branch_parser = subparsers.add_parser('branch', help='分支管理')
    branch_subparsers = branch_parser.add_subparsers(dest='branch_command', help='分支管理子命令')
    
    # branch create
    branch_create_parser = branch_subparsers.add_parser('create', help='创建分支')
    branch_create_parser.add_argument('--repo', help='仓库标识（完整路径或简称）')
    branch_create_parser.add_argument('branch_name', help='新分支名称')
    branch_create_parser.add_argument('base_branch', help='基础分支名称')
    branch_create_parser.add_argument('--list', action='store_true', help='使用映射文件中的所有仓库')
    branch_create_parser.add_argument('--all', action='store_true', help='使用所有可访问仓库')
    
    # branch protect
    branch_protect_parser = branch_subparsers.add_parser('protect', help='保护分支')
    branch_protect_parser.add_argument('--repo', help='仓库标识（完整路径或简称）')
    branch_protect_parser.add_argument('branch_name', help='分支名称')
    branch_protect_parser.add_argument('--access-level', default='noone', choices=ACCESS_LEVEL_MAP.keys(), help='访问级别')
    branch_protect_parser.add_argument('--list', action='store_true', help='使用映射文件中的所有仓库')
    branch_protect_parser.add_argument('--all', action='store_true', help='使用所有可访问仓库')
    
    # branch unprotect
    branch_unprotect_parser = branch_subparsers.add_parser('unprotect', help='取消分支保护')
    branch_unprotect_parser.add_argument('--repo', help='仓库标识（完整路径或简称）')
    branch_unprotect_parser.add_argument('branch_name', help='分支名称')
    branch_unprotect_parser.add_argument('--list', action='store_true', help='使用映射文件中的所有仓库')
    branch_unprotect_parser.add_argument('--all', action='store_true', help='使用所有可访问仓库')
    
    # ========== Tag管理命令 ==========
    tag_parser = subparsers.add_parser('tag', help='Tag管理')
    tag_subparsers = tag_parser.add_subparsers(dest='tag_command', help='Tag管理子命令')
    
    # tag create
    tag_create_parser = tag_subparsers.add_parser('create', help='创建Tag')
    tag_create_parser.add_argument('--repo', help='仓库标识（完整路径或简称）')
    tag_create_parser.add_argument('tag_name', help='Tag名称')
    tag_create_parser.add_argument('ref', help='引用（分支名称或提交SHA）')
    tag_create_parser.add_argument('--list', action='store_true', help='使用映射文件中的所有仓库')
    tag_create_parser.add_argument('--all', action='store_true', help='使用所有可访问仓库')
    
    # tag protect
    tag_protect_parser = tag_subparsers.add_parser('protect', help='保护Tag')
    tag_protect_parser.add_argument('--repo', help='仓库标识（完整路径或简称）')
    tag_protect_parser.add_argument('tag_pattern', help='Tag名称模式')
    tag_protect_parser.add_argument('--access-level', default='noone', choices=ACCESS_LEVEL_MAP.keys(), help='访问级别')
    tag_protect_parser.add_argument('--list', action='store_true', help='使用映射文件中的所有仓库')
    tag_protect_parser.add_argument('--all', action='store_true', help='使用所有可访问仓库')
    
    # tag unprotect
    tag_unprotect_parser = tag_subparsers.add_parser('unprotect', help='取消Tag保护')
    tag_unprotect_parser.add_argument('--repo', help='仓库标识（完整路径或简称）')
    tag_unprotect_parser.add_argument('tag_pattern', help='Tag名称模式')
    tag_unprotect_parser.add_argument('--list', action='store_true', help='使用映射文件中的所有仓库')
    tag_unprotect_parser.add_argument('--all', action='store_true', help='使用所有可访问仓库')
    
    # ========== 合并请求管理命令 ==========
    mr_parser = subparsers.add_parser('merge-request', help='合并请求管理')
    mr_subparsers = mr_parser.add_subparsers(dest='mr_command', help='合并请求管理子命令')
    
    # merge-request create
    mr_create_parser = mr_subparsers.add_parser('create', help='创建合并请求')
    mr_create_parser.add_argument('--repo', help='仓库标识（完整路径或简称）')
    mr_create_parser.add_argument('source_branch', help='源分支名称')
    mr_create_parser.add_argument('target_branch', help='目标分支名称')
    mr_create_parser.add_argument('title', help='合并请求标题')
    mr_create_parser.add_argument('--assignee', help='指派人用户名或ID')
    mr_create_parser.add_argument('--reviewer', help='审核人用户名或ID')
    mr_create_parser.add_argument('--assignee-id', help='指派人ID（跳过用户查找）')
    mr_create_parser.add_argument('--reviewer-id', help='审核人ID（跳过用户查找）')
    mr_create_parser.add_argument('--list', action='store_true', help='使用映射文件中的所有仓库')
    mr_create_parser.add_argument('--all', action='store_true', help='使用所有可访问仓库')
    
    # merge-request approve
    mr_approve_parser = mr_subparsers.add_parser('approve', help='批准合并请求')
    mr_approve_parser.add_argument('--repo', help='仓库标识（完整路径或简称）')
    mr_approve_parser.add_argument('args', nargs='+', help='合并请求IID 或 源分支 目标分支')
    mr_approve_parser.add_argument('--list', action='store_true', help='使用映射文件中的所有仓库')
    mr_approve_parser.add_argument('--all', action='store_true', help='使用所有可访问仓库')
    
    # merge-request merge
    mr_merge_parser = mr_subparsers.add_parser('merge', help='合并合并请求')
    mr_merge_parser.add_argument('--repo', help='仓库标识（完整路径或简称）')
    mr_merge_parser.add_argument('args', nargs='+', help='合并请求IID 或 源分支 目标分支')
    mr_merge_parser.add_argument('--list', action='store_true', help='使用映射文件中的所有仓库')
    mr_merge_parser.add_argument('--all', action='store_true', help='使用所有可访问仓库')
    
    # merge-request close
    mr_close_parser = mr_subparsers.add_parser('close', help='关闭合并请求')
    mr_close_parser.add_argument('--repo', help='仓库标识（完整路径或简称）')
    mr_close_parser.add_argument('args', nargs='+', help='合并请求IID 或 源分支 目标分支')
    mr_close_parser.add_argument('--list', action='store_true', help='使用映射文件中的所有仓库')
    mr_close_parser.add_argument('--all', action='store_true', help='使用所有可访问仓库')
    
    # merge-request approve-and-merge
    mr_approve_merge_parser = mr_subparsers.add_parser('approve-and-merge', help='批准并合并合并请求')
    mr_approve_merge_parser.add_argument('--repo', help='仓库标识（完整路径或简称）')
    mr_approve_merge_parser.add_argument('args', nargs='+', help='合并请求IID 或 源分支 目标分支')
    mr_approve_merge_parser.add_argument('--list', action='store_true', help='使用映射文件中的所有仓库')
    mr_approve_merge_parser.add_argument('--all', action='store_true', help='使用所有可访问仓库')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)
    
    # 初始化映射管理器
    mapping_manager = RepoMappingManager(args.mapping_file)
    
    # 处理映射管理命令
    if args.command == 'mapping':
        if args.mapping_command == 'list':
            mapping_manager.list_mappings()
        elif args.mapping_command == 'add':
            if len(args.pairs) % 2 != 0:
                logger.error("添加映射时，完整路径和简称必须成对出现")
                return
            for i in range(0, len(args.pairs), 2):
                full_path = args.pairs[i]
                short_name = args.pairs[i+1]
                mapping_manager.add_mapping(full_path, short_name)
        elif args.mapping_command == 'update':
            mapping_manager.update_mapping(args.repo_identifier, args.new_short_name)
        elif args.mapping_command == 'remove':
            mapping_manager.remove_mapping(args.repo_identifier)
        elif args.mapping_command == 'clear':
            mapping_manager.clear_mappings()
        elif args.mapping_command == 'sync':
            gl_controller = GitLabController(args.url, args.token)
            mapping_manager.sync_mappings(gl_controller)
        elif args.mapping_command == 'check':
            gl_controller = GitLabController(args.url, args.token)
            mapping_manager.check_mappings(gl_controller)
        else:
            mapping_parser.print_help()
        return
    
    # 初始化GitLab控制器
    gl_controller = GitLabController(args.url, args.token)
    
    # 处理分支管理命令
    if args.command == 'branch':
        target_projects = get_target_projects(
            gl_controller, mapping_manager,
            args.repo, args.list, args.all
        )
        
        for project_path in target_projects:
            logger.info(f"\n处理仓库: {project_path}")
            project = gl_controller.get_project(project_path)
            if not project:
                continue
            
            if args.branch_command == 'create':
                BranchManager.create_branch(project, args.branch_name, args.base_branch)
            elif args.branch_command == 'protect':
                access_level = ACCESS_LEVEL_MAP[args.access_level]
                BranchManager.protect_branch(project, args.branch_name, access_level)
            elif args.branch_command == 'unprotect':
                BranchManager.unprotect_branch(project, args.branch_name)
            else:
                branch_parser.print_help()
        return
    
    # 处理Tag管理命令
    if args.command == 'tag':
        target_projects = get_target_projects(
            gl_controller, mapping_manager,
            args.repo, args.list, args.all
        )
        
        for project_path in target_projects:
            logger.info(f"\n处理仓库: {project_path}")
            project = gl_controller.get_project(project_path)
            if not project:
                continue
            
            if args.tag_command == 'create':
                TagManager.create_tag(project, args.tag_name, args.ref)
            elif args.tag_command == 'protect':
                access_level = ACCESS_LEVEL_MAP[args.access_level]
                TagManager.protect_tag(project, args.tag_pattern, access_level)
            elif args.tag_command == 'unprotect':
                TagManager.unprotect_tag(project, args.tag_pattern)
            else:
                tag_parser.print_help()
        return
    
    # 处理合并请求管理命令
    if args.command == 'merge-request':
        target_projects = get_target_projects(
            gl_controller, mapping_manager,
            args.repo, args.list, args.all
        )
        
        for project_path in target_projects:
            logger.info(f"\n处理仓库: {project_path}")
            project = gl_controller.get_project(project_path)
            if not project:
                continue
            
            if args.mr_command == 'create':
                MergeRequestManager.create_merge_request(
                    project, args.source_branch, args.target_branch, args.title,
                    args.assignee, args.reviewer,
                    args.assignee_id, args.reviewer_id
                )
            else:
                # 处理需要合并请求对象的命令
                mrs_to_process = []
                
                if len(args.args) == 1:
                    # 通过IID获取合并请求
                    mr_iid = int(args.args[0])
                    mr = MergeRequestManager.get_merge_request(project, mr_iid)
                    if mr:
                        mrs_to_process.append(mr)
                elif len(args.args) == 2:
                    # 通过分支查找合并请求
                    source_branch, target_branch = args.args
                    mr = MergeRequestManager.find_merge_request_by_branches(
                        project, source_branch, target_branch
                    )
                    if mr:
                        mrs_to_process.append(mr)
                    else:
                        logger.warning(f"未找到合并请求: {source_branch} -> {target_branch}")
                else:
                    logger.error("请提供合并请求IID 或 源分支 目标分支")
                    continue
                
                for mr in mrs_to_process:
                    if args.mr_command == 'approve':
                        MergeRequestManager.approve_merge_request(project, mr)
                    elif args.mr_command == 'merge':
                        MergeRequestManager.merge_merge_request(project, mr)
                    elif args.mr_command == 'close':
                        MergeRequestManager.close_merge_request(project, mr)
                    elif args.mr_command == 'approve-and-merge':
                        # 在调用approve之前保存iid，因为approve()调用后对象状态会改变
                        mr_iid = mr.iid if hasattr(mr, 'iid') else None
                        
                        # 批准合并请求
                        MergeRequestManager.approve_merge_request(project, mr)
                        
                        # 重新获取完整的合并请求对象
                        if mr_iid:
                            full_mr = MergeRequestManager.get_merge_request(project, mr_iid)
                            if full_mr:
                                # 使用新获取的对象进行合并操作
                                MergeRequestManager.merge_merge_request(project, full_mr)
                            else:
                                logger.error(f"重新获取合并请求失败，无法执行合并操作")
                        else:
                            logger.error(f"无法获取合并请求IID，无法执行合并操作")
        return
    
    # 显示帮助信息
    parser.print_help()


if __name__ == '__main__':
    main()
