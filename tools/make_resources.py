# 此脚本用于扫描图片资源并自动生成 Python 脚本

from genericpath import isfile
import os
import shutil
import uuid
import jinja2
import argparse
from typing import Any, Optional, TypeGuard, Literal, Union, cast
from dataclasses import dataclass
from dataclasses_json import dataclass_json, DataClassJsonMixin

import cv2
from cv2.typing import MatLike

PATH = './kotonebot-resource/sprites'

SpriteType = Literal['basic', 'metadata']


@dataclass
class Resource:
    type: Literal['template', 'hint-box', 'hint-point']
    data: 'Sprite | HintBox | HintPoint'
    description: str
    """资源的描述信息"""

@dataclass
class Sprite:
    """表示一个精灵图像资源及其元数据。"""
    
    
    type: SpriteType
    uuid: str
    """编译后的 UUID。作为图片名称。"""
    name: str
    """在 R.py 的类中出现的属性名称"""
    display_name: str
    """在调试中显示的名称"""
    class_path: list[str]
    """
    在 R.py 的类中出现的路径。
    例如 ['Common', 'Button'] 会变为 Common.Button。
    不包括属性名。
    """
    rel_path: str
    """相对于项目根目录的路径。用于调试信息的显示"""
    abs_path: str
    """sprite 图片的绝对路径"""
    origin_file: str
    """原始图片的绝对路径"""

@dataclass
class HintBox:
    """表示一个提示框"""
    name: str
    display_name: str
    class_path: list[str]
    x1: float
    y1: float
    x2: float
    y2: float
    origin_file: str

@dataclass
class HintPoint:
    """表示一个提示点"""
    name: str
    display_name: str
    class_path: list[str]
    x: float
    y: float
    origin_file: str

@dataclass
class RectPoints(DataClassJsonMixin):
    """表示一个矩形的两个对角点坐标"""
    x1: float
    y1: float
    x2: float
    y2: float

@dataclass
class Point(DataClassJsonMixin):
    """表示一个二维坐标点"""
    x: float
    y: float

@dataclass
class Annotation(DataClassJsonMixin):
    """图像标注数据"""
    id: str
    type: Literal['rect', 'point']
    data: RectPoints | Point

@dataclass
class Definition(DataClassJsonMixin):
    """资源定义基类"""
    name: str
    """在 R.py 的类中出现的属性名称"""
    displayName: str
    """在调试器与调试输出中的名称"""
    type: Literal['template', 'ocr', 'color', 'hint-box', 'hint-point']
    """标注类型"""
    annotationId: str
    """标注 ID"""
    description: Optional[str] = None
    """描述信息"""

class TemplateDefinition(Definition):
    """模板匹配类型的资源定义"""
    useHintRect: bool
    """
    是否将这个模板的矩形范围作为运行时执行模板寻找函数时的提示范围。
    
    若为 true，则运行时会先在这个范围内寻找，如果没找到，再在整张截图中寻找。
    """

@dataclass
class SpriteMetadata(DataClassJsonMixin):
    """Sprite 元数据，包含标注和定义信息"""
    annotations: list[Annotation]
    definitions: dict[str, Definition]

@dataclass
class OutputClass(DataClassJsonMixin):
    """输出类定义"""
    type: Literal['class']
    name: str
    attributes: 'list[OutputClass | ImageAttribute]'

@dataclass
class ImageAttribute(DataClassJsonMixin):
    """图像属性定义"""
    type: Literal['image']
    name: str
    docstring: str
    value: str


def to_camel_case(s: str) -> str:
    return ''.join(word.capitalize() for word in s.split('_'))

def to_camel_cases(arr: list[str]) -> list[str]:
    return [to_camel_case(s) for s in arr]

def escape(s: str) -> str:
    return s.replace('\\', '\\\\')

def unify_path(path: str) -> str:
    return path.replace('\\', '/')

