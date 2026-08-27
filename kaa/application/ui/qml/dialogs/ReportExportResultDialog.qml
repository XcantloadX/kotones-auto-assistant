import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Dialog {
    id: root

    property string message: ""

    modal: true
    title: "导出报告"
    standardButtons: Dialog.Ok
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    parent: Overlay.overlay
    anchors.centerIn: Overlay.overlay
    width: Math.min(520, Overlay.overlay ? Overlay.overlay.width - 80 : 520)

    contentItem: ColumnLayout {
        spacing: 12

        Label {
            text: root.message
            wrapMode: Text.Wrap
            Layout.fillWidth: true
        }
    }
}
