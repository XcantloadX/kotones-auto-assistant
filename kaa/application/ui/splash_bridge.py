"""KaaSplashBridge — 扩展 Shell Splash：更新日志与配置迁移弹窗信号。"""
import logging

from PySide6.QtCore import Signal, Slot

from euishell.bridges.splash import SplashBridge

from kaa.config import manager as config_manager

logger = logging.getLogger(__name__)


class KaaSplashBridge(SplashBridge):
    """KAA Splash 桥接：在 Shell 基础上追加更新日志 / 迁移报告弹窗信号。

    QML 侧由 window.dialogs slot 中的 KaaDialogs.qml 连接这些信号。
    """

    showChangelogDialog = Signal(str, str)
    showMigrationDialog = Signal(list)

    def __init__(self, app_version: str) -> None:
        """
        :param app_version: 当前应用版本（changelog 判定基准）
        """
        super().__init__()
        self._app_version = app_version

    def check_and_show_changelog(self) -> None:
        """版本变更时发射更新日志弹窗信号（后台线程调用）。"""
        try:
            from kaa.application.services.update_service import get_changelogs_since

            shared = config_manager.read_shared()
            if shared.misc.last_seen_changelog != self._app_version:
                text = get_changelogs_since(shared.misc.last_seen_changelog)
                if text:
                    self.showChangelogDialog.emit(self._app_version, text)
        except Exception:
            logger.debug('Failed to check changelog version.', exc_info=True)

    def check_and_show_migration(self) -> None:
        """存在迁移遗留消息时发射迁移报告弹窗信号（后台线程调用）。"""
        try:
            from kaa.config.migration import get_deferred_messages

            messages = get_deferred_messages()
            if messages:
                data = [
                    {
                        'text': msg.text,
                        'level': msg.level,
                        'oldVersion': msg.old_version or '',
                        'newVersion': msg.new_version or '',
                    }
                    for msg in messages
                ]
                self.showMigrationDialog.emit(data)
        except Exception:
            logger.debug('Failed to check migration messages.', exc_info=True)

    @Slot()
    def onChangelogDismissed(self) -> None:
        """用户关闭更新日志弹窗后记录版本。"""
        try:
            shared = config_manager.read_shared()
            shared.misc.last_seen_changelog = self._app_version
            config_manager.write_shared(shared)
        except Exception:
            logger.debug('Failed to save last_seen_changelog.', exc_info=True)
