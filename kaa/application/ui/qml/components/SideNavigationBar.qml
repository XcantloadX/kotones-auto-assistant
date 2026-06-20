import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    width: 200
    color: "transparent"

    property var model: []
    property int currentIndex: 0
    property int previousIndex: 0
    signal currentChanging(int index, int previousIndex)

    function confirmSwitch(index) {
        root.currentIndex = index
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.topMargin: 6
        anchors.bottomMargin: 12
        anchors.leftMargin: 8
        anchors.rightMargin: 8
        spacing: 12

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 82
            color: "transparent"

            MouseArea {
                anchors.fill: parent
                onPressed: window.startSystemMove()
            }

            RowLayout {
                anchors.fill: parent
                spacing: 10

                Rectangle {
                    Layout.preferredWidth: 66
                    Layout.preferredHeight: 66
                    radius: 22
                    color: "transparent"
                    clip: true

                    Image {
                        anchors.fill: parent
                        anchors.margins: 2
                        source: "file:///" + splash.iconPath
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Label {
                        Layout.fillWidth: true
                        text: "琴音小助手"
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                        color: palette.text
                        verticalAlignment: Text.AlignVCenter
                    }

                    Label {
                        Layout.fillWidth: true
                        text: "版本 v" + splash.appVersion
                        font.pixelSize: 12
                        color: palette.placeholderText
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }

        ListView {
            id: listView
            Layout.fillWidth: true
            Layout.fillHeight: true
            model: root.model
            spacing: 4
            interactive: false

            delegate: ItemDelegate {
                width: listView.width
                height: 40
                text: modelData
                font.pixelSize: 14
                highlighted: root.currentIndex === index

                onClicked: {
                    root.previousIndex = root.currentIndex
                    root.currentChanging(index, root.previousIndex)
                }
            }
        }
    }
}
