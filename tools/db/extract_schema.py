# 此脚本用于从 YAML 文件中提取 schema
# 只处理基本数据类型和基本数据类型的数组

import os
import sys
import glob
import json
import sqlite3
import time
import itertools
from dataclasses import dataclass
from typing import Dict, Any, Literal, Optional, List

import yaml
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn
from jinja2 import Template

SchemaDataType = Literal[
    'array', 'boolean', 'integer', 'number',
    'string', 'null', 'object', 'json_string'
]

SQL_KEYWORDS = {
    'abort', 'action', 'add', 'after', 'all', 'alter', 'analyze', 'and', 'as', 'asc',
    'attach', 'autoincrement', 'before', 'begin', 'between', 'by', 'cascade', 'case',
    'cast', 'check', 'collate', 'column', 'commit', 'conflict', 'constraint', 'create',
    'cross', 'current_date', 'current_time', 'current_timestamp', 'database', 'default',
    'deferrable', 'deferred', 'delete', 'desc', 'detach', 'distinct', 'drop', 'each',
    'else', 'end', 'escape', 'except', 'exclusive', 'exists', 'explain', 'fail', 'for',
    'foreign', 'from', 'full', 'glob', 'group', 'having', 'if', 'ignore', 'immediate',
    'in', 'index', 'indexed', 'initially', 'inner', 'insert', 'instead', 'intersect',
    'into', 'is', 'isnull', 'join', 'key', 'left', 'like', 'limit', 'match', 'natural',
    'no', 'not', 'notnull', 'null', 'of', 'offset', 'on', 'or', 'order', 'outer',
    'plan', 'pragma', 'primary', 'query', 'raise', 'recursive', 'references', 'regexp',
    'reindex', 'release', 'rename', 'replace', 'restrict', 'right', 'rollback', 'row',
    'savepoint', 'select', 'set', 'table', 'temp', 'temporary', 'then', 'to', 'transaction',
    'trigger', 'union', 'unique', 'update', 'using', 'vacuum', 'values', 'view', 'virtual',
    'when', 'where', 'with', 'without'
}

@dataclass
class Schema:
    type: SchemaDataType
    array_type: Optional[SchemaDataType] = None  # 如果type是array，这里存储数组元素的类型
    properties: Optional[Dict[str, 'Schema']] = None  # 如果是嵌套对象，这里存储子字段
    is_primary_key: bool = False  # 是否为主键
    composite_key_order: int = 0  # 在组合主键中的顺序，0表示不是组合主键的一部分

def get_type(value: Any) -> SchemaDataType:
    """获取值的类型"""
    if isinstance(value, list):
        return 'array'
    elif isinstance(value, bool):
        return 'boolean'
    elif isinstance(value, int):
        return 'integer'
    elif isinstance(value, float):
        return 'number'
    elif isinstance(value, str):
        return 'string'
    elif value is None:
        return 'null'
    elif isinstance(value, dict):
        return 'json_string'
    raise ValueError(f"不支持的类型: {type(value).__name__}")

def extract(data: Any) -> Schema:
    """分析数据结构，生成 schema"""
    schema_type = get_type(data)
    
    if schema_type == 'array':
        if not data:  # 空数组
            return Schema(type='array', array_type='null')
        
        # 获取第一个元素
        first_element = data[0]
        
        # 如果是字典，视为字符串
        if isinstance(first_element, dict):
            return Schema(type='array', array_type='json_string')
        
        # 处理基本类型数组
        element_type = get_type(first_element)
        if any(get_type(item) != element_type for item in data[1:]):
            raise ValueError("数组元素类型必须一致")
        return Schema(type='array', array_type=element_type)
    
    return Schema(type=schema_type)

def escape_sql_identifier(name: str) -> str:
    """如果标识符是SQL关键字或包含特殊字符，使用双引号包裹"""
    if name.lower() in SQL_KEYWORDS or not name.isalnum():
        return f'"{name}"'
    return name

