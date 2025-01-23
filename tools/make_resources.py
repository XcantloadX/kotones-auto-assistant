# 此脚本用于扫描图片资源并自动生成 Python 脚本

from genericpath import isfile
import os
from typing import Any
import jinja2
PATH = './res/sprites'

def to_camel_case(s: str) -> str:
    return ''.join(word.capitalize() for word in s.split('_'))

def main():
    data = []
    # 列出所有语言
    languages = os.listdir(PATH)

    print('Languages:', languages)
    # 扫描资源
    for language in languages:
        print(f'Scanning {language}...')
        lang_data = {
            'language': language,
            'resources': {}
        }
        # 列出所有资源
        resources = {}
        def list_dir(dir_path: str, parent_class: dict[str, Any], class_path: list[str]):
            for current in os.listdir(dir_path):
                path = os.path.join(dir_path, current)
                if os.path.isfile(path):
                    if not path.endswith('.png') and not path.endswith('.jpg'):
                        continue
                    attr_name = to_camel_case(current.replace('.png', '').replace('.jpg', ''))
                    rel_path = os.path.join(dir_path, current)
                    abs_path = os.path.abspath(os.path.join(dir_path, current))
                    print(current, attr_name)
                    parent_class[attr_name] = {
                        'type': 'image',
                        'value': 'res_path("' + rel_path.replace('\\', '/') + '")',
                        'name': attr_name,
                        'abspath': abs_path.replace('\\', '/'),
                        'class_path': class_path,
                        'rel_path': rel_path.replace('\\', '/'),
                    }
                elif os.path.isdir(path):
                    class_name = to_camel_case(current)
                    resources[class_name] = {
                        # 'type': 'class',
                        # 'attrs': {},
                    }
                    parent_class[class_name] = {
                        'type': 'next_class',
                        'name': class_name,
                        'value': f'{class_name}',
                    }
                    list_dir(path, resources[class_name], class_path + [class_name])

        list_dir(os.path.join(PATH, language), {}, [])
        # resources 结构
        """
        {
            "<类名1>": {
                "<属性1>": { ... },
                "<属性2>": { ... },
                ...
            },
            "<类名2>": {
                "<属性1>": { ... },
                "<属性2>": { ... },
                ...
            },
            ...
        }
        """
        resources = {k: v for k, v in reversed(resources.items())}
        lang_data['resources'] = resources
        data.append(lang_data)

    # 渲染模板
    template = jinja2.Template(open('./tools/R.jinja2', encoding='utf-8').read())
    with open('./kotonebot/tasks/R.py', 'w', encoding='utf-8') as f:
        f.write(template.render(data=data))


if __name__ == '__main__':
    main()
