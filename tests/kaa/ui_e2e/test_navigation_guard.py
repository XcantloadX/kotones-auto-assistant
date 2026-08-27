from __future__ import annotations
from PySide6.QtCore import QObject
from PySide6.QtQml import QQmlApplicationEngine
from .conftest import (
    FakeDialog,
    FakePrefsController,
    FakeSettingsController,
    load_test_qml,
    find,
    click,
)


def make_navigation(
    engine: QQmlApplicationEngine, settings: FakeSettingsController
) -> tuple[QObject, FakeDialog, FakePrefsController]:
    dialog = FakeDialog()
    prefs = FakePrefsController()
    page = load_test_qml(
        engine,
        "NavigationHarness.qml",
        properties={
            "settingsCtrl": settings,
            "produceCtrl": None,
            "prefsCtrl": prefs,
            "dialog": dialog,
        },
    )
    return page, dialog, prefs


def test_clean_navigation_runs_immediately(qml_engine: QQmlApplicationEngine) -> None:
    page, dialog, _ = make_navigation(qml_engine, FakeSettingsController(False))
    click(find(page, "guardedActionButton"))
    assert page.property("actionCount") == 1
    assert not dialog.visible_state


def test_dirty_navigation_opens_guard_dialog(qml_engine: QQmlApplicationEngine) -> None:
    page, dialog, _ = make_navigation(qml_engine, FakeSettingsController(True))
    click(find(page, "guardedActionButton"))
    assert page.property("actionCount") == 0
    assert dialog.visible_state
    assert dialog.action_label_state == "切换页面"


def test_dirty_navigation_save_and_continue(qml_engine: QQmlApplicationEngine) -> None:
    settings = FakeSettingsController(True)
    page, dialog, _ = make_navigation(qml_engine, settings)
    click(find(page, "guardedActionButton"))
    click(find(page, "saveContinueButton"))
    assert settings.save_calls == 1
    assert page.property("actionCount") == 1
    assert not dialog.visible_state


def test_dirty_navigation_discard_and_continue(qml_engine: QQmlApplicationEngine) -> None:
    settings = FakeSettingsController(True)
    page, dialog, _ = make_navigation(qml_engine, settings)
    click(find(page, "guardedActionButton"))
    click(find(page, "discardContinueButton"))
    assert settings.discard_calls == 1
    assert page.property("actionCount") == 1
    assert not dialog.visible_state


