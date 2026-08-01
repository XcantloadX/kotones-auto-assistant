"""测试图像索引预构建：基于注册中心（registry.REGISTRY）的 ensure_all_image_dbs_built。

``registry._build_spec`` 被 stub 掉，避免触发 kotonebot 导入链，
从而在开发环境下也能直接测试 prebuild 的真实逻辑。
"""
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import kaa.image_db.registry as registry
import kaa.image_db.prebuild as prebuild


@pytest.fixture
def fake_build_spec(monkeypatch):
    """stub registry._build_spec，记录每次调用的 (spec, source_dir, cache_dir, progress_cb)。"""
    calls = []

    def _fake(spec, source_dir=None, cache_dir=None, *, progress_cb=None):
        calls.append((spec, source_dir, cache_dir, progress_cb))
        return MagicMock()

    monkeypatch.setattr(registry, "_build_spec", _fake)
    return calls


def test_registry_specs():
    """REGISTRY 包含预期的四个数据库规格。"""
    by_name = {s.name: s for s in registry.REGISTRY}
    assert set(by_name) == {'idols', 'drinks', 'skill_cards', 'skill_cards_dialog'}
    assert by_name['idols'].resource_category == 'idol_cards'
    assert by_name['skill_cards'].resource_category == 'skill_cards'
    assert by_name['skill_cards_dialog'].resource_category == 'skill_cards'
    # 技能卡数据库类经懒加载工厂提供（避免模块级触发 kotonebot）
    assert by_name['skill_cards'].db_class is not None


def test_all_cache_keys_and_categories():
    """缓存 key 与资源分类派生自 REGISTRY，去重保序。"""
    assert registry.all_cache_keys() == ('idols', 'drinks', 'skill_cards', 'skill_cards_dialog')
    assert registry.all_resource_categories() == ('idol_cards', 'drinks', 'skill_cards')


def test_ensure_all_default(fake_build_spec):
    """无 source_base/cache_base → 每个 spec 以 None 源/缓存目录调用 _build_spec。"""
    ok = prebuild.ensure_all_image_dbs_built(force=False)
    assert ok is True
    assert [c[0] for c in fake_build_spec] == list(registry.REGISTRY)
    for _, source_dir, cache_dir, _ in fake_build_spec:
        assert source_dir is None
        assert cache_dir is None


def test_ensure_all_from_staging(tmp_path, fake_build_spec):
    """指定 source_base/cache_base → 映射到各 spec 的源/缓存目录，且 force 删除已有缓存。"""
    source_base = tmp_path / "staging"
    cache_base = tmp_path / "cache"
    source_base.mkdir()
    for res_cat in registry.all_resource_categories():
        (source_base / res_cat).mkdir(parents=True)
    # 预置一个会被 force 删除的缓存目录
    stale = cache_base / "idols"
    stale.mkdir(parents=True)
    (stale / "meta.pkl").write_bytes(b"stale")

    ok = prebuild.ensure_all_image_dbs_built(
        force=True,
        source_base=source_base,
        cache_base=cache_base,
    )
    assert ok is True
    assert not stale.exists()
    assert len(fake_build_spec) == len(registry.REGISTRY)
    for (spec, source_dir, cache_dir, _), expected in zip(fake_build_spec, registry.REGISTRY):
        assert spec is expected
        assert source_dir == str(source_base / spec.resource_category)
        assert cache_dir == str(cache_base / spec.cache_key)


def test_build_image_dbs_from_staging(fake_build_spec):
    """build_image_dbs_from_staging 委托 ensure_all_image_dbs_built 且 force=True。"""
    source_base = Path("staging")
    cache_base = Path("cache")
    ok = prebuild.build_image_dbs_from_staging(source_base, cache_base)
    assert ok is True
    assert len(fake_build_spec) == len(registry.REGISTRY)
    for spec, source_dir, cache_dir, _ in fake_build_spec:
        assert source_dir == str(source_base / spec.resource_category)
        assert cache_dir == str(cache_base / spec.cache_key)
