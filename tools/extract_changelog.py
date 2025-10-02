import subprocess
import argparse
from typing import NamedTuple
from collections import defaultdict

class Commit(NamedTuple):
    message: str
    hash: str

def get_commit_messages():
    # 获取最新的以 kaa 开头的 tag
    # 获取所有以 kaa 开头的 tags，按版本排序，取最新的
    all_kaa_tags = subprocess.check_output(['git', 'tag', '--list', 'kaa*', '--sort=-committerdate']).decode().strip()
    if not all_kaa_tags:
        raise ValueError("没有找到以 'kaa' 开头的 git tags")
    
    latest_tag = all_kaa_tags.split('\n')[0]
    
    # 获取自该 tag 以来的所有 commit message 和 hash
    log = subprocess.check_output(['git', 'log', f'{latest_tag}..HEAD', '--pretty=format:%h|%s']).decode().strip()
    commits = []
    for line in log.split('\n'):
        commit_hash, message = line.split('|', 1)
        commits.append(Commit(message, commit_hash))
    return commits

def categorize_commits(commits):
    categories = defaultdict(lambda: defaultdict(list))
    for commit in commits:
        msg = commit.message
        # 提取类型和范围
        if ':' in msg:
            prefix, content = msg.split(':', 1)
            if '(' in prefix and ')' in prefix:
                type_part, scope = prefix.split('(', 1)
                scope = scope.rstrip(')')
            else:
                type_part = prefix
                scope = '*'
            
            # 分类处理
            if type_part.startswith('feat'):
                categories['feat'][scope].append(commit)
            elif type_part.startswith('fix'):
                categories['fix'][scope].append(commit)
            elif type_part.startswith('refactor'):
                categories['refactor'][scope].append(commit)
            elif msg.startswith('docs:'):
                categories['docs']['*'].append(commit)
            elif msg.startswith('test:'):
                categories['test']['*'].append(commit)
            elif msg.startswith('chore:'):
                categories['chore']['*'].append(commit)
            else:
                categories['other']['*'].append(commit)
    return categories

def print_changelog(categories, output_file=None):
    output = []
    # 定义分类映射
    category_map = {
        'feat': '新增',
        'fix': '修复',
        'refactor': '重构',
        'docs': '文档',
        'test': '单测',
        'chore': '其他',
        'other': '其他'
    }
    
    # 定义范围映射
    scope_map = {
        'task': '脚本',
        'ui': '界面',
        'core': '框架',
        'devtool': '开发工具',
        'bootstrap': '启动器', # 旧写法
        'launcher': '启动器', # 新写法
        '*': '其他'
    }
    
    # 按指定顺序输出
    for scope in scope_map.keys():
        scope_output = []
        for category, scopes in categories.items():
            if scope in scopes and scopes[scope]:
                for commit in scopes[scope]:
                    # 使用 commit 对象中的信息
                    scope_output.append(f"* [{category_map[category]}] {commit.message.split(':', 1)[1].strip()}（#{commit.hash}）")
        
        if scope_output:
            output.append(f"{scope_map[scope]}：")
            output.extend(scope_output)
            output.append("")
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(output))
    else:
        print('\n'.join(output))

def main():
    parser = argparse.ArgumentParser(description='生成更新日志')
    parser.add_argument('-o', '--output', help='输出文件路径')
    args = parser.parse_args()
    
    commits = get_commit_messages()
    categories = categorize_commits(commits)
    print_changelog(categories, args.output)

if __name__ == '__main__':
    main()

