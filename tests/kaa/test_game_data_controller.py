"""测试 GameDataUpdateController 的状态机与后台下载流程。

该控制器模块自身只依赖 QtCore + kaa.util.progress，不触发 kotonebot，
但父包 ``kaa.application.ui.controllers`` 会经 tab_manager 触发 kotonebot
导入链，因此这里绕过父包直接加载目标模块。
"""
import importlib.util
import sys
import threading
import time
import types

import pytest

from PySide6.QtCore import QObject


def _load_controller_module():
    """绕过父包 __init__，直接加载 game_data_controller 模块。"""
    spec = importlib.util.spec_from_file_location(
        "kaa.application.ui.controllers.game_data_controller",
        "kaa/application/ui/controllers/game_data_controller.py",
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


CONTROLLER = _load_controller_module()


class FakeManifest:
    def __init__(self, version: str = "v2026.7.1"):
        self.version = version


class FakeResult:
    def __init__(self, needs_update=True, auto_update_enabled=True, version="v2026.7.1"):
        self.needs_update = needs_update
        self.auto_update_enabled = auto_update_enabled
        self.manifest = FakeManifest(version)


class FakeUpdater:
    """记录调用的假 GameDataUpdater（default_result 供线程内取用）。"""

    instances = []
    default_result = None

    def __init__(self, cancel=None):
        self.cancel = cancel
        self.check_only_calls = 0
        self.mark_checked_calls = 0
        self.download_calls = []
        self.result = FakeUpdater.default_result
        FakeUpdater.instances.append(self)

    def check_only(self, progress_cb=None):
        self.check_only_calls += 1
        return self.result

    def _mark_checked(self):
        self.mark_checked_calls += 1

    def download_to_staging(self, result, file_progress_cb=None, build_started_cb=None, build_progress_cb=None):
        self.download_calls.append((result, file_progress_cb))


class SimpleNamespace:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def make_fake_updater_module():
    """构建带 should_check 与 GameDataUpdater 的假 kaa.game_data.updater 模块。"""
    mod = types.ModuleType("kaa.game_data.updater")
    mod.GameDataUpdater = FakeUpdater
    mod.should_check = lambda misc: True
    return mod


def make_fake_config_manager(pending_version=""):
    """构建带 read_shared 的假 kaa.config.manager 模块。"""
    mod = types.ModuleType("kaa.config.manager")
    shared = SimpleNamespace(misc=SimpleNamespace(game_data_pending_version=pending_version))
    mod.read_shared = lambda: shared
    return mod


def _wait_until(pred, timeout=3.0):
    """轮询等待子线程完成，超时抛错。"""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pred():
            return
        time.sleep(0.01)
    raise AssertionError("Timed out waiting for background thread.")


def _patch_config_manager(monkeypatch, pending_version=""):
    """注入假 kaa.config.manager，同时覆盖 sys.modules 与包属性，
    避免 `from kaa.config import manager` 拿到已加载的真实模块。"""
    import kaa.config
    fake = make_fake_config_manager(pending_version)
    monkeypatch.setitem(sys.modules, "kaa.config.manager", fake)
    monkeypatch.setattr(kaa.config, "manager", fake, raising=False)
    return fake


@pytest.fixture
def ctrl(monkeypatch):
    """构造控制器，并注入假 config manager / updater 模块。"""
    _patch_config_manager(monkeypatch)
    monkeypatch.setitem(sys.modules, "kaa.game_data.updater", make_fake_updater_module())
    FakeUpdater.instances.clear()
    return CONTROLLER.GameDataUpdateController()


@pytest.fixture
def ctrl_pending(monkeypatch):
    """带 pending_version 的控制器。"""
    _patch_config_manager(monkeypatch, "v2026.7.1")
    monkeypatch.setitem(sys.modules, "kaa.game_data.updater", make_fake_updater_module())
    return CONTROLLER.GameDataUpdateController()


def _run_check(ctrl, result):
    """设定后台检查结果并启动后台线程，返回线程内创建的 FakeUpdater。"""
    FakeUpdater.default_result = result
    ctrl.startBackgroundCheck()
    _wait_until(lambda: len(FakeUpdater.instances) >= 1)
    return FakeUpdater.instances[-1]


def test_initial_state(ctrl):
    """初始状态：无更新、无重启要求、状态 idle。"""
    assert ctrl.updateStatus == ctrl.STATUS_IDLE
    assert ctrl.updateAvailable is False
    assert ctrl.restartNeeded is False
    assert ctrl.availableVersion == ""


def test_pending_staging_sets_restart_needed(ctrl_pending):
    """存在 pending_version → restartNeeded + READY 状态。"""
    assert ctrl_pending.restartNeeded is True
    assert ctrl_pending.updateStatus == ctrl_pending.STATUS_READY


def test_pending_staging_exception_ignored(monkeypatch):
    """read_shared 抛异常 → 不崩溃，维持 idle。"""
    import kaa.config
    mod = types.ModuleType("kaa.config.manager")
    mod.read_shared = lambda: (_ for _ in ()).throw(RuntimeError("boom"))
    monkeypatch.setitem(sys.modules, "kaa.config.manager", mod)
    monkeypatch.setattr(kaa.config, "manager", mod, raising=False)
    monkeypatch.setitem(sys.modules, "kaa.game_data.updater", make_fake_updater_module())
    c = CONTROLLER.GameDataUpdateController()
    assert c.restartNeeded is False
    assert c.updateStatus == c.STATUS_IDLE


def test_background_no_update(ctrl):
    """无新版本 → 状态回到 idle。"""
    updater = _run_check(ctrl, FakeResult(needs_update=False))
    _wait_until(lambda: ctrl.updateStatus == ctrl.STATUS_IDLE and updater.check_only_calls == 1)
    assert updater.mark_checked_calls == 1
    assert ctrl.updateAvailable is False


def test_background_auto_download(ctrl):
    """有新版本且 auto_update → 下载到 staging，restartNeeded=True。"""
    updater = _run_check(ctrl, FakeResult(auto_update_enabled=True))
    _wait_until(lambda: ctrl.updateStatus == ctrl.STATUS_READY)
    assert ctrl.restartNeeded is True
    assert len(updater.download_calls) == 1
    assert ctrl.updateAvailable is False


def test_background_manual_prompt(ctrl):
    """有新版本但 auto_update 关闭 → 仅提示，不下载。"""
    updater = _run_check(ctrl, FakeResult(auto_update_enabled=False))
    _wait_until(lambda: ctrl.updateAvailable is True)
    assert ctrl.updateStatus == ctrl.STATUS_IDLE
    assert len(updater.download_calls) == 0


def test_background_check_failure(ctrl):
    """check_only 返回 None → FAILED。"""
    _run_check(ctrl, None)
    _wait_until(lambda: ctrl.updateStatus == ctrl.STATUS_FAILED)


def test_trigger_update(ctrl):
    """用户手动触发 → 检查并下载。"""
    _run_check(ctrl, FakeResult(auto_update_enabled=False))
    _wait_until(lambda: ctrl.updateAvailable is True)

    ctrl.triggerUpdate()
    _wait_until(lambda: ctrl.updateStatus == ctrl.STATUS_READY)
    updater = FakeUpdater.instances[-1]
    assert len(updater.download_calls) == 1
    assert ctrl.restartNeeded is True


def test_trigger_update_up_to_date(ctrl):
    """手动触发但已是最新 → 回到 idle。"""
    FakeUpdater.default_result = FakeResult(needs_update=False)
    ctrl.triggerUpdate()
    _wait_until(lambda: len(FakeUpdater.instances) >= 1)
    updater = FakeUpdater.instances[-1]
    assert updater.check_only_calls == 1
    _wait_until(lambda: ctrl.updateStatus == ctrl.STATUS_IDLE)
    assert ctrl.restartNeeded is False


def test_dismiss_and_skip(ctrl):
    """dismissUpdate 清除提醒；skipDownload 设置取消事件。"""
    ctrl._set_update_available(True)
    ctrl.dismissUpdate()
    assert ctrl.updateAvailable is False

    assert ctrl._cancel_event.is_set() is False
    ctrl.skipDownload()
    assert ctrl._cancel_event.is_set() is True


def test_restart_needed_signal(ctrl):
    """restartNeeded 状态变化触发信号。"""
    got = []
    ctrl.restartNeededChanged.connect(lambda v: got.append(v))
    ctrl._set_restart_needed(True)
    ctrl._set_restart_needed(True)  # 不变不重复 emit
    assert got == [True]
