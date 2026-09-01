"""telemetry 同意机制的单元测试。

覆盖 kaa.util.telemetry 的非阻塞 setup()/状态助手，以及
TelemetryConsentController 的首次同意状态与写入行为。
"""

from unittest import TestCase
from unittest.mock import MagicMock, patch

from kaa.util import telemetry
from kaa.application.ui.controllers.telemetry_consent_controller import (
    TelemetryConsentController,
)


def _shared(sentry=None, screenshot=None, statics=None):
    """构造一个 telemetry.sentry / upload_screenshot / statics 可控的 SharedConfig。"""
    from kaa.config.shared import SharedConfig
    shared = SharedConfig()
    shared.telemetry.sentry = sentry
    shared.telemetry.upload_screenshot = screenshot
    shared.telemetry.statics = statics
    return shared


class TestTelemetryStateHelpers(TestCase):
    """验证 is_enabled / is_pending / set_enabled / set_consent 的判定与落盘。"""

    def test_is_enabled_true(self):
        with patch('kaa.config.manager.read_shared', return_value=_shared(True)):
            self.assertTrue(telemetry.is_enabled())

    def test_is_enabled_false(self):
        with patch('kaa.config.manager.read_shared', return_value=_shared(False)):
            self.assertFalse(telemetry.is_enabled())

    def test_is_pending_when_sentry_none(self):
        # 总开关未表态（None）时视为待同意
        with patch('kaa.config.manager.read_shared', return_value=_shared(None, True, False)):
            self.assertTrue(telemetry.is_pending())

    def test_is_pending_when_screenshot_none(self):
        # 截图开关未表态（None）时同样视为待同意
        with patch('kaa.config.manager.read_shared', return_value=_shared(True, None, False)):
            self.assertTrue(telemetry.is_pending())

    def test_is_pending_when_statics_none(self):
        # 统计数据收集开关未表态（None）时同样视为待同意
        with patch('kaa.config.manager.read_shared', return_value=_shared(True, True, None)):
            self.assertTrue(telemetry.is_pending())

    def test_is_pending_false_when_all_set(self):
        accepted = _shared(True, True, True)
        declined = _shared(False, False, False)
        partial = _shared(True, False, False)
        with patch('kaa.config.manager.read_shared', return_value=accepted):
            self.assertFalse(telemetry.is_pending())
        with patch('kaa.config.manager.read_shared', return_value=declined):
            self.assertFalse(telemetry.is_pending())
        with patch('kaa.config.manager.read_shared', return_value=partial):
            self.assertFalse(telemetry.is_pending())

    def test_set_enabled_persists_sentry(self):
        shared = _shared(None)
        with patch('kaa.config.manager.read_shared', return_value=shared), \
             patch('kaa.config.manager.write_shared') as mock_write:
            telemetry.set_enabled(True)
            self.assertTrue(shared.telemetry.sentry)
            mock_write.assert_called_once_with(shared)

    def test_set_consent_persists_all(self):
        shared = _shared(None, None, None)
        with patch('kaa.config.manager.read_shared', return_value=shared), \
             patch('kaa.config.manager.write_shared') as mock_write:
            telemetry.set_consent(False, True, True)
            self.assertIs(shared.telemetry.sentry, False)
            self.assertIs(shared.telemetry.upload_screenshot, True)
            self.assertIs(shared.telemetry.statics, True)
            mock_write.assert_called_once_with(shared)