def schema_to_sql(schema: Dict[str, Schema], table_name: str = 'root') -> str:
    """将 Schema 转换为 SQLite 建表语句"""
    def _type_to_sql(schema: Schema, field_prefix: str = '') -> list[tuple[str, str, int]]:
        if schema.type == 'object' and schema.properties:
            columns = []
            for field_name, field_schema in schema.properties.items():
                nested_prefix = f"{field_prefix}{field_name}_" if field_prefix else f"{field_name}_"
                columns.extend(_type_to_sql(field_schema, nested_prefix))
            return columns
            
        if schema.type == 'array':
            return [(escape_sql_identifier(field_prefix.rstrip('_')), 'TEXT', schema.composite_key_order)]
        
        type_mapping = {
            'boolean': 'INTEGER',
            'integer': 'INTEGER',
            'number': 'REAL',
            'string': 'TEXT',
            'json_string': 'TEXT',
            'null': 'TEXT'
        }
        return [(escape_sql_identifier(field_prefix.rstrip('_')), type_mapping[schema.type], schema.composite_key_order)]

    columns = []
    composite_key_fields = []
    
    # 处理所有字段
    for field_name, field_schema in schema.items():
        field_columns = _type_to_sql(field_schema, f"{field_name}_")
        for col_name, col_type, composite_key_order in field_columns:
            if composite_key_order > 0:
                composite_key_fields.append((composite_key_order, col_name))
                columns.append(f'{col_name} {col_type}')
            else:
                columns.append(f'{col_name} {col_type}')

    # 如果有组合主键，添加 PRIMARY KEY 约束
    if composite_key_fields:
        composite_key_fields.sort()  # 按照顺序排序
        key_fields = [field[1] for field in composite_key_fields]
        columns.append(f'PRIMARY KEY ({", ".join(key_fields)})')

    table_name = escape_sql_identifier(table_name)
    create_table = f'CREATE TABLE IF NOT EXISTS {table_name} (\n    '
    create_table += ',\n    '.join(columns)
    create_table += '\n);'
    
    return create_table

def process_yaml_data(data: Any, table_name: str) -> tuple[Dict[str, Schema], str]:
    """处理YAML数据，返回schema和建表语句"""
    # 处理空数据的情况
    if data is None:
        return {}, ""
        
    if not isinstance(data, list) or not data:
        raise ValueError("YAML 数据必须包含非空数组")
        
    if not isinstance(data[0], dict):
        raise ValueError("YAML 数据的第一个元素必须是对象")
        
    schema = {}
    # 首先创建所有字段的schema
    for key, value in data[0].items():
        schema[key] = extract(value)
    
    # 查找组合主键
    composite_key_fields = find_composite_key(data)
    
    # 设置组合主键顺序
    for i, field_name in enumerate(composite_key_fields, 1):
        if field_name in schema:
            schema[field_name].composite_key_order = i
                
    sql = schema_to_sql(schema, table_name)
    return schema, sql

def generate_python_models(schema: Dict[str, Schema], class_name: str) -> str:
    """生成Python数据类代码"""
    def _generate_flat_class(schema: Dict[str, Schema], class_name: str) -> str:
        type_mapping = {
            'boolean': 'bool',
            'integer': 'int',
            'number': 'float',
            'string': 'str',
            'null': 'None',
            'array': 'list',
            'json_string': 'str'
        }
        
        fields = []
        
        for field_name, field_schema in schema.items():
            fields.append({'name': field_name, 'type': type_mapping[field_schema.type]})

        # 生成类定义
        template_str = '''
@dataclass
class {{ class_name }}:
{%- for field in fields %}
    {{ field.name }}: {{ field.type }}
{%- endfor %}'''
        
        template = Template(template_str)
        class_def = template.render(class_name=class_name, fields=fields)
        
        return class_def

    # 直接生成平面类
    return _generate_flat_class(schema, class_name)

