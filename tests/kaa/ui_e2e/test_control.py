from __future__ import annotations
from PySide6.QtCore import QObject
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtTest import QTest
from .conftest import FakeRunController, load_qml, find_text, click


def make_control(
    engine: QQmlApplicationEngine, run: FakeRunController | None = None
) -> tuple[QObject, FakeRunController]:
    run = run or FakeRunController()
    page = load_qml(engine, "pages/ControlPage.qml", properties={"runCtrl": run})
    return page, run


def test_control_start_and_stop_state(qml_engine: QQmlApplicationEngine) -> None:
    page, run = make_control(qml_engine)
    start = find_text(page, "启动")
    assert start.property("enabled")
    click(start)
    assert run.running_state
    assert find_text(page, "停止").property("enabled")
    click(find_text(page, "停止"))
    assert run.stopping_state
    assert not find_text(page, "停止中...").property("enabled")


def test_control_pause_resume(qml_engine: QQmlApplicationEngine) -> None:
    page, run = make_control(qml_engine)
    click(find_text(page, "启动"))
    click(find_text(page, "暂停"))
    assert run.paused_state
    click(find_text(page, "恢复"))
    assert not run.paused_state


def test_control_quick_select_actions(qml_engine: QQmlApplicationEngine) -> None:
    page, run = make_control(qml_engine)
    click(find_text(page, "全选"))
    click(find_text(page, "清空"))
    click(find_text(page, "只选培育"))
    click(find_text(page, "只不选培育"))
    assert ("selectAllTasks", True) in run.calls
    assert ("selectAllTasks", False) in run.calls
    assert ("selectOnlyProduce",) in run.calls
    assert ("selectExceptProduce",) in run.calls


_LEGACY_WARNING = "旧版培育引擎已废弃，请尽快在 设置→培育→培育引擎 切换到新版培育引擎。"


def _legacy_warning(page: QObject) -> QObject:
    return find_text(page, _LEGACY_WARNING)


def test_control_legacy_engine_warning_visible(
    qml_engine: QQmlApplicationEngine,
) -> None:
    page, _ = make_control(qml_engine)
    # 默认 produceEngineLegacy = false，警告应隐藏
    assert _legacy_warning(page).property("visible") is False
    page.setProperty("produceEngineLegacy", True)
    QTest.qWait(30)
    assert _legacy_warning(page).property("visible") is not False


def test_control_legacy_engine_warning_hidden(
    qml_engine: QQmlApplicationEngine,
) -> None:
    page, _ = make_control(qml_engine)
    assert _legacy_warning(page).property("visible") is False


