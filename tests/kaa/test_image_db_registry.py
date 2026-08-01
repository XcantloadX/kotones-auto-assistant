"""测试图像数据库注册中心（registry）：规格查询、缓存 key、懒加载实例缓存。

registry 模块级只依赖标准库，本测试不触发 kotonebot 导入链。
"""
from unittest.mock import MagicMock

import pytest

import kaa.image_db.registry as registry


@pytest.fixture(autouse=True)
def _clear_dbs():
    """清理模块级实例缓存，避免测试间互相影响。"""
    registry.invalidate_all()
    yield
    registry.invalidate_all()


def test_all_cache_keys():
    assert registry.all_cache_keys() == ('idols', 'drinks', 'skill_cards', 'skill_cards_dialog')


def test_all_resource_categories():
    assert registry.all_resource_categories() == ('idol_cards', 'drinks', 'skill_cards')


def test_get_spec():
    assert registry.get_spec('idols').cache_key == 'idols'
    assert registry.get_spec('skill_cards').db_class is not None
    with pytest.raises(KeyError):
        registry.get_spec('not_exist')


def test_get_db_default_cached(monkeypatch):
    """默认路径走缓存：同一 name 只构建一次。"""
    calls = []
    built = MagicMock()
    monkeypatch.setattr(
        registry, "_build_spec",
        lambda spec, source_dir=None, cache_dir=None, *, progress_cb=None:
            calls.append((spec.name, source_dir, cache_dir)) or built,
    )

    db1 = registry.get_db('idols')
    db2 = registry.get_db('idols')
    assert db1 is db2
    assert [c[0] for c in calls] == ['idols']


def test_get_db_custom_path_bypasses_cache(monkeypatch):
    """指定自定义路径不走缓存：每次调用都会重新构建。"""
    calls = []
    monkeypatch.setattr(
        registry, "_build_spec",
        lambda spec, source_dir=None, cache_dir=None, *, progress_cb=None:
            calls.append((spec.name, source_dir, cache_dir)) or MagicMock(),
    )

    registry.get_db('idols', source_dir='s', cache_dir='c')
    registry.get_db('idols', source_dir='s', cache_dir='c')
    assert len(calls) == 2


def test_invalidate_all(monkeypatch):
    """invalidate_all 后再次 get_db 会重新构建。"""
    calls = []
    monkeypatch.setattr(
        registry, "_build_spec",
        lambda spec, source_dir=None, cache_dir=None, *, progress_cb=None:
            calls.append(spec.name) or MagicMock(),
    )

    registry.get_db('drinks')
    registry.invalidate_all()
    registry.get_db('drinks')
    assert calls == ['drinks', 'drinks']
