import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"
import "../components/controls"
import "../components/form"

// 控制页：任务运行控制 + 快速开关 + 状态列表 + 进度
PageContainer {
    id: root
    title: "状态"
    required property var runCtrl
    property var progressCtrl: null
    property bool keepScreenshots: false

    readonly property bool ctrl_running:  runCtrl ? runCtrl.running : false
    readonly property bool ctrl_stopping: runCtrl ? runCtrl.isStopping : false
    readonly property bool ctrl_paused:   runCtrl ? runCtrl.isPaused : false
    readonly property string ctrl_task:   runCtrl ? runCtrl.currentTaskName : ""

    function statusText(status) {
        var map = {
            pending: "等待",
            running: "运行中",
            done: "完成",
            error: "出错"
        }
        return map[status] || status
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: 12

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

                        Select {
                            id: endActionCombo
                            Layout.minimumWidth: 190
                            textRole: "label"
                            valueRole: "value"
                            model: [
                                { label: "完成后什么都不做", value: "nothing" },
                                { label: "完成后关机", value: "shutdown" },
                                { label: "完成后休眠", value: "hibernate" }
                            ]
                            onCurrentValueChanged: {
                                if (currentValue) runCtrl.setEndAction(currentValue)
                            }
                            Component.onCompleted: currentValue = runCtrl ? runCtrl.endAction : "nothing"
                            Connections {
                                target: runCtrl
                                function onEndActionChanged() {
                                    endActionCombo.currentValue = runCtrl.endAction
                                }
                            }
                        }

                        Item { Layout.fillWidth: true }

                        Label {
                            text: ctrl_task ? "正在执行: " + ctrl_task : ""
                            color: palette.placeholderText
                        }
                    }

                    // 进度信息（合并到运行控制内）
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

            // ── 快速任务开关 ──────────────────────────────
            GroupBox {
                title: "快速设置"
                Layout.fillWidth: true

                ColumnLayout {
                    width: parent.width
                    spacing: 8

                    RowLayout {
                        spacing: 8
                        Button { text: "全选";     onClicked: runCtrl.selectAllTasks(true) }
                        Button { text: "清空";     onClicked: runCtrl.selectAllTasks(false) }
                        Button { text: "只选培育"; onClicked: runCtrl.selectOnlyProduce() }
                        Button { text: "只不选培育"; onClicked: runCtrl.selectExceptProduce() }
                    }

                    Flow {
                        Layout.fillWidth: true
                        spacing: 8

                        Repeater {
                            model: runCtrl.taskModel
                            CheckBox {
                                text: model.shortName
                                checked: model.enabled
                                onToggled: runCtrl.setTaskEnabled(model.path, checked)
                            }
                        }
                    }
                }
            }

            // ── 调试模式警告 ──────────────────────────────
            FormNotice {
                Layout.fillWidth: true
                visible: root.keepScreenshots
                style: "warning"
                title: "调试模式"
                content: "当前启用了调试功能「保留截图数据」，调试结束后正常使用时建议关闭此选项！"
            }

            // ── 引导提示 ──────────────────────────────
            Label {
                text: '脚本报错或者卡住？前往「反馈」页面可以快速导出报告！'
                color: palette.placeholderText
                font.pixelSize: 12
                Layout.fillWidth: true
            }

            // ── 任务状态列表 ──────────────────────────────
            GroupBox {
                title: "任务状态"
                Layout.fillWidth: true

                ListView {
                    id: statusList
                    implicitHeight: contentHeight
                    width: parent.width
                    clip: true
                    model: runCtrl.taskModel
                    spacing: 4

                    delegate: ItemDelegate {
                        width: statusList.width

                        contentItem: RowLayout {
                            width: parent.availableWidth
                            Label {
                                text: model.name
                                Layout.fillWidth: true
                                elide: Text.ElideRight
                            }
                            Label {
                                text: root.statusText(model.statusText)
                                color: model.statusText === "running" ? "#1976d2"
                                         : model.statusText === "error" ? "#d32f2f"
                                         : palette.placeholderText
                            }
                        }
                    }
                }
            }
        }
    }
}
