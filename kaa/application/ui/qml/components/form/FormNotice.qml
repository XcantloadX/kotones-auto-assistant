import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root
    Layout.fillWidth: true
    property string style: "info"
    property string title: ""
    property string content: ""

    readonly property bool _dark: Application.styleHints.colorScheme === Qt.Dark

    readonly property var _lightColors: ({
        info:    { bg: "#E3F2FD", border: "#BBDEFB" },
        tip:     { bg: "#E8F5E9", border: "#C8E6C9" },
        warning: { bg: "#FFF3E0", border: "#FFE0B2" },
        error:   { bg: "#FFEBEE", border: "#FFCDD2" }
    })

    readonly property var _darkColors: ({
        info:    { bg: "#0D2137", border: "#1A3A5C" },
        tip:     { bg: "#0D2818", border: "#1A3D28" },
        warning: { bg: "#2C1B0D", border: "#4A2E14" },
        error:   { bg: "#2D0D0D", border: "#5C1A1A" }
    })

    readonly property var _palette: root._dark ? _darkColors : _lightColors

    color: (_palette[style] ?? _palette.info).bg
    border.color: (_palette[style] ?? _palette.info).border
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
