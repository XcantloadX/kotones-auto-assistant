from __future__ import annotations
from collections.abc import Generator, Mapping
from typing import Protocol, TypeAlias, TypedDict, cast, runtime_checkable
import json
import os
from pathlib import Path
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl, Qt, QMetaObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlEngine, qmlRegisterSingletonType
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

ROOT = Path(__file__).resolve().parents[3]
QML_DIR = ROOT / "kaa" / "application" / "ui" / "qml"
TEST_DIR = ROOT / "tests" / "kaa" / "ui_e2e"

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


class ConfigInfo(TypedDict, total=False):
    name: str
    path: str
    id: str
    configName: str
    tabIndex: int
    isRunning: bool


class SolutionInfo(TypedDict, total=False):
    id: str
    name: str
    description: str


Call: TypeAlias = tuple[object, ...] | str


class DummyController(QObject):
    def __init__(self) -> None:
        super().__init__()
        self._window_style = "solid"

    windowStyle = Property(str, lambda s: s._window_style)

    @Slot(str, str)
    def show(self, *_args: str) -> None:
        pass


class FakeDialog(QObject):
    opened = Signal()
    closed = Signal()
    actionLabelChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._visible = False
        self._action_label = ""

    visible = Property(
        bool, lambda s: s._visible, lambda s, v: s._set_visible(v), notify=opened
    )
    actionLabel = Property(
        str,
        lambda s: s._action_label,
        lambda s, v: s._set_action_label(v),
        notify=actionLabelChanged,
    )

    @property
    def visible_state(self) -> bool:
        return self._visible

    @property
    def action_label_state(self) -> str:
        return self._action_label

    def _set_visible(self, v: bool) -> None:
        v = bool(v)
        if self._visible != v:
            self._visible = v
            (self.opened if v else self.closed).emit()

    def _set_action_label(self, v: str) -> None:
        self._action_label = str(v)
        self.actionLabelChanged.emit()

    @Slot()
    def open(self) -> None:
        self._set_visible(True)

    @Slot()
    def close(self) -> None:
        self._set_visible(False)

    @Slot()
    def accept(self) -> None:
        self._set_visible(False)

    @Slot()
    def reject(self) -> None:
        self._set_visible(False)


class FakeTabManager(QObject):
    tabsChanged = Signal()
    activeTabChanged = Signal()
    batchModeChanged = Signal()
    stopAllBusyChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._configs: list[ConfigInfo] = []
        self._batch_mode = ""
        self._stop_busy = False
        self.calls: list[Call] = []

    batchMode = Property(str, lambda s: s._batch_mode, notify=batchModeChanged)
    stopAllBusy = Property(bool, lambda s: s._stop_busy, notify=stopAllBusyChanged)

    @Slot(result=str)
    def allConfigsJson(self) -> str:
        return json.dumps(self._configs, ensure_ascii=False)

    @Slot(str)
    def openTab(self, n: str) -> None:
        self.calls.append(("openTab", str(n)))

    @Slot(int)
    def setActiveTab(self, i: int) -> None:
        self.calls.append(("setActiveTab", int(i)))

    @Slot(str)
    def createProfile(self, n: str) -> None:
        self.calls.append(("createProfile", str(n)))

    @Slot(str, str)
    def renameProfile(self, a: str, b: str) -> None:
        self.calls.append(("renameProfile", str(a), str(b)))

    @Slot(str, result=bool)
    def closeTabForConfig(self, n: str) -> bool:
        self.calls.append(("closeTabForConfig", str(n)))
        return True

    @Slot(str)
    def deleteProfile(self, n: str) -> None:
        self.calls.append(("deleteProfile", str(n)))

    @Slot(result=str)
    def availableConfigsJson(self) -> str:
        return "[]"

    @Slot()
    def startAllSequential(self) -> None:
        self.calls.append(("startAllSequential",))
        self._set_batch("sequential")

    @Slot()
    def startAllParallel(self) -> None:
        self.calls.append(("startAllParallel",))
        self._set_batch("parallel")

    @Slot()
    def stopAll(self) -> None:
        self.calls.append(("stopAll",))
        self._set_batch("")

    def _set_batch(self, v: str) -> None:
        self._batch_mode = v
        self.batchModeChanged.emit()

    @property
    def batch_mode_state(self) -> str:
        return self._batch_mode

    def set_configs(self, c: list[ConfigInfo]) -> None:
        self._configs = list(c)
        self.tabsChanged.emit()


