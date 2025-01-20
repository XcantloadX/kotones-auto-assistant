import json
import os
import shutil
import argparse
from pathlib import Path

def process_file(input_file: str, output_dir: str):
    """处理输入文件并复制图片到输出目录"""
    input_path = Path(input_file)
    if not input_path.exists():
        print(f"错误：输入文件 {input_file} 不存在")
        return
    
    # 确保输出目录存在
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # 获取输入文件所在目录
    input_dir = input_path.parent
    
    image_ids = []
    total_lines = 0
    
    print(f"开始处理文件：{input_file}")
    
    # 读取并处理每一行
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            total_lines += 1
            try:
                data = json.loads(line.strip())
                if 'image' in data and 'value' in data['image']:
                    value_array = data['image']['value']
                    if value_array and len(value_array) > 0:
                        image_ids.append(value_array[-1])
            except json.JSONDecodeError as e:
                print(f"警告：第 {total_lines} 行解析失败：{e}")
    
    print(f"文件总行数：{total_lines}")
    print(f"找到的图片ID数量：{len(image_ids)}")
    
    # 复制图片
    copied_count = 0
    for img_id in image_ids:
        source_file = input_dir / f"{img_id}.png"
        target_file = output_path / f"{img_id}.png"
        
        if source_file.exists():
            try:
                shutil.copy2(source_file, target_file)
                copied_count += 1
            except Exception as e:
                print(f"警告：复制图片 {img_id}.png 失败：{e}")
        else:
            print(f"警告：源图片不存在：{source_file}")
    
    print(f"成功复制的图片数量：{copied_count}")

def main():
    parser = argparse.ArgumentParser(description='从 Dump JSON 文件中提取所有原图并复制相应的 PNG 文件到目标目录中')
    parser.add_argument('input', help='输入 Dump JSON 文件的路径')
    parser.add_argument('-o', '--out-dir', required=True, help='图片输出目录')
    
    args = parser.parse_args()
    process_file(args.input, args.out_dir)

if __name__ == '__main__':
    main()
