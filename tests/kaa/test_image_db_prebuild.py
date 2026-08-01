"""测试图像索引重构：ensure_all_image_dbs_built 支持指定源/缓存目录。

本模块会 stub 掉触发 kotonebot 导入链的包（kaa.game_ui / kaa.tasks），
从而在开发环境下也能直接测试 prebuild 的真实逻辑。
"""
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _stub_package(name: str) -> types.ModuleType:
    """在 sys.modules 插入空的父包，避免真实导入。"""
    mod = types.ModuleType(name)
    mod.__path__ = []
    sys.modules[name] = mod
    return mod


@pytest.fixture(autouse=True)
def _stub_kotonebot_deps(monkeypatch):
    """将 prebuild 依赖的四个 build_db 来源 stub 为可记录的 MagicMock。"""
    # 父包全部 stub 掉
    for pkg in ("kaa.tasks", "kaa.tasks.produce", "kaa.tasks.produce.new",
                "kaa.tasks.produce.new.play_cards", "kaa.game_ui"):
        _stub_package(pkg)

    # 叶子模块：带 build_db 函数
    def make_leaf(name):
        mod = types.ModuleType(name)
        mod.build_db = MagicMock()
        sys.modules[name] = mod
        return mod

    make_leaf("kaa.game_ui.idols_overview")
    make_leaf("kaa.game_ui.drinks_overview")
    make_leaf("kaa.game_ui.skill_card_select")
    make_leaf("kaa.tasks.produce.new.play_cards.ui")

    # 先触发 kaa.db 的导入链，再导入 prebuild，
    # 避免 kaa.game_data.paths 被首先导入时形成循环导入（既有行为）
    import kaa.db.sqlite  # noqa: F401

    import kaa.image_db.prebuild as prebuild
    monkeypatch.setitem(sys.modules, "kaa.image_db.prebuild", prebuild)
    yield prebuild

    # 清理 stub，避免污染其它测试
    for name in list(sys.modules):
        if name.startswith(("kaa.tasks", "kaa.game_ui")) and "kaa.game_data" not in name:
            del sys.modules[name]


def test_builders_have_resource_category(_stub_kotonebot_deps):
    """_BUILDERS 元组包含 resource_category 字段。"""
    prebuild = _stub_kotonebot_deps
    assert all(len(b) == 4 for b in prebuild._BUILDERS)
    by_name = {b[0]: b for b in prebuild._BUILDERS}
    assert by_name["idols"][1] == "idol_cards"
    assert by_name["skill_cards"][1] == "skill_cards"
    assert by_name["skill_cards_dialog"][1] == "skill_cards"


def test_ensure_all_default(tmp_path, _stub_kotonebot_deps):
    """无 source_base/cache_base → 使用默认源/缓存目录（回归）。"""
    prebuild = _stub_kotonebot_deps
    # 默认缓存目录在真实 cache/ 下，测试时不强制删除
    ok = prebuild.ensure_all_image_dbs_built(force=False)
    assert ok is True
    for name, res_cat, cache_key, build_fn in prebuild._BUILDERS:
        build_fn.assert_called_once()
        kwargs = build_fn.call_args.kwargs
        assert kwargs["source_dir"] is None
        assert kwargs["cache_dir"] is None


def test_ensure_all_from_staging(tmp_path, _stub_kotonebot_deps):
    """指定 source_base/cache_base → 构建到 staging，且 force=True 时删除已有缓存。"""
    prebuild = _stub_kotonebot_deps
    source_base = tmp_path / "staging"
    cache_base = tmp_path / "cache"
    source_base.mkdir()
    for res_cat in ("idol_cards", "skill_cards", "drinks"):
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
    for name, res_cat, cache_key, build_fn in prebuild._BUILDERS:
        kwargs = build_fn.call_args.kwargs
        assert kwargs["source_dir"] == str(source_base / res_cat)
        assert kwargs["cache_dir"] == str(cache_base / cache_key)


def test_build_image_dbs_from_staging(tmp_path, _stub_kotonebot_deps):
    """build_image_dbs_from_staging 委托给 ensure_all_image_dbs_built。"""
    prebuild = _stub_kotonebot_deps
    source_base = tmp_path / "staging"
    cache_base = tmp_path / "cache"
    source_base.mkdir()

    real = prebuild.ensure_all_image_dbs_built
    calls = []
    prebuild.ensure_all_image_dbs_built = lambda **kw: calls.append(kw) or True
    try:
        prebuild.build_image_dbs_from_staging(source_base, cache_base)
    finally:
        prebuild.ensure_all_image_dbs_built = real

    assert len(calls) == 1
    kw = calls[0]
    assert kw["source_base"] == source_base
    assert kw["cache_base"] == cache_base
    assert kw["force"] is True
