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
    readonly property bool ctrl_paused:   runCtrl ? runCtrl.isPaused : false
    readonly property string ctrl_task:   runCtrl ? runCtrl.currentTaskName : ""

    property var taskNames: []
    property string errorMessage: ""

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
        function onOperationFailed(msg) { root.errorMessage = msg }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: 12

            // ── 全局控制 ──────────────────────────────
            GroupBox {
                title: "执行任务"
                Layout.fillWidth: true

                ColumnLayout {
                    width: parent.width
                    spacing: 10

                    RowLayout {
                        width: parent.width
                        spacing: 8

                        Button {
                            text: "停止任务"
                            enabled: root.ctrl_running && !root.ctrl_stopping
                            onClicked: runCtrl.stop()
                        }

                        Button {
                            text: root.ctrl_paused ? "恢复" : "暂停"
                            enabled: root.ctrl_running && !root.ctrl_stopping
                            onClicked: runCtrl.togglePause()
                        }

                        Item { Layout.fillWidth: true }

                        Label {
                            text: root.ctrl_task
                                  ? "正在执行任务: " + root.ctrl_task
                                  : ""
                            color: palette.placeholderText
                        }
                    }

                    Label {
                        text: root.errorMessage
                        color: "#d32f2f"
                        visible: text.length > 0
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                    }
                }
            }

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
                                onClicked: {
                                    root.errorMessage = ""
                                    runCtrl.runTask(modelData)
                                }
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