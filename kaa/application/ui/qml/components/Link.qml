import QtQuick

Item {
    id: root
    width: labelText.implicitWidth + 12
    height: labelText.implicitHeight + 6

    property url href: ""
    property string label

    Rectangle {
        anchors.fill: parent
        radius: 4
        color: "transparent"
    }

    Rectangle {
        anchors.fill: parent
        radius: 4
        color: "black"
        opacity: mouseArea.containsMouse ? 0.06 : 0.0

        Behavior on opacity {
            NumberAnimation { duration: 100 }
        }
    }

    Text {
        id: labelText
        anchors.centerIn: parent
        text: root.label
        color: mouseArea.containsMouse ? "#1a73e8" : "#2d6cdf"
        font.underline: mouseArea.containsMouse
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor

        onClicked: {
            if (root.href !== "")
                Qt.openUrlExternally(root.href)
        }
    }
}
