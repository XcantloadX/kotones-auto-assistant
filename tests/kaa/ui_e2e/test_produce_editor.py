"""使用真实控制器和独立的方案文件验证 QML 编辑器。"""
from collections.abc import Callable, Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any, TYPE_CHECKING, TypeAlias, cast
import json

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QObject, Qt, Slot
from PySide6.QtGui import QKeyEvent
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest

from kaa.application.services.produce_solution_service import ProduceSolutionService
from kaa.application.ui.controllers.produce_controller import ProduceController
from kaa.config.produce import ProduceData, ProduceSolution, ProduceSolutionManager
from .conftest import FakeDialog, click, load_qml, load_test_qml, find, qml_variant

if TYPE_CHECKING:
    from kaa.application.ui.kaa_session import KaaSession


class EditorController(ProduceController):
    """仅替换外部游戏数据列表，方案增删改查和校验均使用真实实现。"""

    @Slot(result=str)
    def idolCardsJson(self) -> str:
        return "[]"

    @Slot(result=str)
    def cardDecksJson(self) -> str:
        return '[{"name": "Test deck", "value": "test-deck"}]'


Editor: TypeAlias = tuple[QQuickItem, EditorController, ProduceSolutionService, QQuickWindow, Path]


def call(obj: QObject, method: str, *args: object) -> None:
    cast(Callable[..., object], getattr(obj, method))(*args)


def items(root: QQuickItem) -> Iterator[QQuickItem]:
    yield root
    for child in root.childItems():
        yield from items(child)


def by_property(root: QObject, key: str, value: object) -> QObject:
    return next(obj for obj in root.findChildren(QObject) if obj.property(key) == value)


def button(root: QObject, text: str) -> QObject:
    return next(obj for obj in root.findChildren(QObject)
                if obj.property("text") == text and obj.metaObject().indexOfMethod("click()") >= 0)


def input_for(page: QObject, field: str) -> QQuickItem:
    form = by_property(page, "field", field)
    return next(obj for obj in form.findChildren(QQuickItem) if obj.inherits("QQuickTextField"))


def enter(window: QQuickWindow, editor: QQuickItem, text: str) -> None:
    """发送真实键盘事件，不直接设置 QML 文本或触发 textEdited 信号。"""
    editor.forceActiveFocus()
    QTest.keyClick(window, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier)
    for char in text:
        modifiers = Qt.KeyboardModifier.ShiftModifier if char.isupper() else Qt.KeyboardModifier.NoModifier
        for event_type in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            QCoreApplication.sendEvent(window, QKeyEvent(event_type, ord(char.upper()), modifiers, char))


def current(page: QObject) -> dict[str, Any]:
    return cast(dict[str, Any], qml_variant(page.property("currentSolution")))


def row(page: QQuickItem, name: str) -> QQuickItem:
    return next(item for item in items(page)
                if item.inherits("QQuickItemDelegate")
                and any(child.property("text") == name for child in items(item)))


@pytest.fixture
def editor(qml_engine: QQmlApplicationEngine, monkeypatch: pytest.MonkeyPatch,
           tmp_path: Path, request: pytest.FixtureRequest) -> Iterator[Editor]:
    # 方案管理器是单例，测试需同时隔离文件目录和缓存，避免影响实际配置。
    monkeypatch.setattr(ProduceSolutionManager, "_instance", None)
    monkeypatch.setattr(ProduceSolutionManager, "SOLUTIONS_DIR", str(tmp_path))
    service = ProduceSolutionService()
    for sid, number in (("First", 2), ("Second", 7)):
        data = ProduceData(idol="test-idol", memory_set=number, support_card_set=number)
        if getattr(request, "param", None) == "validation" and sid == "First":
            data.idol = None
        service.save_solution(ProduceSolution(id=sid, name=sid, data=data))
    controller = EditorController(cast("KaaSession", SimpleNamespace(produce_solution_service=service, config_service=None)))
    page = cast(QQuickItem, load_qml(qml_engine, "pages/ProducePage.qml", {"produceCtrl": controller}))
    window = QQuickWindow()
    window.resize(1200, 900)
    page.setParentItem(window.contentItem())
    page.setWidth(1200)
    page.setHeight(900)
    window.show()
    call(page, "selectSolution", "First")
    QTest.qWait(20)
    yield page, controller, service, window, tmp_path
    page.setParentItem(None)  # pyright: ignore[reportArgumentType] -- Qt 运行时允许父项为空，此处类型存根未标注。
    window.close()


