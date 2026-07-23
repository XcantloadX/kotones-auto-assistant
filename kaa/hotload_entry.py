import os
import sys
import time
import importlib
import importlib.util
import traceback

from .debug_entry import setup

def load_script_from_path(file_path, module_name="dynamic_script"):
    """直接从磁盘路径动态加载或重载 Python 脚本"""
    # 1. 从文件路径创建规范 (Spec)
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(f"无法解析脚本路径: {file_path}")
        
    # 2. 根据规范创建模块对象
    module = importlib.util.module_from_spec(spec)
    
    # 3. 放入 sys.modules（可选，但推荐，确保脚本内部有复杂的相对依赖时能正常工作）
    sys.modules[module_name] = module
    
    # 4. 执行模块代码（热重载的本质就是重新执行这一步）
    spec.loader.exec_module(module)
    return module

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
                    
                    # 核心：在内存中重载模块
                    script_mod = load_script_from_path(script_file, module_name="processor")
                    print("[Main] 重载成功！")
            except Exception:
                # 如果写代码时存在语法错误(SyntaxError)，reload 会抛错
                print("[Main] 重载失败 (存在语法错误？):")
                traceback.print_exc()

            # --- 步骤 B：执行图像处理逻辑 ---
            try:
                script_mod.tick()
            except Exception:
                # 如果处理逻辑有运行时错误(比如数组越界)，捕获并打印，不让主程序崩溃
                print("[Main] 图像处理报错:")
                traceback.print_exc()
                time.sleep(0.5) # 报错时稍微限速，避免终端被日志刷屏

    finally:
        print("[Main] 退出程序，资源已清理。")

if __name__ == '__main__':
    main()