class FakeSettingsController(QObject):
    dirtyChanged = Signal(bool)
    configChanged = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)

    def __init__(
        self,
        dirty: bool = False,
        validation: list[dict[str, JsonValue]] | None = None,
        config: dict[str, JsonValue] | None = None,
    ) -> None:
        super().__init__()
        self._dirty = dirty
        self.validation: list[dict[str, JsonValue]] = validation or []
        self.save_calls = 0
        self.discard_calls = 0
        self.fields: dict[str, JsonValue] = {}
        self.sharedCtrl = self
        self._config: dict[str, JsonValue] = config or {}

    dirty = Property(bool, lambda s: s._dirty, notify=dirtyChanged)
    config = Property(object, lambda s: s._config, notify=configChanged)

    @Slot(result=str)
    def validateJson(self) -> str:
        return json.dumps(self.validation, ensure_ascii=False)

    @Slot(result=bool)
    def save(self) -> bool:
        self.save_calls += 1
        if any(x.get("severity") == "error" for x in self.validation):
            self.operationFailed.emit("validation failed")
            return False
        self.set_dirty(False)
        self.operationSucceeded.emit("保存成功")
        return True

    @Slot()
    def discard(self) -> None:
        self.discard_calls += 1
        self.set_dirty(False)

    @Slot(result=bool)
    def isDirty(self) -> bool:
        return self._dirty

    @Slot(str, "QVariant")
    def setField(self, p: str, v: JsonValue) -> None:
        self.fields[str(p)] = v
        self.set_dirty(True)

    @Slot(str, "QVariant")
    def setListField(self, p: str, v: JsonValue) -> None:
        self.fields[str(p)] = v
        self.set_dirty(True)

    @Slot(str)
    def listEmulatorInstancesAsync(self, _value: str) -> None:
        pass

    @Slot(result=str)
    def moneyShopItemsJson(self) -> str:
        return "[]"

    @Slot(result=str)
    def apShopItemsJson(self) -> str:
        return "[]"

    @Slot(result=str)
    def noteItemsJson(self) -> str:
        return "[]"

    @Slot(result=str)
    def produceSolutionsJson(self) -> str:
        return "[]"

    @Slot()
    def resetGameWindow(self) -> None:
        pass

    def set_dirty(self, v: bool) -> None:
        v = bool(v)
        if self._dirty != v:
            self._dirty = v
            self.dirtyChanged.emit(v)


class FakePrefsController(FakeSettingsController):
    pass


class FakeGameDataController(QObject):
    updateStatusChanged = Signal()
    progressMessageChanged = Signal()
    restartNeededChanged = Signal()
    currentVersionChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._status = "idle"
        self._message = ""
        self._restart = False
        self._version = "test-data"
        self.calls: list[str] = []

    updateStatus = Property(str, lambda s: s._status, notify=updateStatusChanged)
    progressMessage = Property(str, lambda s: s._message, notify=progressMessageChanged)
    restartNeeded = Property(bool, lambda s: s._restart, notify=restartNeededChanged)
    currentVersion = Property(str, lambda s: s._version, notify=currentVersionChanged)
    buildPercent = Property(float, lambda s: 0.0)
    buildMessage = Property(str, lambda s: "")
    downloadFiles = Property(list, lambda s: [])

    @Slot()
    def triggerUpdate(self) -> None:
        self.calls.append("triggerUpdate")

    @Slot()
    def skipDownload(self) -> None:
        self.calls.append("skipDownload")

    @Slot()
    def checkForUpdates(self) -> None:
        self.calls.append("checkForUpdates")

    @Slot()
    def cancelUpdate(self) -> None:
        self.calls.append("cancelUpdate")


class FakeUpdateController(QObject):
    versionsLoaded = Signal(str)
    loadFailed = Signal(str)
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[Call] = []
        self._changelog = "## Test\n- changelog"
        self._loading = False

    @Property(str, constant=True)
    def changelog(self) -> str:
        return self._changelog

    @Slot()
    def loadVersionsAsync(self) -> None:
        self.calls.append("loadVersionsAsync")

    @Slot(str)
    def installVersion(self, v: str) -> None:
        self.calls.append(("installVersion", str(v)))

    @Slot(result=str)
    def changelogText(self) -> str:
        return self._changelog


