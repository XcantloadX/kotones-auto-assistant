from __future__ import annotations
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQml import QQmlComponent
from PySide6.QtQml import QQmlApplicationEngine
from .conftest import SHELL_QML_DIR


def test_main_qml_compiles(qml_engine: QQmlApplicationEngine) -> None:
    component = QQmlComponent(qml_engine, QUrl.fromLocalFile(str(SHELL_QML_DIR / "EuiShell" / "main.qml")))
    assert component.status() == QQmlComponent.Status.Ready, "\n".join(
        e.toString() for e in component.errors()
    )


