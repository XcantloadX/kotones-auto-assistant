import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtWebEngine

ApplicationWindow {
    id: root
    title: "琴音小助手"
    visible: Window.Maximized
    width: 1280
    height: 800
    minimumWidth: 800
    minimumHeight: 600

    SystemPalette { id: sysPalette }
    color: sysPalette.window

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
        target: errorDialog
        function onShowDialog(mainInstruction, content, buttons) {
            taskErrorDialog.mainInstruction = mainInstruction
            taskErrorDialog.content = content
            taskErrorDialog.buttons = buttons
            taskErrorDialog.open()
        }
    }

    Dialog {
        id: taskErrorDialog
        property string mainInstruction: ""
        property string content: ""
        property var buttons: []

        title: taskErrorDialog.mainInstruction
        modal: true
        closePolicy: Popup.NoAutoClose
        anchors.centerIn: parent
        width: Math.min(480, root.width - 80)
        standardButtons: Dialog.NoButton

        Column {
            width: parent.width
            spacing: 8

            Text {
                text: taskErrorDialog.content
                font.pixelSize: 13
                color: sysPalette.windowText
                wrapMode: Text.Wrap
                width: parent.width
                lineHeight: 1.4
            }
        }

        footer: Rectangle {
            implicitHeight: 81
            color: sysPalette.window

            Rectangle {
                width: parent.width
                height: 1
                color: Application.styleHints.colorScheme === Qt.Light ? "#0F000000" : "#15FFFFFF"
            }

            Row {
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.rightMargin: 24
                spacing: 8

                Repeater {
                    model: taskErrorDialog.buttons
                    Button {
                        text: modelData.text
                        highlighted: index === taskErrorDialog.buttons.length - 1
                        onClicked: {
                            errorDialog.onButtonClicked(modelData.id)
                            taskErrorDialog.close()
                        }
                    }
                }
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
            anchors.fill: parent
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical.policy: ScrollBar.AlwaysOn

            Text {
                width: changelogDialog.width - 48
                text: changelogDialog.changelogText
                wrapMode: Text.Wrap
                font.pixelSize: 14
                lineHeight: 1.5
                color: sysPalette.windowText
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
            anchors.fill: parent
            clip: true
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ScrollBar.vertical.policy: ScrollBar.AsNeeded

            Column {
                width: migrationDialog.width - 48
                spacing: 8
                topPadding: 8
                bottomPadding: 8

                Repeater {
                    model: migrationDialog.messages

                    delegate: Row {
                        spacing: 6
                        width: parent.width

                        Text {
                            text: modelData.level === "warning" ? "⚠️" : "ℹ️"
                            font.pixelSize: 13
                            color: modelData.level === "warning" ? "#e65100" : sysPalette.windowText
                            verticalAlignment: Text.AlignTop
                        }

                        Text {
                            width: parent.width - 26
                            text: {
                                var versionInfo = ""
                                if (modelData.oldVersion && modelData.newVersion)
                                    versionInfo = "（" + modelData.oldVersion + " → " + modelData.newVersion + "）"
                                return versionInfo + modelData.text
                            }
                            wrapMode: Text.Wrap
                            font.pixelSize: 13
                            lineHeight: 1.4
                            color: sysPalette.windowText
                        }
                    }
                }
            }
        }
    }

    SplashOverlay { visible: splash.gradioUrl.length === 0 }

    WebEngineView {
        id: webView
        anchors.fill: parent
        url: splash.gradioUrl
        visible: splash.gradioUrl.length > 0

        onLoadingChanged: function(loadRequest) {
            if (loadRequest.status === WebEngineView.LoadFailedStatus) {
                loadError.text = "加载失败，请检查 Gradio 服务是否正常运行。\nURL: " + splash.gradioUrl
            }
        }
    }

    LoadingOverlay {
        loadingProgress: webView.loadingProgress
        visible: splash.gradioUrl.length > 0 && webView.loadingProgress < 100
    }

    Text {
        id: loadError
        anchors.centerIn: parent
        text: ""
        color: "#d32f2f"
        font.pixelSize: 14
        horizontalAlignment: Text.AlignHCenter
        visible: text.length > 0 && webView.loadingProgress < 100
        z: 100
    }
}
