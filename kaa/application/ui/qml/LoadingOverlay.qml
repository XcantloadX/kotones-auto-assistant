import QtQuick
import QtQuick.Controls

Rectangle {
    property int loadingProgress: 0

    anchors.fill: parent

    SystemPalette { id: sysPalette }

    color: sysPalette.window

    Column {
        anchors.centerIn: parent
        spacing: 16

        BusyIndicator {
            anchors.horizontalCenter: parent.horizontalCenter
            running: true
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: splash.statusText.length > 0 ? splash.statusText : "正在加载琴音小助手..."
            color: sysPalette.windowText
            font.pixelSize: 16
        }

        ProgressBar {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 300
            from: 0
            to: 100
            value: loadingProgress || 0
        }
    }
}