class FakeBrowserController(QObject):
    indexReady = Signal()
    staticIconsChanged = Signal()
    pageReset = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[Call] = []
        self._indexLoaded = True
        self._loading = False
        self._loadingMore = False
        self._hasMore = False
        self._total = 0

    indexLoaded = Property(bool, lambda s: s._indexLoaded)
    loading = Property(bool, lambda s: s._loading)
    loadingMore = Property(bool, lambda s: s._loadingMore)
    hasMore = Property(bool, lambda s: s._hasMore)
    totalCount = Property(int, lambda s: s._total)

    @Slot()
    def ensureLoaded(self) -> None:
        self.calls.append("ensureLoaded")

    @Slot(result=str)
    def staticIconsJson(self) -> str:
        return "{}"

    @Slot(str, str, str, str, str)
    def applyFilter(self, a: str, b: str, c: str, d: str, e: str) -> None:
        args = (a, b, c, d, e)
        self.calls.append(("applyFilter",) + tuple(str(x) for x in args))

    @Slot()
    def loadMore(self) -> None:
        self.calls.append("loadMore")


class FakeLogBridge(QObject):
    textWritten = Signal(str, str)

    def __init__(self, entries: list[JsonValue] | None = None) -> None:
        super().__init__()
        self.entries: list[JsonValue] = entries or []

    @Slot(result="QVariant")
    def bufferedEntries(self) -> list[JsonValue]:
        return self.entries


class FakeProduceController(QObject):
    solutionsChanged = Signal()
    dirtyChanged = Signal(bool)
    saveRequested = Signal()
    discardRequested = Signal()
    operationSucceeded = Signal(str)
    operationFailed = Signal(str)
    selectedSolutionIdChanged = Signal()

    def __init__(self, solutions: list[SolutionInfo] | None = None) -> None:
        super().__init__()
        self._dirty = False
        self._solutions: list[SolutionInfo] = solutions or []
        self.calls: list[Call] = []

    dirty = Property(bool, lambda s: s._dirty, notify=dirtyChanged)
    selectedSolutionId = Property(
        str,
        lambda s: s._solutions[0]["id"] if s._solutions else "",
        notify=selectedSolutionIdChanged,
    )
    solutionsModel = Property(QObject, lambda s: None, constant=True)

    @Slot(result=str)
    def solutionsJson(self) -> str:
        return json.dumps(self._solutions, ensure_ascii=False)

    @Slot(str, result=str)
    def solutionJson(self, sid: str) -> str:
        for x in self._solutions:
            if x.get("id") == sid:
                return json.dumps(x, ensure_ascii=False)
        return "{}"

    @Slot(str, str, result=bool)
    def checkSolutionNameExists(self, name: str, exclude: str) -> bool:
        return any(
            x.get("name") == name and x.get("id") != exclude for x in self._solutions
        )

    @Slot(str, result=bool)
    def saveSolution(self, value: str) -> bool:
        self.calls.append(("saveSolution", value))
        self.markClean()
        return True

    @Slot(str, result=str)
    def createSolution(self, name: str) -> str:
        self.calls.append(("createSolution", name))
        return "{}"

    @Slot(str, result=bool)
    def deleteSolution(self, sid: str) -> bool:
        self.calls.append(("deleteSolution", sid))
        return True

    @Slot(str, result=str)
    def duplicateSolution(self, sid: str) -> str:
        self.calls.append(("duplicateSolution", sid))
        return "{}"

    @Slot(str, result=str)
    def validateSolution(self, value: str) -> str:
        return "[]"

    @Slot(result=str)
    def idolCardsJson(self) -> str:
        return "[]"

    @Slot(result=str)
    def produceActionsJson(self) -> str:
        return "[]"

    @Slot(result=str)
    def cardDecksJson(self) -> str:
        return "[]"

    @Slot()
    def markDirty(self) -> None:
        if not self._dirty:
            self._dirty = True
            self.dirtyChanged.emit(True)

    @Slot()
    def markClean(self) -> None:
        if self._dirty:
            self._dirty = False
            self.dirtyChanged.emit(False)


