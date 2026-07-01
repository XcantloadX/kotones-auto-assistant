import QtQuick
import QtQuick.Controls
import QtQuick.Window

// 窗口控件（最小化 / 最大化 / 关闭）。
// hit-test 布局（从右到左，各 46px）：
//   close    → HTCLIENT（QML 处理点击 + hover）
//   maximize → HTMAXBUTTON（OS 处理贴靠布局弹窗 + 最大化/还原；
//              hover 由 maxHoverBridge 中转）
//   minimize → HTCLIENT（QML 处理点击 + hover）
Row {
    id: root

    signal minimizeRequested()
    signal closeRequested()

    required property var window

    visible: Qt.platform.os === "windows"
    spacing: 0

    readonly property color _hover: Application.styleHints.colorScheme === Qt.Light
        ? Qt.rgba(0,0,0,0.08) : Qt.rgba(1,1,1,0.08)
    readonly property color _fg:   Application.styleHints.colorScheme === Qt.Light ? "#000000" : "#ffffff"

    readonly property string _iconFont: "FluentSystemIcons-Regular"
    property bool _maxHoveredByOS: false

    Connections {
        target: (Qt.platform.os === "windows" && typeof maxHoverBridge !== "undefined")
            ? maxHoverBridge : null
        function onHoveredChanged(hovered) { root._maxHoveredByOS = hovered }
    }

    // ── Minimize（FluentSystemIcons subtract_20 = \uEBD0）──────────────────
    Rectangle {
        width: 46; height: root.height
        color: _minHover.containsMouse
            ? root._hover
            : "transparent"
        Text {
            anchors.centerIn: parent
            font.family: root._iconFont
            font.pixelSize: 16
            text: "\uEBD0"
            color: root._fg
        }
        MouseArea {
            id: _minHover
            anchors.fill: parent
            hoverEnabled: true
            onClicked: root.minimizeRequested()
        }
    }

    // ── Maximize / Restore（maximize_20 = \uE7EB / square_multiple_20 = \uEB96）──
    Rectangle {
        width: 46; height: root.height
        readonly property bool _hovered: Qt.platform.os === "windows"
            ? root._maxHoveredByOS
            : _maxHover.containsMouse
        color: _hovered
            ? root._hover
            : "transparent"
        Text {
            anchors.centerIn: parent
            font.family: root._iconFont
            font.pixelSize: 16
            text: root.window.visibility === Window.Maximized ? "\uEB96" : "\uE7EB"
            color: root._fg
        }
        MouseArea {
            id: _maxHover
            anchors.fill: parent
            hoverEnabled: Qt.platform.os !== "windows"
            enabled:      Qt.platform.os !== "windows"
            onClicked: {
                if (root.window.visibility === Window.Maximized) root.window.showNormal()
                else root.window.showMaximized()
            }
        }
    }

    // ── Close（FluentSystemIcons dismiss_20 = \uF369）─────────────────
    Rectangle {
        width: 46; height: root.height
        color: _closeHover.containsMouse ? "#c42b1c" : "transparent"
        Text {
            anchors.centerIn: parent
            font.family: root._iconFont
            font.pixelSize: 16
            text: "\uF369"
            color: _closeHover.containsMouse ? "white" : root._fg
        }
        MouseArea {
            id: _closeHover
            anchors.fill: parent
            hoverEnabled: true
            onClicked: root.closeRequested()
        }
    }
}
