"""TelemetryConsentController — 匿名错误上报同意弹窗桥接。

对应 IAA 的 AppController.telemetryConsentRequired / setTelemetryConsent。
启动时若 shared.telemetry 中任一配置（总开关 sentry / 截图上传 upload_screenshot）
尚未设置（None）且非开发环境，QML 弹窗询问用户；用户选择后两个开关一并写入
_shared.json，下次启动生效。
"""

import logging

from PySide6.QtCore import Property, QObject, Signal, Slot

from kaa.config import manager as config_manager
from kaa.util import telemetry

logger = logging.getLogger(__name__)


class TelemetryConsentController(QObject):
    """暴露"是否需要首次同意"状态与用户决定的写入入口给 QML。

    初始化即读取 shared 配置，将两个开关的当前状态暴露给 QML 弹窗展示；并在
    （非开发环境且任一配置项尚未表态时）将 ``telemetryConsentRequired`` 置为 True。
    用户在弹窗中选择后调用 :meth:`setTelemetryConsent` 持久化两个配置并清除待表态标记。
    """

    telemetryConsentRequiredChanged = Signal()
    sentryEnabledChanged = Signal()
    screenshotEnabledChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        telemetry_cfg = config_manager.read_shared().telemetry
        self._sentry = telemetry_cfg.sentry is True
        self._screenshot = telemetry_cfg.upload_screenshot is True
        self._consent_required = (
            (telemetry_cfg.sentry is None or telemetry_cfg.upload_screenshot is None)
        )

    def _get_sentry(self) -> bool:
        return self._sentry

    def _get_screenshot(self) -> bool:
        return self._screenshot

    def _get_consent_required(self) -> bool:
        return self._consent_required

    sentryEnabled = Property(bool, _get_sentry, notify=sentryEnabledChanged)
    screenshotEnabled = Property(bool, _get_screenshot, notify=screenshotEnabledChanged)
    telemetryConsentRequired = Property(
        bool, _get_consent_required, notify=telemetryConsentRequiredChanged
    )

    @Slot(bool, bool)
    def setTelemetryConsent(self, sentry: bool, screenshot: bool) -> None:
        """写入用户对两个开关的选择，并清除"待同意"状态。

        :param sentry: True 允许匿名错误上报。
        :param screenshot: True 允许错误上报时附带截图。
        """
        telemetry.set_consent(bool(sentry), bool(screenshot))
        self._sentry = bool(sentry)
        self._screenshot = bool(screenshot)
        self._consent_required = False
        self.sentryEnabledChanged.emit()
        self.screenshotEnabledChanged.emit()
        self.telemetryConsentRequiredChanged.emit()
        logger.info('Telemetry consent settled: sentry=%s screenshot=%s', sentry, screenshot)