class FakeRunController(QObject):
    stateChanged = Signal()
    endActionChanged = Signal()
    tasksChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._running = False
        self._stopping = False
        self._paused = False
        self._task = ""
        self._end_action = "nothing"
        self.taskModel: list[JsonValue] = []
        self.task_names: list[str] = ["任务A", "任务B"]
        self.calls: list[Call] = []

    running = Property(bool, lambda s: s._running, notify=stateChanged)
    isStopping = Property(bool, lambda s: s._stopping, notify=stateChanged)
    isPaused = Property(bool, lambda s: s._paused, notify=stateChanged)
    currentTaskName = Property(str, lambda s: s._task, notify=stateChanged)
    endAction = Property(str, lambda s: s._end_action, notify=endActionChanged)

    @property
    def running_state(self) -> bool:
        return self._running

    @property
    def stopping_state(self) -> bool:
        return self._stopping

    @property
    def paused_state(self) -> bool:
        return self._paused

    @Slot(result=str)
    def allTaskNamesJson(self) -> str:
        return json.dumps(self.task_names, ensure_ascii=False)

    @Slot(str)
    def runTask(self, n: str) -> None:
        self.calls.append(("runTask", str(n)))
        self._running = True
        self._task = str(n)
        self.stateChanged.emit()

    @Slot()
    def start(self) -> None:
        self.calls.append("start")
        self._running = True
        self.stateChanged.emit()

    @Slot()
    def stop(self) -> None:
        self.calls.append("stop")
        self._stopping = True
        self.stateChanged.emit()

    @Slot()
    def togglePause(self) -> None:
        self.calls.append("togglePause")
        self._paused = not self._paused
        self.stateChanged.emit()

    @Slot(str)
    def setEndAction(self, v: str) -> None:
        self.calls.append(("setEndAction", str(v)))
        self._end_action = str(v)
        self.endActionChanged.emit()

    @Slot(bool)
    def selectAllTasks(self, v: bool) -> None:
        self.calls.append(("selectAllTasks", bool(v)))

    @Slot()
    def selectOnlyProduce(self) -> None:
        self.calls.append(("selectOnlyProduce",))

    @Slot()
    def selectExceptProduce(self) -> None:
        self.calls.append(("selectExceptProduce",))

    @Slot(str, bool)
    def setTaskEnabled(self, p: str, v: bool) -> None:
        self.calls.append(("setTaskEnabled", str(p), bool(v)))


@pytest.fixture(scope="session")
def qapp():
    app = QGuiApplication.instance() or QGuiApplication([])
    yield app
    app.quit()


# ---------------------------------------------------------------------------
# Production-global QML dependencies
# ---------------------------------------------------------------------------


class _FakeSplash(QObject):
    readyChanged = Signal()
    iconPathChanged = Signal()
    appVersionChanged = Signal()
    statusTextChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._ready = True
        self._iconPath = ""
        self._appVersion = "test"
        self._statusText = ""
        self.gameDataDownloading = False
        self.gameDataSkippable = False
        self.downloadFiles = []
        self.downloadTotalBytes = 0
        self.downloadedBytes = 0

    @Property(str, notify=iconPathChanged)
    def iconPath(self) -> str:
        return self._iconPath

    @Property(str, notify=appVersionChanged)
    def appVersion(self) -> str:
        return self._appVersion

    @Property(str, notify=statusTextChanged)
    def statusText(self) -> str:
        return self._statusText

    @Property(bool, notify=readyChanged)
    def ready(self) -> bool:
        return self._ready

    def skipGameDataUpdate(self) -> None:
        self.gameDataDownloading = False

    def onChangelogDismissed(self) -> None:
        pass


def _create_test_theme(_engine: QQmlEngine) -> _FakeTheme:
    """Provide the controller as a real QML singleton for AppTheme.qml."""
    return _FakeTheme()

class _FakeTheme(QObject):
    windowStyleChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._windowStyle = "solid"

    @Property(str, notify=windowStyleChanged)
    def windowStyle(self) -> str:
        return self._windowStyle


class _FakeErrorDialog(QObject):
    visibleChanged = Signal()

    def show(self, *_args: object) -> None:
        pass


class _FakeProfileStore(QObject):
    profilesChanged = Signal()
    profilesJson = Property(str, lambda s: '{"profiles": []}', constant=True)


qmlRegisterSingletonType(_FakeTheme, "QtQuick", 6, 0, cast(bytes, "AppThemeController"), _create_test_theme)

def _install_production_context(engine: QQmlApplicationEngine) -> None:
    """Install every global used by the QML application before loading QML."""
    context = engine.rootContext()
    objects = {
        "splash": _FakeSplash(),
        "errorDialog": _FakeErrorDialog(),
        "TabManager": FakeTabManager(),
        "AppThemeController": _FakeTheme(),
        "PreferencesController": FakePrefsController(),
        "GameDataCtrl": FakeGameDataController(),
        "UpdateCtrl": FakeGameDataController(),
        "TelemetryConsentController": DummyController(),
        "ProfileStore": _FakeProfileStore(),
        "Notice": DummyController(),
        "DebugInspector": DummyController(),
        "maxHoverBridge": DummyController(),
        "tabBarBridge": DummyController(),
        "windowStateBridge": DummyController(),
        "fluentFontPath": "",
    }
    for name, value in objects.items():
        context.setContextProperty(name, value)
    # Keep Python-owned context objects alive for the complete test.
    _retain_test_objects(engine, objects)


