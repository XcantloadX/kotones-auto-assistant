from __future__ import annotations
from PySide6.QtCore import QObject
from PySide6.QtQml import QQmlApplicationEngine
from .conftest import (
    FakeGameDataController,
    FakePrefsController,
    find_text,
    load_qml,
    click,
)


def make_preferences(
    engine: QQmlApplicationEngine,
) -> tuple[QObject, FakePrefsController, FakeGameDataController]:
    prefs = FakePrefsController(
        config={
            "telemetry": {
                "sentry": False,
                "upload_screenshot": False,
                "statics": False,
            },
            "interface": {
                "window_style": "",
                "color_scheme": "auto",
                "startup_page": "last_opened",
                "theme_color": "",
            },
            "misc": {
                "check_update": "startup",
                "auto_install_update": False,
                "update_channel": "release",
                "game_data_check": "startup",
                "game_data_auto_update": False,
            },
        }
    )
    game_data = FakeGameDataController()
    page = load_qml(
        engine,
        "pages/PreferencesPage.qml",
        properties={"prefsCtrl": prefs},
        context={"GameDataCtrl": game_data},
    )
    return page, prefs, game_data


def test_preferences_loads_clean(qml_engine: QQmlApplicationEngine) -> None:
    page, prefs, _ = make_preferences(qml_engine)
    assert not page.property("dirty")
    assert not find_text(page, "保存").property("enabled")
    assert prefs.fields == {}


def test_preferences_checkbox_changes_mark_dirty(qml_engine: QQmlApplicationEngine) -> None:
    page, prefs, _ = make_preferences(qml_engine)
    checkbox = find_text(page, "自动发送匿名错误报告")
    click(checkbox)
    assert prefs.fields["telemetry.sentry"] is True
    assert page.property("dirty")
    assert find_text(page, "保存").property("enabled")


def test_preferences_save_clears_dirty(qml_engine: QQmlApplicationEngine) -> None:
    page, prefs, _ = make_preferences(qml_engine)
    click(find_text(page, "自动发送匿名错误报告"))
    click(find_text(page, "保存"))
    assert prefs.save_calls == 1
    assert not page.property("dirty")


