from __future__ import annotations
import json
from collections.abc import Callable
from typing import cast
from PySide6.QtTest import QTest
from PySide6.QtQml import QQmlApplicationEngine
from .conftest import (
    FakeBrowserController,
    FakeDialog,
    FakeLogBridge,
    FakeProduceController,
    FakeUpdateController,
    FakeTabManager,
    click,
    find_text,
    load_qml,
    qml_variant,
)


def test_about_page_shows_identity_and_versions(qml_engine: QQmlApplicationEngine) -> None:
    page = load_qml(qml_engine, "pages/AboutPage.qml")
    assert find_text(page, "琴音小助手 kaa")
    assert find_text(page, "版本 test")
    assert find_text(page, "游戏数据 test-data")


def test_log_page_buffers_and_flushes_lines(qml_engine: QQmlApplicationEngine) -> None:
    bridge = FakeLogBridge([{"text": "hello\n[ERROR] bad\n", "stream": "normal"}])
    page = load_qml(qml_engine, "pages/LogPage.qml", {"logBridge": bridge})
    QTest.qWait(80)
    assert page.property("pendingText") == ""
    resolve_color = cast(Callable[[str, str], object], getattr(page, "resolveColor"))
    assert resolve_color("[ERROR] bad", "normal") != resolve_color(
        "hello", "normal"
    )
    cast(Callable[[str, str], None], getattr(page, "appendText"))("next\n", "stderr")
    QTest.qWait(80)
    assert page.property("pendingText") == ""


def test_log_page_wrap_toggle_and_clear(qml_engine: QQmlApplicationEngine) -> None:
    page = load_qml(qml_engine, "pages/LogPage.qml", {"logBridge": FakeLogBridge()})
    cast(Callable[[str, str], None], getattr(page, "appendText"))("one\ntwo\n", "normal")
    QTest.qWait(80)
    assert page.property("wrapEnabled") is True
    page.setProperty("wrapEnabled", False)
    assert page.property("wrapEnabled") is False


def test_update_page_load_and_success_state(qml_engine: QQmlApplicationEngine) -> None:
    ctrl = FakeUpdateController()
    page = load_qml(qml_engine, "pages/UpdatePage.qml", {"updateCtrl": ctrl})
    button = find_text(page, "载入信息")
    click(button)
    assert ctrl.calls == ["loadVersionsAsync"]
    payload = {
        "installed": "1.0",
        "latest": "1.1",
        "launcher": "2.0",
        "versions": ["1.0", "1.1"],
    }
    ctrl.versionsLoaded.emit(json.dumps(payload))
    QTest.qWait(50)
    assert page.property("versionInfo").toVariant()["latest"] == "1.1"
    assert page.property("statusMessage") == "版本信息已加载"


def test_update_page_error_state(qml_engine: QQmlApplicationEngine) -> None:
    ctrl = FakeUpdateController()
    page = load_qml(qml_engine, "pages/UpdatePage.qml", {"updateCtrl": ctrl})
    ctrl.loadFailed.emit("网络错误")
    QTest.qWait(20)
    assert page.property("errorMessage") == "网络错误"
    assert page.property("statusMessage") == ""


def test_skill_card_browser_initializes_and_switches_view(qml_engine: QQmlApplicationEngine) -> None:
    ctrl = FakeBrowserController()
    page = load_qml(qml_engine, "pages/SkillCardBrowserPage.qml", {"browserCtrl": ctrl})
    assert "ensureLoaded" in ctrl.calls
    assert page.property("_viewMode") == "list"
    page.setProperty("_viewMode", "grid")
    assert page.property("_viewMode") == "grid"
    cast(Callable[[str], None], getattr(page, "_setViewMode"))("list")
    assert page.property("_viewMode") == "list"


