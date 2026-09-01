"""测试游戏数据更新机制：完整性校验 / staging 应用 / staging 下载 / 缓存失效。"""
import io
import sys
import types
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from kaa.game_data import updater


@pytest.fixture
def fake_prebuild_module(monkeypatch):
    """向 sys.modules 注入假的 kaa.image_db.prebuild，避免触发 kotonebot 导入链。

    download_to_staging 内部会 ``from kaa.image_db.prebuild import ...``，
    在本环境（kotonebot 开发版不兼容）无法真正导入该模块。
    """
    module = types.ModuleType("kaa.image_db.prebuild")
    module.build_image_dbs_from_staging = MagicMock(return_value=True)
    module.ensure_all_image_dbs_built = MagicMock(return_value=True)
    monkeypatch.setitem(sys.modules, "kaa.image_db.prebuild", module)
    return module


@pytest.fixture
def fake_paths(tmp_path, monkeypatch):
    """将 updater 模块内引用的路径函数替换为 tmp_path 下的目录。

    返回 (data_dir, cache_dir, staging_dir) 命名空间，便于测试构造数据。
    """
    data = tmp_path / "game_data"
    data.mkdir()
    cache = tmp_path / "cache"
    cache.mkdir()

    staging = data / ".staging"

    monkeypatch.setattr(updater, "game_db_path", lambda: data / "game.db")
    monkeypatch.setattr(updater, "sprites_path", lambda cat: data / cat)
    monkeypatch.setattr(updater, "version_path", lambda: data / "version.txt")
    monkeypatch.setattr(updater, "staging_dir", lambda: staging)
    monkeypatch.setattr(updater, "staging_complete_marker", lambda: staging / ".complete")
    monkeypatch.setattr(updater, "staging_game_db_path", lambda: staging / "game.db")
    monkeypatch.setattr(updater, "staging_sprites_path", lambda cat: staging / cat)
    monkeypatch.setattr(updater, "staging_version_path", lambda: staging / "version.txt")
    monkeypatch.setattr(updater, "staging_cache_dir", lambda: cache / ".staging")

    return SimpleNamespace(data=data, cache=cache, staging=staging)


@pytest.fixture
def fake_shared(tmp_path, monkeypatch):
    """将共享配置读写重定向到 tmp_path。"""
    import kaa.config.manager as config_manager

    monkeypatch.setattr(config_manager, "conf_dir", str(tmp_path / "conf"))
    monkeypatch.setattr(config_manager, "_shared", None)
    yield config_manager
    monkeypatch.setattr(config_manager, "_shared", None)


def _make_sprite_dir(base: Path, category: str, names: list[str]) -> None:
    d = base / category
    d.mkdir(parents=True, exist_ok=True)
    for name in names:
        (d / name).write_bytes(b"png")


# ── check_data_integrity ─────────────────────────────────────────────────────

def test_integrity_complete(fake_paths):
    """完整数据（game.db + version.txt + 各 sprite 目录）→ True。"""
    _write_valid_sqlite(fake_paths.data / "game.db")
    (fake_paths.data / "version.txt").write_text("v1")
    for cat in updater._CATEGORIES:
        (fake_paths.data / cat).mkdir(parents=True, exist_ok=True)
    assert updater.check_data_integrity() is True


def test_integrity_missing_db(fake_paths):
    """缺 game.db → False。"""
    (fake_paths.data / "version.txt").write_text("v1")
    for cat in updater._CATEGORIES:
        (fake_paths.data / cat).mkdir(parents=True, exist_ok=True)
    assert updater.check_data_integrity() is False


def test_integrity_tiny_db(fake_paths):
    """game.db 过小（<1024 字节）→ False。"""
    (fake_paths.data / "game.db").write_bytes(b"\x00")
    (fake_paths.data / "version.txt").write_text("v1")
    for cat in updater._CATEGORIES:
        (fake_paths.data / cat).mkdir(parents=True, exist_ok=True)
    assert updater.check_data_integrity() is False


