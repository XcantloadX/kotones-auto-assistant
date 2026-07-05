import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../components"
import "../components/controls"

// 更新页：版本检查 + 更新日志
PageContainer {
    id: root
    title: "更新"
    property var updateCtrl: null

    // ── 状态 ──────────────────────────────────────────
    property var versionInfo: null  // {installed, latest, launcher, versions:[]}
    property bool loading: false
    property string statusMessage: ""
    property string errorMessage: ""

    // 懒加载：只在用户切到"更新"页时首次加载
    onVisibleChanged: {
        if (visible && updateCtrl && versionInfo === null) {
            updateCtrl.loadVersionsAsync()
            loading = true
        }
    }

    Connections {
        target: updateCtrl
        function onVersionsLoaded(json) {
            loading = false
            try {
                root.versionInfo = JSON.parse(json)
                root.statusMessage = "版本信息已加载"
                root.errorMessage = ""
                // 默认选中最新版本
                if (root.versionInfo.versions.length > 0 && root.versionInfo.latest) {
                    var idx = root.versionInfo.versions.indexOf(root.versionInfo.latest)
                    if (idx >= 0) versionCombo.currentIndex = idx
                }
            } catch(e) {
                root.errorMessage = "解析版本信息失败"
            }
        }
        function onLoadFailed(msg) {
            loading = false
            if (msg === "会话未初始化") {
                sessionRetryTimer.start()
            } else {
                root.errorMessage = msg
                root.statusMessage = ""
            }
        }
        function onOperationSucceeded(msg) {
            root.statusMessage = msg
        }
        function onOperationFailed(msg) {
            root.errorMessage = msg
        }
    }

    // Retry when session isn't ready yet (openTab initializes session asynchronously)
    Timer {
        id: sessionRetryTimer
        interval: 1500
        repeat: false
        onTriggered: {
            if (updateCtrl) {
                updateCtrl.loadVersionsAsync()
                loading = true
            }
        }
    }

    ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true

        ColumnLayout {
            width: parent.width
            spacing: 16

            // ── 版本信息 ──────────────────────────────
            GroupBox {
                title: "版本信息"
                Layout.fillWidth: true

                ColumnLayout {
                    width: parent.width
                    spacing: 8

                    RowLayout {
                        spacing: 8
                        Button {
                            text: root.loading ? "载入中..." : "载入信息"
                            enabled: !root.loading && updateCtrl !== null
                            onClicked: {
                                updateCtrl.loadVersionsAsync()
                                loading = true
                                errorMessage = ""
                            }
                        }
                        Item { Layout.fillWidth: true }
                    }

                    // 版本详情
                    GridLayout {
                        columns: 2
                        Layout.fillWidth: true
                        visible: root.versionInfo !== null

                        Label { text: "当前版本"; color: palette.placeholderText }
                        Label {
                            text: root.versionInfo ? root.versionInfo.installed : "—"
                            font.bold: true
                        }
                        Label { text: "最新版本"; color: palette.placeholderText }
                        Label {
                            text: root.versionInfo ? root.versionInfo.latest : "—"
                            font.bold: true
                            color: root.versionInfo && root.versionInfo.installed !== root.versionInfo.latest
                                   ? "#1976d2" : palette.text
                        }
                        Label { text: "启动器版本"; color: palette.placeholderText }
                        Label {
                            text: root.versionInfo ? root.versionInfo.launcher : "—"
                        }
                        Label { text: "可用版本数"; color: palette.placeholderText }
                        Label {
                            text: root.versionInfo ? root.versionInfo.versions.length : "0"
                        }
                    }

                    // 状态/错误消息
                    Label {
                        text: root.statusMessage
                        color: "#388e3c"
                        visible: text.length > 0
                    }
                    Label {
                        text: root.errorMessage
                        color: "#d32f2f"
                        visible: text.length > 0
                        wrapMode: Text.Wrap
                        textFormat: Text.PlainText
                        Layout.fillWidth: true
                    }
                }
            }

            // ── 安装版本 ──────────────────────────────
            GroupBox {
                title: "安装版本"
                Layout.fillWidth: true
                visible: root.versionInfo !== null && root.versionInfo.versions.length > 0

                ColumnLayout {
                    width: parent.width
                    spacing: 8

                    RowLayout {
                        Label { text: "选择要安装的版本" }
                        Select {
                            id: versionCombo
                            Layout.fillWidth: true
                            model: root.versionInfo ? root.versionInfo.versions : []
                        }
                        Button {
                            text: "安装选定版本"
                            highlighted: true
                            enabled: versionCombo.currentText !== ""
                            onClicked: {
                                installConfirmDialog.open()
                            }
                        }
                    }

                    Label {
                        text: "安装新版本将重启应用"
                        color: palette.placeholderText
                        font.pixelSize: 11
                    }
                }
            }

            // ── 更新日志 ──────────────────────────────
            GroupBox {
                title: "更新日志"
                Layout.fillWidth: true
                Layout.fillHeight: true

                TextArea {
                    anchors.fill: parent
                    readOnly: true
                    wrapMode: TextArea.Wrap
                    textFormat: TextEdit.MarkdownText
                    text: updateCtrl ? updateCtrl.changelogText() : ""
                    font.pixelSize: 13
                    background: Rectangle {
                        color: "transparent"
                    }
                }
            }
        }
    }

    // ── 确认对话框 ──────────────────────────────────────
    Dialog {
        id: installConfirmDialog
        modal: true
        title: "确认安装"
        standardButtons: Dialog.Ok | Dialog.Cancel
        implicitWidth: 360

        contentItem: Label {
            text: "确定要安装版本 " + versionCombo.currentText + " 吗？\n应用将重启。"
            wrapMode: Text.Wrap
            width: parent ? parent.width : implicitWidth
        }

        onAccepted: {
            if (updateCtrl) {
                updateCtrl.installVersion(versionCombo.currentText)
            }
        }
    }
}
