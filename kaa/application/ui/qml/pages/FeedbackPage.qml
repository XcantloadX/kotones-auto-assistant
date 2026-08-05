import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

// 反馈页：提交 bug 报告 + 导出日志
PageContainer {
    id: root
    title: "反馈"
    property var feedbackCtrl: null

    // ── 状态 ──────────────────────────────────────────
    property bool submitting: false
    property string progressText: ""
    property real progressValue: 0.0
    property string resultMessage: ""
    property string errorMessage: ""

    Connections {
        target: feedbackCtrl
        function onReportProgress(desc, fraction) {
            root.progressText = desc
            root.progressValue = fraction
        }
        function onReportDone(msg) {
            root.submitting = false
            root.resultMessage = msg
            root.progressText = ""
            root.progressValue = 0.0
        }
        function onReportFailed(msg) {
            root.submitting = false
            root.errorMessage = msg
            root.progressText = ""
            root.progressValue = 0.0
        }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: 16

            // ── 报告表单 ──────────────────────────────
            GroupBox {
                title: "提交反馈"
                Layout.fillWidth: true

                ColumnLayout {
                    width: parent.width
                    spacing: 8

                    RowLayout {
                        Label { text: "标题"; Layout.preferredWidth: 60 }
                        TextField {
                            id: titleField
                            Layout.fillWidth: true
                            placeholderText: "简要描述问题"
                            enabled: !root.submitting
                        }
                    }

                    RowLayout {
                        Label { text: "描述"; Layout.preferredWidth: 60 }
                        TextArea {
                            id: descField
                            Layout.fillWidth: true
                            Layout.preferredHeight: 100
                            placeholderText: "详细描述问题发生的过程、预期结果和实际结果"
                            wrapMode: TextArea.Wrap
                            enabled: !root.submitting
                        }
                    }

                    // 进度条
                    ProgressBar {
                        Layout.fillWidth: true
                        visible: root.submitting
                        from: 0.0
                        to: 1.0
                        value: root.progressValue
                    }
                    Label {
                        text: root.progressText
                        visible: root.submitting
                        color: palette.placeholderText
                        font.pixelSize: 12
                    }

                    // 操作按钮
                    RowLayout {
                        spacing: 8
                        Button {
                            text: "上传"
                            highlighted: true
                            enabled: !root.submitting && titleField.text.length > 0
                            onClicked: {
                                root.submitting = true
                                root.resultMessage = ""
                                root.errorMessage = ""
                                feedbackCtrl.submitReport(titleField.text, descField.text, true)
                            }
                        }
                        Button {
                            text: "保存至本地"
                            enabled: !root.submitting && titleField.text.length > 0
                            onClicked: {
                                root.submitting = true
                                root.resultMessage = ""
                                root.errorMessage = ""
                                feedbackCtrl.submitReport(titleField.text, descField.text, false)
                            }
                        }
                    }

                    // 结果/错误消息
                    Label {
                        text: root.resultMessage
                        color: "#388e3c"
                        visible: text.length > 0
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
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

            // ── 导出日志 ──────────────────────────────
            GroupBox {
                title: "日志导出"
                Layout.fillWidth: true

                ColumnLayout {
                    width: parent.width
                    spacing: 8

                    Label {
                        text: "将 logs 目录打包为 ZIP 文件"
                        color: palette.placeholderText
                    }

                    Button {
                        text: "导出日志"
                        enabled: !root.submitting && feedbackCtrl !== null
                        onClicked: {
                            var result = feedbackCtrl.exportLogsZip()
                            root.resultMessage = result
                        }
                    }
                }
            }
        }
    }
}
