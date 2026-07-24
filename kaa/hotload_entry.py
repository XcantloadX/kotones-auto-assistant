import os
import sys
import time
import importlib
import importlib.util
import traceback

import cv2

from .debug_entry import setup


def load_script_from_path(file_path, module_name="dynamic_script"):
    """直接从磁盘路径动态加载或重载 Python 脚本"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(f"无法解析脚本路径: {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _wait_reload(script_file, last_mtime):
    """等待脚本文件更新并重载，返回 (new_module, new_mtime)"""
    while True:
        time.sleep(0.5)
        try:
            current_mtime = os.path.getmtime(script_file)
            if current_mtime != last_mtime:
                print("\n[Main] 检测到代码更新，正在热重载...")
                script_mod = load_script_from_path(script_file, module_name="processor")
                print("[Main] 重载成功！")
                cv2.destroyAllWindows()
                return script_mod, current_mtime
        except Exception:
            print("[Main] 重载失败 (存在语法错误？):")
            traceback.print_exc()


def main():
    setup()
    script_file = sys.argv[1]
    script_mod = load_script_from_path(script_file, module_name="processor")

    last_mtime = os.path.getmtime(script_file)

    try:
        while True:
            # --- 步骤 A：检查文件是否被修改 ---
            try:
                current_mtime = os.path.getmtime(script_file)
                if current_mtime != last_mtime:
                    last_mtime = current_mtime
                    print("\n[Main] 检测到代码更新，正在热重载...")
                    script_mod = load_script_from_path(script_file, module_name="processor")
                    print("[Main] 重载成功！")
                    cv2.destroyAllWindows()
            except Exception:
                print("[Main] 重载失败 (存在语法错误？):")
                traceback.print_exc()

            # --- 步骤 B：执行图像处理逻辑 ---
            try:
                script_mod.tick()
            except Exception:
                print("[Main] 图像处理报错:")
                traceback.print_exc()
                # 报错后等待脚本更新才继续 tick，避免重复刷屏
                script_mod, last_mtime = _wait_reload(script_file, last_mtime)

    finally:
        print("[Main] 退出程序，资源已清理。")

if __name__ == '__main__':
    main()