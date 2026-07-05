import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    anchors.fill: parent

    SystemPalette { id: sysPalette }

    color: sysPalette.window

    Column {
        anchors.centerIn: parent
        spacing: 24

        Image {
            anchors.horizontalCenter: parent.horizontalCenter
            source: "file:///" + splash.iconPath
            width: 120
            height: 120
            fillMode: Image.PreserveAspectFit
            smooth: true
            visible: splash.iconPath.length > 0
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "琴音小助手"
            color: sysPalette.windowText
            font.pixelSize: 36
            font.weight: Font.DemiBold
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "v" + splash.appVersion
            color: sysPalette.windowText
            opacity: 0.45
            font.pixelSize: 15
        }

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: splash.statusText
            color: sysPalette.windowText
            opacity: 0.6
            font.pixelSize: 15
        }

        BusyIndicator {
            anchors.horizontalCenter: parent.horizontalCenter
            running: !splash.ready
            implicitWidth: 48
            implicitHeight: 48
        }

        // ── Game data download progress ──────────────────────────────
        GridLayout {
            visible: splash.gameDataActive && splash.downloadFiles.length > 0
            columns: 5
            columnSpacing: 8
            rowSpacing: 6

            // ── 列头 ──
            Text { text: "文件名";  Layout.preferredWidth: 180; Layout.preferredHeight: 28; font.pixelSize: 12; opacity: 0.55; color: sysPalette.windowText; verticalAlignment: Text.AlignVCenter }
            Text { text: "进度";   Layout.preferredWidth: 52;  Layout.preferredHeight: 28; font.pixelSize: 12; opacity: 0.55; color: sysPalette.windowText; verticalAlignment: Text.AlignVCenter; horizontalAlignment: Text.AlignRight }
            Item {                 Layout.preferredWidth: 160; Layout.preferredHeight: 28 }
            Text { text: "速度";   Layout.preferredWidth: 90;  Layout.preferredHeight: 28; font.pixelSize: 12; opacity: 0.55; color: sysPalette.windowText; verticalAlignment: Text.AlignVCenter; horizontalAlignment: Text.AlignRight }
            Text { text: "大小";   Layout.preferredWidth: 126; Layout.preferredHeight: 28; font.pixelSize: 12; opacity: 0.55; color: sysPalette.windowText; verticalAlignment: Text.AlignVCenter; horizontalAlignment: Text.AlignHCenter }

            // ── 数据行 ──
            Repeater {
                model: splash.downloadFiles

                delegate: GridLayout {
                    columns: 5
                    columnSpacing: 8
                    Layout.columnSpan: 5
                    Layout.preferredHeight: 28

                    Text {
                        text: modelData.fileName || ""
                        color: sysPalette.windowText
                        Layout.preferredWidth: 180
                        Layout.fillHeight: true
                        elide: Text.ElideRight
                        font.pixelSize: 13
                        verticalAlignment: Text.AlignVCenter
                    }
                    Text {
                        text: (modelData.percent || 0).toFixed(1) + "%"
                        color: sysPalette.windowText
                        opacity: 0.7
                        font.pixelSize: 13
                        Layout.preferredWidth: 52
                        Layout.fillHeight: true
                        horizontalAlignment: Text.AlignRight
                        verticalAlignment: Text.AlignVCenter
                    }
                    ProgressBar {
                        Layout.preferredWidth: 160
                        Layout.alignment: Qt.AlignVCenter
                        from: 0; to: 100
                        value: modelData.percent || 0
                    }
                    Text {
                        text: modelData.speedText || "—"
                        color: sysPalette.windowText
                        opacity: 0.7
                        font.pixelSize: 13
                        Layout.preferredWidth: 90
                        Layout.fillHeight: true
                        horizontalAlignment: Text.AlignRight
                        verticalAlignment: Text.AlignVCenter
                    }
                    Text {
                        text: modelData.sizeText || "—"
                        color: sysPalette.windowText
                        opacity: 0.7
                        font.pixelSize: 13
                        Layout.preferredWidth: 126
                        Layout.fillHeight: true
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
    }
}
