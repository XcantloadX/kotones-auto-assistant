import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    visible: false

    readonly property int _duration: 4000
    readonly property int _maxCount: 5

    readonly property bool _dark: Application.styleHints.colorScheme === Qt.Dark

    function show(kind, text) {
        if (toastModel.count >= root._maxCount)
            toastModel.remove(0)
        toastModel.append({ kind: kind, text: text })
    }

    function removeToast(index) {
        toastModel.remove(index)
    }

    Connections {
        target: Notice
        function onShowNotification(kind, text) { root.show(kind, text) }
    }

    ListModel { id: toastModel }

    ListView {
        parent: Overlay.overlay
        anchors.right: parent.right
        anchors.rightMargin: 24
        anchors.top: parent.top
        anchors.topMargin: 24
        width: 340
        height: contentHeight
        spacing: 8
        model: toastModel
        interactive: false

        add: Transition {
            NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 220; easing.type: Easing.OutCubic }
            NumberAnimation { property: "x"; from: 32; to: 0; duration: 220; easing.type: Easing.OutCubic }
        }
        remove: Transition {
            NumberAnimation { property: "opacity"; from: 1; to: 0; duration: 160; easing.type: Easing.InCubic }
            NumberAnimation { property: "x"; from: 0; to: 32; duration: 160; easing.type: Easing.InCubic }
        }
        displaced: Transition {
            NumberAnimation { properties: "x,y"; duration: 200; easing.type: Easing.OutCubic }
        }

        delegate: Item {
            required property int index
            required property string kind
            required property string text

            width: 340
            height: toastCard.implicitHeight

            readonly property color accentColor: {
                switch (toastItem.kind) {
                    case "success": return root._dark ? "#6ccb5f" : "#107c10"
                    case "warning": return root._dark ? "#fce100" : "#c05a00"
                    case "error":   return root._dark ? "#ff99a4" : "#c42b1c"
                    default:        return root._dark ? "#60cdff" : "#0067c0"
                }
            }
            readonly property color iconColor: accentColor
            readonly property string icon: {
                switch (toastItem.kind) {
                    case "success": return "\uF298"
                    case "warning": return "\uF869"
                    case "error":   return "\uF3F1"
                    default:        return "\uF4A3"
                }
            }

            Timer {
                interval: root._duration
                running: true
                onTriggered: root.removeToast(toastItem.index)
            }

            Rectangle {
                id: toastCard
                width: parent.width
                implicitHeight: contentRow.implicitHeight + 20
                radius: 6
                color: root._dark ? "#2d2d2d" : "#ffffff"
                border.color: root._dark ? Qt.rgba(1,1,1,0.12) : Qt.rgba(0,0,0,0.12)
                border.width: 1

                Rectangle {
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    anchors.margins: 1
                    width: 3
                    radius: 2
                    color: toastItem.accentColor
                }

                RowLayout {
                    id: contentRow
                    anchors.left: parent.left
                    anchors.leftMargin: 14
                    anchors.right: parent.right
                    anchors.rightMargin: 6
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 8

                    Label {
                        text: toastItem.icon
                        color: toastItem.iconColor
                        font.family: "FluentSystemIcons-Regular"
                        font.pixelSize: 16
                        Layout.alignment: Qt.AlignVCenter
                    }

                    Label {
                        Layout.fillWidth: true
                        text: toastItem.text
                        color: root._dark ? "#ffffff" : "#000000"
                        wrapMode: Text.Wrap
                        font.pixelSize: 13
                        lineHeightMode: Text.ProportionalHeight
                        lineHeight: 1.3
                    }

                    Item {
                        Layout.preferredWidth: 24
                        Layout.preferredHeight: 24
                        Layout.alignment: Qt.AlignVCenter

                        Rectangle {
                            anchors.fill: parent
                            radius: 4
                            color: closeMouse.containsMouse
                                ? (root._dark ? Qt.rgba(1,1,1,0.08) : Qt.rgba(0,0,0,0.08))
                                : "transparent"
                        }

                        Label {
                            anchors.centerIn: parent
                            text: "\uF369"
                            font.family: "FluentSystemIcons-Regular"
                            font.pixelSize: 12
                            color: closeMouse.containsMouse
                                ? (root._dark ? "#ffffff" : "#000000")
                                : (root._dark ? Qt.rgba(1,1,1,0.45) : Qt.rgba(0,0,0,0.45))
                        }

                        MouseArea {
                            id: closeMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.removeToast(toastItem.index)
                        }
                    }
                }
            }
        }
    }
}
