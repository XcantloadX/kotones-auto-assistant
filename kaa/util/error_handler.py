"""统一异常处理：日志 + UI 弹窗 + Sentry 上报。

所有线程/所有阶段（任务内、初始化期、全局兜底）均委托至此，
避免中间件与 threading.excepthook 各自为战。
"""
import logging
from typing import Any

from kotonebot.errors import UserFriendlyError, StopCurrentTask, UnscalableResolutionError
from kotonebot.interop.window.model import WindowQueryError

logger = logging.getLogger(__name__)

# 去重：同一异常对象在多层（_initialize → run → threading.excepthook）只处理一次
_handled_ids: set[int] = set()


def _show_bridge(message: str, buttons: list[tuple[int, str]], on_click) -> None:
    try:
        from kaa.application.ui.error_bridge import get_bridge
        bridge = get_bridge()
        if bridge is not None:
            bridge.show(message, buttons, on_click)
        else:
            logger.error(message)
    except Exception:
        logger.exception("Failed to show error dialog.", exc_info=True)


def _capture_sentry(exc: BaseException, *, task_name: str | None) -> None:
    """按 sentry_middleware 语义上报系统错误；友好错由调用方跳过。"""
    try:
        from kaa.util.telemetry import use_sentry, collect_report_context
        sentry_sdk = use_sentry()
        # _DummySentry 在未启用时吞掉
        with sentry_sdk.isolation_scope() as scope:
            if task_name:
                scope.set_tag("task_name", task_name)
            try:
                for k, v in collect_report_context().items():
                    scope.set_tag(k, v)
            except Exception:
                logger.warning("Failed to attach report context.", exc_info=True)
            try:
                from kaa.kaa_context import conf as get_conf
                scope.set_extra("config", get_conf().model_dump_json())
            except Exception:
                logger.warning("Failed to attach config to Sentry report.", exc_info=True)
            try:
                from kaa.config import manager as config_manager
                shared = config_manager.read_shared()
                scope.set_extra("shared_config", shared.model_dump_json())
            except Exception:
                logger.warning("Failed to attach shared config to Sentry report.", exc_info=True)
            try:
                from kaa.config import manager as config_manager
                if config_manager.read_shared().telemetry.upload_screenshot is True:
                    from kaa.util.telemetry_screenshot import upload_report_screenshot
                    sid = upload_report_screenshot()
                    if sid:
                        scope.set_tag("screenshot_id", sid)
            except Exception:
                logger.warning("Failed to upload screenshot to Sentry report.", exc_info=True)
            sentry_sdk.capture_exception(exc)
    except Exception:
        logger.warning("Failed to capture exception to Sentry.", exc_info=True)


def _build_resolution_message(screen_size: tuple[int, int]) -> str:
    w, h = screen_size
    return (
        f"游戏窗口尺寸/模拟器分辨率（{w}x{h}）为不支持的分辨率。\n"
        f"请调整尺寸/分辨率为 16:9 或 9:16 的比例（720x1280 最佳）。"
    )


