from __future__ import annotations
from PySide6.QtCore import QObject
from PySide6.QtQml import QQmlApplicationEngine
from .conftest import ConfigInfo, FakeDialog, FakeTabManager, load_qml, find, click, qml_variant


def make_overview(
    engine: QQmlApplicationEngine, tab: FakeTabManager | None = None
) -> tuple[QObject, FakeDialog]:
    tab = tab or FakeTabManager()
    dialog = FakeDialog()
    page = load_qml(
        engine,
        "pages/OverviewPage.qml",
        properties={"configManagerDialog": dialog},
        context={"TabManager": tab},
    )
    return page, dialog


def test_empty_overview_opens_config_manager(qml_engine: QQmlApplicationEngine) -> None:
    page, dialog = make_overview(qml_engine)
    assert qml_variant(page.property("_allConfigs")) == []
    click(find(page, "overviewCreateConfigButton"))
    assert dialog.visible_state


def test_overview_renders_configs(qml_engine: QQmlApplicationEngine) -> None:
    tab = FakeTabManager()
    configs: list[ConfigInfo] = [
        {"configName": "A", "tabIndex": 0, "isRunning": False},
        {"configName": "B", "tabIndex": 1, "isRunning": True},
    ]
    tab.set_configs(configs)
    page, _ = make_overview(qml_engine, tab)
    assert qml_variant(page.property("_allConfigs")) == configs


def test_overview_batch_sequential_state(qml_engine: QQmlApplicationEngine) -> None:
    tab = FakeTabManager()
    configs: list[ConfigInfo] = [{"configName": "A", "tabIndex": 0, "isRunning": False}]
    tab.set_configs(configs)
    page, _ = make_overview(qml_engine, tab)
    click(find(page, "overviewSequentialButton"))
    assert tab.batch_mode_state == "sequential"
    assert find(page, "overviewSequentialButton").property("enabled")


def test_overview_batch_parallel_state(qml_engine: QQmlApplicationEngine) -> None:
    tab = FakeTabManager()
    configs: list[ConfigInfo] = [{"configName": "A", "tabIndex": 0, "isRunning": False}]
    tab.set_configs(configs)
    page, _ = make_overview(qml_engine, tab)
    click(find(page, "overviewParallelButton"))
    assert tab.batch_mode_state == "parallel"
    assert find(page, "overviewParallelButton").property("enabled")