@pytest.mark.parametrize("field", ["memory_set", "support_card_set"])
def test_number_save_switch_and_disk_isolation(editor: Editor, field: str) -> None:
    page, controller, service, window, directory = editor
    untouched = (directory / "Second.json").read_bytes()
    number = input_for(page, field)
    assert number.property("text") == "2"
    enter(window, number, "12")
    assert controller.isDirty()
    # 焦点仍在输入框中时，通过真实控制器信号保存。
    assert number.hasActiveFocus()
    assert controller.save()
    assert json.loads((directory / "First.json").read_text(encoding="utf-8"))["data"][field] == 12
    assert (directory / "Second.json").read_bytes() == untouched
    # 失焦也会执行归一化，此时必须保留数据绑定。
    page.forceActiveFocus()
    assert not controller.isDirty()
    for sid, value in (("Second", "7"), ("First", "12"), ("Second", "7")):
        click(row(page, sid))
        assert number.property("text") == value
    assert service.get_solution("First").data.model_dump()[field] == 12


@pytest.mark.parametrize("editor", ["write", "validation", "name"], indirect=True)
def test_failed_save_keeps_draft_and_can_retry(editor: Editor, monkeypatch: pytest.MonkeyPatch,
                                              request: pytest.FixtureRequest) -> None:
    page, controller, service, window, directory = editor
    failure = cast(pytest.Function, request.node).callspec.params["editor"]
    before = {p.name: p.read_bytes() for p in directory.glob("*.json")}
    name = input_for(page, "name")
    enter(window, name, "Second" if failure == "name" else "Edited")
    original_save = service.save_solution
    if failure == "write":
        def fail(_solution: ProduceSolution) -> None:
            raise OSError("simulated write failure")
        monkeypatch.setattr(service, "save_solution", fail)
    click(row(page, "Second"))
    dialog = by_property(page, "title", "提示")
    click(button(dialog, "保存"))
    assert current(page)["id"] == "First"
    assert controller.isDirty()
    assert dialog.property("visible") is True
    assert {p.name: p.read_bytes() for p in directory.glob("*.json")} == before
    if failure == "write":
        monkeypatch.setattr(service, "save_solution", original_save)
        click(button(dialog, "保存"))
        assert current(page)["id"] == "Second"
        assert not controller.isDirty()
        assert service.get_solution("First").name == "Edited"


@pytest.mark.parametrize("choice", ["丢弃", "继续编辑"])
def test_switch_confirmation_preserves_or_discards_only_as_requested(editor: Editor, choice: str) -> None:
    page, controller, service, window, _ = editor
    enter(window, input_for(page, "name"), "Edited")
    click(row(page, "Second"))
    click(button(by_property(page, "title", "提示"), choice))
    assert current(page)["id"] == ("First" if choice == "继续编辑" else "Second")
    assert controller.isDirty() is (choice == "继续编辑")
    assert service.get_solution("First").name == "First"


def test_clicking_current_row_preserves_draft(editor: Editor) -> None:
    page, controller, _, window, _ = editor
    enter(window, input_for(page, "name"), "Edited")
    click(row(page, "First"))
    assert current(page)["name"] == "Edited"
    assert controller.isDirty()


@pytest.mark.parametrize("operation", ["new", "copy"])
def test_new_and_copy_require_unsaved_confirmation(editor: Editor, operation: str) -> None:
    page, controller, service, window, _ = editor
    enter(window, input_for(page, "name"), "Edited")
    source_row = row(page, "Second")
    target = button(page, "新建培育") if operation == "new" else button(source_row, "⧉")
    click(target)
    assert by_property(page, "title", "提示").property("visible") is True
    assert len(service.list_solutions()) == 2
    assert controller.isDirty()


def test_copy_button_copies_its_row_and_persists_name(editor: Editor) -> None:
    page, _, service, window, _ = editor
    source_row = row(page, "Second")
    click(button(source_row, "⧉"))
    dialog = by_property(page, "title", "复制培育方案")
    name = next(obj for obj in dialog.findChildren(QQuickItem) if obj.inherits("QQuickTextField"))
    enter(window, name, "Copied")
    click(button(dialog, "确定"))
    copied = service.get_solution(current(page)["id"])
    assert copied.name == "Copied"
    assert copied.data.memory_set == 7
    assert len(service.list_solutions()) == 3


def test_failed_delete_preserves_editor_and_file(editor: Editor, monkeypatch: pytest.MonkeyPatch) -> None:
    page, controller, service, window, directory = editor
    before = (directory / "First.json").read_bytes()
    enter(window, input_for(page, "name"), "Edited")
    def fail(_sid: str) -> None:
        raise OSError("simulated delete failure")
    monkeypatch.setattr(service, "delete_solution", fail)
    call(page, "deleteSolution", "First")
    assert current(page)["name"] == "Edited"
    assert controller.isDirty()
    assert (directory / "First.json").read_bytes() == before