def ide_type() -> Literal['vscode', 'pycharm'] | None:
    """通过递归枚举父进程判断当前IDE类型"""
    import psutil
    
    me = psutil.Process()
    while True:
        parent = me.parent()
        if parent is None:
            break
        name = parent.name().lower()
        if 'code.exe' in name:
            return 'vscode'
        elif 'cursor.exe' in name:
            return 'vscode'
        elif 'windsurf.exe' in name:
            return 'vscode'
        elif 'pycharm' in name:
            return 'pycharm'
        me = parent
    return None

def scan_png_files(path: str) -> list[str]:
    """扫描所有 PNG 文件"""
    png_files = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith('.png'):
                file_path = os.path.join(root, file)
                png_files.append(file_path)
    return png_files

def query_annotation(annotations: list[Annotation], id: str) -> Annotation:
    for annotation in annotations:
        if annotation.id == id:
            return annotation
    raise ValueError(f'Annotation not found: {id}')

def load_metadata(root_path: str, png_file: str) -> list[Resource]:
    """加载 metadata 类型的标注"""
    json_path = png_file + '.json'
    with open(json_path, 'r', encoding='utf-8') as f:
        metadata = SpriteMetadata.from_json(f.read())
    # 遍历标注，裁剪、保存图片
    clips: dict[str, str] = {} # id -> 文件路径
    image = cv2.imread(png_file)
    for annotation in metadata.annotations:
        if annotation.type == 'rect':
            rect = annotation.data
            assert isinstance(rect, RectPoints)
            x1, y1, x2, y2 = rect.x1, rect.y1, rect.x2, rect.y2
            # 检查坐标是否超出图像
            if x1 < 0 or y1 < 0 or x2 > image.shape[1] or y2 > image.shape[0]:
                raise ValueError(f'Invalid annotation: {annotation} out of image: {png_file}')
            clip = image[int(y1):int(y2), int(x1):int(x2)]
            # 保存图片
            if not os.path.exists('tmp'):
                os.makedirs('tmp')
            path = os.path.join('tmp', f'{annotation.id}.png')
            cv2.imwrite(path, clip)
            print(f'Writing image: {path}')
            clips[annotation.id] = path
    # 关联 Definition，创建 Sprite
    resources: list[Resource] = []
    for definition in metadata.definitions.values():
        if definition.type == 'template':
            spr = Sprite(
                type='metadata',
                uuid=definition.annotationId,
                name=definition.name.split('.')[-1],
                display_name=definition.displayName,
                class_path=definition.name.split('.')[:-1],
                rel_path=png_file,
                abs_path=os.path.abspath(clips[definition.annotationId]),
                origin_file=os.path.abspath(png_file),
            )
            resources.append(Resource('template', spr, definition.description or ''))
        elif definition.type == 'hint-box':
            annotation = query_annotation(metadata.annotations, definition.annotationId)
            rect = annotation.data
            assert isinstance(rect, RectPoints)
            hb = HintBox(
                name=definition.name.split('.')[-1],
                display_name=definition.displayName,
                class_path=definition.name.split('.')[:-1],
                x1=rect.x1,
                y1=rect.y1,
                x2=rect.x2,
                y2=rect.y2,
                origin_file=os.path.abspath(png_file),
            )
            resources.append(Resource('hint-box', hb, definition.description or ''))
        elif definition.type == 'hint-point':
            annotation = query_annotation(metadata.annotations, definition.annotationId)
            pt = annotation.data
            assert isinstance(pt, Point)
            hp = HintPoint(
                x=int(pt.x),
                y=int(pt.y),
                name=definition.name.split('.')[-1],
                display_name=definition.displayName,
                class_path=definition.name.split('.')[:-1],
                origin_file=os.path.abspath(png_file),
            )
            resources.append(Resource('hint-point', hp, definition.description or ''))
        else:
            raise ValueError(f'Unknown definition type: {definition.type}')

    return resources

def load_basic_sprite(root_path: str, png_file: str) -> Resource:
    """加载 basic 类型的 sprite"""
    file_name = os.path.basename(png_file)
    class_path = os.path.relpath(os.path.dirname(png_file), root_path).split(os.sep)
    class_path = [to_camel_case(c) for c in class_path]
    spr = Sprite(
        type='basic',
        uuid=str(uuid.uuid4()),
        name=to_camel_case(file_name.replace('.png', '')),
        display_name=file_name,
        class_path=class_path,
        rel_path=png_file,
        abs_path=os.path.abspath(png_file),
        origin_file=os.path.abspath(png_file)
    )
    return Resource('template', spr, "")

