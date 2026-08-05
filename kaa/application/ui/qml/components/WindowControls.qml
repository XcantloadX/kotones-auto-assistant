import QtQuick
import QtQuick.Controls
import QtQuick.Window
import ".." as App

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

    property bool _maxHoveredByOS: false

    Connections {
        target: (Qt.platform.os === "windows" && typeof maxHoverBridge !== "undefined")
            ? maxHoverBridge : null
        function onHoveredChanged(hovered) { root._maxHoveredByOS = hovered }
    }

    // ── Minimize ─────────────────────────────────────────────────────────
    Rectangle {
        width: 46; height: root.height
        color: _minHover.containsMouse
            ? App.AppTheme.hover
            : "transparent"
        FluentIcon {
            anchors.centerIn: parent
            glyph: App.FluentIcons.subtract_20_regular
        }
        MouseArea {
            id: _minHover
            anchors.fill: parent
            hoverEnabled: true
            onClicked: root.minimizeRequested()
        }
    }

    // ── Maximize / Restore ───────────────────────────────────────────────
    Rectangle {
        width: 46; height: root.height
        readonly property bool _hovered: Qt.platform.os === "windows"
            ? root._maxHoveredByOS
            : _maxHover.containsMouse
        color: _hovered
            ? App.AppTheme.hover
            : "transparent"
        FluentIcon {
            anchors.centerIn: parent
            glyph: root.window.visibility === Window.Maximized
                ? App.FluentIcons.square_multiple_20_regular
                : App.FluentIcons.maximize_20_regular
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

    // ── Close ────────────────────────────────────────────────────────────
    Rectangle {
        width: 46; height: root.height
        color: _closeHover.containsMouse ? "#c42b1c" : "transparent"
        FluentIcon {
            anchors.centerIn: parent
            glyph: App.FluentIcons.dismiss_20_regular
            color: _closeHover.containsMouse ? "white" : App.AppTheme.fg
        }
        MouseArea {
            id: _closeHover
            anchors.fill: parent
            hoverEnabled: true
            onClicked: root.closeRequested()
        }
    }
}
