import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// 独立页面的标题行：返回按钮 + 图标 + 标题文本 + 可拖动填充区。
// 由 TitleBar 在 prefsMode 时切入。
Item {
    id: root

    property string title: ""
    property string iconSource: ""

    signal backRequested()

    // 供 TitleBar 同步给 Win32 hit-test：返回按钮右边界即交互区终点
    readonly property real interactiveEnd: backBtn.width + 4

    readonly property color _fg:    Application.styleHints.colorScheme === Qt.Light ? "#000000" : "#ffffff"
    readonly property color _hover: Application.styleHints.colorScheme === Qt.Light ? Qt.rgba(0,0,0,0.08) : Qt.rgba(1,1,1,0.08)

    RowLayout {
        anchors.fill: parent
        spacing: 0

        // ── 返回按钮 ──────────────────────────────────────────
        Item {
            id: backBtn
            Layout.preferredWidth: 40
            Layout.fillHeight: true

            HoverHandler { id: backHover }

            Rectangle {
                anchors.fill: parent
                anchors.margins: 4
                radius: 5
                color: backHover.hovered ? root._hover : "transparent"
            }

            Text {
                anchors.centerIn: parent
                font.family: "FluentSystemIcons-Regular"
                font.pixelSize: 13
                text: "\uF2AA"   // chevron_left_20
                color: root._fg
            }

            MouseArea {
                anchors.fill: parent
                onClicked: root.backRequested()
                onPressed: event => event.accepted = true
            }
        }

        // ── 图标 + 标题（其余区域均可拖动窗口）────────────────
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            MouseArea {
                anchors.fill: parent
                onPressed: function(event) {
                    event.accepted = true
                    ApplicationWindow.window.startSystemMove()
                }
            }

            Row {
                anchors.verticalCenter: parent.verticalCenter
                anchors.left: parent.left
                anchors.leftMargin: 6
                spacing: 10

                Item {
                    width: 16; height: 16

                    Image {
                        anchors.fill: parent
                        source: root.iconSource
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        visible: status === Image.Ready
                    }
                }

                Text {
                    text: root.title
                    color: root._fg
                    font.pixelSize: 12
                }
            }
        }
    }
}