def load_sprites(root_path: str, png_files: list[str]) -> list[Resource]:
    """"""
    resources = []
    for file in png_files:
        # 判断类型
        json_path = file + '.json'
        if os.path.exists(json_path):
            resources.extend(load_metadata(root_path, file))
            print(f'Loaded metadata: {file}')
        else:
            resources.append(load_basic_sprite(root_path, file))
            print(f'Loaded basic sprite: {file}')
    return resources

def make_img(ide: Literal['vscode', 'pycharm'], path: str, title: str, height: str = ''):
    if ide == 'vscode':
        return f'<img src="vscode-file://vscode-app/{escape(path)}" title="{title}" height="{height}" />\n'
    elif ide == 'pycharm':
        return f'.. image:: http://localhost:6532/image?path={unify_path(path)}\n'
    else:
        return f'<img src="file:///{escape(path)}" title="{title}" height="{height}" />\n'

def make_classes(resources: list[Resource], ide: Literal['vscode', 'pycharm']) -> list[OutputClass]:
    """根据 Sprite 数据生成 R.py 中的类信息。"""
    # 按照 class_path 对 sprites 进行分组
    class_map: dict[str, OutputClass] = {}

    # 创建或获取指定路径的类
    def get_or_create_class(path: list[str]) -> Union[OutputClass, None]:
        if not path:
            return None
        
        class_key = '.'.join(path)
        if class_key in class_map:
            return class_map[class_key]
        
        new_class = OutputClass(
            type='class',
            name=path[-1],
            attributes=[]
        )
        class_map[class_key] = new_class
        return new_class
    
    # 处理每个 资源
    for resource in resources:
        # 获取当前 sprite 的完整路径
        class_path = resource.data.class_path

        # 创建或获取所有父类
        current_class = None
        for i in range(len(class_path)):
            path = class_path[:i + 1]
            cls = get_or_create_class(path)
            if not cls:
                continue
            
            # 如果这个类还没有被添加到父类的属性中，添加它
            if i > 0:
                parent = get_or_create_class(path[:-1])
                if parent and not any(isinstance(attr, OutputClass) and attr.name == cls.name for attr in parent.attributes):
                    parent.attributes.append(cls)
            
            current_class = cls
        
        # 将 sprite 添加为最后一级类的属性
        if current_class:
            if resource.type == 'template':
                sprite = resource.data
                assert isinstance(sprite, Sprite)
                origin_img = cv2.imread(sprite.origin_file)
                w, h = origin_img.shape[1], origin_img.shape[0]
                if h > 1000:
                    height = 500
                else:
                    height = ''
                docstring = (
                    f"名称：{sprite.display_name}\\n\n"
                    f"描述：{resource.description}\\n\n"
                    f"路径：{unify_path(sprite.rel_path)}\\n\n"
                    f"模块：`{'.'.join(sprite.class_path)}`\\n\n"
                    + make_img(ide, sprite.abs_path, sprite.display_name)
                )
                if sprite.type == 'metadata':
                    docstring += (
                        f"原始文件：\\n\n"
                        + make_img(ide, sprite.origin_file, '原始文件', height)
                    )
                img_attr = ImageAttribute(
                    type='image',
                    name=sprite.name,
                    docstring=docstring,
                    value=f'Image(path=sprite_path(r"{sprite.uuid}.png"), name="{sprite.display_name}")'
                )
                current_class.attributes.append(img_attr)
            elif resource.type == 'hint-box':
                hint_box = resource.data
                assert isinstance(hint_box, HintBox)
                # 裁剪并保存 hint-box 区域
                image = cv2.imread(hint_box.origin_file)
                x1, y1, x2, y2 = int(hint_box.x1), int(hint_box.y1), int(hint_box.x2), int(hint_box.y2)
                clip = image[y1:y2, x1:x2]
                if not os.path.exists('tmp'):
                    os.makedirs('tmp')
                clip_path = os.path.join('tmp', f'hintbox_{hint_box.name}.png')
                cv2.imwrite(clip_path, clip)
                clip_abs_path = os.path.abspath(clip_path)

                docstring = (
                    f"名称：{hint_box.display_name}\\n\n"
                    f"描述：{resource.description}\\n\n"
                    f"模块：`{'.'.join(hint_box.class_path)}`\\n\n"
                    f"值：x1={hint_box.x1}, y1={hint_box.y1}, x2={hint_box.x2}, y2={hint_box.y2}\\n\n"
                    f"裁剪区域：\\n\n"
                    + make_img(ide, clip_abs_path, '裁剪区域')
                    + f"原始图片：\\n\n"
                    + make_img(ide, hint_box.origin_file, '原始文件', '80%')
                )
                img_attr = ImageAttribute(
                    type='image',
                    name=hint_box.name,
                    docstring=docstring,
                    value=(
                        f'HintBox(' + 
                        f'x1={int(hint_box.x1)}, y1={int(hint_box.y1)}, '
                        f'x2={int(hint_box.x2)}, y2={int(hint_box.y2)}, '
                        f'source_resolution=(720, 1280))' # HACK: 硬编码分辨率
                    )
                )
                current_class.attributes.append(img_attr)
            elif resource.type == 'hint-point':
                hint_point = resource.data
                assert isinstance(hint_point, HintPoint)
                docstring = (
                    f"名称：{hint_point.display_name}\\n\n"
                    f"描述：{resource.description}\\n\n"
                    f"模块：`{'.'.join(hint_point.class_path)}`\\n\n"
                    f"坐标：(x={hint_point.x}, y={hint_point.y})\\n\n"
                )
                img_attr = ImageAttribute(
                    type='image',
                    name=hint_point.name,
                    docstring=docstring,
                    value=f'HintPoint(x={hint_point.x}, y={hint_point.y})'
                )
                current_class.attributes.append(img_attr)
    
    # 返回顶层类列表
    return [cls for (path, cls) in class_map.items() if path.find('.') == -1]

