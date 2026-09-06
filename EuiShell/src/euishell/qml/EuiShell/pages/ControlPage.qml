import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import ".." as App

// 控制页：任务运行控制 + 进度 + 快速开关；其余区域为下游 slot。
// 页面统一契约：tab / navigation / fullscreenMode。
PageContainer {
    id: root
    title: "状态"

    required property var tab
    property var navigation: null
    property string fullscreenMode: ""

    readonly property var runCtrl: tab ? tab.runCtrl : null
    readonly property var progressCtrl: tab ? tab.progressCtrl : null

    readonly property bool ctrl_running:  runCtrl ? runCtrl.running : false
    readonly property bool ctrl_stopping: runCtrl ? runCtrl.isStopping : false
    readonly property bool ctrl_paused:   runCtrl ? runCtrl.isPaused : false
    readonly property string ctrl_task:   runCtrl ? runCtrl.currentTaskName : ""

    // 批量操作按钮（由下游 TaskTogglesSource 提供）
    property var bulkActions: []
    function reloadBulkActions() {
        if (runCtrl) bulkActions = JSON.parse(runCtrl.bulkActionsJson())
        else bulkActions = []
    }
    Component.onCompleted: reloadBulkActions()
    Connections {
        target: runCtrl
        function onTasksChanged() { root.reloadBulkActions() }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: 12

            // ── 页面顶部通知 slot ─────────────────────────
            App.SlotHost {
                slotName: App.SlotName.controlNotices
                tab: root.tab
                Layout.fillWidth: true
            }

            // ── 运行控制 + 进度 ──────────────────────────
            GroupBox {
                title: "运行控制"
                Layout.fillWidth: true

                ColumnLayout {
                    width: parent.width
                    spacing: 12

                    RowLayout {
                        width: parent.width
                        spacing: 8

                        Button {
                            text: ctrl_running ? (ctrl_stopping ? "停止中..." : "停止") : "启动"
                            highlighted: !ctrl_running
                            enabled: !ctrl_stopping
                            onClicked: ctrl_running ? runCtrl.stop() : runCtrl.start()
                        }

                        Button {
                            text: ctrl_paused ? "恢复" : "暂停"
                            enabled: ctrl_running && !ctrl_stopping
                            onClicked: runCtrl.togglePause()
                        }

                        // ── 运行控制行内附加控件 slot ──────────
                        App.SlotHost {
                            slotName: App.SlotName.controlRunExtras
                            tab: root.tab
                        }

                        Item { Layout.fillWidth: true }

                        Label {
                            text: ctrl_task ? "正在执行: " + ctrl_task : ""
                            color: palette.placeholderText
                        }
                    }

                    // 进度信息
                    ColumnLayout {
                        width: parent.width
                        spacing: 6
                        visible: progressCtrl !== null

                        RowLayout {
                            width: parent.width
                            Label {
                                text: progressCtrl ? progressCtrl.statusText : ""
                                Layout.fillWidth: true
                            }
                            Label {
                                text: progressCtrl ? (progressCtrl.progressPercent + "%") : ""
                                color: palette.placeholderText
                            }
                        }

                        ProgressBar {
                            Layout.fillWidth: true
                            from: 0
                            to: 100
                            value: progressCtrl ? progressCtrl.progressPercent : 0
                        }

                        Label {
                            text: progressCtrl && progressCtrl.lastErrorText
                                  ? "错误: " + progressCtrl.lastErrorText
                                  : ""
                            color: "#d32f2f"
                            visible: text.length > 0
                            wrapMode: Text.Wrap
                            Layout.fillWidth: true
                        }
                    }
                }
            }

            // ── 快速开关 ──────────────────────────────────
            GroupBox {
                title: "快速设置"
                Layout.fillWidth: true
                visible: root.runCtrl && root.runCtrl.taskModel

                ColumnLayout {
                    width: parent.width
                    spacing: 8

                    RowLayout {
                        spacing: 8
                        visible: root.bulkActions.length > 0

                        Repeater {
                            model: root.bulkActions
                            delegate: Button {
                                required property int index
                                required property var modelData
                                text: modelData.label
                                onClicked: root.runCtrl.invokeBulkAction(index)
                            }
                        }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8

                        Repeater {
                            model: root.runCtrl ? root.runCtrl.taskModel : null
                            delegate: CheckBox {
                                required property int index
                                required property var modelData
                                text: model.label
                                checked: model.enabled
                                onToggled: root.runCtrl.setTaskEnabled(model.key, checked)
                            }
                        }
                    }
                }
            }

            // ── 页面底部附加区 slot ───────────────────────
            App.SlotHost {
                slotName: App.SlotName.controlFooter
                tab: root.tab
                Layout.fillWidth: true
            }
        }
    }
}
