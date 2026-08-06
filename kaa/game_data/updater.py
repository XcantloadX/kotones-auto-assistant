import concurrent.futures
import hashlib
import io
import logging
import os
import shutil
import sqlite3
import threading
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from kaa.config.shared import SharedMiscConfig

import requests
import zstandard

from kaa.db._util import clear_db_caches
from kaa.db.sqlite import invalidate_connections
from kaa.image_db.registry import all_cache_keys, all_resource_categories
from .manifest import Manifest, parse as parse_manifest
from .paths import (
    game_db_path, sprites_path, version_path,
    staging_dir, staging_complete_marker, staging_game_db_path,
    staging_sprites_path, staging_version_path, staging_cache_dir,
)

logger = logging.getLogger(__name__)

# 资源分类与图像缓存 key 派生自图像数据库注册中心（单一事实来源）
_CATEGORIES = all_resource_categories()
_IMAGE_CACHE_KEYS = all_cache_keys()

# 运行依赖的关键表：缺失时判定数据不完整（阻止旧/不完整 dump 注入）。
# 参照 kaa/db 下实际查询的 game.db 表。
_REQUIRED_DB_TABLES = frozenset({
    'ProduceCard',
    'ProduceExamEffect',
    'IdolCard',
    'SupportCard',
    'ProduceDrink',
    'EffectGroup',
})

# 不读取系统代理：镜像站本身就是代理，叠加系统代理会导致 SSL 握手失败
_session = requests.Session()
_session.trust_env = False

# ── 镜像定义 ──────────────────────────────────────────────────────────────────

_OWNER = "kotonebot"
_REPO  = "kaa-game-data"
_RELEASE_SUBPATH = f"{_OWNER}/{_REPO}/releases/latest/download"

def _github(path: str) -> str:
    """直连 GitHub Releases。"""
    return f"https://github.com/{_RELEASE_SUBPATH}/{path}"

def _prefix_proxy(base: str) -> Callable[[str], str]:
    """前缀代理风格：{proxy}/https://github.com/…"""
    def build(path: str) -> str:
        return f"{base.rstrip('/')}/{_github(path)}"
    return build

@dataclass
class _Mirror:
    label: str
    make_url: Callable[[str], str]


# 只收录 URL 格式已知且近期可用的镜像。
# 探测时并发测试，选延迟最低且实际返回 2xx/3xx 的那个。
_BUILTIN_MIRRORS: list[_Mirror] = [
    _Mirror("直连 GitHub", _github),
    _Mirror("mirror.1ichika.de",  _prefix_proxy("https://mirror.1ichika.de")),
    _Mirror("ghfast.top",  _prefix_proxy("https://ghfast.top")),
]

# 进程级缓存（TTL 到期后重新探测）
_selected_mirror: Optional[_Mirror] = None
_mirror_selected_at: float = 0.0
_MIRROR_TTL_SECONDS = 300  # 5 分钟

# ── 结果 / 异常 ───────────────────────────────────────────────────────────────

class UpdateOutcome(Enum):
    NOT_NEEDED = "not_needed"
    SKIPPED_AUTO = "skipped_auto"
    UPDATED = "updated"
    CANCELLED = "cancelled"
    CHECK_FAILED = "check_failed"


class GameDataUpdateCancelled(Exception):
    """用户主动跳过本次下载/安装。"""


@dataclass
class CheckResult:
    mirror: _Mirror
    manifest: Manifest
    needs_update: bool
    auto_update_enabled: bool
    needs_db: bool
    category_missing: dict[str, set[str]]

# ── 镜像探测 ──────────────────────────────────────────────────────────────────

def _probe(mirror: _Mirror, timeout: float = 3.0) -> tuple[float, _Mirror]:
    """
    HEAD 请求探测镜像连通性。
    只接受 2xx/3xx（< 400）作为"可用"；4xx（含代理返回的 422）视为不可用。
    """
    url = mirror.make_url("manifest.json")
    t0 = time.monotonic()
    try:
        resp = _session.head(url, timeout=timeout, allow_redirects=True)
        if resp.status_code < 400:
            return time.monotonic() - t0, mirror
    except Exception:
        pass
    return float('inf'), mirror