def copy_sprites(resources: list[Resource], output_folder: str) -> list[Resource]:
    """复制 sprites 图片到目标路径，并输出 R.py"""
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for resource in resources:
        if resource.type == 'template':
            spr = resource.data
            assert isinstance(spr, Sprite)
            src_img_path = spr.abs_path
            img_name = spr.uuid + '.png'
            dst_img_path = os.path.join(output_folder, img_name)
            shutil.copy(src_img_path, dst_img_path)
            print(f'Copying image: {src_img_path} to {dst_img_path}')
            spr.abs_path = os.path.abspath(dst_img_path)

    return resources


def indent(text: str, indent: int = 4) -> str:
    """调整文本的缩进"""
    lines = text.split('\n')
    return '\n'.join(' ' * indent + line for line in lines)

if __name__ == '__main__':
    # 添加命令行参数解析
    parser = argparse.ArgumentParser(description='生成图片资源文件')
    parser.add_argument('-p', '--production', action='store_true', help='生产模式：不输出注释')
    parser.add_argument('-i', '--ide', help='IDE 类型', default=ide_type())
    args = parser.parse_args()

    if os.path.exists(r'kaa/prites'):
        shutil.rmtree(r'kaa/sprites')
    path = PATH + '/jp'
    files = scan_png_files(path)
    sprites = load_sprites(path, files)
    sprites = copy_sprites(sprites, r'kaa/sprites')
    classes = make_classes(sprites, args.ide)
    
    env = jinja2.Environment(loader=jinja2.FileSystemLoader('./tools'))
    env.filters['indent'] = indent
    
    template = env.get_template('R.jinja2')
    print(f'Rendering template: {template.name}')
    with open('./kaa/tasks/R.py', 'w', encoding='utf-8') as f:
        f.write(template.render(data=classes, production=args.production))
    print('Creating __init__.py')
    os.makedirs('./kaa/sprites', exist_ok=True)
    with open('./kaa/sprites/__init__.py', 'w', encoding='utf-8') as f:
        f.write('')
    print('All done!')