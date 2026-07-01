import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    Layout.fillWidth: true
    property string style: "info"
    property string title: ""
    property string content: ""

    readonly property var _colors: ({
        info:    { bg: "#E3F2FD", border: "#BBDEFB" },
        tip:     { bg: "#E8F5E9", border: "#C8E6C9" },
        warning: { bg: "#FFF3E0", border: "#FFE0B2" },
        error:   { bg: "#FFEBEE", border: "#FFCDD2" }
    })

    color: (_colors[style] ?? _colors.info).bg
    border.color: (_colors[style] ?? _colors.info).border
    border.width: 1
    radius: 4
    implicitHeight: layout.implicitHeight + 24

    ColumnLayout {
        id: layout
        anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
        spacing: 4
        Label {
            text: root.title
            font.weight: Font.DemiBold
            visible: root.title.length > 0
            Layout.fillWidth: true
        }
        Label {
            text: root.content
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
    }
}