def handle_exception(
    exc: BaseException,
    *,
    ctx: Any | None = None,
    task: Any | None = None,
    source: str = "runner",
) -> None:
    """统一处理：日志 + 弹窗 + Sentry + ctx 状态。

    :param exc: 异常实例
    :param ctx: BotContext | None（有则设置 has_error/last_exception 并 stop）
    :param task: Task | None（有则日志带 task.name，Sentry tag task_name）
    :param source: 来源标签，用于日志前缀（task/runner/global）
    """
    # 去重：同一异常在多层捕获时仅首次生效
    eid = id(exc)
    if eid in _handled_ids:
        return
    _handled_ids.add(eid)

    # 用户主动中断：静默忽略，不弹窗、不记错误
    if isinstance(exc, (StopCurrentTask, KeyboardInterrupt)):
        return

    task_name = getattr(task, "name", None) if task is not None else None
    prefix = f"[{source}]" if source else ""

    # 友好错：不报 Sentry
    if isinstance(exc, UserFriendlyError):
        if ctx is not None:
            ctx.has_error = True
            ctx.last_exception = exc
        msg = getattr(exc, "message", str(exc))
        if task_name:
            logger.warning(f"{prefix} Task {task_name} failed: {msg}")
        else:
            logger.warning(f"{prefix} {msg}")
        buttons = getattr(exc, "action_buttons", [(0, "知道了")])
        invoke = getattr(exc, "invoke", lambda _: None)
        _show_bridge(msg, buttons, invoke)
        if ctx is not None:
            try:
                ctx.stop()
            except Exception:
                logger.debug("Failed to stop context after UserFriendlyError.", exc_info=True)
        return

    if isinstance(exc, WindowQueryError):
        if ctx is not None:
            ctx.has_error = True
            ctx.last_exception = exc
        if task_name:
            logger.warning(f"{prefix} Window query failed in {task_name}: {exc}")
        else:
            logger.warning(f"{prefix} Window query failed: {exc}")
        _show_bridge(
            "未找到游戏窗口，任务已停止。请确认游戏已启动，然后重新启动任务。",
            [(0, "知道了")],
            lambda _: None,
        )
        if ctx is not None:
            try:
                ctx.stop()
            except Exception:
                logger.debug("Failed to stop context after WindowQueryError.", exc_info=True)
        return

    if isinstance(exc, UnscalableResolutionError):
        if ctx is not None:
            ctx.has_error = True
            ctx.last_exception = exc
        w, h = exc.screen_size
        if task_name:
            logger.warning(f"{prefix} Resolution error in {task_name}: screen {w}x{h}.")
        else:
            logger.warning(f"{prefix} Resolution error: screen {w}x{h}.")
        message = _build_resolution_message((w, h))
        _show_bridge(message, [(0, "知道了")], lambda _: None)
        if ctx is not None:
            try:
                ctx.stop()
            except Exception:
                logger.debug("Failed to stop context after UnscalableResolutionError.", exc_info=True)
        return

    # 系统错误：上报 Sentry + 日志 + 通用弹窗
    if ctx is not None:
        ctx.has_error = True
        ctx.last_exception = exc
    if task_name:
        logger.warning(f"{prefix} System Error in {task_name}: {exc}", exc_info=True)
    else:
        logger.warning(f"{prefix} System Error: {exc}", exc_info=True)
    _capture_sentry(exc, task_name=task_name)
    # 通用弹窗：避免静默失败（原 windows_gui_error_middleware 仅记日志）
    _show_bridge(
        f"发生未预期的系统错误：{exc}\n请查看日志或通过反馈功能提交报告。",
        [(0, "知道了")],
        lambda _: None,
    )
    if ctx is not None:
        try:
            ctx.stop()
        except Exception:
            logger.debug("Failed to stop context after System Error.", exc_info=True)


def handle_global_exception(exc_type, exc_value, exc_traceback, *, thread_name: str | None = None) -> None:
    """供 sys.excepthook / threading.excepthook 委托（最后兜底）。"""
    # KeyboardInterrupt / StopCurrentTask / SystemExit / Cancelled 忽略
    try:
        if issubclass(exc_type, (KeyboardInterrupt, SystemExit)) or isinstance(exc_value, StopCurrentTask):
            import sys
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
    except Exception:
        pass
    # 已有 handler 的友好错会走 handle_exception 的 warning + 弹窗语义，
    # 这里作为最后兜底，统一委托 handle_exception 以保证 Sentry 去重一致
    try:
        handle_exception(exc_value, ctx=None, task=None, source=thread_name or "global")
    except Exception:
        logger.critical("Failed to handle global exception.", exc_info=(exc_type, exc_value, exc_traceback))
        # 仍记录原始堆栈到日志，避免丢失
        logger.critical("Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback))
