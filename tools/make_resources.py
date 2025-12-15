import os
import shutil
import argparse

from kotonebot.devtools.resgen.parsers import ParserRegistry, KotoneV1Parser, BasicSpriteParser
from kotonebot.devtools.resgen.utils import build_class_tree
from kotonebot.devtools.resgen.codegen import StandardGenerator, EntityGenerator

ROOT_SCAN_PATH = './kotonebot-resource/sprites/jp' # 图片资源根目录
OUTPUT_IMG_DIR = './kaa/sprites'                  # 处理后的图片存放处
OUTPUT_CODE_FILE = './kaa/tasks/R.py'             # 生成的代码文件


class KaaGenerator(EntityGenerator):
    def render_header(self):
        super().render_header()
        self.writer.write("from kaa.common import sprite_path")
        self.writer.write("from kaa.game_ui.elements import GakumasPrimaryButtonPrefab")

def scan_files(path: str) -> list[str]:
    files = []
    for root, _, filenames in os.walk(path):
        for f in filenames:
            files.append(os.path.join(root, f))
    return files

def ide_type_detection() -> str:
    import psutil
    try:
        me = psutil.Process()
        while True:
            parent = me.parent()
            if parent is None:
                break
            name = parent.name().lower()
            if 'code' in name or 'cursor' in name:
                return 'vscode'
            if 'pycharm' in name:
                return 'pycharm'
            me = parent
    except:  # noqa: E722
        pass
    return 'vscode'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--production', action='store_true', help='No docstrings')
    parser.add_argument('--ide', default=None)
    args = parser.parse_args()

    ide = args.ide or ide_type_detection()

    # 1. 准备环境
    if os.path.exists(OUTPUT_IMG_DIR):
        shutil.rmtree(OUTPUT_IMG_DIR)
    os.makedirs(OUTPUT_IMG_DIR, exist_ok=True)
    
    # 2. 注册解析器
    registry = ParserRegistry()
    registry.register(KotoneV1Parser())    # 优先尝试解析 JSON
    registry.register(BasicSpriteParser()) # 兜底解析普通 PNG

    # 3. 扫描与解析
    print(f"Scanning {ROOT_SCAN_PATH}...")
    all_files = scan_files(ROOT_SCAN_PATH)
    all_resources = []
    
    context = {
        'output_img_dir': OUTPUT_IMG_DIR,
        'root_scan_path': ROOT_SCAN_PATH
    }

    for f in all_files:
        # 解析文件
        # parse_file 会内部遍历 parsers，如果 JSON 存在，V1Parser 会处理 .png.json
        # 此时 .png 文件本身会被 BasicParser 跳过（因为 parse_file 是按文件列表来的，我们需要处理去重逻辑）
        
        # 优化逻辑：如果是 .png 且存在对应的 .json，则跳过 .png 的 BasicParser 处理
        if f.endswith('.png') and os.path.exists(f + '.json'):
            continue
            
        res = registry.parse_file(f, context)
        if res:
            print(f"Parsed: {os.path.basename(f)} -> {len(res)} items")
            all_resources.extend(res)

    # 4. 构建树
    print("Building class tree...")
    tree = build_class_tree(all_resources)

    # 5. 生成代码
    print("Generating code...")
    generator = KaaGenerator(production=args.production, ide_type=ide)
    code = generator.generate(tree)

    # 6. 写入文件
    out_dir = os.path.dirname(OUTPUT_CODE_FILE)
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
        
    with open(OUTPUT_CODE_FILE, 'w', encoding='utf-8') as f:
        f.write(code)
        
    # 创建 __init__.py
    init_file = os.path.join(OUTPUT_IMG_DIR, '__init__.py')
    with open(init_file, 'w') as f:
        f.write('')

    print("Done!")

if __name__ == "__main__":
    main()