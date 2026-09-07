from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

from .conftest import (
    KAA_QML_DIR,
    SHELL_QML_DIR,
    FakeGameDataController,
    FakePrefsController,
    find_text,
    find_text_visual,
    load_path,
    click,
)

_PREFERENCES_DIR = KAA_QML_DIR / "pages" / "preferences"


def _telemetry_spec(engine: QQmlApplicationEngine) -> QObject:
    """构造 KAA 遥测偏好 section 的 EuiSectionSpec。"""
    comp = QQmlComponent(engine)
    comp.setData(
        (
            'import EuiShell\n'
            'EuiSectionSpec {\n'
            '    title: "数据收集"\n'
            '    source: TelemetrySection { }\n'
            '}\n'
        ).encode(),
        QUrl.fromLocalFile(str(_PREFERENCES_DIR / "_spec.qml")),
    )
    assert comp.status() == QQmlComponent.Status.Ready, "\n".join(
        e.toString() for e in comp.errors()
    )
    spec = comp.create()
    assert spec is not None
    # spec 由 QML 侧 preferenceSections 持有指针但无所有权,挂到 engine 下防止 Python 局部引用消失后 C++ 对象被回收
    spec.setParent(engine)
    return spec


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
    spec = _telemetry_spec(engine)
    page = load_path(
        engine,
        Path(SHELL_QML_DIR) / "EuiShell" / "pages" / "PreferencesPage.qml",
        properties={"prefsCtrl": prefs, "preferenceSections": [spec]},
        context={"GameDataCtrl": game_data},
    )
    return page, prefs, game_data


def test_preferences_loads_clean(qml_engine: QQmlApplicationEngine) -> None:
    page, prefs, _ = make_preferences(qml_engine)
    assert not page.property("dirty")
    assert not find_text(page, "保存").property("enabled")
    assert prefs.fields == {}


def test_preferences_setfield_marks_dirty_and_binds_section(
    qml_engine: QQmlApplicationEngine,
) -> None:
    page, prefs, _ = make_preferences(qml_engine)
    prefs.setField("telemetry.sentry", True)
    assert prefs.fields["telemetry.sentry"] is True
    assert page.property("dirty")
    assert find_text(page, "保存").property("enabled")
    # 遥测 section 已加载并绑定 prefsCtrl（勾选框反映 base 配置值 False）
    checkbox = find_text_visual(page, "自动发送匿名错误报告")
    assert checkbox is not None


def test_preferences_save_clears_dirty(qml_engine: QQmlApplicationEngine) -> None:
    page, prefs, _ = make_preferences(qml_engine)
    prefs.setField("telemetry.sentry", True)
    click(find_text(page, "保存"))
    assert prefs.save_calls == 1
    assert not page.property("dirty")
