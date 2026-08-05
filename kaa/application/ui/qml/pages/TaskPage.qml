import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

// 任务页：单独执行指定任务（对应旧 Gradio「任务」Tab）
PageContainer {
    id: root
    title: "任务"
    required property var runCtrl

    readonly property bool ctrl_running:  runCtrl ? runCtrl.running : false
    readonly property bool ctrl_stopping: runCtrl ? runCtrl.isStopping : false
    property var taskNames: []

    function reloadTaskNames() {
        if (runCtrl) {
            taskNames = JSON.parse(runCtrl.allTaskNamesJson())
        } else {
            taskNames = []
        }
    }

    Component.onCompleted: reloadTaskNames()

    Connections {
        target: runCtrl
        function onTasksChanged() { reloadTaskNames() }
        function onStateChanged() { reloadTaskNames() }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: 12

            // ── 任务列表 ──────────────────────────────
            GroupBox {
                title: "任务列表"
                Layout.fillWidth: true

                ListView {
                    id: taskList
                    implicitHeight: contentHeight
                    width: parent.width
                    clip: true
                    model: root.taskNames
                    spacing: 4

                    delegate: ItemDelegate {
                        width: taskList.width
                        height: 44

                        contentItem: RowLayout {
                            spacing: 12

                            Button {
                                text: root.ctrl_running
                                      ? (root.ctrl_stopping ? "停止中..." : "运行中")
                                      : "启动"
                                highlighted: !root.ctrl_running
                                enabled: !root.ctrl_running
                                onClicked: runCtrl.runTask(modelData)
                            }

                            Label {
                                text: modelData
                                font.pixelSize: 15
                                font.weight: Font.Medium
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
        }
    }
}