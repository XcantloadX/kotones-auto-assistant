from __future__ import annotations
from PySide6.QtQml import QQmlApplicationEngine
import pytest
from .conftest import DummyController, load_qml


@pytest.mark.parametrize(
    "filename",
    [
        "dialogs/ExportReportDialog.qml",
        "dialogs/ReportExportResultDialog.qml",
    ],
)
def test_report_dialogs_compile(qml_engine: QQmlApplicationEngine, filename: str) -> None:
    dialog = load_qml(qml_engine, filename)
    assert dialog is not None


def test_school_event_inspector_dialog_compiles(qml_engine: QQmlApplicationEngine) -> None:
    dialog = load_qml(
        qml_engine,
        "dialogs/SchoolEventInspectorDialog.qml",
        {"debugInspectorCtrl": DummyController()},
    )
    assert dialog is not None


def test_idol_picker_dialog_compiles(qml_engine: QQmlApplicationEngine) -> None:
    dialog = load_qml(qml_engine, "components/IdolPickerDialog.qml")
    assert dialog is not None


