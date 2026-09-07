"""KaaPlugin — KAA 对 EuiShell 框架的插件实现。"""
import logging
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path

from PySide6.QtCore import QMetaObject, Qt, QObject

from euishell.plugin import EuiShellPlugin, StartupContext
from euishell.bridges.splash import SplashBridge
from euishell.controllers.preferences_controller import PreferencesControllerBase
from euishell.session import (
    AppearanceSettingsStore,
    ProfileProvider,
    ShellSession,
    TabPersistence,
)

from kaa.application.core.hotkeys import HotkeyManager
from kaa.application.ui.backends import (
    KaaAppearanceStore,
    KaaProfileProvider,
    KaaTabPersistence,
)
from kaa.application.ui.controllers.debug_inspector_controller import DebugInspectorController
from kaa.application.ui.controllers.game_data_controller import GameDataUpdateController
from kaa.application.ui.controllers.schedule_controller import ScheduleController
from kaa.application.ui.controllers.skill_card_browser_controller import SkillCardBrowserController
from kaa.application.ui.controllers.telemetry_consent_controller import TelemetryConsentController
from kaa.application.ui.paths import ICON_PATH, QML_DIR
from kaa.application.ui.kaa_session import KaaSession
from kaa.application.ui.splash_bridge import KaaSplashBridge
from kaa.application.services.scheduler_service import SchedulerService

logger = logging.getLogger(__name__)


def _app_version() -> str:
    try:
        return pkg_version('ksaa')
    except PackageNotFoundError:
        logger.debug('ksaa package not installed; using dev version.')
        return 'dev'


