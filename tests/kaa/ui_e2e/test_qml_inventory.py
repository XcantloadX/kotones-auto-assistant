from __future__ import annotations
from PySide6.QtQml import QQmlApplicationEngine
import pytest
from .conftest import (
    FakeDialog,
    load_path,
    KAA_QML_DIR,
    SHELL_QML_DIR,
)

# Shell（EuiShell）侧 QML：框架组件与内置页面
SHELL_QML_ROOTS = [
    "AppTheme.qml",
    "FluentIcons.qml",
    "LoadingOverlay.qml",
    "SplashOverlay.qml",
    "SlotHost.qml",
    "SlotName.qml",
    "components/FluentIcon.qml",
    "components/HelpTip.qml",
    "components/Link.qml",
    "components/NoticeHost.qml",
    "components/PageContainer.qml",
    "components/PageHeader.qml",
    "components/SideNavigationBar.qml",
    "components/TabStrip.qml",
    "components/TabContent.qml",
    "components/TitleBar.qml",
    "components/WindowControls.qml",
    "components/NavigationCoordinator.qml",
    "components/ProfileManagerDialog.qml",
    "components/controls/MultiSelect.qml",
    "components/controls/SegmentedButton.qml",
    "components/controls/Select.qml",
    "components/form/FieldRegistrar.qml",
    "components/form/FormBinder.qml",
    "components/form/FormCheckBox.qml",
    "components/form/FormComboBox.qml",
    "components/form/FormError.qml",
    "components/form/FormField.qml",
    "components/form/FormGroupBox.qml",
    "components/form/FormNotice.qml",
    "components/form/FormSection.qml",
    "components/form/FormSegmentedButton.qml",
    "components/form/FormSpinBox.qml",
    "components/form/FormTextField.qml",
    "components/form/HotkeyField.qml",
    "pages/ControlPage.qml",
    "pages/TaskPage.qml",
    "pages/SettingsPage.qml",
    "pages/LogPage.qml",
    "pages/AboutPage.qml",
    "pages/PreferencesPage.qml",
]

# KAA 侧 QML：业务页面 / section / 对话框 / slot
KAA_QML_ROOTS = [
    "components/CostNumberIcon.qml",
    "components/EffectDescription.qml",
    "components/ExamEffectIcon.qml",
    "components/InstancePicker.qml",
    "components/SkillCardIcon.qml",
    "components/IdolPickerDialog.qml",
    "components/UpdateIndicator.qml",
    "components/form/FormInstancePicker.qml",
    "dialogs/ExportReportDialog.qml",
    "dialogs/ReportExportResultDialog.qml",
    "dialogs/ScheduleManagerDialog.qml",
    "dialogs/SchoolEventInspectorDialog.qml",
    "pages/OverviewPage.qml",
    "pages/ProducePage.qml",
    "pages/SkillCardBrowserPage.qml",
    "pages/UpdatePage.qml",
    "pages/sections/DailySection.qml",
    "pages/sections/EmulatorSection.qml",
    "pages/sections/MiscSection.qml",
    "pages/sections/ProduceSection.qml",
    "pages/preferences/InterfaceExtraSection.qml",
    "pages/preferences/UpdateSection.qml",
    "pages/preferences/GameDataSection.qml",
    "pages/preferences/NotifySection.qml",
    "pages/preferences/HotkeysSection.qml",
    "pages/preferences/TelemetrySection.qml",
    "slots/OverviewSlot.qml",
    "slots/KaaDialogs.qml",
    "slots/EndActionRow.qml",
    "slots/ProduceEngineNotice.qml",
    "slots/ControlFooterExtras.qml",
    "slots/GameDataVersionRow.qml",
]


def _shell_props(path: str) -> dict[str, object]:
    from .conftest import (
        FakeLogBridge,
        FakePrefsController,
        _fake_tab_controller,
        FakeRunController,
    )

    if path == "components/FluentIcon.qml":
        return {"glyph": "\uf001"}
    if path in ("components/TabStrip.qml", "components/TitleBar.qml", "components/ProfileManagerDialog.qml"):
        return {"configManagerDialog": FakeDialog(), "tabManager": FakeDialog()}
    if path in ("components/TabContent.qml", "pages/ControlPage.qml", "pages/TaskPage.qml", "pages/SettingsPage.qml"):
        return {"tab": _fake_tab_controller(run=FakeRunController())}
    if path == "pages/LogPage.qml":
        return {"tab": _fake_tab_controller(), "logBridge": FakeLogBridge()}
    if path == "components/NavigationCoordinator.qml":
        return {"unsavedChangesDialog": FakeDialog()}
    if path == "components/WindowControls.qml":
        return {"window": None}
    if path == "components/form/HotkeyField.qml":
        return {"label": "Test"}
    if path == "pages/AboutPage.qml":
        return {"tab": _fake_tab_controller()}
    if path == "pages/PreferencesPage.qml":
        return {"prefsCtrl": FakePrefsController()}
    return {}


def _kaa_props(path: str) -> dict[str, object]:
    from .conftest import (
        FakePrefsController,
        FakeProduceController,
        FakeSettingsController,
        FakeUpdateController,
        _fake_tab_controller,
        FakeRunController,
    )
    if path == "pages/OverviewPage.qml":
        return {"configManagerDialog": FakeDialog(), "scheduleManagerDialog": FakeDialog()}
    if path == "pages/ProducePage.qml":
        return {"tab": _fake_tab_controller(controllers={"produce": FakeProduceController()})}
    if path == "pages/UpdatePage.qml":
        return {"tab": _fake_tab_controller(controllers={"update": FakeUpdateController()})}
    if path == "pages/SkillCardBrowserPage.qml":
        return {}
    if path == "dialogs/SchoolEventInspectorDialog.qml":
        from .conftest import DummyController
        return {"debugInspectorCtrl": DummyController()}
    if path in ("slots/EndActionRow.qml", "slots/ProduceEngineNotice.qml", "slots/ControlFooterExtras.qml"):
        return {"tab": _fake_tab_controller(run=FakeRunController())}
    if path.startswith("pages/sections/"):
        return {"settingsCtrl": FakeSettingsController()}
    if path.startswith("pages/preferences/"):
        return {"prefsCtrl": FakePrefsController()}
    return {}


def test_app_theme_resolves_controller_from_qml_singleton_scope(qml_engine: QQmlApplicationEngine) -> None:
    root = load_path(qml_engine, SHELL_QML_DIR / "EuiShell" / "AppTheme.qml")
    assert bool(root.property("isSolid")) is True


@pytest.mark.parametrize("path", SHELL_QML_ROOTS)
def test_every_shell_qml_component_can_be_instantiated(qml_engine: QQmlApplicationEngine, path: str) -> None:
    root = load_path(qml_engine, SHELL_QML_DIR / "EuiShell" / path, _shell_props(path))
    assert root is not None


@pytest.mark.parametrize("path", KAA_QML_ROOTS)
def test_every_kaa_qml_component_can_be_instantiated(qml_engine: QQmlApplicationEngine, path: str) -> None:
    root = load_path(qml_engine, KAA_QML_DIR / path, _kaa_props(path))
    assert root is not None
