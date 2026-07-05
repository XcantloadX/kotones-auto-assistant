import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "sections"

PageContainer {
    id: root
    title: "设置"

    titleRightContent: RowLayout {
        spacing: 8
        Rectangle {
            visible: root.scriptRunning
            color: "#FEF3C7"
            border.color: "#F59E0B"
            radius: 4
            implicitHeight: 32
            width: runningLabel.implicitWidth + 16

            Label {
                id: runningLabel
                text: "运行中"
                color: "#B45309"
                font.bold: true
                anchors.centerIn: parent
            }
        }
        Rectangle {
            visible: root.dirty
            color: "#FFEBE9"
            border.color: "#DC3545"
            radius: 4
            implicitHeight: 32
            width: unsavedLabel.implicitWidth + 16

            Label {
                id: unsavedLabel
                text: "未保存的更改"
                color: "#DC3545"
                font.bold: true
                anchors.centerIn: parent
            }
        }
    }

    headerActions: Button {
        text: "保存"
        highlighted: true
        enabled: !root.scriptRunning && root.dirty
        onClicked: root.save()
    }

    required property var settingsCtrl
    property var runCtrl: null
    readonly property bool scriptRunning: runCtrl ? (runCtrl.running || runCtrl.isStopping) : false
    property bool dirty: false

    function save() {
        if (settingsCtrl) settingsCtrl.save()
    }

    Connections {
        target: settingsCtrl
        function onDirtyChanged(isDirty) { root.dirty = isDirty }
        function onOperationSucceeded(msg) { Notice.show("success", msg) }
        function onOperationFailed(msg) { Notice.show("error", msg) }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── TabBar ────────────────────────────────────
        TabBar {
            id: settingsTabs
            Layout.fillWidth: true
            TabButton { text: "基本" }
            TabButton { text: "日常" }
            TabButton { text: "培育" }
            TabButton { text: "杂项" }
        }

        // ── StackLayout ───────────────────────────────
        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: settingsTabs.currentIndex

            EmulatorSection {
                settingsCtrl: root.settingsCtrl
            }
            DailySection {
                settingsCtrl: root.settingsCtrl
            }
            ProduceSection {
                settingsCtrl: root.settingsCtrl
            }
            MiscSection {
                settingsCtrl: root.settingsCtrl
            }
        }
    }
}
