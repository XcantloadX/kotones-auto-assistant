from __future__ import annotations
from .conftest import load_qml, find, click
from PySide6.QtCore import QObject, Property, Signal, Slot
from PySide6.QtQml import QQmlApplicationEngine


class Splash(QObject):
    stateChanged = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._ready = False
        self._downloading = False
        self._skippable = False
        self._status = ""
        self._files = []
        self.skipped = False

    ready = Property(bool, lambda s: s._ready, notify=stateChanged)
    gameDataDownloading = Property(bool, lambda s: s._downloading, notify=stateChanged)
    gameDataSkippable = Property(bool, lambda s: s._skippable, notify=stateChanged)
    statusText = Property(str, lambda s: s._status, notify=stateChanged)
    downloadFiles = Property(list, lambda s: s._files, notify=stateChanged)
    iconPath = Property(str, lambda s: "", constant=True)
    appVersion = Property(str, lambda s: "test", constant=True)

    def set_ready(self, value: bool) -> None:
        self._ready = value
        self.stateChanged.emit()

    def set_download_state(self, downloading: bool, skippable: bool, files: list[dict[str, object]]) -> None:
        self._downloading = downloading
        self._skippable = skippable
        self._files = files
        self.stateChanged.emit()

    @Slot()
    def skipGameDataUpdate(self) -> None:
        self.skipped = True


def make_splash(engine: QQmlApplicationEngine, splash: Splash) -> QObject:
    return load_qml(engine, "SplashOverlay.qml", context={"splash": splash})


def test_splash_ready_stops_busy_indicator(qml_engine: QQmlApplicationEngine) -> None:
    splash = Splash()
    page = make_splash(qml_engine, splash)
    splash.set_ready(True)
    busy = find(page, "splashBusyIndicator")
    assert not busy.property("running")


def test_splash_download_progress_is_visible(qml_engine: QQmlApplicationEngine) -> None:
    splash = Splash()
    page = make_splash(qml_engine, splash)
    splash.set_download_state(True, True, [
        {
            "fileName": "game.dat",
            "percent": 50.0,
            "speedText": "1 MB/s",
            "sizeText": "2 MB",
        }
    ])
    grid = find(page, "splashDownloadGrid")
    assert grid.property("visible")
    assert find(page, "splashSkipButton").property("visible")


def test_splash_skip_calls_bridge(qml_engine: QQmlApplicationEngine) -> None:
    splash = Splash()
    page = make_splash(qml_engine, splash)
    splash.set_download_state(True, True, [])
    click(find(page, "splashSkipButton"))
    assert splash.skipped


