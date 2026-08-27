from __future__ import annotations
from PySide6.QtQml import QQmlApplicationEngine
import pytest
from .conftest import (
    DummyController,
    FakeDialog,
    FakeRunController,
    load_path,
    QML_DIR,
)


QML_ROOTS = [
    "AppTheme.qml",
    "FluentIcons.qml",
    "LoadingOverlay.qml",
    "SplashOverlay.qml",
    "components/CostNumberIcon.qml",
    "components/EffectDescription.qml",
    "components/ExamEffectIcon.qml",
    "components/FluentIcon.qml",
    "components/FormField.qml",
    "components/HelpTip.qml",
    "components/Link.qml",
    "components/NoticeHost.qml",
    "components/PageContainer.qml",
    "components/PageHeader.qml",
    "components/SideNavigationBar.qml",
    "components/SkillCardIcon.qml",
    "components/TabContent.qml",
    "components/TabStrip.qml",
    "components/TitleBar.qml",
    "components/UpdateIndicator.qml",
    "components/controls/InstancePicker.qml",
    "components/controls/MultiSelect.qml",
    "components/controls/SegmentedButton.qml",
    "components/controls/Select.qml",
    "components/form/FieldRegistrar.qml",
    "components/form/FormBinder.qml",
    "components/form/FormCheckBox.qml",
    "components/form/FormComboBox.qml",
    "components/form/FormError.qml",
    "components/form/FormGroupBox.qml",
    "components/form/FormInstancePicker.qml",
    "components/form/FormNotice.qml",
    "components/form/FormSection.qml",
    "components/form/FormSegmentedButton.qml",
    "components/form/FormSpinBox.qml",
    "components/form/FormTextField.qml",
    "components/form/HotkeyField.qml",
    "dialogs/ExportReportDialog.qml",
    "dialogs/ReportExportResultDialog.qml",
    "pages/AboutPage.qml",
    "pages/ControlPage.qml",
    "pages/LogPage.qml",
    "pages/OverviewPage.qml",
    "pages/PreferencesPage.qml",
    "pages/ProducePage.qml",
    "pages/SettingsPage.qml",
    "pages/SkillCardBrowserPage.qml",
    "pages/TaskPage.qml",
    "pages/UpdatePage.qml",
    "pages/sections/DailySection.qml",
    "pages/sections/EmulatorSection.qml",
    "pages/sections/MiscSection.qml",
    "pages/sections/ProduceSection.qml",
]


def _props(path: str) -> dict[str, object]:
    if path == "components/FluentIcon.qml":
        return {"glyph": "\uf001"}
    if path == "components/TabContent.qml":
        return {"runCtrl": FakeRunController()}
    if path == "components/TabStrip.qml":
        return {"configManagerDialog": FakeDialog()}
    if path == "components/TitleBar.qml":
        return {"configManagerDialog": FakeDialog()}
    if path == "pages/OverviewPage.qml":
        return {"configManagerDialog": FakeDialog()}
    if path == "pages/ControlPage.qml":
        return {"runCtrl": FakeRunController()}
    if path == "pages/SettingsPage.qml":
        return {
            "settingsCtrl": __import__(
                "tests.kaa.ui_e2e.conftest", fromlist=["FakeSettingsController"]
            ).FakeSettingsController()
        }
    if path == "pages/PreferencesPage.qml":
        return {
            "prefsCtrl": __import__(
                "tests.kaa.ui_e2e.conftest", fromlist=["FakePrefsController"]
            ).FakePrefsController()
        }
    if path == "pages/ProducePage.qml":
        return {
            "produceCtrl": __import__(
                "tests.kaa.ui_e2e.conftest", fromlist=["FakeProduceController"]
            ).FakeProduceController()
        }
    if path == "pages/TaskPage.qml":
        return {"runCtrl": FakeRunController()}
    if path == "pages/LogPage.qml":
        return {
            "logBridge": __import__(
                "tests.kaa.ui_e2e.conftest", fromlist=["FakeLogBridge"]
            ).FakeLogBridge()
        }
    if path == "pages/SkillCardBrowserPage.qml":
        return {
            "browserCtrl": __import__(
                "tests.kaa.ui_e2e.conftest", fromlist=["FakeBrowserController"]
            ).FakeBrowserController()
        }
    if path == "pages/UpdatePage.qml":
        return {
            "updateCtrl": __import__(
                "tests.kaa.ui_e2e.conftest", fromlist=["FakeUpdateController"]
            ).FakeUpdateController()
        }
    if path == "dialogs/SchoolEventInspectorDialog.qml":
        return {"debugInspectorCtrl": DummyController()}
    if path == "components/form/HotkeyField.qml":
        return {"label": "Test"}
    return {}


def test_app_theme_resolves_controller_from_qml_singleton_scope(qml_engine: QQmlApplicationEngine) -> None:
    root = load_path(qml_engine, QML_DIR / "AppTheme.qml")
    assert bool(root.property("isSolid")) is True


@pytest.mark.parametrize("path", QML_ROOTS)
def test_every_ui_qml_component_can_be_instantiated(qml_engine: QQmlApplicationEngine, path: str) -> None:
    root = load_path(qml_engine, QML_DIR / path, _props(path))
    assert root is not None