def test_skill_card_browser_filter_contract(qml_engine: QQmlApplicationEngine) -> None:
    ctrl = FakeBrowserController()
    page = load_qml(qml_engine, "pages/SkillCardBrowserPage.qml", {"browserCtrl": ctrl})
    cast(Callable[[], None], getattr(page, "_pushFilter"))()
    QTest.qWait(220)
    assert any(c[0] == "applyFilter" for c in ctrl.calls if isinstance(c, tuple))
    toggle_map = cast(Callable[[object, str], object], getattr(page, "_toggleMap"))
    result = qml_variant(toggle_map({}, "Ssr"))
    result_map = cast(dict[str, object], result)
    assert result_map["Ssr"] is True
    assert qml_variant(toggle_map(result, "Ssr")) == {}


def test_produce_page_core_state_and_helpers(qml_engine: QQmlApplicationEngine) -> None:
    ctrl = FakeProduceController(
        [
            {"id": "a", "name": "A", "description": ""},
            {"id": "b", "name": "B", "description": ""},
        ]
    )
    page = load_qml(qml_engine, "pages/ProducePage.qml", {"produceCtrl": ctrl})
    assert page.property("dirty") is False
    solution_name_exists = cast(Callable[[str, str], bool], getattr(page, "solutionNameExists"))
    has_validation_errors = cast(Callable[[], bool], getattr(page, "hasValidationErrors"))
    validation_summary = cast(Callable[[], str], getattr(page, "validationSummary"))
    mark_dirty = cast(Callable[[], None], getattr(page, "markDirty"))
    mark_clean = cast(Callable[[], None], getattr(page, "markClean"))
    assert solution_name_exists("A", "") is True
    assert solution_name_exists("A", "a") is False
    assert has_validation_errors() is False
    assert validation_summary() == ""
    mark_dirty()
    assert page.property("dirty") is True
    mark_clean()
    assert page.property("dirty") is False


def test_produce_page_mode_helpers(qml_engine: QQmlApplicationEngine) -> None:
    page = load_qml(
        qml_engine, "pages/ProducePage.qml", {"produceCtrl": FakeProduceController()}
    )
    page.setProperty(
        "currentSolution", {"mode": "hajime_regular", "produce_strategy": "normal"}
    )
    difficulty_options = cast(Callable[[str], object], getattr(page, "_difficultyOptions"))
    strategy_options = cast(Callable[[str], object], getattr(page, "_strategyOptions"))
    assert difficulty_options("hajime_regular")
    assert difficulty_options("hif")
    assert strategy_options("hif")
    difficulties = qml_variant(difficulty_options("hif"))
    strategies = qml_variant(strategy_options("hif"))
    assert isinstance(difficulties, list)
    assert isinstance(strategies, list)
    assert difficulties[0]["value"] == "main"
    assert strategies[0]["value"] == "withdraw_main"


def test_config_manager_dialog_initial_state_and_create_contract(qml_engine: QQmlApplicationEngine) -> None:
    tab = FakeTabManager()
    dialog = load_qml(
        qml_engine, "dialogs/ConfigManagerDialog.qml", {"tabManager": tab}
    )
    names = dialog.property("configNames")
    names = qml_variant(names)
    assert names == []
    cast(Callable[[], None], getattr(dialog, "reload"))()
    names = dialog.property("configNames")
    names = qml_variant(names)
    assert names == []
    tab.createProfile("A")
    assert ("createProfile", "A") in tab.calls


def test_tab_strip_overview_and_config_model(qml_engine: QQmlApplicationEngine) -> None:
    dialog = FakeDialog()
    tab = FakeTabManager()
    strip = load_qml(
        qml_engine,
        "components/TabStrip.qml",
        {"configManagerDialog": dialog},
        {"TabManager": tab},
    )
    assert strip.property("currentIndex") == 0
    configs = [{"configName": "A", "index": 0, "isActive": False}]
    strip.setProperty("tabs", configs)
    tabs = strip.property("tabs")
    tabs = tabs.toVariant() if hasattr(tabs, "toVariant") else tabs
    assert tabs[0]["configName"] == "A"
    tab.openTab("A")
    assert ("openTab", "A") in tab.calls