class KaaPlugin(EuiShellPlugin):
    """KAA 业务插件：把 KAA 的页面 / 控制器 / 服务接入 EuiShell Shell。"""

    def __init__(self) -> None:
        self._version = _app_version()
        self._prefs_ctrl = None
        self._hotkey_mgr: HotkeyManager | None = None
        self._scheduler_service: SchedulerService | None = None
        self._game_data_ctrl: GameDataUpdateController | None = None
        # startup 阶段记录数据是否经历阻塞更新，供 post_ready 决定是否后台检查
        self._needs_background_check = True

    # ── 应用元信息 ───────────────────────────────────────────

    @property
    def app_name(self) -> str:
        return '琴音小助手'

    @property
    def app_version(self) -> str:
        return self._version

    @property
    def icon_path(self) -> Path:
        return ICON_PATH

    def entry_qml(self) -> Path:
        return QML_DIR / 'index.qml'

    # ── 会话与后端 ───────────────────────────────────────────

    def create_session(self, profile_id: str) -> ShellSession:
        return KaaSession(profile_id)

    def profile_provider(self) -> ProfileProvider:
        return KaaProfileProvider()

    def tab_persistence(self) -> TabPersistence:
        return KaaTabPersistence()

    def appearance_store(self) -> AppearanceSettingsStore:
        return KaaAppearanceStore()

    def create_preferences_controller(self) -> PreferencesControllerBase:
        from kaa.application.ui.controllers.preferences_controller import PreferencesController

        if self._prefs_ctrl is None:
            self._prefs_ctrl = PreferencesController()
        return self._prefs_ctrl

    def create_splash_bridge(self) -> SplashBridge:
        return KaaSplashBridge(self._version)

    # ── 全局控制器 ───────────────────────────────────────────

    def global_controllers(self, ctx: StartupContext) -> dict[str, QObject]:
        """构造 KAA 全局控制器并完成调度器与 Tab 管理器的接线。"""
        schedule_ctrl = ScheduleController()
        scheduler_service = SchedulerService(ctx.tab_manager)
        game_data_ctrl = GameDataUpdateController()

        # 调度器占用的 profile 暂不可打开；profile 删除/重命名同步到调度器
        ctx.tab_manager.set_tab_open_guard(scheduler_service.isProfileBusyByScheduler)
        ctx.tab_manager.set_profile_handlers(
            on_remove=schedule_ctrl.handleProfileRemoved,
            on_rename=schedule_ctrl.handleProfileRenamed,
        )
        # 调度器写回 last_run 后通知 UI 刷新（任务执行完立即更新下次触发描述）
        scheduler_service.configChanged.connect(schedule_ctrl.entriesChanged)

        self._scheduler_service = scheduler_service
        self._game_data_ctrl = game_data_ctrl

        return {
            'GameDataCtrl': game_data_ctrl,
            'SkillCardBrowserController': SkillCardBrowserController(),
            'TelemetryConsentController': TelemetryConsentController(),
            'ScheduleController': schedule_ctrl,
            'SchedulerService': scheduler_service,
            'DebugInspector': DebugInspectorController(),
        }

    def global_dirty_guards(self) -> list[QObject]:
        prefs = self._prefs_ctrl
        return [prefs] if prefs is not None else []

    # ── 生命周期钩子 ─────────────────────────────────────────

    def startup(self, ctx: StartupContext) -> None:
        """后台线程：游戏数据 staging 应用 → 完整性校验 → 阻塞更新 → 索引构建。"""
        splash = ctx.splash

        # ── Step 0: 应用 pending staging ────────────────────────
        try:
            from kaa.game_data.updater import apply_pending
            if apply_pending():
                splash.onStatusChanged('正在应用游戏数据更新…')
                logger.info('Applied pending game data staging.')
        except BaseException:
            logger.exception('Failed to apply pending staging.')

        # ── Step 1: 轻量完整性校验 ───────────────────────────
        from kaa.game_data.updater import check_data_integrity
        needs_blocking = not check_data_integrity()
        self._needs_background_check = not needs_blocking

        if needs_blocking:
            # 阻塞更新（增量修复，立即替换）— 数据不完整时强制
            outcome = None
            try:
                from kaa.game_data.updater import GameDataUpdater
                updater = GameDataUpdater(cancel=splash.cancel_event)
                outcome = updater.check_and_update(
                    progress_cb=None,
                    file_progress_cb=lambda name, dl, total: splash.onFileProgress(name, dl, total),
                    check_started_cb=splash.onGameDataChecking,
                    download_started_cb=splash.onGameDataDownloading,
                )
                splash.onGameDataFinished()
                logger.info('Blocking game data check finished: %s', outcome.value)
            except BaseException:
                logger.exception('Blocking game data update failed; continuing.')
                splash.onGameDataFinished()

            # 阻塞更新后构建图像索引
            try:
                from kaa.image_db.prebuild import ensure_all_image_dbs_built
                was_updated = outcome is not None and outcome.value == 'updated'
                splash.onStatusChanged('正在构建图像数据索引，可能需要若干分钟')
                ensure_all_image_dbs_built(status_cb=splash.onStatusChanged, force=was_updated)
            except BaseException:
                logger.exception('Image db rebuild failed; continuing.')
        else:
            logger.info('Game data integrity OK, fast startup.')

    def post_startup(self, ctx: StartupContext) -> None:
        """后台线程：Tab 恢复后启动热键 / 调度器，并检查迁移与更新日志。"""
        splash = ctx.splash

        # ── 启动全局热键 ─────────────────────────────────────
        self._hotkey_mgr = self._make_hotkey_manager(ctx)
        try:
            if self._hotkey_mgr is not None:
                self._hotkey_mgr.start()
        except Exception:
            logger.exception('Failed to start hotkeys')

        # ── 启动定时调度 ─────────────────────────────────────
        # SchedulerService 及其 QTimer 归属主线程，本函数运行在后台线程，不能
        # 直接 start()（否则触发 "Timers cannot be started from another thread"）。
        # 用 QueuedConnection 投递到主线程事件循环执行。
        scheduler_service = self._find_scheduler_service()
        if scheduler_service is not None:
            try:
                QMetaObject.invokeMethod(
                    scheduler_service,
                    'start',
                    Qt.ConnectionType.QueuedConnection,
                )
            except Exception:
                logger.exception('Failed to start scheduler')

        # ── 检查迁移和更新日志 ───────────────────────────────
        if isinstance(splash, KaaSplashBridge):
            splash.check_and_show_migration()
            splash.check_and_show_changelog()

    def post_ready(self, ctx: StartupContext) -> None:
        """UI 就绪后：数据完整时启动后台资源检查。"""
        if not self._needs_background_check:
            game_data_ctrl = self._find_game_data_controller()
            if game_data_ctrl is not None:
                game_data_ctrl.startBackgroundCheck()

    def shutdown(self, ctx: StartupContext) -> None:
        """事件循环结束后停止热键与调度器。"""
        if self._hotkey_mgr is not None:
            self._hotkey_mgr.stop()
        scheduler_service = self._find_scheduler_service()
        if scheduler_service is not None:
            scheduler_service.stop()

    # ── 内部工具 ─────────────────────────────────────────────

    def _make_hotkey_manager(self, ctx: StartupContext) -> HotkeyManager:
        tab_manager = ctx.tab_manager

        def _active_control():
            return tab_manager.get_active_task_control()

        def _stop() -> None:
            control = _active_control()
            if control is not None:
                control.stop()

        def _get_pause() -> bool | None:
            control = _active_control()
            if control is None:
                return None
            return control.paused

        def _pause() -> None:
            control = _active_control()
            if control is not None and not control.paused:
                control.toggle_pause()

        def _resume() -> None:
            control = _active_control()
            if control is not None and control.paused:
                control.toggle_pause()

        return HotkeyManager(
            request_stop=_stop,
            get_pause_status=_get_pause,
            request_pause=_pause,
            request_resume=_resume,
        )

    def _find_scheduler_service(self) -> SchedulerService | None:
        return self._scheduler_service

    def _find_game_data_controller(self) -> GameDataUpdateController | None:
        return self._game_data_ctrl
