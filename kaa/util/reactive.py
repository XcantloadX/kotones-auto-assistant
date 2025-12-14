from typing import TypeVar, Generic, Any, Callable, Optional, cast

# T: 原始对象的类型 (Root)
# V: 属性值的类型 (Leaf)
T = TypeVar("T")
V = TypeVar("V")

class PathRecorder(Generic[T]):
    """
    记录路径操作（属性访问 或 索引访问）
    """
    # FIX: 显式声明 path 可以为 None
    def __init__(self, root: Any = None, path: Optional[list[tuple[str, Any]]] = None):
        self._root = root
        # path 存储操作记录: ('attr', 'name') 或 ('item', 'key')
        self._path: list[tuple[str, Any]] = path if path is not None else []

    def __getattr__(self, name: str) -> "PathRecorder":
        # 记录 .attr 操作
        return PathRecorder(self._root, self._path + [('attr', name)])
    
    def __getitem__(self, key: Any) -> "PathRecorder":
        # 记录 [key] 操作
        return PathRecorder(self._root, self._path + [('item', key)])

    # 内部接口
    def _get_recorder_info(self) -> tuple[Any, list[tuple[str, Any]]]:
        return self._root, self._path

def of(obj: T) -> T:
    """
    Proxy 入口。类型标记返回 T 以获得 IDE 提示，运行时返回 Recorder。
    """
    return cast(T, PathRecorder(root=obj))

def _traverse(target: Any, path: list[tuple[str, Any]]) -> tuple[Any, str, Any]:
    """
    辅助函数：遍历路径，返回 (parent_container, last_op_type, last_key)
    """
    current = target
    
    # 遍历直到倒数第二个节点（获取父容器）
    for op_type, key in path[:-1]:
        if op_type == 'attr':
            current = getattr(current, key)
        elif op_type == 'item':
            current = current[key]
    
    # 获取最后一个操作的信息
    last_op, last_key = path[-1]
    return current, last_op, last_key

def getter(proxy: V) -> Callable[[], V]:
    """
    创建一个 getter 函数。
    """
    # 运行时检查
    if not isinstance(proxy, PathRecorder):
        raise TypeError("getter argument must be a proxy object created by of()")

    # 显式转换类型以通过静态检查
    recorder = cast(PathRecorder, proxy)
    root, path = recorder._get_recorder_info()
    
    if not path:
        return lambda: cast(V, root)

    def _getter_impl() -> V:
        parent, last_op, last_key = _traverse(root, path)
        
        if last_op == 'attr':
            return getattr(parent, last_key)
        elif last_op == 'item':
            return parent[last_key]
        
        # FIX: 抛出异常而不是返回 None，以满足返回类型 V
        raise ValueError(f"Unknown operation type: {last_op}")

    return _getter_impl

def setter(proxy: V) -> Callable[[V], None]:
    """
    创建一个 setter 函数。
    """
    if not isinstance(proxy, PathRecorder):
        raise TypeError("setter argument must be a proxy object created by of()")

    recorder = cast(PathRecorder, proxy)
    root, path = recorder._get_recorder_info()
    
    if not path:
        raise ValueError("Cannot set root object directly")

    def _setter_impl(value: V) -> None:
        parent, last_op, last_key = _traverse(root, path)
        
        if last_op == 'attr':
            setattr(parent, last_key, value)
        elif last_op == 'item':
            parent[last_key] = value
        else:
             raise ValueError(f"Unknown operation type: {last_op}")

    return _setter_impl

class Ref(Generic[T]):
    """
    持有对特定数据路径的引用，支持读写。
    Ref 接收一个 path recorder 代理对象。
    """
    def __init__(self, proxy: T):
        self._getter_fn = getter(proxy)
        self._setter_fn = setter(proxy)

    @property
    def value(self) -> T:
        return self._getter_fn()
    
    @value.setter
    def value(self, new_value: T) -> None:
        self._setter_fn(new_value)

def ref(proxy: T) -> Ref[T]:
    """
    创建一个引用对象 (Ref)，用于直接读写路径记录器的目标值。
    
    Example:
        name_ref = ref(of(user).name)
        name_ref.value = "Bob"
    """
    return Ref(proxy)

if __name__ == "__main__":
    class Address:
        def __init__(self, city):
            self.city = city
        def __repr__(self):
            return f"Address(city='{self.city}')"

    class User:
        def __init__(self, name, city):
            self.name = name
            self.addresses = {"home": Address(city)}
        def __repr__(self):
            return f"User(name='{self.name}', addresses={self.addresses})"

    data = User("Alice", "New York")
    print(f"Original Data: {data}")

    # 1. 测试 Getter (混合 属性 和 字典索引)
    get_city = getter(of(data).addresses["home"].city)
    print(f"Getter result: {get_city()}")  # Output: New York

    # 2. 测试 Setter
    set_city = setter(of(data).addresses["home"].city)
    set_city("San Francisco")
    print(f"After Setter: {data.addresses['home'].city}")  # Output: San Francisco

    # 3. 测试 Ref (引用)
    print("-" * 30)
    print("Testing Ref...")
    
    # 创建一个指向 user.name 的 Ref
    name_ref = ref(of(data).name)
    
    print(f"Ref initial value: {name_ref.value}") # Alice

    # 修改 Ref，应该影响原始对象
    name_ref.value = "Bob"
    print(f"Ref value set to 'Bob'.")
    print(f"Original object name: {data.name}") # Bob
    
    # 修改原始对象，Ref 应该能感知
    data.name = "Charlie"
    print(f"Original object name set to 'Charlie'.")
    print(f"Ref value: {name_ref.value}") # Charlie

    # 复杂路径 Ref
    city_ref = ref(of(data).addresses["home"].city)
    print(f"City Ref value: {city_ref.value}") # San Francisco
    city_ref.value = "Tokyo"
    print(f"City Ref set to 'Tokyo'. Original: {data.addresses['home'].city}")