def test_integrity_corrupt_db(fake_paths):
    """game.db 非 SQLite（无法打开）→ False。"""
    (fake_paths.data / "game.db").write_bytes(b"SQLite format 3\x00" + b"garbage" * 400)
    (fake_paths.data / "version.txt").write_text("v1")
    for cat in updater._CATEGORIES:
        (fake_paths.data / cat).mkdir(parents=True, exist_ok=True)
    assert updater.check_data_integrity() is False


def test_integrity_missing_version(fake_paths):
    """缺 version.txt → False。"""
    (fake_paths.data / "game.db").write_bytes(b"\x00" * 2048)
    for cat in updater._CATEGORIES:
        (fake_paths.data / cat).mkdir(parents=True, exist_ok=True)
    assert updater.check_data_integrity() is False


def test_integrity_missing_sprite(fake_paths):
    """缺 sprite 目录 → False。"""
    (fake_paths.data / "game.db").write_bytes(b"\x00" * 2048)
    (fake_paths.data / "version.txt").write_text("v1")
    (fake_paths.data / updater._CATEGORIES[0]).mkdir(parents=True, exist_ok=True)
    assert updater.check_data_integrity() is False


def test_integrity_missing_required_tables(fake_paths):
    """game.db 可读但缺少关键表（旧/不完整 dump）→ False。"""
    _write_valid_sqlite(fake_paths.data / "game.db", with_required_tables=False)
    (fake_paths.data / "version.txt").write_text("v1")
    for cat in updater._CATEGORIES:
        (fake_paths.data / cat).mkdir(parents=True, exist_ok=True)
    assert updater.check_data_integrity() is False


def test_has_usable_baseline_requires_tables(fake_paths):
    """has_usable_baseline 同样要求关键表存在。"""
    db = fake_paths.data / "game.db"
    _write_valid_sqlite(db, with_required_tables=False)
    assert updater.has_usable_baseline() is False
    db.unlink()
    _write_valid_sqlite(db, with_required_tables=True)
    assert updater.has_usable_baseline() is True


# ── apply_pending ────────────────────────────────────────────────────────────

def _write_valid_sqlite(path: Path, *, with_required_tables: bool = True) -> None:
    """写入合法的 SQLite 文件。

    :param with_required_tables: 是否创建运行依赖的关键表（见
        updater._REQUIRED_DB_TABLES）。为 False 时模拟旧/不完整 dump。
    """
    import sqlite3
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    if with_required_tables:
        for table in updater._REQUIRED_DB_TABLES:
            conn.execute(f"CREATE TABLE {table} (id TEXT PRIMARY KEY)")
    conn.execute("INSERT INTO t VALUES (1)")
    conn.commit()
    conn.close()


def _make_complete_staging(fake_paths, version="v2") -> None:
    staging = fake_paths.staging
    staging.mkdir(parents=True, exist_ok=True)
    _write_valid_sqlite(staging / "game.db")
    for cat in updater._CATEGORIES:
        _make_sprite_dir(staging, cat, [f"{cat}_a.png"])
    (staging / "version.txt").write_text(version)
    (staging / ".complete").touch()


def test_apply_staging_complete(fake_paths, fake_shared):
    """有 .complete → 替换活跃数据、写版本、清除 pending_version，返回 True。"""
    # 活跃数据旧版本
    _write_valid_sqlite(fake_paths.data / "game.db")
    (fake_paths.data / "version.txt").write_text("v1")
    for cat in updater._CATEGORIES:
        _make_sprite_dir(fake_paths.data, cat, [f"{cat}_old.png"])

    shared = fake_shared.read_shared()
    shared.misc.game_data_pending_version = "v2"
    fake_shared.write_shared(shared)

    _make_complete_staging(fake_paths)

    with patch("kaa.game_data.updater.clear_db_caches") as clear_mock:
        result = updater.apply_pending()

    assert result is True
    # 活跃数据被替换为新版本
    assert (fake_paths.data / "version.txt").read_text() == "v2"
    assert (fake_paths.data / updater._CATEGORIES[0] / f"{updater._CATEGORIES[0]}_a.png").exists()
    assert not (fake_paths.data / updater._CATEGORIES[0] / f"{updater._CATEGORIES[0]}_old.png").exists()
    # staging 被删除
    assert not fake_paths.staging.exists()
    # pending_version 被清除
    assert fake_shared.read_shared().misc.game_data_pending_version is None
    clear_mock.assert_called_once()