def test_action_candidate_list_refreshes_and_saves(editor: Editor) -> None:
    page, controller, service, _, _ = editor
    dialog = by_property(page, "title", "行动优先级")
    combo = by_property(dialog, "textRole", "display_name")
    combo.setProperty("currentIndex", 0)
    value = combo.property("currentValue")
    click(button(dialog, "添加"))
    assert value not in [item["value"] for item in cast(list[dict[str, str]], qml_variant(combo.property("model")))]
    assert controller.save()
    assert value in [action.value for action in service.get_solution("First").data.actions_order]


def test_navigation_waits_for_real_save_to_succeed(editor: Editor, qml_engine: QQmlApplicationEngine,
                                                 monkeypatch: pytest.MonkeyPatch) -> None:
    page, controller, service, window, _ = editor
    enter(window, input_for(page, "name"), "Edited")
    original_save = service.save_solution
    def fail(_solution: ProduceSolution) -> None:
        raise OSError("simulated write failure")
    monkeypatch.setattr(service, "save_solution", fail)
    dialog = FakeDialog()
    navigation = load_test_qml(qml_engine, "NavigationHarness.qml", {
        "settingsCtrl": None, "produceCtrl": controller, "prefsCtrl": None, "dialog": dialog,
    })
    click(find(navigation, "guardedActionButton"))
    coordinator = next(obj for obj in navigation.findChildren(QObject)
                       if obj.metaObject().indexOfMethod("saveAndContinuePendingAction()") >= 0)
    call(coordinator, "saveAndContinuePendingAction")
    assert navigation.property("actionCount") == 0
    assert controller.isDirty()
    assert coordinator.property("pendingActionLabel") == "切换页面"
    monkeypatch.setattr(service, "save_solution", original_save)
    call(coordinator, "saveAndContinuePendingAction")
    assert navigation.property("actionCount") == 1
    assert not controller.isDirty()
    assert service.get_solution("First").name == "Edited"


def test_automatic_deck_selection_round_trips(editor: Editor) -> None:
    page, controller, service, window, _ = editor
    form = by_property(page, "field", "card_deck_id")
    combo = next(obj for obj in form.findChildren(QQuickItem) if obj.inherits("QQuickComboBox"))
    assert combo.property("currentIndex") == 0
    combo.forceActiveFocus()
    QTest.keyClick(window, Qt.Key.Key_Down)
    assert controller.isDirty()
    assert controller.save()
    assert service.get_solution("First").data.card_deck_id == "test-deck"
    click(row(page, "Second"))
    assert combo.property("currentIndex") == 0


def test_copy_rename_failure_retains_unsaved_name(editor: Editor, monkeypatch: pytest.MonkeyPatch) -> None:
    page, controller, service, window, _ = editor
    original_save = service.save_solution
    def fail_rename(solution: ProduceSolution) -> None:
        if solution.name == "Copied":
            raise OSError("simulated rename save failure")
        original_save(solution)
    monkeypatch.setattr(service, "save_solution", fail_rename)
    source_row = row(page, "Second")
    click(button(source_row, "⧉"))
    dialog = by_property(page, "title", "复制培育方案")
    name = next(obj for obj in dialog.findChildren(QQuickItem) if obj.inherits("QQuickTextField"))
    enter(window, name, "Copied")
    click(button(dialog, "确定"))
    assert controller.isDirty()
    assert current(page)["name"] == "Copied"
    assert service.get_solution(current(page)["id"]).name != "Copied"


@pytest.mark.parametrize("operation", ["new", "copy"])
@pytest.mark.parametrize("choice", ["保存", "丢弃"])
def test_pending_creation_survives_save_model_reset(editor: Editor, operation: str, choice: str) -> None:
    page, controller, service, window, _ = editor
    enter(window, input_for(page, "name"), "Edited")
    source_row = row(page, "Second")
    target = button(page, "新建培育") if operation == "new" else button(source_row, "⧉")
    click(target)
    click(button(by_property(page, "title", "提示"), choice))
    next_dialog = by_property(page, "title", "新建培育方案" if operation == "new" else "复制培育方案")
    assert next_dialog.property("visible") is True
    assert not controller.isDirty()
    assert service.get_solution("First").name == ("Edited" if choice == "保存" else "First")
    if operation == "copy":
        assert next_dialog.property("sourceId") == "Second"
