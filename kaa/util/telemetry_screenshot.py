"""错误上报时的截图上传模块。

将实时截图上传到 Cloudflare Worker（转发至 Google Drive），返回服务端分配的
UUID。该 ID 作为 tag 附加到 Sentry 报告，便于在 Drive 中检索对应图片。所有失败
均静默降级（仅记 warning 日志并返回 None），绝不阻断错误上报链路。

截图上传覆盖两条上报路径：
1. 异常上报：sentry_middleware 在 capture_exception 时同步上传。
2. 日志上报：screenshot_before_send 钩子为 error/critical/fatal 级别的纯日志事件
   上传（异常事件由 sentry_middleware 处理，这里不再重复）。已知良性的日志消息
   （见 _SKIP_UPLOAD_MESSAGE_FRAGMENTS）会跳过上传，避免刷屏 Drive。
"""

import logging
import threading
import time
from collections import deque
from typing import TYPE_CHECKING, cast

import requests

from kaa.constants import SCREENSHOT_UPLOAD_URL
from kaa.util.telemetry import is_dev, is_enabled

if TYPE_CHECKING:
    from sentry_sdk.types import Event, Hint

logger = logging.getLogger(__name__)

# Cloudflare Worker 侧单个文件大小上限（413 判定阈值）。
_MAX_BYTES = 3 * 1024 * 1024

# 单进程内每分钟最多尝试的上传次数。与 Worker 侧 IP 限流一致，避免触发 429。
_MAX_UPLOADS_PER_MINUTE = 5

# 已知良性日志错误：消息包含以下任一片段时跳过截图上传（不影响 Sentry 上报本身）。
# 如「未找到 +30 选项，改选第二个按钮」属于游戏 UI 识别的可恢复分支，无需浪费云盘配额。
_SKIP_UPLOAD_MESSAGE_FRAGMENTS = (
    'Failed to find +30 option',
)

# 上传尝试的时间戳滑动窗口（monotonic），跨线程用锁保护。
_upload_attempt_lock = threading.Lock()
_upload_attempt_times: deque[float] = deque()


def _allow_upload() -> bool:
    """按每分钟上限节流上传尝试；放行时记录本次尝试时间戳。"""
    now = time.monotonic()
    with _upload_attempt_lock:
        while _upload_attempt_times and now - _upload_attempt_times[0] >= 60:
            _upload_attempt_times.popleft()
        if len(_upload_attempt_times) >= _MAX_UPLOADS_PER_MINUTE:
            return False
        _upload_attempt_times.append(now)
        return True


def _is_skipped_log_message(message: str) -> bool:
    """判断日志消息是否命中免上传清单。"""
    return any(frag in message for frag in _SKIP_UPLOAD_MESSAGE_FRAGMENTS)


def screenshot_before_send(event: 'Event', hint: 'Hint') -> 'Event | None':
    """Sentry before_send 钩子：为 error 级别的纯日志事件附加截图上传。

    异常事件（event 含 ``exception``）已由 sentry_middleware 同步上传，此处仅覆盖
    LoggingIntegration 上报的 error/critical/fatal 日志事件。命中免上传清单的已知
    良性消息直接放行（不上传）。任何失败都只降级日志，不改动事件本身。

    :param event: Sentry 事件字典（scope tag 已合并）。
    :param hint: Sentry 事件附带元数据（此处未使用）。
    :return: 原事件（可能已追加 ``tags.screenshot_id``）；本实现从不返回 None。
    """
    print(11111111111)
    # 事件以 TypedDict 传入，统一转成普通 dict 进行读写，规避 TypedDict 的静态限制。
    data: dict = cast(dict, event)

    # 异常事件由 sentry_middleware 处理截图上传，避免重复。
    if data.get('exception'):
        return event
    # 仅处理 error 级及以上的日志事件。
    if data.get('level') not in ('error', 'critical', 'fatal'):
        return event

    logentry = data.get('logentry')
    message = ''
    if isinstance(logentry, dict):
        message = str(logentry.get('message') or logentry.get('formatted') or '')
    if not message:
        message = str(data.get('message') or '')
    # 已知良性消息免上传。
    if _is_skipped_log_message(message):
        return event

    try:
        from kotonebot import device  # noqa: PLC0415
        upload_id = upload_screenshot(device.screenshot())
        if upload_id:
            data.setdefault('tags', {})['screenshot_id'] = upload_id
    except Exception:
        # 截图/上传失败一律降级，不影响 Sentry 上报主流程。
        logger.warning('Failed to attach screenshot for log error event.', exc_info=True)
    return event


def upload_screenshot(image_bgr) -> str | None:
    """上传截图到图片上传服务，成功后返回分配的 UUID。

    :param image_bgr: OpenCV BGR 格式截图数组（cv2.imencode 可直接编码）。
    :return: 上传成功返回服务端分配的 UUID；遥测未启用/服务不可达/超限时返回 None。
    """
    # 遥测未启用或开发模式下不产生任何网络请求。
    if is_dev() or not is_enabled():
        return None
    # 达到每分钟上传上限时静默跳过，避免触发 Worker 侧 429。
    if not _allow_upload():
        logger.debug('Screenshot upload rate limit reached, skipping.')
        return None

    try:
        import cv2

        # 编码为 PNG；超过 3MiB 时按 0.7 倍循环缩放直至达标（Worker 会拒绝 413）。
        data = cv2.imencode('.png', image_bgr)[1].tobytes()
        scale = 1.0
        while len(data) >= _MAX_BYTES and scale > 0.1:
            scale *= 0.7
            resized = cv2.resize(
                image_bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA
            )
            data = cv2.imencode('.png', resized)[1].tobytes()

        resp = requests.post(
            f'{SCREENSHOT_UPLOAD_URL}/upload',
            headers={'Content-Type': 'image/png'},
            data=data,
            timeout=10,
            proxies={'http': '', 'https': ''},
        )
        if resp.status_code == 201:
            payload = resp.json()
            upload_id = payload.get('id') if isinstance(payload, dict) else None
            if upload_id:
                return str(upload_id)
            logger.warning('Screenshot upload returned 201 but missing id: %r', payload)
        else:
            logger.warning('Screenshot upload failed: HTTP %s', resp.status_code)
    except Exception:
        # 网络错误/解析失败等一律降级，不影响 Sentry 上报主流程。
        logger.warning('Failed to upload screenshot.', exc_info=True)
    return None
