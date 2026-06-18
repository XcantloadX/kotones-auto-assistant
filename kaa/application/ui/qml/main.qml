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
