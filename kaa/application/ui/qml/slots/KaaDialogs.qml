import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import EuiShell
import "../components"

// 窗口级对话框 slot：更新日志 / 配置迁移报告 / 匿名上报同意弹窗。
// 依赖 Shell 注入的 splash 上下文属性（KaaSplashBridge 提供扩展信号）。
Item {
    id: root

    Connections {
        target: splash
        function onShowChangelogDialog(version, text) {
            changelogDialog.changelogVersion = version
            changelogDialog.changelogText = text
            changelogDialog.open()
        }
    }

    Connections {
        target: splash
        function onShowMigrationDialog(messages) {
            migrationDialog.messages = messages
            migrationDialog.open()
        }
    }

    Connections {
        target: TelemetryConsentController
        function onTelemetryConsentRequiredChanged() {
            if (TelemetryConsentController.telemetryConsentRequired) {
                telemetryConsentDialog.open()
            }
        }
    }

    Dialog {
        id: changelogDialog
        property string changelogVersion: ""
        property string changelogText: ""
        title: "更新日志（v" + changelogVersion + "）"
        modal: true
        anchors.centerIn: parent
        width: Math.min(560, root.width - 80)
        height: Math.min(420, root.height - 120)
        standardButtons: Dialog.Ok
        onAccepted: splash.onChangelogDismissed()
        onRejected: splash.onChangelogDismissed()

        ScrollView {
            anchors.fill: parent; clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical.policy: ScrollBar.AlwaysOn
            Text {
                width: changelogDialog.width - 48
                text: changelogDialog.changelogText
                wrapMode: Text.Wrap; font.pixelSize: 14; lineHeight: 1.5
                color: palette.windowText
            }
        }
    }

    Dialog {
        id: migrationDialog
        property var messages: []
        title: "配置升级报告"
        modal: true
        anchors.centerIn: parent
        width: Math.min(560, root.width - 80)
        height: Math.min(420, root.height - 120)
        standardButtons: Dialog.Ok

        ScrollView {
            anchors.fill: parent; clip: true
            ScrollBar.vertical.policy: ScrollBar.AsNeeded
            Column {
                width: migrationDialog.width - 48; spacing: 8; topPadding: 8; bottomPadding: 8
                Repeater {
                    model: migrationDialog.messages
                    delegate: Row {
                        spacing: 6; width: parent.width
                        Text {
                            text: modelData.level === "warning" ? "⚠️" : "ℹ️"
                            font.pixelSize: 13
                            color: modelData.level === "warning" ? "#e65100" : palette.windowText
                            verticalAlignment: Text.AlignTop
                        }
                        Text {
                            width: parent.width - 26
                            text: {
                                var vi = ""
                                if (modelData.oldVersion && modelData.newVersion)
                                    vi = "（" + modelData.oldVersion + " → " + modelData.newVersion + "）"
                                return vi + modelData.text
                            }
                            wrapMode: Text.Wrap; font.pixelSize: 13; lineHeight: 1.4
                            color: palette.windowText
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: telemetryConsentDialog
        title: "数据收集"
        modal: true
        closePolicy: Popup.NoAutoClose
        anchors.centerIn: parent
        width: Math.min(420, root.width - 80)
        standardButtons: Dialog.NoButton

        Column {
            width: parent.width
            spacing: 10
            Text {
                text: "是否允许琴音小助手自动发送匿名错误报告？发送的信息仅用于改善琴音小助手，你也可以随时在“偏好”中更改。"
                font.pixelSize: 13
                color: palette.windowText
                wrapMode: Text.Wrap
                width: parent.width
                lineHeight: 1.4
            }

            Switch {
                id: staticsSwitch
                text: "匿名收集统计数据"
                checked: true
            }

            Switch {
                id: sentrySwitch
                text: "发送匿名错误报告"
                checked: true
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 2

                Switch {
                    id: screenshotSwitch
                    text: "错误上报时附带游戏截图"
                    checked: true
                }

                HelpTip {
                    richText: "只包含游戏画面截图，不含电脑桌面或其他应用内容。<br>如果不希望发送截图，请关闭此选项。"
                    Layout.alignment: Qt.AlignVCenter
                }
            }
        }

        footer: Rectangle {
            implicitHeight: 81
            color: palette.window
            Rectangle {
                width: parent.width; height: 1
                color: AppTheme.isDark ? "#15FFFFFF" : "#0F000000"
            }
            Row {
                anchors.right: parent.right; anchors.verticalCenter: parent.verticalCenter
                anchors.rightMargin: 24; spacing: 8
                Button {
                    text: "确定"
                    highlighted: true
                    onClicked: {
                        TelemetryConsentController.setTelemetryConsent(sentrySwitch.checked, screenshotSwitch.checked, staticsSwitch.checked)
                        Notice.show("success", "数据收集设置将于下次启动时生效。")
                        telemetryConsentDialog.close()
                    }
                }
            }
        }
    }

    Component.onCompleted: {
        // 首次启动且未设置匿名上报时，弹出同意询问
        if (TelemetryConsentController.telemetryConsentRequired) {
            telemetryConsentDialog.open()
        }
    }
}
