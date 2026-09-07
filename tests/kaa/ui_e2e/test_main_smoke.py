from __future__ import annotations
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQml import QQmlComponent
from .conftest import KAA_QML_DIR, SHELL_QML_DIR


def test_euishell_app_qml_compiles(qml_engine: QQmlApplicationEngine) -> None:
    """Standalone 框架编译检查：EuiShellApp 作为 ApplicationWindow 可独立编译。"""
    component = QQmlComponent(
        qml_engine, QUrl.fromLocalFile(str(SHELL_QML_DIR / "EuiShell" / "EuiShellApp.qml"))
    )
    assert component.status() == QQmlComponent.Status.Ready, "\n".join(
        e.toString() for e in component.errors()
    )


def test_kaa_index_qml_compiles(qml_engine: QQmlApplicationEngine) -> None:
    """真实组合根编译检查：KAA index.qml 根元素为 EuiShellApp。"""
    component = QQmlComponent(
        qml_engine, QUrl.fromLocalFile(str(KAA_QML_DIR / "index.qml"))
    )
    assert component.status() == QQmlComponent.Status.Ready, "\n".join(
        e.toString() for e in component.errors()
    )