def test_apply_staging_incomplete(fake_paths, fake_shared):
    """无 .complete → 清理 staging 残留，返回 False。"""
    _write_valid_sqlite(fake_paths.data / "game.db")
    (fake_paths.data / "version.txt").write_text("v1")
    for cat in updater._CATEGORIES:
        _make_sprite_dir(fake_paths.data, cat, [])

    # 残留的不完整 staging
    fake_paths.staging.mkdir(parents=True, exist_ok=True)
    (fake_paths.staging / "game.db").write_bytes(b"partial")
    (fake_paths.cache / ".staging").mkdir(parents=True, exist_ok=True)
    (fake_paths.cache / ".staging" / "dummy").write_bytes(b"x")

    result = updater.apply_pending()

    assert result is False
    assert not fake_paths.staging.exists()
    assert not (fake_paths.cache / ".staging").exists()
    # 活跃数据未被动过
    assert (fake_paths.data / "version.txt").read_text() == "v1"


def test_apply_staging_absent(fake_paths):
    """staging 不存在 → 返回 False。"""
    result = updater.apply_pending()
    assert result is False


# ── download_to_staging ──────────────────────────────────────────────────────

def _make_check_result(needs_db=True, categories_missing=None, version="v3", needs_update=True):
    categories_missing = categories_missing or {"idol_cards": {"a.png"}}
    mirror = SimpleNamespace(make_url=lambda p: f"https://mirror/{p}")
    manifest = SimpleNamespace(version=version)
    return SimpleNamespace(
        mirror=mirror,
        manifest=manifest,
        needs_db=needs_db,
        category_missing=categories_missing,
        needs_update=needs_update,
        auto_update_enabled=True,
    )


def _zst_bytes(data: bytes) -> bytes:
    import zstandard
    return zstandard.ZstdCompressor().compress(data)


def test_download_to_staging_structure(fake_paths, fake_shared, fake_prebuild_module):
    """download_to_staging → 目录结构正确、.complete 最后写入、pending 设置。"""
    result = _make_check_result()

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as z:
        z.writestr("idol_cards/a.png", b"pngdata")
    zip_bytes = zip_buf.getvalue()

    def fake_download(url, **kwargs):
        if url.endswith("game.db.zst"):
            return _zst_bytes(b"\x00" * 2048)
        if url.endswith("idol_cards.zip"):
            return zip_bytes
        raise AssertionError(f"unexpected url: {url}")

    with patch("kaa.game_data.updater._download", side_effect=fake_download):
        updater.GameDataUpdater().download_to_staging(result)

    staging = fake_paths.staging
    # 目录结构
    assert (staging / "game.db").exists()
    assert (staging / "idol_cards" / "a.png").read_bytes() == b"pngdata"
    assert (staging / "version.txt").read_text() == "v3"
    assert (staging / ".complete").exists()
    # 活跃数据未被修改
    assert not (fake_paths.data / "game.db").exists()
    # 图像索引从 staging 构建
    fake_prebuild_module.build_image_dbs_from_staging.assert_called_once()
    # pending_version 被设置
    assert fake_shared.read_shared().misc.game_data_pending_version == "v3"