def _select_mirror(log_cb: Optional[Callable[[str], None]] = None) -> Optional[_Mirror]:
    """
    并发探测所有内置镜像，返回延迟最低的可用镜像。
    结果按 TTL 进程级缓存，TTL 内直接返回；None 不缓存，下次调用重新探测。
    所有镜像均不可达时返回 None。
    """
    def log(msg: str):
        logger.info(msg)
        if log_cb:
            log_cb(msg)

    global _selected_mirror, _mirror_selected_at
    # 缓存有效且非 None 时直接返回
    if (_selected_mirror is not None
            and time.monotonic() - _mirror_selected_at < _MIRROR_TTL_SECONDS):
        return _selected_mirror

    log(f"正在探测 GitHub 镜像连通性（{len(_BUILTIN_MIRRORS)} 个候选）...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(_probe, m) for m in _BUILTIN_MIRRORS]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    results.sort(key=lambda r: r[0])
    best_latency, best_mirror = results[0]

    if best_latency == float('inf'):
        log("所有镜像均不可达，跳过更新")
        # 不缓存 None，下次调用会重新探测
        _selected_mirror = None
    else:
        log(f"选用镜像：{best_mirror.label}（延迟 {best_latency * 1000:.0f} ms）")
        _selected_mirror = best_mirror
        _mirror_selected_at = time.monotonic()

    return _selected_mirror

# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


# ── 配置访问（线程安全） ─────────────────────────────────────────────────────

_config_lock = threading.Lock()


def _update_misc(fn: Callable[['SharedMiscConfig'], None]) -> None:
    """线程安全地读取-修改-写回 shared misc 配置。

    :param fn: 对 ``SharedMiscConfig`` 执行修改的回调
    """
    from kaa.config import manager as config_manager
    with _config_lock:
        shared = config_manager.read_shared()
        fn(shared.misc)
        config_manager.write_shared(shared)


def _db_has_required_tables(db: Path) -> bool:
    """检查 game.db 是否包含运行所需的关键表。

    只查询 sqlite_master 元数据，不做全表扫描。旧版本或不完整 dump
    可能缺少新功能依赖的表（如 ProduceCard），需识别并触发重新下载。
    """
    if not db.exists() or db.stat().st_size < 1024:
        return False
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            rows = conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        finally:
            conn.close()
    except Exception:
        return False
    names = {r[0] for r in rows}
    return _REQUIRED_DB_TABLES.issubset(names)


def has_usable_baseline() -> bool:
    """本地是否已有可运行的 game.db 基线（允许跳过本次下载）。

    除文件可读外，还需包含运行依赖的关键表（见 _REQUIRED_DB_TABLES）。
    """
    db = game_db_path()
    if not db.exists() or db.stat().st_size < 1024:
        return False
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        conn.execute("SELECT 1")
        conn.close()
    except Exception:
        return False
    if not _db_has_required_tables(db):
        return False
    return True


def check_data_integrity() -> bool:
    """轻量检查本地数据是否完整可用，用于决定是否需要阻塞更新。

    检查项：game.db 存在且可读、包含关键表（_REQUIRED_DB_TABLES）、
    version.txt 存在、各 sprite 目录存在。
    注意：不做 md5 全量比对（那是 check_only 的职责），仅保证可运行。
    """
    db = game_db_path()
    if not db.exists() or db.stat().st_size < 1024:
        return False
    try:
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        # schema_version 读取数据库头，能识别非 SQLite / 损坏文件
        conn.execute("PRAGMA schema_version")
        conn.close()
    except Exception:
        return False
    if not _db_has_required_tables(db):
        return False
    if not version_path().exists():
        return False
    for cat in _CATEGORIES:
        if not sprites_path(cat).exists():
            return False
    return True


def apply_pending() -> bool:
    """启动时检查并应用 pending staging。返回是否实际应用了。

    流程：存在 .complete 标记 → 替换 game.db / sprite 目录 / 版本号 /
    图像索引 cache → 清理所有缓存 → 清除 pending_version → 删除 staging。
    无完整 staging 时清理残留并返回 False。

    崩溃恢复：如果应用中途崩溃（进程重启），此时 .complete 仍存在且
    ``pending_version`` 尚未清除，下次启动会重新应用（``os.replace`` 覆盖
    已替换的文件是幂等且安全的）。只有 ``pending_version`` 已清除后才
    删除 staging，避免删除后无法恢复。
    """
    staging = staging_dir()
    if not staging_complete_marker().exists():
        # 清理残留
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        sc = staging_cache_dir()
        if sc.exists():
            shutil.rmtree(sc, ignore_errors=True)
        return False

    # 1. 关闭 SQLite 连接
    invalidate_connections()

    # 2. 替换 game.db
    s_db = staging_game_db_path()
    if s_db.exists():
        os.replace(s_db, game_db_path())

    # 3. 替换 sprite 目录（整体替换）
    for category in _CATEGORIES:
        s_cat = staging_sprites_path(category)
        if s_cat.exists():
            active_cat = sprites_path(category)
            if active_cat.exists():
                shutil.rmtree(active_cat)
            os.replace(s_cat, active_cat)

    # 4. 写版本号
    version_path().write_text(staging_version_path().read_text())

    # 5. 替换 image DB cache
    s_cache = staging_cache_dir()
    if s_cache.exists():
        for cache_key in _IMAGE_CACHE_KEYS:
            staged = s_cache / cache_key
            if staged.exists():
                active = Path('./cache') / cache_key
                if active.exists():
                    shutil.rmtree(active)
                os.replace(staged, active)
        shutil.rmtree(s_cache, ignore_errors=True)

    # 6. 清理所有缓存（包含 skill_card_index.cache_clear）与内存中的图像数据库实例
    clear_db_caches()
    from kaa.image_db.registry import invalidate_all
    invalidate_all()

    # 7. 先清除 pending_version（幂等标记）
    _update_misc(lambda misc: setattr(misc, 'game_data_pending_version', None))

    # 8. 再删除 staging（此时即使崩溃也无影响，pending 已清）
    shutil.rmtree(staging, ignore_errors=True)

    return True


def _check_cancel(cancel: Optional[threading.Event]) -> None:
    if cancel is not None and cancel.is_set():
        raise GameDataUpdateCancelled()


_RETRYABLE = (
    requests.exceptions.ChunkedEncodingError,
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
)


def _download(
    url: str,
    max_retries: int = 5,
    log_cb: Optional[Callable[[str], None]] = None,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    cancel: Optional[threading.Event] = None,
) -> bytes:
    """下载 URL 内容，支持断点续传和指数退避重试。

    progress_cb(downloaded_bytes, total_bytes) 在每个 chunk 后调用。
    total_bytes 为完整文件大小（续传时也是全量值，不是剩余量）。
    cancel 仅在 Phase 2（安装下载）时传入；被取消时不重试。
    """
    buf = io.BytesIO()
    downloaded = 0
    size_logged = False

    for attempt in range(1, max_retries + 1):
        _check_cancel(cancel)
        try:
            headers = {'Range': f'bytes={downloaded}-'} if downloaded > 0 else {}
            resp = _session.get(url, stream=True, timeout=60, headers=headers)

            if resp.status_code == 206:
                # Content-Length 是剩余量，total 需加上已下载部分
                total = downloaded + int(resp.headers.get('content-length', 0))
            elif resp.status_code == 200:
                if downloaded > 0:
                    logger.warning("服务器不支持断点续传，重新下载")
                    buf = io.BytesIO()
                    downloaded = 0
                    size_logged = False
                resp.raise_for_status()
                total = int(resp.headers.get('content-length', 0))
            else:
                resp.raise_for_status()
                total = 0

            if not size_logged:
                if total and log_cb:
                    log_cb(f"文件大小: {total / 1024 / 1024:.1f} MB")
                size_logged = True

            for chunk in resp.iter_content(chunk_size=65536):
                _check_cancel(cancel)
                buf.write(chunk)
                downloaded += len(chunk)
                if progress_cb:
                    progress_cb(downloaded, total)

            buf.seek(0)
            return buf.read()

        except GameDataUpdateCancelled:
            raise
        except _RETRYABLE as e:
            if cancel is not None and cancel.is_set():
                raise GameDataUpdateCancelled() from e
            if attempt == max_retries:
                raise
            wait = 2 ** attempt  # 2, 4, 8, 16 秒
            logger.warning(
                "下载中断（第 %d/%d 次，已下载 %.1f MB），%ds 后重试: %s",
                attempt, max_retries, downloaded / 1024 / 1024, wait, e,
            )
            time.sleep(wait)

    raise RuntimeError(f"下载失败，已重试 {max_retries} 次")

# ── 检查时机 ──────────────────────────────────────────────────────────────────

def should_check(misc: 'SharedMiscConfig') -> bool:
    """根据配置的检查频率，判断当前是否需要检查游戏资源。"""
    if not version_path().exists():
        return True
    mode = misc.game_data_check
    if mode == 'manual':
        return False
    if mode == 'startup':
        return True
    last = misc.game_data_last_checked
    if last is None:
        return True
    try:
        last_dt = datetime.fromisoformat(last)
        # 若 last_dt 没有时区信息，当作本地时间处理
        if last_dt.tzinfo is None:
            now = datetime.now()
        else:
            now = datetime.now(timezone.utc)
        delta = now - last_dt
        if mode == 'daily':
            return delta.total_seconds() >= 86400
        if mode == 'weekly':
            return delta.total_seconds() >= 604800
    except ValueError:
        return True
    return True


# ── 更新器 ────────────────────────────────────────────────────────────────────

class GameDataUpdater:
    def __init__(self, cancel: Optional[threading.Event] = None) -> None:
        self._cancel = cancel

    def check_only(
        self,
        progress_cb: Optional[Callable[[str], None]] = None,
    ) -> Optional[CheckResult]:
        """
        Phase 1：镜像探测、拉取 manifest、版本比对、缺失文件计算。
        不可取消。检查失败时返回 None。
        """
        from kaa.config import manager as config_manager

        shared = config_manager.read_shared()

        def log(msg: str):
            logger.info(msg)

        mirror = _select_mirror(log_cb=progress_cb)
        if mirror is None:
            return None

        log("正在获取游戏数据版本信息...")
        try:
            manifest_bytes = _download(mirror.make_url('manifest.json'))
        except Exception as e:
            logger.warning("无法获取 manifest.json，跳过更新: %s", e)
            return None

        manifest = parse_manifest(manifest_bytes)

        ver_file = version_path()
        local_version = ver_file.read_text().strip() if ver_file.exists() else ""

        db_path = game_db_path()
        db_entry = manifest.files.get('game.db')
        needs_db = not db_path.exists() or (
            db_entry is not None and _md5(db_path) != db_entry.md5
        )

        # 版本号一致但本地 game.db 与 manifest 不符（旧/不完整 dump）时仍需更新
        if local_version == manifest.version and not needs_db:
            log("游戏数据已是最新版本")
            return CheckResult(
                mirror=mirror,
                manifest=manifest,
                needs_update=False,
                auto_update_enabled=shared.misc.game_data_auto_update,
                needs_db=False,
                category_missing={},
            )

        if local_version != manifest.version:
            log(f"发现新版本: {manifest.version[:8]}")
        else:
            log("版本号一致但 game.db 与清单不符，重新校验数据")

        category_missing: dict[str, set[str]] = {}
        for category in _CATEGORIES:
            cat_dir = sprites_path(category)
            cat_dir.mkdir(parents=True, exist_ok=True)
            cat_files = manifest.get_category_files(category)
            missing: set[str] = set()
            for fname, entry in cat_files.items():
                path = cat_dir / fname
                if not path.exists():
                    missing.add(fname)
                elif _md5(path) != entry.md5:
                    logger.warning("文件损坏（md5 不匹配），将重新下载: %s", fname)
                    missing.add(fname)
            category_missing[category] = missing

        return CheckResult(
            mirror=mirror,
            manifest=manifest,
            needs_update=True,
            auto_update_enabled=shared.misc.game_data_auto_update,
            needs_db=needs_db,
            category_missing=category_missing,
        )

    def _mark_checked(self) -> None:
        _update_misc(lambda misc: setattr(misc, 'game_data_last_checked',
                                          datetime.now().isoformat()))

    def download_to_staging(
        self,
        result: CheckResult,
        file_progress_cb: Optional[Callable[[str, int, int], None]] = None,
        build_started_cb: Optional[Callable[[], None]] = None,
        build_progress_cb: Optional[Callable[[int, int, str, int, int], None]] = None,
    ) -> None:
        """
        Phase 2：下载到 staging 目录（唯一下载路径）。

        下载完成后从 staging 构建图像索引到 staging cache，最后写入 .complete
        标记并设置 ``game_data_pending_version``。默认下次启动时由
        :func:`apply_pending` 原子替换活跃数据；阻塞路径可直接调用
        :func:`apply_pending` 内联应用。
        可通过 self._cancel 取消。

        :param build_started_cb: 进入图像索引构建阶段时调用
        :param build_progress_cb: 图像索引构建进度回调 (builder_index, total, name, file_cur, file_total)
        """
        from kaa.image_db.prebuild import build_image_dbs_from_staging

        def log(msg: str):
            logger.info(msg)

        def make_progress(name: str) -> Optional[Callable[[int, int], None]]:
            cb = file_progress_cb
            if cb is None:
                return None
            return lambda dl, total: cb(name, dl, total)

        mirror = result.mirror
        manifest = result.manifest
        needs_db = result.needs_db
        category_missing = result.category_missing

        staging = staging_dir()
        staging.mkdir(parents=True, exist_ok=True)

        log("开始下载到 staging...")

        # file_progress_cb 初始化
        if file_progress_cb:
            if needs_db:
                file_progress_cb('game.db.zst', 0, 0)
            for category, missing in category_missing.items():
                if missing:
                    file_progress_cb(f'{category}.zip', 0, 0)

        # 1. game.db
        if needs_db:
            _check_cancel(self._cancel)
            log("正在下载 game.db.zst ...")
            zst_bytes = _download(
                mirror.make_url('game.db.zst'),
                log_cb=log,
                progress_cb=make_progress('game.db.zst'),
                cancel=self._cancel,
            )
            _check_cancel(self._cancel)
            log("正在解压 game.db ...")
            tmp = staging_game_db_path().with_suffix('.db.tmp')
            try:
                dctx = zstandard.ZstdDecompressor()
                with open(tmp, 'wb') as f_out:
                    dctx.copy_stream(io.BytesIO(zst_bytes), f_out)
                os.replace(tmp, staging_game_db_path())
            except BaseException:
                tmp.unlink(missing_ok=True)
                raise
            log("game.db staging 完成")

        # 2. sprite categories — 完整提取
        for category, missing in category_missing.items():
            if not missing:
                log(f"{category}: 无需更新")
                continue
            _check_cancel(self._cancel)
            log(f"{category}: 正在下载 {category}.zip ...")
            zip_bytes = _download(
                mirror.make_url(f'{category}.zip'),
                log_cb=log,
                progress_cb=make_progress(f'{category}.zip'),
                cancel=self._cancel,
            )
            cat_staging = staging_sprites_path(category)
            cat_staging.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                for member in z.namelist():
                    _check_cancel(self._cancel)
                    fname = os.path.basename(member)
                    if fname and fname.endswith('.png'):
                        (cat_staging / fname).write_bytes(z.read(member))
            log(f"{category}: staging 解压完成")

        # 3. 写版本号
        staging_version_path().write_text(manifest.version)

        # 4. 从 staging 构建图像索引
        log("正在从 staging 构建图像索引...")
        if build_started_cb:
            build_started_cb()
        build_image_dbs_from_staging(
            staging_dir=staging,
            staging_cache_dir=staging_cache_dir(),
            status_cb=lambda msg: log(msg),
            progress_cb=build_progress_cb,
        )

        # 5. 写完整性标记（最后一步）
        (staging / '.complete').touch()

        # 6. 更新配置
        _update_misc(lambda misc: setattr(misc, 'game_data_pending_version',
                                          manifest.version))

        log("Staging 下载完成，下次启动时自动应用")

    @staticmethod
    def _cleanup_staging() -> None:
        """清理不完整的 staging 目录。"""
        s = staging_dir()
        if s.exists():
            shutil.rmtree(s, ignore_errors=True)
        sc = staging_cache_dir()
        if sc.exists():
            shutil.rmtree(sc, ignore_errors=True)

    def check_and_update(
        self,
        progress_cb: Optional[Callable[[str], None]] = None,
        file_progress_cb: Optional[Callable[[str, int, int], None]] = None,
        check_started_cb: Optional[Callable[[], None]] = None,
        download_started_cb: Optional[Callable[[bool], None]] = None,
    ) -> UpdateOutcome:
        """
        检查并更新游戏数据。检查阶段不可跳过；下载阶段可取消。

        下载统一走 staging（含图像索引构建），完成后立即调用
        :func:`apply_pending` 内联应用，保证原子性（半途失败不会留下不一致数据）。

        file_progress_cb(filename, downloaded_bytes, total_bytes) 在每个下载
        chunk 后调用，供 UI 层展示实时进度。
        download_started_cb(skippable) 在进入下载阶段时调用。
        """
        if check_started_cb:
            check_started_cb()

        result = self.check_only(progress_cb=progress_cb)
        if result is None:
            return UpdateOutcome.CHECK_FAILED

        self._mark_checked()

        if not result.needs_update:
            return UpdateOutcome.NOT_NEEDED

        if not result.auto_update_enabled:
            log_msg = (
                f"发现新版本 {result.manifest.version[:8]}，"
                "自动安装已关闭，跳过更新。"
            )
            logger.info(
                "自动安装已关闭，跳过更新。如需自动安装，请在设置中启用「自动安装游戏资源更新」。"
            )
            if progress_cb:
                progress_cb(log_msg)
            return UpdateOutcome.SKIPPED_AUTO

        skippable = has_usable_baseline()
        if download_started_cb:
            download_started_cb(skippable)

        try:
            # 统一下载到 staging（含图像索引构建）
            self.download_to_staging(result, file_progress_cb=file_progress_cb)
            # 阻塞路径：立即内联应用
            apply_pending()
            return UpdateOutcome.UPDATED
        except GameDataUpdateCancelled:
            self._cleanup_staging()
            logger.info("游戏数据更新已被用户跳过")
            return UpdateOutcome.CANCELLED