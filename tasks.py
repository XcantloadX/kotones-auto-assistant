import os
import sys
import shutil
from pathlib import Path

from invoke import task, Context # type: ignore

@task
def env(c: Context):
    """检查并创建虚拟环境"""
    venv_path = Path(".venv")
    if not venv_path.exists():
        print("正在创建虚拟环境...")
        c.run("python -m venv .venv")
        
        # 根据操作系统选择激活脚本
        if sys.platform == "win32":
            c.run(".venv\\Scripts\\pip install -r requirements.txt")
        else:
            c.run(".venv/bin/pip install -r requirements.txt")
            
        print("虚拟环境创建完成并已安装依赖")
    else:
        print("虚拟环境已存在")

    # 激活虚拟环境
    if sys.platform == "win32":
        c.run(".venv\\Scripts\\activate")
    else:
        c.run("source .venv/bin/activate")

@task(env)
def build(c: Context):
    c.run("pyinstaller -y kotonebot-gr.spec")

@task(build)
def package(c: Context):
    # copy files
    shutil.copytree("./res", "./dist/gr/res")
    # zip
    shutil.make_archive("./dist/gr", "zip", "./dist/gr")