class TestTelemetrySetup(TestCase):
    """验证 setup() 非阻塞：开发环境 / 未启用时均不初始化 sentry。"""

    def test_dev_env_skips_init(self):
        fake_sentry = MagicMock()
        with patch.dict('sys.modules', {'sentry_sdk': fake_sentry}):
            with patch('kaa.util.telemetry.is_dev', return_value=True):
                telemetry.setup()
        fake_sentry.init.assert_not_called()

    def test_pending_consent_skips_init(self):
        # 任一配置为 None（待同意）时不初始化，也不弹控制台询问
        fake_sentry = MagicMock()
        with patch.dict('sys.modules', {'sentry_sdk': fake_sentry}):
            with patch('kaa.util.telemetry.is_dev', return_value=False):
                with patch('kaa.config.manager.read_shared', return_value=_shared(None, None, None)):
                    telemetry.setup()
        fake_sentry.init.assert_not_called()

    def test_disabled_skips_init(self):
        shared = _shared(False, False, False)
        fake_sentry = MagicMock()
        with patch.dict('sys.modules', {'sentry_sdk': fake_sentry}):
            with patch('kaa.util.telemetry.is_dev', return_value=False):
                with patch('kaa.config.manager.read_shared', return_value=shared):
                    with patch('kaa.util.telemetry._attach_global_tags') as mock_tags:
                        telemetry.setup()
        fake_sentry.init.assert_not_called()
        mock_tags.assert_not_called()

    def test_enabled_initializes_sentry(self):
        shared = _shared(True, False, False)
        fake_sentry = MagicMock()
        with patch.dict('sys.modules', {'sentry_sdk': fake_sentry}):
            with patch('kaa.util.telemetry.is_dev', return_value=False):
                with patch('kaa.config.manager.read_shared', return_value=shared):
                    with patch('kaa.util.telemetry._attach_global_tags') as mock_tags:
                        with patch('importlib.metadata.version', return_value='1.0.0'):
                            telemetry.setup()
        fake_sentry.init.assert_called_once()
        mock_tags.assert_called_once()


class TestTelemetryConsentController(TestCase):
    """验证首次同意状态与 setTelemetryConsent 的持久化行为。"""

    def _make_ctrl(self, shared, *, is_dev=False):
        with patch('kaa.util.telemetry.is_dev', return_value=is_dev), \
             patch('kaa.config.manager.read_shared', return_value=shared):
            return TelemetryConsentController()

    def test_pending_when_sentry_none_and_not_dev(self):
        # 总开关未表态：需要同意，开关初始状态从配置读取（screenshot 已开启）
        ctrl = self._make_ctrl(_shared(None, True, False))
        self.assertTrue(ctrl.telemetryConsentRequired)
        self.assertFalse(ctrl.sentryEnabled)
        self.assertTrue(ctrl.screenshotEnabled)
        self.assertFalse(ctrl.staticsEnabled)

    def test_pending_when_screenshot_none(self):
        # 截图开关未表态：同样需要同意
        ctrl = self._make_ctrl(_shared(True, None, False))
        self.assertTrue(ctrl.telemetryConsentRequired)
        self.assertTrue(ctrl.sentryEnabled)

    def test_pending_when_statics_none(self):
        # 统计数据收集开关未表态：同样需要同意
        ctrl = self._make_ctrl(_shared(True, True, None))
        self.assertTrue(ctrl.telemetryConsentRequired)
        self.assertTrue(ctrl.sentryEnabled)
        self.assertTrue(ctrl.screenshotEnabled)
        self.assertFalse(ctrl.staticsEnabled)

    def test_dev_env_does_not_require_consent(self):
        ctrl = self._make_ctrl(_shared(None, None, None), is_dev=True)
        self.assertFalse(ctrl.telemetryConsentRequired)

    def test_settled_consent_does_not_require(self):
        ctrl = self._make_ctrl(_shared(True, False, True))
        self.assertFalse(ctrl.telemetryConsentRequired)
        self.assertTrue(ctrl.sentryEnabled)
        self.assertFalse(ctrl.screenshotEnabled)
        self.assertTrue(ctrl.staticsEnabled)

    def test_set_telemetry_consent_persists_and_clears(self):
        ctrl = self._make_ctrl(_shared(None, None, None))
        self.assertTrue(ctrl.telemetryConsentRequired)
        fired = []
        ctrl.telemetryConsentRequiredChanged.connect(lambda: fired.append(True))
        with patch('kaa.util.telemetry.set_consent', return_value=None) as mock_set:
            ctrl.setTelemetryConsent(True, False, True)
        mock_set.assert_called_once_with(True, False, True)
        self.assertTrue(ctrl.sentryEnabled)
        self.assertFalse(ctrl.screenshotEnabled)
        self.assertTrue(ctrl.staticsEnabled)
        self.assertFalse(ctrl.telemetryConsentRequired)
        self.assertEqual(fired, [True])