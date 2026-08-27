from __future__ import annotations
from PySide6.QtCore import QObject
from PySide6.QtQml import QQmlApplicationEngine
from .conftest import (
    FakeRunController,
    FakeSettingsController,
    load_qml,
    find,
    click,
)


def make_settings(
    engine: QQmlApplicationEngine,
    settings: FakeSettingsController | None = None,
    run: FakeRunController | None = None,
) -> tuple[QObject, FakeSettingsController, FakeRunController]:
    settings = settings or FakeSettingsController()
    run = run or FakeRunController()
    page = load_qml(
        engine,
        "pages/SettingsPage.qml",
        properties={"settingsCtrl": settings, "runCtrl": run},
    )
    return page, settings, run


def test_settings_initial_save_disabled(qml_engine: QQmlApplicationEngine) -> None:
    page, _, _ = make_settings(qml_engine)
    assert not find(page, "settingsSaveButton").property("enabled")
    assert not page.property("dirty")


def test_settings_dirty_enables_save(qml_engine: QQmlApplicationEngine) -> None:
    page, settings, _ = make_settings(qml_engine)
    settings.set_dirty(True)
    assert page.property("dirty")
    assert find(page, "settingsSaveButton").property("enabled")


def test_settings_save_clears_dirty(qml_engine: QQmlApplicationEngine) -> None:
    page, settings, _ = make_settings(qml_engine)
    settings.set_dirty(True)
    click(find(page, "settingsSaveButton"))
    assert settings.save_calls == 1
    assert not page.property("dirty")
    assert not find(page, "settingsSaveButton").property("enabled")


def test_settings_tabs_switch(qml_engine: QQmlApplicationEngine) -> None:
    page, _, _ = make_settings(qml_engine)
    assert page.property("dirty") is False


def test_settings_validation_blocks_save(qml_engine: QQmlApplicationEngine) -> None:
    settings = FakeSettingsController(
        validation=[
            {"field": "emulator.type", "severity": "error", "message": "invalid"}
        ]
    )
    page, settings, _ = make_settings(qml_engine, settings=settings)
    settings.set_dirty(True)
    click(find(page, "settingsSaveButton"))
    assert settings.save_calls == 0
    assert page.property("dirty")