def test_download_to_staging_cancel(fake_paths, fake_shared, fake_prebuild_module):
    """下载中断（_download 抛 GameDataUpdateCancelled）→ staging 不完整，无 .complete。"""
    from kaa.game_data.updater import GameDataUpdateCancelled

    result = _make_check_result()

    def fake_download(url, **kwargs):
        raise GameDataUpdateCancelled()

    with patch("kaa.game_data.updater._download", side_effect=fake_download):
        with pytest.raises(GameDataUpdateCancelled):
            updater.GameDataUpdater().download_to_staging(result)

    assert not (fake_paths.staging / ".complete").exists()
    assert fake_shared.read_shared().misc.game_data_pending_version is None


def test_cleanup_staging(fake_paths):
    """_cleanup_staging 删除不完整 staging。"""
    fake_paths.staging.mkdir(parents=True, exist_ok=True)
    (fake_paths.staging / "game.db").write_bytes(b"partial")
    (fake_paths.cache / ".staging").mkdir(parents=True, exist_ok=True)
    (fake_paths.cache / ".staging" / "dummy").write_bytes(b"x")

    updater.GameDataUpdater._cleanup_staging()

    assert not fake_paths.staging.exists()
    assert not (fake_paths.cache / ".staging").exists()


# ── check_and_update（统一下载路径：staging → 立即 apply） ───────────────────

def test_check_and_update_unified(fake_paths, fake_shared, fake_prebuild_module, monkeypatch):
    """check_and_update 阻塞路径：下载到 staging 后立即 apply，活跃数据被替换。"""
    from kaa.game_data.updater import GameDataUpdater, UpdateOutcome

    result = _make_check_result(needs_db=True, categories_missing={"idol_cards": {"a.png"}}, version="v3")
    # check_only 被 mock，避免真实探测镜像 / 解析 manifest
    monkeypatch.setattr(updater.GameDataUpdater, "check_only", lambda self, progress_cb=None: result)

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as z:
        z.writestr("idol_cards/a.png", b"pngdata")
    zip_bytes = zip_buf.getvalue()

    def fake_download(url, **kwargs):
        if url.endswith("game.db.zst"):
            return _zst_bytes(b"\x00" * 2048)
        if url.endswith("idol_cards.zip"):
            return zip_bytes
        raise AssertionError(f"unexpected url: {url}")

    with patch("kaa.game_data.updater._download", side_effect=fake_download):
        with patch("kaa.game_data.updater.clear_db_caches") as clear_mock:
            outcome = GameDataUpdater().check_and_update()

    assert outcome is UpdateOutcome.UPDATED
    # 活跃数据已被替换为新版本
    assert (fake_paths.data / "game.db").exists()
    assert (fake_paths.data / "version.txt").read_text() == "v3"
    assert (fake_paths.data / "idol_cards" / "a.png").read_bytes() == b"pngdata"
    # staging 已删除、pending_version 已清除
    assert not fake_paths.staging.exists()
    assert fake_shared.read_shared().misc.game_data_pending_version is None
    # 图像索引构建回调与 clear_db_caches 均被触发
    fake_prebuild_module.build_image_dbs_from_staging.assert_called_once()
    clear_mock.assert_called_once()


def test_check_and_update_cancelled(fake_paths, fake_shared, fake_prebuild_module, monkeypatch):
    """check_and_update 下载被取消 → 清理 staging，返回 CANCELLED。"""
    from kaa.game_data.updater import GameDataUpdater, GameDataUpdateCancelled, UpdateOutcome

    result = _make_check_result(needs_db=True, categories_missing={"idol_cards": {"a.png"}}, version="v3")
    monkeypatch.setattr(updater.GameDataUpdater, "check_only", lambda self, progress_cb=None: result)

    def fake_download(url, **kwargs):
        raise GameDataUpdateCancelled()

    with patch("kaa.game_data.updater._download", side_effect=fake_download):
        outcome = GameDataUpdater().check_and_update()

    assert outcome is UpdateOutcome.CANCELLED
    assert not fake_paths.staging.exists()
    assert fake_shared.read_shared().misc.game_data_pending_version is None


# ── check_only 版本号一致但 db 不符 ──────────────────────────────────────────