@pytest.fixture
def qml_engine(qapp: QGuiApplication) -> Generator[QQmlApplicationEngine, None, None]:
    """Create a QML engine with the same global dependency contract as KAA."""

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    _install_production_context(engine)
    _retain_test_components(engine)
    yield engine
    engine.clearComponentCache()
    engine.deleteLater()


@pytest.fixture(scope="session")
def qapp_args():
    """Run Qt in a deterministic headless platform for the UI suite."""
    import os

    os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "FluentWinUI3")
    return ["-platform", "offscreen"]


# Override the lightweight helpers above with a production-compatible loader.
# Keeping this at the end also makes the helper resilient to future additions
# to the original fixture module.
@runtime_checkable
class _VariantObject(Protocol):
    def toVariant(self) -> object: ...


class _TestEngineState:
    def __init__(self) -> None:
        self.context_objects: dict[str, object] = {}
        self.components: list[QQmlComponent] = []
        self.roots: list[QObject] = []


_ENGINE_STATE: dict[int, _TestEngineState] = {}


def _state(engine: QQmlApplicationEngine) -> _TestEngineState:
    key = id(engine)
    state = _ENGINE_STATE.get(key)
    if state is None:
        state = _TestEngineState()
        _ENGINE_STATE[key] = state
    return state


def _retain_test_objects(engine: QQmlApplicationEngine, objects: Mapping[str, object]) -> None:
    _state(engine).context_objects = dict(objects)


def _retain_test_components(engine: QQmlApplicationEngine) -> None:
    _state(engine).components = []
    _state(engine).roots = []


def load_path(
    engine: QQmlApplicationEngine,
    path: Path,
    properties: dict[str, object] | None = None,
    context: dict[str, object] | None = None,
) -> QObject:
    if context:
        root_context = engine.rootContext()
        for name, value in context.items():
            root_context.setContextProperty(name, value)

    component = QQmlComponent(engine, QUrl.fromLocalFile(str(path)))
    if component.status() == QQmlComponent.Status.Error:
        errors = "\n".join(error.toString() for error in component.errors())
        raise AssertionError(f"QML component failed to compile: {path}\n{errors}")

    initial = properties or {}
    if initial:
        root = component.createWithInitialProperties(initial)
    else:
        root = component.create()

    # QQmlComponent owns the created object tree.  Keep both alive for the
    # complete test; otherwise the component can be garbage-collected as soon
    # as this helper returns, leaving a dangling Shiboken wrapper.
    state = _state(engine)
    state.components.append(component)
    state.roots.append(root)
    return root


def load_qml(
    engine: QQmlApplicationEngine,
    filename: str,
    properties: dict[str, object] | None = None,
    context: dict[str, object] | None = None,
) -> QObject:
    return load_path(engine, QML_DIR / filename, properties, context)


def load_test_qml(
    engine: QQmlApplicationEngine,
    filename: str,
    properties: dict[str, object] | None = None,
    context: dict[str, object] | None = None,
) -> QObject:
    return load_path(engine, TEST_DIR / filename, properties, context)


def find(root: QObject, name: str) -> QObject:
    o = root.findChild(QObject, name)
    assert o is not None, f"QML objectName not found: {name}"
    return o



def find_visual(root: QQuickItem, name: str) -> QQuickItem:
    if root.objectName() == name:
        return root
    for child in root.childItems():
        try:
            return find_visual(child, name)
        except AssertionError:
            continue
    raise AssertionError(f"QML visual objectName not found: {name}")

def find_text(root: QObject, text: str) -> QObject:
    for o in root.findChildren(QObject):
        try:
            if o.property("text") == text:
                return o
        except RuntimeError:
            pass
    raise AssertionError(f"QML text not found: {text!r}")


def click(o: QObject) -> None:
    assert o.property("enabled") is not False, f"object is disabled: {o}"
    assert QMetaObject.invokeMethod(o, "click", Qt.ConnectionType.DirectConnection)
    QTest.qWait(30)


def enabled(o: QObject) -> bool:
    return bool(o.property("enabled"))


def qml_variant(value: object) -> object:
    if isinstance(value, _VariantObject):
        return value.toVariant()
    return value
