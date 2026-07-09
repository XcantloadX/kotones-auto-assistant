import concurrent.futures
import hashlib
import io
import logging
import os
import time
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

if TYPE_CHECKING:
    from kaa.config.shared import SharedMiscConfig

import requests
import zstandard

from .manifest import parse as parse_manifest
from .paths import (
    game_db_path, sprites_path, version_path
)

logger = logging.getLogger(__name__)

_CATEGORIES = ('idol_cards', 'skill_cards', 'drinks')

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
    _Mirror("ghfast.top",  _prefix_proxy("https://ghfast.top")),
]

# 进程级缓存
_selected_mirror: Optional[_Mirror] = None

# ── 镜像探测 ──────────────────────────────────────────────────────────────────

def _probe(mirror: _Mirror, timeout: float = 5.0) -> tuple[float, _Mirror]:
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


def _select_mirror(log_cb: Optional[Callable[[str], None]] = None) -> _Mirror:
    """
    并发探测所有内置镜像，返回延迟最低的可用镜像。
    结果进程级缓存，后续调用直接返回缓存值。
    """
    def log(msg: str):
        logger.info(msg)
        if log_cb:
            log_cb(msg)

    global _selected_mirror
    if _selected_mirror is not None:
        return _selected_mirror

    log(f"正在探测 GitHub 镜像连通性（{len(_BUILTIN_MIRRORS)} 个候选）...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(_BUILTIN_MIRRORS)) as pool:
        futures = [pool.submit(_probe, m) for m in _BUILTIN_MIRRORS]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    results.sort(key=lambda r: r[0])
    best_latency, best_mirror = results[0]

    if best_latency == float('inf'):
        log("所有镜像均不可达，回退到直连 GitHub")
        _selected_mirror = _BUILTIN_MIRRORS[0]
    else:
        log(f"选用镜像：{best_mirror.label}（延迟 {best_latency * 1000:.0f} ms）")
        _selected_mirror = best_mirror

    return _selected_mirror

# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


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
) -> bytes:
    """下载 URL 内容，支持断点续传和指数退避重试。

    progress_cb(downloaded_bytes, total_bytes) 在每个 chunk 后调用。
    total_bytes 为完整文件大小（续传时也是全量值，不是剩余量）。
    """
    buf = io.BytesIO()
    downloaded = 0
    size_logged = False

    for attempt in range(1, max_retries + 1):
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
                buf.write(chunk)
                downloaded += len(chunk)
                if progress_cb:
                    progress_cb(downloaded, total)

            buf.seek(0)
            return buf.read()

        except _RETRYABLE as e:
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
    def check_and_update(
        self,
        progress_cb: Optional[Callable[[str], None]] = None,
        file_progress_cb: Optional[Callable[[str, int, int], None]] = None,
    ) -> bool:
        """
        自动选择最优镜像，检查并更新游戏数据。

        file_progress_cb(filename, downloaded_bytes, total_bytes) 在每个下载
        chunk 后调用，供 UI 层展示实时进度。
        :return: 是否执行了更新
        """
        from kaa.config import manager as config_manager
        _shared = config_manager.read_shared()
        _shared.misc.game_data_last_checked = datetime.now().isoformat()
        config_manager.write_shared(_shared)
        def log(msg: str):
            logger.info(msg)

        def make_progress(name: str) -> Optional[Callable[[int, int], None]]:
            cb = file_progress_cb
            if cb is None:
                return None
            return lambda dl, total: cb(name, dl, total)

        # 0. 选择最优镜像（首次调用时并发探测，后续命中缓存）
        mirror = _select_mirror(log_cb=progress_cb)

        # 1. 拉取 manifest
        log("正在获取游戏数据版本信息...")
        try:
            manifest_bytes = _download(mirror.make_url('manifest.json'))
        except Exception as e:
            logger.warning("无法获取 manifest.json，跳过更新: %s", e)
            return False

        manifest = parse_manifest(manifest_bytes)

        # 2. 比较版本
        ver_file = version_path()
        local_version = ver_file.read_text().strip() if ver_file.exists() else ""
        if local_version == manifest.version:
            log("游戏数据已是最新版本")
            return False

        log(f"发现新版本: {manifest.version[:8]}")

        if not _shared.misc.game_data_auto_update:
            log("自动安装已关闭，跳过更新。如需自动安装，请在设置中启用「自动安装游戏资源更新」。")
            if progress_cb:
                progress_cb(f"发现新版本 {manifest.version[:8]}，自动安装已关闭，跳过更新。")
            return False

        log("开始更新...")

        # 3. 检查 game.db
        db_path = game_db_path()
        db_entry = manifest.files.get('game.db')
        needs_db = (
            not db_path.exists() or
            (db_entry and _md5(db_path) != db_entry.md5)
        )

        # 4. 检查所有 sprite 分类（先全部算完，再统一通知 UI 预填充）
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

        # 通知 UI 预先展示所有待下载文件（0 进度占位）
        if file_progress_cb:
            if needs_db:
                file_progress_cb('game.db.zst', 0, 0)
            for category, missing in category_missing.items():
                if missing:
                    file_progress_cb(f'{category}.zip', 0, 0)

        # 5. 下载 game.db
        if needs_db:
            log("正在下载 game.db.zst ...")
            zst_bytes = _download(mirror.make_url('game.db.zst'), log_cb=log,
                                  progress_cb=make_progress('game.db.zst'))
            log("正在解压 game.db ...")
            dctx = zstandard.ZstdDecompressor()
            with open(db_path, 'wb') as f_out:
                dctx.copy_stream(io.BytesIO(zst_bytes), f_out)
            log(f"game.db 更新完成（{db_path.stat().st_size // 1024 // 1024} MB）")

        # 6. 下载 sprites
        for category, missing in category_missing.items():
            if not missing:
                log(f"{category}: 无需更新")
                continue
            log(f"{category}: 需更新 {len(missing)} 个文件，正在下载 {category}.zip ...")
            zip_bytes = _download(mirror.make_url(f'{category}.zip'), log_cb=log,
                                  progress_cb=make_progress(f'{category}.zip'))
            cat_dir = sprites_path(category)
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                for member in z.namelist():
                    fname = os.path.basename(member)
                    if fname and fname.endswith('.png') and fname in missing:
                        (cat_dir / fname).write_bytes(z.read(member))
            log(f"{category}: 解压完成")

        # 7. 写入版本号
        ver_file.write_text(manifest.version)
        if needs_db:
            from kaa.db._util import clear_db_caches
            clear_db_caches()
        log("游戏数据更新完成")
        return True