class _FakeManifest:
    """check_only 所需的 manifest 最小实现。"""

    def __init__(self, version: str, files: dict) -> None:
        self.version = version
        self.files = files

    def get_category_files(self, category: str) -> dict:
        prefix = category + '/'
        return {
            k[len(prefix):]: v
            for k, v in self.files.items()
            if k.startswith(prefix)
        }


def test_check_only_version_match_db_mismatch(fake_paths, monkeypatch):
    """版本号一致但本地 game.db 与 manifest 不符 → needs_update=True。"""
    from kaa.game_data.updater import GameDataUpdater

    _write_valid_sqlite(fake_paths.data / "game.db")
    (fake_paths.data / "version.txt").write_text("v1")

    mirror = SimpleNamespace(make_url=lambda p: f"https://mirror/{p}")
    manifest = _FakeManifest(
        version="v1",
        files={"game.db": SimpleNamespace(md5="x" * 32, size=1)},
    )
    monkeypatch.setattr(updater, "_select_mirror", lambda log_cb=None: mirror)
    monkeypatch.setattr(updater, "_download", lambda url, **kw: b"manifest")
    monkeypatch.setattr(updater, "parse_manifest", lambda data: manifest)

    result = GameDataUpdater().check_only()

    assert result is not None
    assert result.needs_update is True
    assert result.needs_db is True


def test_check_only_version_match_db_ok(fake_paths, monkeypatch):
    """版本号一致且 game.db 与 manifest 一致 → needs_update=False（不重下）。"""
    from kaa.game_data.updater import GameDataUpdater

    _write_valid_sqlite(fake_paths.data / "game.db")
    (fake_paths.data / "version.txt").write_text("v1")

    # 用真实 _md5 计算本地 db 的指纹作为 manifest md5
    db_md5 = updater._md5(fake_paths.data / "game.db")
    mirror = SimpleNamespace(make_url=lambda p: f"https://mirror/{p}")
    manifest = _FakeManifest(
        version="v1",
        files={"game.db": SimpleNamespace(md5=db_md5, size=1)},
    )
    monkeypatch.setattr(updater, "_select_mirror", lambda log_cb=None: mirror)
    monkeypatch.setattr(updater, "_download", lambda url, **kw: b"manifest")
    monkeypatch.setattr(updater, "parse_manifest", lambda data: manifest)

    result = GameDataUpdater().check_only()

    assert result is not None
    assert result.needs_update is False
    assert result.needs_db is False


# ── P0: skill_card_index 缓存失效 ───────────────────────────────────────────

def test_skill_card_index_cleared_by_clear_db_caches(tmp_path, monkeypatch):
    """clear_db_caches() 后 skill_card_index 重新扫描。"""
    import kaa.game_data.paths as paths
    from kaa.db._util import clear_db_caches

    sprite_dir = tmp_path / "skill_cards"
    sprite_dir.mkdir(parents=True)
    monkeypatch.setattr(paths, "sprites_path", lambda cat: sprite_dir if cat == "skill_cards" else tmp_path / cat)
    monkeypatch.setattr(paths, "_CHAR_IDS", frozenset({"fktn"}))

    (sprite_dir / "img_general_skillcard_act-0_001-fktn.png").write_bytes(b"x")

    idx1 = paths.skill_card_index()
    assert "img_general_skillcard_act-0_001-fktn" in idx1.exact

    # 新增 sprite
    (sprite_dir / "img_general_skillcard_act-0_002-fktn.png").write_bytes(b"x")

    # 未清缓存前仍为旧索引
    idx2 = paths.skill_card_index()
    assert "img_general_skillcard_act-0_002-fktn" not in idx2.exact

    # 清缓存后重新扫描
    clear_db_caches()
    idx3 = paths.skill_card_index()
    assert "img_general_skillcard_act-0_002-fktn" in idx3.exact

    # 恢复，避免影响其它测试
    paths.skill_card_index.cache_clear()
