from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem

from .conftest import FakeRunController, click, find_visual, load_qml, qml_variant


def make_tasks(
    engine: QQmlApplicationEngine, run: FakeRunController | None = None
) -> tuple[QObject, FakeRunController]:
    run = run or FakeRunController()
    page = load_qml(engine, "pages/TaskPage.qml", properties={"runCtrl": run})
    return page, run


def test_task_page_lists_tasks(qml_engine: QQmlApplicationEngine) -> None:
    page, run = make_tasks(qml_engine)
    assert qml_variant(page.property("taskNames")) == run.task_names


def test_task_page_starts_selected_task(qml_engine: QQmlApplicationEngine) -> None:
    page, run = make_tasks(qml_engine)
    task_list = page.findChild(QObject, "taskList")
    assert isinstance(task_list, QQuickItem)
    button = find_visual(task_list, "taskStartButton_0")
    click(button)
    assert run.calls[0] == ("runTask", run.task_names[0])


def test_task_page_disables_start_while_running(qml_engine: QQmlApplicationEngine) -> None:
    run = FakeRunController()
    run.start()
    page, _ = make_tasks(qml_engine, run)
    task_list = page.findChild(QObject, "taskList")
    assert isinstance(task_list, QQuickItem)
    button = find_visual(task_list, "taskStartButton_0")
    assert not button.property("enabled")
