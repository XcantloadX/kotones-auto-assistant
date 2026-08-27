from __future__ import annotations
from PySide6.QtQml import QQmlApplicationEngine
from .conftest import FakeDialog, FakeTabManager, load_qml


def test_fluent_icon_accepts_glyph(qml_engine: QQmlApplicationEngine) -> None:
    icon = load_qml(qml_engine, "components/FluentIcon.qml", {"glyph": "\uf001"})
    assert icon.property("glyph") == "\uf001"


def test_navigation_coordinator_clean_and_dirty_contract(qml_engine: QQmlApplicationEngine) -> None:
    dialog = FakeDialog()
    coordinator = load_qml(
        qml_engine,
        "components/NavigationCoordinator.qml",
        {"unsavedChangesDialog": dialog},
    )
    coordinator.setProperty("dirty", False)
    assert coordinator.property("dirty") is False
    coordinator.setProperty("dirty", True)
    assert coordinator.property("dirty") is True


def test_tab_strip_active_tab_and_batch_properties(qml_engine: QQmlApplicationEngine) -> None:
    dialog = FakeDialog()
    manager = FakeTabManager()
    strip = load_qml(
        qml_engine,
        "components/TabStrip.qml",
        {"configManagerDialog": dialog},
        {"TabManager": manager},
    )
    strip.setProperty(
        "tabs",
        [
            {"configName": "A", "index": 0, "isActive": True},
            {"configName": "B", "index": 1, "isActive": False},
        ],
    )
    assert len(strip.property("tabs")) == 2
    manager.startAllSequential()
    assert manager.property("batchMode") == "sequential"
    manager.stopAll()
    assert manager.property("batchMode") == ""


def test_update_indicator_idle_is_hidden(qml_engine: QQmlApplicationEngine) -> None:
    indicator = load_qml(qml_engine, "components/UpdateIndicator.qml")
    assert indicator.property("_active") is False
    assert indicator.property("visible") is False


def test_loading_overlay_default_state(qml_engine: QQmlApplicationEngine) -> None:
    overlay = load_qml(qml_engine, "LoadingOverlay.qml")
    assert overlay.property("loadingProgress") == 0


def test_page_headers_and_containers_compile(qml_engine: QQmlApplicationEngine) -> None:
    header = load_qml(qml_engine, "components/PageHeader.qml")
    container = load_qml(qml_engine, "components/PageContainer.qml")
    assert header is not None
    assert container is not None


def test_simple_controls_compile(qml_engine: QQmlApplicationEngine) -> None:
    select = load_qml(
        qml_engine, "components/controls/Select.qml", {"model": ["A", "B"]}
    )
    segmented = load_qml(
        qml_engine, "components/controls/SegmentedButton.qml", {"model": ["A", "B"]}
    )
    multi = load_qml(
        qml_engine, "components/controls/MultiSelect.qml", {"model": ["A", "B"]}
    )
    assert select.property("model") == ["A", "B"]
    assert segmented is not None
    assert multi is not None


def test_form_controls_compile(qml_engine: QQmlApplicationEngine) -> None:
    checkbox = load_qml(
        qml_engine, "components/form/FormCheckBox.qml", {"label": "Test"}
    )
    combo = load_qml(qml_engine, "components/form/FormComboBox.qml", {"label": "Test"})
    spin = load_qml(qml_engine, "components/form/FormSpinBox.qml", {"label": "Test"})
    text = load_qml(qml_engine, "components/form/FormTextField.qml", {"label": "Test"})
    hotkey = load_qml(qml_engine, "components/form/HotkeyField.qml", {"label": "Test"})
    assert checkbox is not None and combo is not None and spin is not None
    assert text is not None and hotkey is not None


