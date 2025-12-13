import subprocess
import argparse
import sys
from typing import NamedTuple, List, Dict
from collections import defaultdict

# GUI Imports
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog
    HAS_TK = True
except ImportError:
    HAS_TK = False

class Commit(NamedTuple):
    message: str
    hash: str

def get_git_tags() -> List[str]:
    """获取所有 git tags，按时间倒序排列"""
    try:
        tags_output = subprocess.check_output(['git', 'tag', '--sort=-committerdate']).decode().strip()
        if not tags_output:
            return []
        return tags_output.split('\n')
    except subprocess.CalledProcessError:
        return []

def get_commits(start_ref: str, end_ref: str) -> List[Commit]:
    """获取两个引用之间的 commits"""
    range_spec = f'{start_ref}..{end_ref}'
    try:
        log = subprocess.check_output(['git', 'log', range_spec, '--pretty=format:%h|%s']).decode().strip()
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Git log failed for range {range_spec}: {e}")

    commits = []
    if not log:
        return commits
        
    for line in log.split('\n'):
        if '|' in line:
            commit_hash, message = line.split('|', 1)
            commits.append(Commit(message, commit_hash))
    return commits

def auto_detect_start_tag() -> str:
    """原有逻辑：自动寻找最新的 kaa* tag"""
    tags = get_git_tags()
    kaa_tags = [t for t in tags if t.startswith('kaa')]
    if not kaa_tags:
        raise ValueError("没有找到以 'kaa' 开头的 git tags")
    return kaa_tags[0]

def categorize_commits(commits: List[Commit]) -> Dict:
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

def generate_changelog_content(categories: Dict) -> str:
    """生成变更日志文本内容"""
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
                    cat_name = category_map.get(category, category)
                    msg_content = commit.message.split(':', 1)[1].strip()
                    scope_output.append(f"* [{cat_name}] {msg_content}（#{commit.hash}）")
        
        if scope_output:
            output.append(f"{scope_map[scope]}：")
            output.extend(scope_output)
            output.append("")
            
    return '\n'.join(output)

class ChangelogApp:
    def __init__(self, root):
        self.root = root
        self.root.title("更新日志生成器")
        self.root.geometry("600x700")
        
        self.tags = get_git_tags()
        if not self.tags:
            messagebox.showwarning("警告", "未在当前目录找到 Git Tag")
            self.tags = []

        self.setup_ui()

    def setup_ui(self):
        # Frame: Controls
        control_frame = ttk.LabelFrame(self.root, text="配置", padding="10")
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        # Start Tag
        ttk.Label(control_frame, text="开始 Tag:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.start_tag_var = tk.StringVar()
        self.start_combo = ttk.Combobox(control_frame, textvariable=self.start_tag_var, values=self.tags)
        self.start_combo.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        
        # 尝试自动选择第二个tag（如果有），或者第一个kaa tag
        default_start = ""
        kaa_tags = [t for t in self.tags if t.startswith('kaa')]
        if len(self.tags) > 1:
            default_start = self.tags[1] # 默认为上一个版本
        elif kaa_tags:
            default_start = kaa_tags[0]
        elif self.tags:
            default_start = self.tags[-1]
        
        if default_start:
            self.start_combo.set(default_start)

        # End Tag
        ttk.Label(control_frame, text="结束 Tag:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.end_tag_var = tk.StringVar(value="HEAD")
        # 选项包含 HEAD 和所有 tag
        end_options = ["HEAD"] + self.tags
        self.end_combo = ttk.Combobox(control_frame, textvariable=self.end_tag_var, values=end_options)
        self.end_combo.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)

        control_frame.columnconfigure(1, weight=1)

        # Frame: Actions
        action_frame = ttk.Frame(self.root, padding="5")
        action_frame.pack(fill=tk.X, padx=10)

        ttk.Button(action_frame, text="生成日志", command=self.generate).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="复制到剪贴板", command=self.copy_to_clipboard).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="保存文件...", command=self.save_file).pack(side=tk.LEFT, padx=5)

        # Frame: Output
        output_frame = ttk.LabelFrame(self.root, text="预览", padding="10")
        output_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.text_area = tk.Text(output_frame, wrap=tk.WORD)
        self.text_area.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        scrollbar = ttk.Scrollbar(output_frame, orient=tk.VERTICAL, command=self.text_area.yview)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT)
        self.text_area.config(yscrollcommand=scrollbar.set)

    def generate(self):
        start = self.start_tag_var.get()
        end = self.end_tag_var.get()
        
        if not start or not end:
            messagebox.showerror("错误", "请选择开始和结束 Tag")
            return

        try:
            commits = get_commits(start, end)
            categories = categorize_commits(commits)
            content = generate_changelog_content(categories)
            
            self.text_area.delete(1.0, tk.END)
            self.text_area.insert(tk.END, content)
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def copy_to_clipboard(self):
        content = self.text_area.get(1.0, tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        messagebox.showinfo("提示", "已复制到剪贴板")

    def save_file(self):
        content = self.text_area.get(1.0, tk.END)
        filepath = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown Files", "*.md"), ("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("成功", f"文件已保存至: {filepath}")
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")

def run_gui():
    if not HAS_TK:
        print("错误: 未找到 tkinter 模块，无法启动 GUI。请安装 python-tk 或使用 CLI 模式。")
        sys.exit(1)
    root = tk.Tk()
    app = ChangelogApp(root)
    root.mainloop()

def run_cli(args):
    try:
        start_tag = args.start
        end_tag = args.end
        
        # 如果未指定开始 tag，使用原有逻辑自动检测
        if not start_tag:
            try:
                start_tag = auto_detect_start_tag()
                print(f"自动检测到的起始 Tag: {start_tag}")
            except ValueError as e:
                print(f"错误: {e}")
                sys.exit(1)

        commits = get_commits(start_tag, end_tag)
        categories = categorize_commits(commits)
        content = generate_changelog_content(categories)

        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            print(content)
            
    except Exception as e:
        print(f"执行出错: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='生成更新日志')
    parser.add_argument('--gui', action='store_true', help='启动图形界面')
    parser.add_argument('-s', '--start', help='起始 Tag (如果不指定，自动寻找最新的 kaa*)')
    parser.add_argument('-e', '--end', default='HEAD', help='结束 Tag (默认: HEAD)')
    parser.add_argument('-o', '--output', help='输出文件路径')
    args = parser.parse_args()
    
    if args.gui:
        run_gui()
    else:
        run_cli(args)

if __name__ == '__main__':
    main()
