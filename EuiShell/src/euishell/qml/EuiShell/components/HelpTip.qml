import QtQuick
import QtQuick.Controls
import QtQuick.Effects

Control {
    id: root
    implicitWidth: 18
    implicitHeight: 18

    property string richText: ""
    property int maxPopupWidth: 360
    property int openDelay: 220
    property int closeDelay: 140
    readonly property bool hovering: iconMouse.containsMouse || popupMouse.containsMouse

    function updatePopupPosition() {
        if (!tipPopup.parent) {
            return;
        }
        var p = root.mapToItem(tipPopup.parent, 0, root.height + 6);
        tipPopup.x = p.x;
        tipPopup.y = p.y;
    }

    function withAlpha(c, a) {
        return Qt.rgba(c.r, c.g, c.b, a)
    }

    onHoveringChanged: {
        if (!richText || richText.length === 0) {
            openTimer.stop();
            closeTimer.stop();
            return;
        }
        if (hovering) {
            closeTimer.stop();
            openTimer.restart();
        } else {
            openTimer.stop();
            closeTimer.restart();
        }
    }

    Timer {
        id: openTimer
        interval: root.openDelay
        repeat: false
        onTriggered: {
            root.updatePopupPosition();
            tipPopup.open();
        }
    }

    Timer {
        id: closeTimer
        interval: root.closeDelay
        repeat: false
        onTriggered: tipPopup.close()
    }

    Rectangle {
        anchors.fill: parent
        radius: width / 2
        color: iconMouse.containsMouse ? root.palette.accent : "#A0A0A0"

        Text {
            anchors.centerIn: parent
            text: "?"
            color: root.palette.window
            font.pixelSize: 12
            font.bold: true
        }
    }

    MouseArea {
        id: iconMouse
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
    }

    Popup {
        id: tipPopup
        parent: Overlay.overlay
        width: Math.min(root.maxPopupWidth, contentLabel.implicitWidth + leftPadding + rightPadding)
        padding: 10
        modal: false
        focus: false
        closePolicy: Popup.NoAutoClose

        background: Rectangle {
            color: root.palette.toolTipBase
            radius: 6
            border.color: root.palette.mid
            border.width: 1
        }

        contentItem: Label {
            id: contentLabel
            width: Math.min(root.maxPopupWidth - tipPopup.leftPadding - tipPopup.rightPadding, implicitWidth)
            wrapMode: Text.Wrap
            textFormat: Text.RichText
            text: root.richText
            color: root.palette.toolTipText
            lineHeight: 1.2
            font.pixelSize: 13
        }

        MouseArea {
            id: popupMouse
            anchors.fill: parent
            hoverEnabled: true
            acceptedButtons: Qt.NoButton
        }

        onOpened: root.updatePopupPosition()
        onWidthChanged: root.updatePopupPosition()
    }
}
