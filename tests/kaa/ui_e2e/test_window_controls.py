from __future__ import annotations
from PySide6.QtGui import QWindow
from PySide6.QtQml import QQmlApplicationEngine
from .conftest import load_qml


def test_window_controls_compile_with_window(qml_engine: QQmlApplicationEngine) -> None:
    window = QWindow()
    controls = load_qml(qml_engine, "components/WindowControls.qml", {"window": window})
    assert controls.property("window") is window
    assert controls.property("spacing") == 0