def create_sqlite_database(sql_statements: list[str], db_path: str):
    """创建SQLite数据库并执行建表语句"""
    folder_path = os.path.dirname(db_path)
    os.makedirs(folder_path, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        for sql in sql_statements:
            if sql.strip():
                conn.execute(sql)
        conn.commit()
    print(f"成功创建数据库：{db_path}")

def insert_data_to_sqlite(conn, table_name: str, data_list: list):
    """将数据插入到SQLite数据库中"""
    if not data_list:
        return
        
    # 获取表的列名
    table_name = escape_sql_identifier(table_name)
    cursor = conn.execute(f"SELECT * FROM {table_name} LIMIT 0")
    columns = [description[0] for description in cursor.description]
    
    # 准备INSERT语句
    placeholders = ','.join(['?' for _ in columns])
    escaped_columns = [escape_sql_identifier(col) for col in columns]
    insert_sql = f'INSERT INTO {table_name} ({",".join(escaped_columns)}) VALUES ({placeholders})'
    
    # 准备数据
    rows = []
    for item in data_list:
        row = []
        for col in columns:
            # 处理嵌套字段，比如 field_subfield
            parts = col.split('_')
            value = item
            for part in parts:
                value = value.get(part, None) if isinstance(value, dict) else None
                
            # 如果是列表或字典，转换为JSON字符串
            if isinstance(value, (list, dict)):
                value = json.dumps(value, ensure_ascii=False)
            row.append(value)
        rows.append(row)
    
    # 执行插入
    conn.executemany(insert_sql, rows)
    conn.commit()

try:
    from yaml import CSafeLoader as SafeLoader
except ImportError:
    from yaml import SafeLoader

def process_file_worker(yaml_file: str) -> tuple[Optional[str], Optional[str], str, Any]:
    """
    Worker function to process a single YAML file.
    Reads, parses, and generates schema, SQL, and Python model.
    """
    with open(yaml_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Clean content
    content = content.replace('\t', '\\t').replace('\x0b', ' ')
    
    data = yaml.load(content, Loader=SafeLoader)
    
    table_name = os.path.splitext(os.path.basename(yaml_file))[0]
    
    schema, sql = process_yaml_data(data, table_name)
    
    if not schema:
        return None, None, yaml_file, data
        
    class_name = table_name
    python_model = generate_python_models(schema, class_name)
    
    return python_model, sql, yaml_file, data



def find_composite_key(data: List[dict]) -> List[str]:
    """查找组合主键
    返回组成组合主键的字段名列表
    """
    if not data or not isinstance(data[0], dict):
        return []
        
    # 获取所有字段名
    fields = list(data[0].keys())
    
    def make_hashable(value: Any) -> Any:
        """将值转换为可哈希的类型"""
        if isinstance(value, (list, dict)):
            return json.dumps(value, sort_keys=True)
        return value
    
    # 从单个字段开始，逐渐增加字段组合
    for combination_size in range(1, len(fields) + 1):
        # 获取所有可能的字段组合
        for i in range(len(fields) - combination_size + 1):
            current_fields = fields[i:i + combination_size]
            
            # 检查当前字段组合是否构成唯一键
            combinations = set()
            is_unique = True
            has_null = False
            
            for item in data:
                # 获取当前组合的值并转换为可哈希类型
                combination = tuple(make_hashable(item.get(field)) for field in current_fields)
                
                # 检查是否有空值
                if None in combination:
                    has_null = True
                    break
                    
                # 检查是否重复
                if combination in combinations:
                    is_unique = False
                    break
                    
                combinations.add(combination)
            
            # 如果找到有效的组合主键，返回
            if is_unique and not has_null:
                return current_fields
                
    return []

def main():
    import argparse
    import concurrent.futures
    
    start_time = time.time()
    
    # 设置命令行参数
    parser = argparse.ArgumentParser(description='从YAML文件提取schema并生成Python类和SQLite数据库')
    parser.add_argument('-i', '--input', required=True, help='输入YAML文件夹路径')
    parser.add_argument('-p', '--python', help='输出Python模型文件路径')
    parser.add_argument('-d', '--database', help='输出SQLite数据库文件路径')
    parser.add_argument('-l', '--limit', type=int, help='限制处理的文件个数')
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.input):
        print(f"错误：'{args.input}' 不是一个有效的目录")
        sys.exit(1)
    
    yaml_files = glob.glob(os.path.join(args.input, "*.yaml"))
    yaml_files.extend(glob.glob(os.path.join(args.input, "*.yml")))
    
    if not yaml_files:
        print(f"警告：在 '{args.input}' 目录下没有找到YAML文件")
        sys.exit(0)

    if args.limit and args.limit > 0:
        yaml_files = yaml_files[:args.limit]
    
    print(f"找到 {len(yaml_files)} 个YAML文件\n")
    
    all_python_models = []
    all_sql_statements = []
    yaml_data = {}

    progress_columns = [
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("({task.completed}/{task.total})"),
        TimeElapsedColumn(),
    ]

    with Progress(*progress_columns) as progress:
        with concurrent.futures.ProcessPoolExecutor(max_workers=10) as executor:
            
            overall_task = progress.add_task("[bold green]总进度", total=len(yaml_files))
            files_iter = iter(yaml_files)
            
            # Submit the first batch of tasks
            futures = {
                executor.submit(process_file_worker, f): 
                progress.add_task(os.path.basename(f))
                for f in itertools.islice(files_iter, 10) if f
            }
            
            while futures:
                done_future = next(concurrent.futures.as_completed(futures))
                
                task_id = futures.pop(done_future)
                
                python_model, sql, yaml_file, data = done_future.result()
                
                progress.remove_task(task_id)
                progress.update(overall_task, advance=1)

                yaml_data[yaml_file] = data
                if python_model and sql:
                    all_python_models.append(python_model)
                    all_sql_statements.append(sql)

                try:
                    new_file = next(files_iter)
                    new_future = executor.submit(process_file_worker, new_file)
                    new_task_id = progress.add_task(os.path.basename(new_file))
                    futures[new_future] = new_task_id
                except StopIteration:
                    pass

    if args.python:
        with open(args.python, 'w', encoding='utf-8') as f:
            f.write('####### AUTO GENERATED. DO NOT EDIT. #######\n')
            f.write('from dataclasses import dataclass\n')
            f.write('from typing import Optional, List, Any\n\n')
            f.write('\n\n'.join(all_python_models))
        print(f"\n成功生成Python模型文件：{args.python}")
    
    # 创建SQLite数据库和SQL文件
    if args.database:
        # 生成SQL文件
        # sql_file_path = os.path.splitext(args.database)[0] + '.sql'
        # with open(sql_file_path, 'w', encoding='utf-8') as f:
        #     for sql in all_sql_statements:
        #         if sql.strip():
        #             f.write(sql + ';\n\n')
        # print(f"成功生成SQL文件：{sql_file_path}")
        
        # 创建数据库
        create_sqlite_database(all_sql_statements, args.database)
        
        # 在创建数据库后添加以下代码
        print("\n开始插入数据...")
        with sqlite3.connect(args.database) as conn:
            with Progress(*progress_columns, transient=True) as progress:
                task = progress.add_task("插入数据中...", total=len(yaml_data))
                for yaml_file in yaml_data.keys():
                    table_name = os.path.splitext(os.path.basename(yaml_file))[0]
                    data = yaml_data[yaml_file]
                    if isinstance(data, list) and data:
                        try:
                            insert_data_to_sqlite(conn, table_name, data)
                        except Exception as e:
                            print(f"\n警告：插入数据到表 {table_name} 时出错：{str(e)}")
                    progress.update(task, advance=1)
        print("\n数据插入完成！")
        
    end_time = time.time()
    print(f"\n总耗时: {end_time - start_time:.2f} 秒") 
        
if __name__ == '__main__':
        
    main()
        